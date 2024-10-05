import os
import json
import argparse
import shutil
from pathlib import Path
from collections import defaultdict

from pg_config import get_work_dir


# HOME = os.path.expanduser("~")
WD = get_work_dir()


class CellInfo(object):
    def __init__(self, content: str, span: int = 1):
        self.content = content
        self.span = span

    def to_json(self):
        return {"content": self.content, "colspan": self.span}


class RowInfo(object):
    def __init__(self, row_id: int, header: bool = False):
        self.row_id = row_id
        self.header = header
        self.row = []

    def add_cell(self, cell: CellInfo):
        self.row.append(cell)

    def to_json(self):
        return [ci.to_json() for ci in self.row]


class TableInfo(object):
    def __init__(self, table_name: str):
        self.table_name = table_name
        self.rows = []

    def add_row(self, row: RowInfo):
        self.rows.append(row)

    def to_json(self):
        return {"name": self.table_name,
                "rows": [ri.to_json() for ri in self.rows]}

    def get_num_cols(self):
        max_col = 0
        min_col = 1000
        for row in self.rows:
            total = sum(cell.span for cell in row.row)
            max_col = max(total, max_col)
            min_col = min(total, min_col)
        if min_col != max_col:
            print(f"{self.table_name} min_col: {min_col} max_col: {max_col}")
        return max_col

    def make_homogeneous(self):
        num_cols = self.get_num_cols()
        for ri in self.rows:
            if len(ri.row) < num_cols:
                for _ in range(len(ri.row), num_cols):
                    ri.add_cell(CellInfo(""))


def is_empty_row(_row: list[str]) -> bool:
    for item in _row:
        if item.strip() != '':
            return False
    return True


def load_table_info(table_info_json_fpath: Path) -> TableInfo:
    with open(table_info_json_fpath) as f:
        data = json.load(f)
        table_name = table_info_json_fpath.name.replace(".json", "")
        ti = TableInfo(table_name)
        row_idx = 0
        for rj in data["rows"]:
            ri = RowInfo(row_idx)
            empty = True
            for cj in rj:
                content = cj['content']
                if len(content.strip()) > 0:
                    empty = False
                col_span = int(cj['colspan'])
                ri.add_cell(CellInfo(content, col_span))
            if not empty:
                ti.add_row(ri)
                row_idx += 1
        return ti


def save_table_info(ti: TableInfo, out_json_path: Path):
    with open(out_json_path, 'w') as f:
        json.dump( ti.to_json(), f, indent=2)
        print(f"saved {out_json_path}")


def to_bow(ti: TableInfo) -> set[str]:
    bow_set = set()
    for ri in ti.rows:
        for ci in ri.row:
            bow_set.update(ci.content.split())
    return bow_set


def are_tables_similar(ti: TableInfo, gs_bow_set: set[str]) -> bool:
    if len(ti.rows) <= 1:
        return False
    ti_bow_set = to_bow(ti)
    if len(ti_bow_set) == 0:
        return False
    common_set = set.intersection(ti_bow_set, gs_bow_set)
    coverage = len(common_set) / len(ti_bow_set)
    return coverage > 0.4


def load_table_infos(tei_tables_dir: Path) -> dict[str, list[TableInfo]]:
    paper_2ti_list_map = defaultdict(list)
    json_paths = tei_tables_dir.glob("*.json")
    for json_path in json_paths:
        tokens = json_path.name.split('_')
        paper_id = "{}_{}".format(tokens[0], tokens[1])
        ti = load_table_info(json_path)
        paper_2ti_list_map[paper_id].append(ti)
    return paper_2ti_list_map


def convert_extractor_to_table_infos(extractor_json_fpath) -> tuple[str, list[TableInfo]]:
    with open(extractor_json_fpath) as f:
        data = json.load(f)
    paper_id = data["paper_id"]
    ti_list = []
    for page in data["result"]["pages"]:
        page_no = int(page["page"])
        table_idx = 1
        for tj in page["tables"]:
            name = "{}_page_{}_table_{}".format(paper_id, page_no, table_idx)
            ti = TableInfo(name)
            ti_list.append(ti)
            row_idx = 0
            for rj in tj["rows"]:
                if is_empty_row(rj):
                    continue
                ri = RowInfo(row_idx)
                ti.add_row(ri)
                for cj in rj:
                    ri.add_cell(CellInfo(cj))
                row_idx += 1
    return paper_id, ti_list


def align_grobid_tables_2_gs(grobid_tables_dir: Path, gs_root: Path):
    grobid_table_map = load_table_infos(grobid_tables_dir)
    gs_table_map = load_table_infos(gs_root)
    # gs_json_paths = gs_root.glob("*.json")
    # for gs_json_path in gs_json_paths:
    #    paper_id, ti_list = convert_extractor_to_table_infos(gs_json_path)
    #    gs_table_map[paper_id].extend(ti_list)
    matched_grobid_table_map = defaultdict(list)
    for paper_id, gs_ti_list in gs_table_map.items():
        if paper_id not in grobid_table_map:
            continue
        ti_list = grobid_table_map[paper_id]
        seen_set = set()
        for gs_ti in gs_ti_list:
            gs_bow_set = to_bow(gs_ti)
            for ti in ti_list:
                if ti in seen_set:
                    continue
                if are_tables_similar(ti, gs_bow_set):
                    ti.table_name = gs_ti.table_name
                    ti.make_homogeneous()
                    matched_grobid_table_map[paper_id].append(ti)
                    seen_set.add(ti)
    return matched_grobid_table_map


def convert_extractor_to_table_json(extractor_json_fpath, out_dir: Path, prefix="sampled_pdfs_"):
    with open(extractor_json_fpath) as f:
        data = json.load(f)
    paper_id = data["paper_id"]
    if prefix:
        paper_id = paper_id.replace(prefix, '')
    for page in data["result"]["pages"]:
        page_no = int(page["page"])
        table_idx = 1
        for tj in page["tables"]:
            name = "{}_page_{}_table_{}".format(paper_id, page_no, table_idx)
            table_json = {"name": name, "rows": []}
            fname = "{}.json".format(name)
            for rj in tj["rows"]:
                if is_empty_row(rj):
                    continue
                row = []
                for cj in rj:
                    row.append({"colspan": 1, "content": cj})
                table_json['rows'].append(row)
            out_path = out_dir / fname
            with open(out_path, 'w') as f:
                json.dump(table_json, f, indent=2)
                print(f"wrote {out_path}")
            table_idx += 1


def convert_main_pipeline_result():
    in_root = Path(WD, "data/table_content_extract/bundle/bioarxiv_extracted_key_resources_tables_sampled")
    out_root = Path("/tmp/bioarxiv_extracted_key_resources_tables_sampled_table_json")
    out_root.mkdir(parents=True, exist_ok=True)
    in_json_paths = in_root.glob("*.json")
    for in_json_path in in_json_paths:
        convert_extractor_to_table_json(in_json_path, out_root)


def convert_main_pipeline_merged_result():
    in_root = Path(WD, "data/table_content_extract/bundle/bioarxiv_main_merged")
    out_root = Path("/tmp/bioarxiv_main_merged_table_json")
    out_root.mkdir(parents=True, exist_ok=True)
    in_json_paths = in_root.glob("*.json")
    for in_json_path in in_json_paths:
        convert_extractor_to_table_json(in_json_path, out_root)


def convert_main_pipeline_with_row_info_result():
    ref_root = Path(WD, "data/table_content_extract/bundle/bioarxiv_extracted_key_resources_tables_sampled")
    in_root = Path(WD, "data/table_content_extract/bundle/extracted_key_resources_tables_with_row_info_sampled_v2")
    out_root = Path("/tmp/bioarxiv_extracted_key_resources_tables_with_row_info_sampled_table_json")
    out_root.mkdir(parents=True, exist_ok=True)
    ref_json_path_map = {rfp.name: rfp for rfp in ref_root.glob("*.json")}
    in_json_paths = in_root.glob("*.json")
    for in_json_path in in_json_paths:
        if in_json_path.name not in ref_json_path_map:
            continue
        convert_extractor_to_table_json(in_json_path, out_root)


def convert_ocr_pipeline_result():
    ref_root = Path(WD, "data/table_content_extract/bundle/bioarxiv_extracted_key_resources_tables_sampled")
    in_root = Path(WD, "data/table_content_extract/bundle/bioarxiv_extracted_key_resources_tables_sampled_ocr")
    out_root = Path("/tmp/bioarxiv_extracted_key_resources_tables_sampled_ocr_table_json")
    out_root.mkdir(parents=True, exist_ok=True)
    ref_json_path_map = {rfp.name: rfp for rfp in ref_root.glob("*.json")}
    in_json_paths = in_root.glob("*.json")
    for in_json_path in in_json_paths:
        if in_json_path.name not in ref_json_path_map:
            continue
        convert_extractor_to_table_json(in_json_path, out_root)


def prep_main_pipeline_gs_sampled_pdfs(out_dir: Path):
    ref_root = Path(WD, "data/table_content_extract/bundle/bioarxiv_extracted_key_resources_tables_sampled")
    pdf_dir = Path(WD, "data/table_content_extract/bundle/pdfs")
    out_dir.mkdir(parents=True, exist_ok=True)
    ref_json_paths = list(ref_root.glob("*.json"))
    pdf_filename_set = set()
    for rjp in ref_json_paths:
        tokens = rjp.name.split('_')
        pdf_filename = "{}_{}.pdf".format(tokens[0], tokens[1])
        pdf_filename_set.add(pdf_filename)
    for pdf_filename in pdf_filename_set:
        print(pdf_filename)
    for in_pdf_path in pdf_dir.glob("*.pdf"):
        if in_pdf_path.name in pdf_filename_set:
            out_path = out_dir / in_pdf_path.name
            print(f"copying {in_pdf_path} to {out_path}")
            shutil.copyfile(in_pdf_path, out_path)


def convert_grobid_result():
    grobid_root = Path(WD, "data/table_content_extract/bundle/sampled_pdfs_grobid_tables")
    gs_root = Path(WD, "data/table_content_extract/gs_bioarxiv_extracted_key_resources_tables_sampled")
    out_dir = Path("/tmp/bioarxiv_extracted_key_resources_tables_sampled_grobid_table_json")
    out_dir.mkdir(parents=True, exist_ok=True)
    matched_map = align_grobid_tables_2_gs(grobid_root, gs_root)
    num_aligned = 0
    for paper_id, ti_list in matched_map.items():
        print(f"{paper_id} -> {len(ti_list)}")
        for ti in ti_list:
            out_path = out_dir / "{}.json".format(ti.table_name)
            save_table_info(ti, out_path)
            num_aligned += 1
    print(f"done.")
    print(f"num of aligned: {num_aligned}")


def cli():
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", required=True, metavar="<command one of [col_only, row_info, ocr, merged, grobid]>")
    args = parser.parse_args()
    cmd = args.c
    print(f"cmd: {cmd}")
    if cmd == 'col_only':
        convert_main_pipeline_result()
    elif cmd == 'row_info':
        convert_main_pipeline_with_row_info_result()
    elif cmd == 'ocr':
        convert_ocr_pipeline_result()
    elif cmd == 'merged':
        convert_main_pipeline_merged_result()
    elif cmd == 'grobid':
        convert_grobid_result()


if __name__ == '__main__':
    cli()



