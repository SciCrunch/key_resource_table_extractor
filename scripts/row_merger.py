import os
import re
import pickle
import json
import numpy as np
import torch
from torch.utils.data import Dataset, DataLoader
from pathlib import Path

from model import GPTConfig
from table_cell_merge_model import TableCellMergeModel
from merge_model_data_prep import Instance, TableInfo, RowInfo, CellInfo, MergeLocation
from merge_model_data_prep import to_table_infos_from_extracted_tables_json, do_prep_pred_instances


batch_size = 64


class Vocabulary:
    def __init__(self, meta_pk_path: Path):
        with open(meta_pk_path, 'rb') as f:
            meta = pickle.load(f)
        self.vocab_size = meta['vocab_size']
        self.stoi = meta['stoi']
        self.itos = meta['itos']

    def encode(self, s: str):
        return [self._encode_char(c) for c in s]

    def _encode_char(self, c):
        return self.stoi[c] if c in self.stoi else self.stoi['<UNK>']

    def decode(self, l: list[int]):
        return [self.itos[i] for i in l]

    def get_eos_encoded(self):
        return self.stoi['<EOS>']


class CellMergeInfo:
    def __init__(self, col_idx: int, score):
        self.col_idx = col_idx
        self.score = score


class RowMergeInfo:
    def __init__(self, row1: RowInfo, row2: RowInfo):
        self.row1 = row1
        self.row2 = row2
        self.cmi_list = []

    def add_cell_merge(self, cmi: CellMergeInfo):
        self.cmi_list.append(cmi)

    def _get_effective_empty_col_count(self):
        row1_empty_cols = len(list(filter(lambda col: len(col.content.strip()) == 0, self.row1.row)))
        row2_empty_cols = len(list(filter(lambda col: len(col.content.strip()) == 0, self.row2.row)))
        return max(row1_empty_cols, row2_empty_cols)

    def should_merge(self):
        # by majority vote
        if len(self.cmi_list) == len(self.row1.row):
            total = sum(cmi.score for cmi in self.cmi_list)
            score = total / len(self.cmi_list)
            return score >= 0.5
        else:
            n_empty_cols = self._get_effective_empty_col_count()
            total = sum(cmi.score for cmi in self.cmi_list)
            total += 0.5 * n_empty_cols
            score = total / len(self.row1.row)
            return score >= 0.5


def find_row(ti: TableInfo, row_idx):
    for ri in ti.rows:
        if ri.row_id == row_idx:
            return ri
    return None


class TableMergeInfo:
    def __init__(self, table_name):
        self.table_name = table_name
        self.rmi_list = []
        self.rmi_map = {}

    def add_row_merge_info(self, rmi: RowMergeInfo):
        rmi_key = "{}_{}".format(rmi.row1.row_id, rmi.row2.row_id)
        self.rmi_map[rmi_key] = rmi
        self.rmi_list.append(rmi)

    def find_rmi(self, row1: RowInfo, row2: RowInfo):
        rmi_key = "{}_{}".format(row1.row_id, row2.row_id)
        if rmi_key in self.rmi_map:
            return self.rmi_map[rmi_key]
        return None

    def do_merge(self, ti: TableInfo):
        adj_map = {}
        for rmi in self.rmi_list:
            if rmi.should_merge():
                adj_map[rmi.row1.row_id] = rmi.row2.row_id

        nti = TableInfo(ti.table_name)
        row_idx = 0
        seen_set = set()
        for ri in ti.rows:
            if ri in seen_set:
                continue
            if ri.row_id in adj_map:
                nri = RowInfo(row_idx)
                nti.add_row(nri)
                next_row_id = adj_map[ri.row_id]
                next_ri = find_row(ti, next_row_id)
                seen_set.add(next_ri)
                for i, col in enumerate(ri.row):
                    nc = col.content + " " + next_ri.row[i].content
                    nri.add_cell(CellInfo(nc))
                while next_row_id in adj_map:
                    nrid = adj_map[next_row_id]
                    nn_ri = find_row(ti, nrid)
                    seen_set.add(nn_ri)
                    for i, col in enumerate(nri.row):
                        col.content += " " + nn_ri.row[i].content
                    next_row_id = nrid
                row_idx += 1
            else:
                nri = RowInfo(row_idx)
                nti.add_row(nri)
                for col in ri.row:
                    nri.add_cell(col)
                row_idx += 1
        # remove any trailing spaces in cells
        for nri in nti.rows:
            for nc in nri.row:
                nc.content = nc.content.rstrip()
        return nti


def find_rows(ti: TableInfo, ml: MergeLocation):
    row1, row2 = None, None
    for ri in ti.rows:
        if ri.row_id == ml.first.row_idx:
            row1 = ri
        if ri.row_id == ml.second.row_idx:
            row2 = ri
        if row1 is not None and row2 is not None:
            break
    assert row1 is not None and row2 is not None
    return row1, row2


def do_row_merge(instances: list[Instance], pred_list, ti_list: list[TableInfo]):
    ti_map = {ti.table_name: ti for ti in ti_list}
    tmi_map = {ti.table_name: TableMergeInfo(ti.table_name) for ti in ti_list}
    for instance, pred in zip(instances, pred_list):
        ti = ti_map[instance.location.table_name]
        tmi = tmi_map[instance.location.table_name]
        row1, row2 = find_rows(ti, instance.location)
        rmi = tmi.find_rmi(row1, row2)
        if rmi is None:
            rmi = RowMergeInfo(row1, row2)
            tmi.add_row_merge_info(rmi)
        rmi.add_cell_merge(CellMergeInfo(instance.location.first.col_idx, pred))
    merged_ti_list = []
    for ti in ti_list:
        tmi = tmi_map[ti.table_name]
        merged_ti = tmi.do_merge(ti)
        merged_ti_list.append(merged_ti)
    return merged_ti_list


def save_merged_paper_tables(ti_list: list[TableInfo], out_json_path):
    wrapper = to_merged_paper_tables(ti_list)
    with open(out_json_path, 'w') as f:
        json.dump(wrapper, f, indent=2)
        print(f"wrote {out_json_path}")


def to_merged_paper_tables(ti_list: list[TableInfo]):
    tokens = ti_list[0].table_name.split('_')
    paper_id = "{}_{}".format(tokens[0], tokens[1])
    result = {"pages": []}
    wrapper = {"paper_id": paper_id, "result": result}
    page_map = {}
    for ti in ti_list:
        m = re.search(r'page_(\d+)_.+', ti.table_name)
        assert m
        page_id = m.group(1)
        if page_id in page_map:
            page = page_map[page_id]
        else:
            page = {"tables": [], "page": int(page_id)}
            page_map[page_id] = page
        tbl_dict = {"rows": []}
        page["tables"].append(tbl_dict)
        for row in ti.rows:
            r_list = [col.content for col in row.row]
            tbl_dict["rows"].append(r_list)
    page_ids = list(page_map.keys())
    page_ids = sorted(page_ids, key=lambda x: int(x))
    for page_id in page_ids:
        result["pages"].append(page_map[page_id])
    return wrapper


class CellMergePredDataset(Dataset):
    def __init__(self, instances: list[Instance], vocab: Vocabulary):
        self.vocab = vocab
        self.instances = instances
        n_instances = len(instances)
        xs = np.zeros((n_instances, 256), dtype=np.int32)
        for i, inst in enumerate(instances):
            el = []
            el.extend(vocab.encode(inst.line1))
            el.append(vocab.get_eos_encoded())
            el.extend(vocab.encode(inst.line2))
            xs[i, :len(el)] = el
        self.X = torch.tensor(xs, dtype=torch.int32)
        print(f"X: {self.X.shape}")

    def __len__(self):
        return len(self.X)

    def __getitem__(self, idx):
        features = self.X[idx]
        return features


class RowMerger(object):
    def __init__(self, model_path, vocab: Vocabulary, device):
        self.vocab = vocab
        self.device = device
        model_args = dict(n_layer=6, n_head=6, n_embd=384, block_size=256,
                          bias=False, vocab_size=vocab.vocab_size, dropout=0.1)
        gpt_conf = GPTConfig(**model_args)
        self.model = TableCellMergeModel(gpt_conf)
        self.model.load_state_dict(torch.load(model_path, map_location=device, weights_only=True))
        self.model = self.model.to(device)

    def predict(self, pred_dataset: CellMergePredDataset):
        self.model.eval()
        data_loader = DataLoader(pred_dataset, batch_size=batch_size)
        _predictions = []
        with torch.no_grad():
            for X in data_loader:
                X = X.to(self.device)
                pred = self.model(X)
                # print(pred)
                # print(f"pred {pred.shape}")
                p = pred.cpu().squeeze(1).tolist()
                _predictions.extend(p)
        return _predictions

    def do_predict(self, extracted_tables_json):
        ti_list = to_table_infos_from_extracted_tables_json(extracted_tables_json)
        paper_pred_instances = do_prep_pred_instances(ti_list)
        cmp_dataset = CellMergePredDataset(paper_pred_instances, self.vocab)
        predictions = self.predict(cmp_dataset)
        merged_ti_list = do_row_merge(cmp_dataset.instances, predictions, ti_list)
        return to_merged_paper_tables(merged_ti_list)

    @classmethod
    def create(cls, model_dir: Path):
        meta_path = model_dir / "meta.pkl"
        vocabulary = Vocabulary(meta_path)
        model_path = model_dir / "model.pth"
        _device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        return cls(model_path, vocabulary, _device)


def load_instances(json_path: Path):
    with open(json_path) as f:
        data = json.load(f)
        instances = []
        for inst_dict in data['instances']:
            instances.append(Instance.from_json(inst_dict))
        return instances

