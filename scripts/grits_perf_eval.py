import os
import json
import argparse
import traceback
import logging
from pathlib import Path
from collections import defaultdict

from grits import grits_from_html
from html_table_converter import to_html_table, load_json
from pg_config import get_work_dir

WD = get_work_dir()


class DataCollector:
    def __init__(self, json_file: Path = None):
        if json_file is not None:
            with open(json_file) as f:
                self.metric_data = json.load(f)
        else:
            self.metric_data = defaultdict(list)

    def push(self, metric):
        for k, v in metric.items():
            self.metric_data[k].append(v)

    def save(self, out_path: Path):
        with open(out_path, 'w') as f:
            json.dump(self.metric_data, f, indent=2)
            print(f"wrote {out_path}")

    @classmethod
    def from_json(cls, json_file: Path):
        return cls(json_file)


def eval_perf(gs_table_json_paths, pred_table_json_paths, data_collector: DataCollector = None):
    metrics = None
    pred_map = {fp.name: fp for fp in pred_table_json_paths}
    count = 0
    for gs_tj_path in gs_table_json_paths:
        if gs_tj_path.name not in pred_map:
            print(f"missing {gs_tj_path.name} in GS set. Skipping...")
            continue
        pred_tj_path = pred_map[gs_tj_path.name]

        gs_html_table = to_html_table(load_json(gs_tj_path))
        pred_html_table = to_html_table(load_json(pred_tj_path))
        print(f"handling {gs_tj_path.name}")
        try:
            m = grits_from_html(gs_html_table.to_html(), pred_html_table.to_html())
        except Exception as e:
            logging.error(traceback.format_exc())
            continue
        count += 1
        if data_collector is not None:
            data_collector.push(m)
        if metrics is not None:
            for k, v in m.items():
                metrics[k] += v
        else:
            metrics = m
    print(f"count: {count} total: {len(gs_table_json_paths)}")
    for k, v in metrics.items():
        metrics[k] /= len(gs_table_json_paths)
    print(metrics)


def test_driver():
    in_root = Path(WD, "data/table_content_extract/gs_bioarxiv_extracted_key_resources_tables_sampled")
    json_table_files = list(in_root.glob("*.json"))
    for json_table_file in json_table_files:
        js_dict = load_json(json_table_file)
        html_table = to_html_table(js_dict)
        ht_str = html_table.to_html()
        metrics = grits_from_html(ht_str, ht_str)
        print(metrics)
        break


def do_eval_with_row_info():
    in_root = Path(WD, "data/table_content_extract/gs_bioarxiv_extracted_key_resources_tables_sampled")
    json_table_files = list(in_root.glob("*.json"))
    pred_ri_root = Path("/tmp/bioarxiv_extracted_key_resources_tables_with_row_info_sampled_table_json")
    pred_ri_json_table_files = list(pred_ri_root.glob("*.json"))
    eval_perf(json_table_files, pred_ri_json_table_files)


def do_eval_main():
    in_root = Path(WD, "data/table_content_extract/gs_bioarxiv_extracted_key_resources_tables_sampled")
    pred_root = Path("/tmp/bioarxiv_extracted_key_resources_tables_sampled_table_json")
    json_table_files = list(in_root.glob("*.json"))
    pred_json_table_files = list(pred_root.glob("*.json"))
    eval_perf(json_table_files, pred_json_table_files)


def do_eval_main_merged():
    in_root = Path(WD, "data/table_content_extract/gs_bioarxiv_extracted_key_resources_tables_sampled")
    pred_root = Path("/tmp/bioarxiv_main_merged_table_json")
    json_table_files = list(in_root.glob("*.json"))
    pred_json_table_files = list(pred_root.glob("*.json"))
    eval_perf(json_table_files, pred_json_table_files)


def do_eval_ocr():
    in_root = Path(WD, "data/table_content_extract/gs_bioarxiv_extracted_key_resources_tables_sampled")
    gs_json_table_files = list(in_root.glob("*.json"))
    pred_root = Path("/tmp/bioarxiv_extracted_key_resources_tables_sampled_ocr_table_json")
    pred_json_table_files = list(pred_root.glob("*.json"))
    eval_perf(gs_json_table_files, pred_json_table_files)


def do_eval_grobid():
    in_root = Path(WD, "data/table_content_extract/gs_bioarxiv_extracted_key_resources_tables_sampled")
    gs_json_table_files = list(in_root.glob("*.json"))
    pred_root = Path("/tmp/bioarxiv_extracted_key_resources_tables_sampled_grobid_table_json")
    pred_json_table_files = list(pred_root.glob("*.json"))
    eval_perf(gs_json_table_files, pred_json_table_files)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", required=True, metavar="<command one of [col_only, row_info, ocr, merged, grobid]>")
    args = parser.parse_args()
    cmd = args.c
    if cmd == 'col_only':
        do_eval_main()
    elif cmd == 'row_info':
        do_eval_with_row_info()
    elif cmd == 'ocr':
        do_eval_ocr()
    elif cmd == 'merged':
        do_eval_main_merged()
    elif cmd == 'grobid':
        do_eval_grobid()
