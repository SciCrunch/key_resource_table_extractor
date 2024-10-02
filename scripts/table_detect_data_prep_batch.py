import os
import shutil
import subprocess
from pathlib import Path
from data_prep import load_list

HOME = os.path.expanduser('~')
WD = os.path.join(HOME, "dev/java/pdf_table_extractor")


def do_data_prep(_pdf_file, _out_json_file):
    wd = os.getcwd()
    os.chdir(WD)
    script_path = "table_detect_data_prep.sh"
    subprocess.run(['bash', script_path, "-i", _pdf_file, '-o', _out_json_file])
    os.chdir(wd)


def handle_rrid_papers_sample_200_03_07_2023(_papers_file, _out_dir):
    _root_dir = Path(HOME, "czi/rrid_papers_sample_200_03_07_2023")
    _out_dir_path = Path(_out_dir)
    if not _out_dir_path.is_dir():
        _out_dir_path.mkdir(parents=True)
    pdf_out_dir = Path(_out_dir_path, "pdfs")
    if not pdf_out_dir.is_dir():
        pdf_out_dir.mkdir()
    papers = load_list(_papers_file)
    for paper in papers:
        pdf_file_path = Path(_root_dir, paper)
        basename = pdf_file_path.stem
        paper_id = pdf_file_path.parent.name
        out_json_file = paper_id + '_' + basename + '_instances.json'
        out_path = Path(_out_dir) / out_json_file
        print(out_path)
        paper_pdf_dir = Path(pdf_out_dir, paper_id)
        if not paper_pdf_dir.is_dir():
            paper_pdf_dir.mkdir()
        new_path = Path(paper_pdf_dir, pdf_file_path.name)
        shutil.copyfile(pdf_file_path, new_path)
        print(f"copied {pdf_file_path} to {new_path}")
        # do_data_prep(pdf_file_path, out_path)


def handle_good_pdfs():
    root_dir = os.path.join(HOME, "dev/java/pdf_table_extractor/data/good_pdfs")
    out_dir = '/tmp/out'
    if not Path(out_dir).is_dir():
        Path(out_dir).mkdir(parents=True)
    pdf_file_paths = list(Path(root_dir).rglob("*.pdf"))
    for pdf_file_path in pdf_file_paths:
        basename = pdf_file_path.stem
        paper_id = pdf_file_path.parent.parent.name
        out_json_file = paper_id + '_' + basename + '_instances.json'
        out_path = Path(out_dir) / out_json_file
        print(out_path)
        do_data_prep(pdf_file_path, out_path)


if __name__ == '__main__':
    # handle_good_pdfs()
    papers_file = "/tmp/rrid_papers_sample_200_03_07_2023_papers_4annotate.txt"
    handle_rrid_papers_sample_200_03_07_2023(papers_file, "/tmp/out")
