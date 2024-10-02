import os
import shutil
import subprocess
from pathlib import Path
from data_prep import load_list

HOME = os.path.expanduser('~')
WD = os.path.join(HOME, "dev/java/pdf_table_extractor")


def do_data_prep2(_pdf_file, _out_json_file):
    wd = os.getcwd()
    os.chdir(WD)
    script_path = "table_detect_data_prep_2.sh"
    subprocess.run(['bash', script_path, "-i", _pdf_file, '-o', _out_json_file])
    os.chdir(wd)


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
        do_data_prep2(pdf_file_path, out_path)


def handle_first_dataset():
    root_dir = os.path.join(HOME, "dev/java/pdf_table_extractor/src/test/resources/data")
    out_dir = '/tmp/out_v1'
    pdf_filenames = ['media-2.pdf', 'media-4.pdf', 'media-5.pdf', 'media-6.pdf',
                     'media-7.pdf', 'media-8.pdf', 'media-9.pdf', 'media-10.pdf',
                     'media-11.pdf', 'media-12.pdf', 'media-13.pdf', 'media-14.pdf',
                     'media-15.pdf', 'media-16.pdf', 'media-17.pdf']
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    pdf_file_paths = [Path(root_dir, f) for f in pdf_filenames]
    for pdf_file_path in pdf_file_paths:
        basename = pdf_file_path.stem
        out_json_file = basename + '_instances.json'
        out_path = Path(out_dir) / out_json_file
        print(out_path)
        do_data_prep2(pdf_file_path, out_path)


if __name__ == '__main__':
    # handle_first_dataset()
    handle_good_pdfs()
