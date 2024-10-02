import os
import re
import json
import subprocess
from pathlib import Path

from extract_tables_from_pdf import TableExtractor, pdf_to_images
from rel_table_pages_filter import RelevantTablePagesDetector

# global
HOME = os.path.expanduser('~')
WD = os.path.join(HOME, "dev/java/pdf_table_extractor")


def do_hybrid_table_content_extraction(_pdf_file_path, _struct_json_dir, _out_json_file,
                                       use_row_info=False):
    wd = os.getcwd()
    os.chdir(WD)
    script_path = "hybrid_table_content_extractor.sh"
    if use_row_info:
        subprocess.run(['bash', script_path, "-i", _pdf_file_path, '-o', _out_json_file,
                        '-s', _struct_json_dir, '-r'])
    else:
        subprocess.run(['bash', script_path, "-i", _pdf_file_path, '-o', _out_json_file, '-s', _struct_json_dir])
    os.chdir(wd)


class PDFTableExtractor(object):
    def __init__(self):
        self.tex = TableExtractor()
        self.detector = RelevantTablePagesDetector()

    def extract_table_contents_from_pdf(self, _pdf_file_path, _out_dir, out_table_root: Path):
        pages = self.detector.get_relevant_pages(_pdf_file_path)
        if len(pages) == 0:
            return None
        pdf_file_stem = Path(_pdf_file_path).stem
        im_out_dir = os.path.join(_out_dir, pdf_file_stem)
        Path(im_out_dir).mkdir(parents=True, exist_ok=True)
        image_files = pdf_to_images(_pdf_file_path, im_out_dir)
        page_ids = {p['page'] for p in pages}
        all_tables = {}
        for image_file in image_files:
            page_num = re.search(r"-(\d+)\.jpg", image_file).group(1)
            page_no = int(page_num) - 1
            if page_no in page_ids:
                tables = self.tex.extract_tables(image_file, out_dir=im_out_dir, prefix=pdf_file_stem)
                if tables:
                    all_tables[page_num] = tables
        if len(all_tables) == 0:
            return None
        result = {"paper_id": pdf_file_stem, "result": {"pages": []}}
        pages_list = result['result']['pages']
        for page_id, tables in all_tables.items():
            page_dict = {"page": int(page_id), "tables": []}
            pages_list.append(page_dict)
            tables_lst = page_dict['tables']
            for table in tables:
                table_dict = {"rows": []}
                tables_lst.append(table_dict)
                for row in table.rows:
                    r = []
                    for cell in row.cells:
                        r.append(cell.text)
                    table_dict['rows'].append(r)
        json_path = out_table_root / "{}_tables.json".format(pdf_file_stem)
        with open(json_path, 'w') as f:
            json.dump(result, f, indent=2)
            print(f'wrote {json_path}')

        return all_tables


if __name__ == '__main__':
    in_dir = Path(HOME, 'data/table_content_extract/bundle/sampled_pdfs')
    out_dir = Path("/tmp/pdf_table_extractor_ocr/cache")
    out_dir.mkdir(parents=True, exist_ok=True)
    tables_out_dir = Path("/tmp/bioarxiv_extracted_key_resources_tables_sampled_ocr")
    tables_out_dir.mkdir(parents=True, exist_ok=True)
    table_extractor = PDFTableExtractor()
    pdf_files = in_dir.glob("*.pdf")
    for pdf_file in pdf_files:
        table_extractor.extract_table_contents_from_pdf(pdf_file, out_dir, tables_out_dir)
    print("done.")