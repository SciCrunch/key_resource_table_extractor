import os
import re
import json
import subprocess
from pathlib import Path

from extract_tables_from_pdf import TableExtractor, pdf_to_images
from rel_table_pages_filter import RelevantTablePagesDetector
from row_merger import RowMerger
from pg_config import get_work_dir

# global
# HOME = os.path.expanduser('~')
# WD = os.path.join(HOME, "dev/java/pdf_table_extractor")
WD = get_work_dir()


def do_hybrid_table_content_extraction(_pdf_file_path, _struct_json_dir, _out_json_file,
                                       use_row_info=False):
    wd = os.getcwd()
    os.chdir(WD)
    script_path = "hybrid_table_content_extractor.sh"
    if use_row_info:
        subprocess.run(['bash', script_path, "-i", _pdf_file_path, '-o', _out_json_file,
                        '-s', _struct_json_dir, '-r'])
    else:
        subprocess.run(['bash', script_path, "-i", _pdf_file_path, '-o', _out_json_file,
                        '-s', _struct_json_dir])
    os.chdir(wd)


class PDFTableExtractor(object):
    def __init__(self, model_dir: Path):
        self.tex = TableExtractor()
        self.detector = RelevantTablePagesDetector()
        self.row_merger = RowMerger.create(model_dir)

    def extract_table_contents_from_pdf(self, _pdf_file_path, _out_dir, use_row_info=False):
        pages = self.detector.get_relevant_pages(_pdf_file_path)
        if len(pages) == 0:
            return None
        pdf_file_stem = Path(_pdf_file_path).stem
        im_out_dir = os.path.join(_out_dir, pdf_file_stem)
        Path(im_out_dir).mkdir(parents=True, exist_ok=True)
        image_files = pdf_to_images(_pdf_file_path, im_out_dir)
        page_ids = {p['page'] for p in pages}
        all_tables = []
        for image_file in image_files:
            page_num = re.search(r"-(\d+)\.jpg", image_file).group(1)
            page_no = int(page_num) - 1
            if page_no in page_ids:
                tables = self.tex.extract_tables_structures(image_file, out_dir=im_out_dir, prefix=pdf_file_stem)
                if tables:
                    all_tables.extend(tables)
        if len(all_tables) == 0:
            return None

        # do hybrid table content extraction
        struct_json_dir = Path(im_out_dir, 'structure')
        if struct_json_dir.is_dir():
            json_files = [os.path.join(struct_json_dir, f) for f in os.listdir(struct_json_dir) if
                          re.match(r'.+\.json', f)]
            if len(json_files) == 0:
                return None
            out_json_file = Path(_out_dir, "table_report.json")
            do_hybrid_table_content_extraction(_pdf_file_path, str(struct_json_dir),
                                               str(out_json_file), use_row_info)
            if out_json_file.is_file():
                with open(out_json_file) as f:
                    data = json.load(f)
                if not use_row_info:
                    print("***** doing row merging ****")
                    data = self.row_merger.do_predict(data)
                    print("=" * 80)
                return data
        return None
