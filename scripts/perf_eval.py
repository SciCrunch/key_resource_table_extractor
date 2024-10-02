import os.path
import json
from pathlib import Path
from typing import Union
from pydantic import BaseModel


HOME = os.path.expanduser('~')
WD = os.path.join(HOME, "dev/java/pdf_table_extractor")


class RelTablePaperInfo(BaseModel):
    paper: str
    doc: str
    missedPages: Union[list[int], None] = None
    pages: Union[list[int], None] = None
    curation: Union[list[bool], None] = None


def load_rel_table_filter_annotations(_rel_tables_annot_json_file, _no_tables_annot_json_file):
    rtpi_list = []
    with open(rel_tables_annot_json_file) as f:
        data = json.load(f)
    for rec in data:
        r = RelTablePaperInfo(**rec)
        rtpi_list.append(r)
    with open(_no_tables_annot_json_file) as f:
        data = json.load(f)
    for rec in data:
        r = RelTablePaperInfo(**rec)
        rtpi_list.append(r)
    return rtpi_list


def show_perf(_rtpi_list):
    tp, fp, fn = 0, 0, 0
    for rtpi in _rtpi_list:
        if rtpi.curation:
            for v in rtpi.curation:
                if v:
                    tp += 1
                else:
                    fp += 1
        if rtpi.missedPages:
            fn += len(rtpi.missedPages)
    precision = tp / (tp + fp)
    recall = tp / (tp + fn)
    F1 = 2 * (precision * recall / (precision + recall))
    print(f"Precision: {precision:.2f} Recall: {recall:.2f} F1: {F1:.2f}")


def prep_paper_list_4annot(_rtpi_list, _out_file):
    paper_lst = []
    for rtpi in _rtpi_list:
        has_error = False
        if rtpi.curation:
            for v in rtpi.curation:
                if not v:
                    has_error = True
                    break
        if rtpi.missedPages:
            has_error = len(rtpi.missedPages) > 0
        if has_error:
            paper_lst.append(rtpi.paper + "/" + rtpi.doc)
    if _out_file:
        with open(_out_file , 'w') as f:
            for p in paper_lst:
                f.write(p + "\n")
        print(f"wrote {_out_file}")
    return paper_lst


if __name__ == '__main__':
    rel_tables_annot_json_file = Path(WD, "data/rrid_papers_sample_200_03_07_2023"
                                          "/rrid_papers_sample_200_03_07_2023_relevant_tables_ANNOTATED.json")
    no_tables_annot_json_file = Path(WD, "data/rrid_papers_sample_200_03_07_2023"
                                         "/rrid_papers_sample_200_03_07_2023_no_tables_ANNOTATED.json")

    papers = load_rel_table_filter_annotations(rel_tables_annot_json_file, no_tables_annot_json_file)
    for paper in papers:
        print(paper)
    show_perf(papers)
    # prep_paper_list_4annot(papers, "/tmp/rrid_papers_sample_200_03_07_2023_papers_4annotate.txt")



