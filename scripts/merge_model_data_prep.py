import json
import os
import random
import shutil
import argparse
import string
from pathlib import Path
from tqdm import tqdm
import numpy as np


HOME = os.path.expanduser('~')


def extract_cell_contents(table_json_path):
    with open(table_json_path) as f:
        data = json.load(f)
    cells = []
    headers = data['headers']
    for header in headers:
        for col in header['columns']:
            content = col['content'].strip()
            if len(content) > 0:
                cells.append(content)
    rows = data['rows']
    for row in rows:
        for col in row:
            content = col['content'].strip()
            if len(content) > 0:
                cells.append(content)
    return cells


class CellInfo(object):
    def __init__(self, content: str, span: int = 1):
        self.content = content
        self.span = span


class RowInfo(object):
    def __init__(self, row_id: int, header: bool = False):
        self.row_id = row_id
        self.header = header
        self.row = []

    def add_cell(self, cell: CellInfo):
        self.row.append(cell)

    def get_col_at_idx(self, col_idx):
        offset = 0
        for cell in self.row:
            if offset <= col_idx < offset + cell.span:
                return cell
            offset += cell.span
        # return dummy empty cell
        return CellInfo('')


class TableInfo(object):
    def __init__(self, table_name: str):
        self.table_name = table_name
        self.rows = []

    def add_row(self, row: RowInfo):
        self.rows.append(row)

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


class RowStats(object):
    def __init__(self, table: TableInfo):
        self.num_rows = len(table.rows)
        lengths = []
        for row in table.rows:
            lengths.append(sum(len(c.content) for c in row.row))
        self.max_len = max(lengths)
        self.min_len = min(lengths)
        self.avg_len = np.average(lengths)
        self.std_len = np.std(lengths)
        self.median_len = np.median(lengths)

    def __str__(self):
        return f"# rows: {self.num_rows} avg: {self.avg_len} median: {self.median_len} std: {self.std_len} min: {self.min_len} max: {self.max_len}"


class ColStats(object):
    def __init__(self, col_idx: int, table: TableInfo):
        self.num_rows = len(table.rows)
        lengths = [len(row.get_col_at_idx(col_idx).content) for row in table.rows]
        self.max_len = max(lengths)
        self.min_len = min(lengths)
        self.avg_len = np.average(lengths)
        self.std_len = np.std(lengths)
        self.median_len = np.median(lengths)

    def __str__(self):
        return f"# rows: {self.num_rows} avg: {self.avg_len} median: {self.median_len} std: {self.std_len} min: {self.min_len} max: {self.max_len}"


class TableStats(object):
    def __init__(self, table: TableInfo):
        num_cols = table.get_num_cols()
        self.row_stats = RowStats(table)
        self.col_stats = [ColStats(col_idx, table) for col_idx in range(num_cols)]


class OFCell:
    def __init__(self, content: list[str], span: int = 1):
        self.content = content
        self.span = span


class OFRow:
    def __init__(self, row_idx: int):
        self.row_idx = row_idx
        self.columns = []

    def add_cell(self, cell: OFCell):
        self.columns.append(cell)

    def has_merged_cells(self):
        return any(len(col.content) > 1 for col in self.columns)


class OFTable:
    def __init__(self, table_name: str):
        self.table_name = table_name
        self.rows = []

    def add_row(self, row: OFRow):
        self.rows.append(row)


class CellLocation:
    def __init__(self, row_idx, col_idx, line_idx):
        self.row_idx = row_idx
        self.col_idx = col_idx
        self.line_idx = line_idx

    def to_json(self):
        return {'ridx': self.row_idx, 'cidx': self.col_idx, 'lidx': self.line_idx}

    @classmethod
    def from_json(cls, js_dict):
        return cls(int(js_dict['ridx']), int(js_dict['cidx']), int(js_dict['lidx']))


class MergeLocation:
    def __init__(self, table_name, first: CellLocation, second: CellLocation):
        self.table_name = table_name
        self.first = first
        self.second = second

    def to_json(self):
        return {'name': self.table_name, 'f': self.first.to_json(), 's': self.second.to_json()}

    @classmethod
    def from_json(cls, js_dict):
        first = CellLocation.from_json(js_dict['f'])
        second = CellLocation.from_json(js_dict['s'])
        return cls(js_dict['name'], first, second)


class Instance:
    def __init__(self, idx: int, line1: str, line2: str, label: int, location: MergeLocation):
        self.idx = idx
        self.line1 = line1
        self.line2 = line2
        self.label = label
        self.location = location

    def has_empty_line(self):
        return self.line1 == '' or self.line2 == ''

    def to_json(self):
        return {'idx': self.idx, 'l1': self.line1, 'l2': self.line2, 'label': self.label,
                'loc': self.location.to_json()}

    @classmethod
    def from_json(cls, js_dict):
        loc = MergeLocation.from_json(js_dict['loc'])
        return cls(int(js_dict['idx']), js_dict["l1"], js_dict["l2"], js_dict["label"], loc)


class TokenInfo:
    def __init__(self, tok: str, start: int):
        self.tok = tok
        self.start = start
        self.end = start + len(tok)

    def __str__(self):
        return f"<tok={self.tok} s:{self.start} e:{self.end}>"

    def __repr__(self):
        return self.__str__()


def tokenize(content: str) -> list[TokenInfo]:
    ti_list = []
    offset = 0
    in_ws = False
    for i, c in enumerate(content):
        if c in string.whitespace:
            if not in_ws:
                tok = content[offset:i]
                ti_list.append(TokenInfo(tok, offset))
                in_ws = True
        else:
            if in_ws:
                offset = i
                in_ws = False
    if len(ti_list) == 0:
        ti_list.append(TokenInfo(content, 0))
    elif offset < len(content):
        tok = content[offset:]
        tok = tok.rstrip()
        if len(tok) > 0:
            ti_list.append(TokenInfo(tok, offset))
    return ti_list


def split_to_lines(content: str, col_width: int):
    offset = 0
    lines = []
    cl = len(content)
    count = 0
    while True:
        end = min(cl, offset + col_width)
        lines.append(content[offset:end])
        offset += end - offset
        count += 1
        if end == cl:
            break
        if count > 10:
            break

    return lines


class ColumnConfig:
    def __init__(self, col_idx: int, col_width: int):
        self.col_idx = col_idx
        self.col_width = col_width

    def to_overflowed_rows(self, content):
        if len(content) < self.col_width:
            return [content]
        ti_list = tokenize(content)
        if len(ti_list) == 1:
            return split_to_lines(content, self.col_width)
        else:
            i = 0
            lines = []
            line = ""
            while i < len(ti_list):
                new_len = len(line) + len(ti_list[i].tok)
                if new_len <= self.col_width:
                    line += ti_list[i].tok + ' '
                else:
                    lines.append(line.rstrip())
                    line = ""
                    if len(ti_list[i].tok) <= self.col_width:
                        line = ti_list[i].tok + ' '
                    else:
                        tok_lines = split_to_lines(ti_list[i].tok, self.col_width)
                        lines.extend(tok_lines[:-1])
                        line = tok_lines[-1] + ' '
                i += 1
            if len(line.rstrip()) > 0:
                lines.append(line.rstrip())
            return [line.rstrip() for line in lines]


class TableCellMergeLabeledDataGen:
    def __init__(self, ti: TableInfo, table_stats: TableStats):
        self.ti = ti
        self.table_stats = table_stats


def load_table(table_file_path: Path) -> TableInfo:
    with open(table_file_path) as f:
        data = json.load(f)
    table_name = table_file_path.name.replace(".json", "")
    ti = TableInfo(table_name)
    row_idx = 0
    if "headers" in data:
        headers = data['headers']
        for header in headers:
            ri = RowInfo(row_idx, header=True)
            ti.add_row(ri)
            row_idx += 1
            for col in header['columns']:
                span = int(col['colspan'])
                content = col['content']
                ri.add_cell(CellInfo(content, span))
    for row in data['rows']:
        ri = RowInfo(row_idx, header=False)
        ti.add_row(ri)
        row_idx += 1
        for col in row:
            span = int(col['colspan'])
            content = col['content']
            ri.add_cell(CellInfo(content, span))
    return ti


def load_tables(in_dir: Path, max_tables=None) -> list[TableInfo]:
    table_paths = in_dir.glob("*.json")
    ti_list = []
    for i, table_path in enumerate(table_paths):
        ti = load_table(table_path)
        ti_list.append(ti)
        if max_tables and 0 < max_tables <= i:
            break
    return ti_list


def calc_stats(ti_list: list[TableInfo]) -> list[TableStats]:
    ts_list = []
    count = 0
    for ti in ti_list:
        ts = TableStats(ti)
        ts_list.append(ts)
        print(ti.table_name)
        print(ts.row_stats)
        for cs in ts.col_stats:
            print(f"\t{cs}")
        print('-' * 80)
        count += 1
    return ts_list


def prep_col_configs(table_stats: TableStats, max_table_width=80) -> list[ColumnConfig]:
    raw_col_lengths = [cs.avg_len + cs.std_len for cs in table_stats.col_stats]
    raw_total = sum(raw_col_lengths)
    col_lengths = [int(max_table_width * rcl / raw_total) for rcl in raw_col_lengths]
    if sum(col_lengths) > max_table_width:
        col_lengths[-1] -= sum(col_lengths) - max_table_width
    return [ColumnConfig(i, cw) for i, cw in enumerate(col_lengths)]


def prep_overflow_table_data(table_info: TableInfo, table_stats: TableStats) -> OFTable:
    max_row_len = table_stats.row_stats.max_len
    max_table_width = 90 if max_row_len >= 100 else 80
    cc_list = prep_col_configs(table_stats, max_table_width)
    has_zero_width_col = any(cc.col_width == 0 for cc in cc_list)
    if has_zero_width_col:
        print(f"Table {table_info.table_name} has at least one 0 width column. Skipping")
        return None
    of_table = OFTable(table_name=table_info.table_name)
    for ri in table_info.rows:
        of_row = OFRow(row_idx=ri.row_id)
        of_table.add_row(of_row)
        for i, cc in enumerate(cc_list):
            ci = ri.get_col_at_idx(i)
            if len(ci.content) > 0:
                content_lines = cc.to_overflowed_rows(ci.content)
                of_row.add_cell(OFCell(content_lines))
            else:
                of_row.add_cell(OFCell([""]))
    return of_table


def idx_generator(init_val=0):
    idx = init_val
    while True:
        yield idx
        idx += 1


def prep_instances_4_adj_rows(first: OFRow, second: OFRow, table_name: str, idx_gen) -> list[Instance]:
    instances = []
    for i, of_cell in enumerate(first.columns):
        fc = CellLocation(first.row_idx, i, 0)
        sc = CellLocation(second.row_idx, i, 0)
        ml = MergeLocation(table_name, fc, sc)
        inst_idx = next(idx_gen)
        instances.append(Instance(inst_idx, of_cell.content[0], second.columns[i].content[9], 0, ml))
    return instances


def prep_instances_4_overflow_rows(first: OFRow, second: OFRow, table_name: str, idx_gen) -> list[Instance]:
    instances = []
    if second is None:
        for i, of_cell in enumerate(first.columns):
            if len(of_cell.content) > 0:
                for j in range(1, len(of_cell.content)):
                    fc = CellLocation(first.row_idx, i, j - 1)
                    sc = CellLocation(first.row_idx, i, j)
                    ml = MergeLocation(table_name, fc, sc)
                    inst_idx = next(idx_gen)
                    inst = Instance(inst_idx, of_cell.content[j - 1], of_cell.content[j], 1, ml)
                    instances.append(inst)
    else:
        for i, of_cell in enumerate(first.columns):
            if len(of_cell.content) > 0:
                for j in range(1, len(of_cell.content)):
                    fc = CellLocation(first.row_idx, i, j - 1)
                    sc = CellLocation(first.row_idx, i, j)
                    ml = MergeLocation(table_name, fc, sc)
                    inst_idx = next(idx_gen)
                    inst = Instance(inst_idx, of_cell.content[j - 1], of_cell.content[j], 1, ml)
                    instances.append(inst)
                # last
                last_idx = len(of_cell.content) - 1
                fc = CellLocation(first.row_idx, i, last_idx)
                sc = CellLocation(second.row_idx, i, 0)
                ml = MergeLocation(table_name, fc, sc)
                inst_idx = next(idx_gen)
                sec_of_cell = second.columns[i]
                instances.append(Instance(inst_idx, of_cell.content[last_idx], sec_of_cell.content[0], 0, ml))
            else:
                fc = CellLocation(first.row_idx, i, 0)
                sc = CellLocation(second.row_idx, i, 0)
                ml = MergeLocation(table_name, fc, sc)
                inst_idx = next(idx_gen)
                sec_of_cell = second.columns[i]
                inst = Instance(inst_idx, of_cell.content[0], sec_of_cell.cotent[0], 0, ml)
                instances.append(inst)

    return instances


def prep_instances(of_table: OFTable, idx_gen) -> list[Instance]:
    tbl_name = of_table.table_name
    instances = []
    for i in range(1, len(of_table.rows)):
        prev_row = of_table.rows[i - 1]
        cur_row = of_table.rows[i]
        if prev_row.has_merged_cells:
            row_instances = prep_instances_4_overflow_rows(prev_row, cur_row, tbl_name, idx_gen)
            instances.extend(row_instances)
        else:
            row_instances = prep_instances_4_adj_rows(prev_row, cur_row, tbl_name, idx_gen)
            instances.extend(row_instances)
    return instances


def do_prep_instances(ti_list: list[TableInfo], ts_list: list[TableStats]) -> list[Instance]:
    instances = []
    id_gen = idx_generator(0)
    
    for ti, ts in tqdm(zip(ti_list, ts_list), total=len(ti_list)):
        of_table = prep_overflow_table_data(ti, ts)
        if of_table:
            table_instances = prep_instances(of_table, id_gen)
            instances.extend(table_instances)
    instances = list(filter(lambda inst: not inst.has_empty_line(), instances))
    return instances


def save_instances(inst_list: list[Instance], out_json_path):
    js_dict = {'instances': [inst.to_json() for inst in inst_list]}
    with open(out_json_path, 'w') as f:
        json.dump(js_dict, f, indent=2)
        print(f'wrote {out_json_path}')


def prep_tr_test_instances(ti_list: list[TableInfo], out_dir: Path, test_frac=0.1):
    random.seed(43)
    random.shuffle(ti_list)
    test_size = int(len(ti_list) * test_frac)
    test_ti_list = ti_list[:test_size]
    tr_ti_list = ti_list[test_size:]
    out_dir.mkdir(parents=True, exist_ok=True)
    test_ts_list = calc_stats(test_ti_list)
    tr_ts_list = calc_stats(tr_ti_list)

    train_instances = do_prep_instances(tr_ti_list, tr_ts_list)
    print(f"created {len(train_instances)} training instances.")
    save_instances(train_instances, out_dir / "cell_merge_tr_instances.json")
    test_instances = do_prep_instances(test_ti_list, test_ts_list)
    print(f"created {len(test_instances)} testing instances.")
    save_instances(test_instances, out_dir / "cell_merge_test_instances.json")


def filter_dir(in_dir: Path, out_dir: Path, keyword_set: set):
    table_paths = list(in_dir.glob("*.json"))
    out_dir.mkdir(parents=True, exist_ok=True)
    num_selected = 0
    for table_path in tqdm(table_paths, desc="Filter"):
        cells = extract_cell_contents(table_path)
        content = '\n'.join(cells)
        content = content.lower()
        for kw in keyword_set:
            if content.find(kw) != -1:
                out_path = out_dir / table_path.name
                shutil.copyfile(table_path, out_path)
                num_selected += 1
                break
    print(f"# of selected tables: {num_selected}")


def filter_dirs(in_root_dir: Path, out_dir: Path, keyword_set: set):
    sub_dirs = [Path(f.path) for f in os.scandir(in_root_dir) if f.is_dir()]
    for sub_dir in sub_dirs:
        filter_dir(sub_dir, out_dir, keyword_set)


def is_empty_row(_row: list[str]) -> bool:
    for item in _row:
        if item.strip() != '':
            return False
    return True


def to_table_infos_from_extracted_tables(tables_json_path: Path) -> list[TableInfo]:
    with open(tables_json_path) as f:
        data = json.load(f)
    return to_table_infos_from_extracted_tables_json(data)


def to_table_infos_from_extracted_tables_json(tables_json) -> list[TableInfo]:
    data = tables_json
    tables = []
    table_idx = 1
    for page in data['pages']:
        page_id = page['page']
        for tbl_dict in page["tables"]:
            tbl_name = "page_{}_table_{}".format(page_id, table_idx)
            ti = TableInfo(tbl_name)
            tables.append(ti)
            table_idx += 1
            row_idx = 0
            for row_lst in tbl_dict["rows"]:
                if is_empty_row(row_lst):
                    continue
                ri = RowInfo(row_idx)
                ti.add_row(ri)
                row_idx += 1
                for col in row_lst:
                    ri.add_cell(CellInfo(col))
    return tables


def prep_instances_4_row_pair(first: RowInfo, second: RowInfo, table_name: str, idx_gen) -> list[Instance]:
    instances = []
    for i, cell in enumerate(first.row):
        fc = CellLocation(first.row_id, i, 0)
        sc = CellLocation(second.row_id, i, 0)
        ml = MergeLocation(table_name, fc, sc)
        inst_idx = next(idx_gen)
        sec_cell = second.row[i]
        instances.append(Instance(inst_idx, cell.content, sec_cell.content, -1, ml))
    return instances


def prep_pred_instances(ti: TableInfo, idx_gen) -> list[Instance]:
    tbl_name = ti.table_name
    instances = []
    for i in range(1, len(ti.rows)):
        prev_row = ti.rows[i-1]
        cur_row = ti.rows[i]
        row_instances = prep_instances_4_row_pair(prev_row, cur_row, tbl_name, idx_gen)
        instances.extend(row_instances)
    return instances


def do_prep_pred_instances(ti_list: list[TableInfo]) -> list[Instance]:
    instances = []
    id_gen = idx_generator(0)
    for ti in tqdm(ti_list, total=len(ti_list)):
        table_instances = prep_pred_instances(ti, id_gen)
        instances.extend(table_instances)
    instances = list(filter(lambda inst: not inst.has_empty_line(), instances))
    return instances


def prep_pred_instances_4dir(in_dir: Path, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    json_paths = list(in_dir.glob("*.json"))
    for json_path in json_paths:
        ti_list = to_table_infos_from_extracted_tables(json_path)
        out_path = out_dir / "{}_instances.json".format(json_path.name.replace(".json", ""))
        instances = do_prep_pred_instances(ti_list)
        print(f"created {len(instances)} instances.")
        save_instances(instances, out_path)
    print("done.")



