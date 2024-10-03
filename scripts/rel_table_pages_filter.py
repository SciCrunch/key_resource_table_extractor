import os.path
import sys
import traceback

from table_detect_data_prep_batch import do_data_prep
from classifier import PDFLineClassifier
from stacked_gen import RelTablePageClassifier
from pg_config import get_work_dir


# HOME = os.path.expanduser('~')
# WD = os.path.join(HOME, "dev/table_extraction_paper/key_resource_table_extractor")
WD = get_work_dir()


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





