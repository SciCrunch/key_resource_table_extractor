import os.path
import sys
import traceback
import json
from pathlib import Path

from table_detect_data_prep_batch import do_data_prep
from classifier import PDFLineClassifier
from stacked_gen import RelTablePageClassifier

HOME = os.path.expanduser('~')
WD = os.path.join(HOME, "dev/java/pdf_table_extractor")


class RelevantTablePagesDetector(object):
    def __init__(self):
        pdf_line_clf_model_path = os.path.join(WD, "models/table_detect_classifier.keras")
        self.pl_clf = PDFLineClassifier(pdf_line_clf_model_path)
        self.clf = RelTablePageClassifier()

    def get_relevant_pages(self, _pdf_file_path):
        pdf_inst_json_path = '/tmp/pdf_line_clf_instances.json'
        try:
            do_data_prep(_pdf_file_path, pdf_inst_json_path)
            stack_instances = self.pl_clf.prep_stack_instances(pdf_inst_json_path)
            # import pdb; pdb.set_trace()
            return self.clf.get_detected_pages(stack_instances)
        except:
            print("An error occurred: ", sys.exc_info()[0])
            print(traceback.format_exc())
            return []


def get_relevant_pages(_pdf_file_path):
    pdf_line_clf_model_path = os.path.join(WD, "models/table_detect_classifier")
    pl_clf = PDFLineClassifier(pdf_line_clf_model_path)
    clf = RelTablePageClassifier()
    pdf_inst_json_path = '/tmp/pdf_line_clf_instances.json'
    do_data_prep(_pdf_file_path, pdf_inst_json_path)
    stack_instances = pl_clf.prep_stack_instances(pdf_inst_json_path)
    return clf.get_detected_pages(stack_instances)


def handle_batch():
    detector = RelevantTablePagesDetector()
    root_dir = Path(HOME, "czi/rrid_papers_sample_200_03_07_2023")
    paper_dirs = [f for f in root_dir.iterdir() if f.is_dir()]
    results = []
    no_table_ones = []
    count = 0
    for paper_dir in paper_dirs:
        paper_name = paper_dir.stem
        pdf_files = [f for f in paper_dir.iterdir() if f.is_file() and f.name.endswith(".pdf")]
        for pdf_file in pdf_files:
            print(pdf_file)
            pages = detector.get_relevant_pages(pdf_file)
            count += 1
            if len(pages) > 0:
                print(f"*** found relevant table pages in {pdf_file}")
                page_ids = [p['page'] for p in pages]
                results.append({'paper': paper_name, "doc": pdf_file.name,
                                'pages': page_ids})
            else:
                no_table_ones.append({'paper': paper_name, "doc": pdf_file.name})

        # if count > 20:
        #    break
    out_json_path = "/tmp/rrid_papers_sample_200_03_07_2023_relevant_tables.json"
    nto_json_path = "/tmp/rrid_papers_sample_200_03_07_2023_no_tables.json"
    with open(out_json_path, "w") as f:
        json.dump(results, f, indent=2)
        print(f"wrote {out_json_path}")
    with open(nto_json_path, "w") as f:
        json.dump(no_table_ones, f, indent=2)
        print(f"wrote {nto_json_path}")


if __name__ == '__main__':
    # pdf_file_path = os.path.join(HOME, "czi/rrid_papers_sample_200_03_07_2023/2022_10_26_513928/main.pdf")
    # pdf_file_path = os.path.join(HOME, "czi/rrid_papers_sample_200_03_07_2023/534750/main.pdf")
    pdf_file_path = os.path.join(HOME, "czi/rrid_papers_sample_200_03_07_2023/617936/main.pdf")
    # get_relevant_pages(pdf_file_path)
    handle_batch()
