import json
import os
import time
import shutil

import requests
from pathlib import Path


BASE_URL = "http://localhost:8001"
HOME = os.path.expanduser("~")


def save_json(_data, _out_json_file):
    with open(_out_json_file, 'w') as f:
        json.dump(_data, f, indent=2)
        print(f"wrote {_out_json_file}.")


def submit_paper(_paper_id: str, _pdf_file_path, _use_row_info=False):
    url = BASE_URL + '/pdf_table_extractor/submit_paper'
    files = {'pdf_file': open(_pdf_file_path, 'rb')}
    params = {'paper_id': _paper_id, 'use_row_info': _use_row_info}
    response = requests.post(url, files=files, params=params)
    if response.status_code == requests.codes.ok:
        print(response.json())
        return response.json()
    else:
        response.raise_for_status()
        
      
def submit_a_pdf(_paper_id, _pdf_file, use_row_info=False):
    result = submit_paper(_paper_id, _pdf_file, _use_row_info=use_row_info)
    if result:
        print(f"job_id:{result['job_id']}")
    return result


def get_job_results(job_id):
    url = BASE_URL + "/pdf_table_extractor/get_job_results"
    params = {'job_id': job_id}
    response = requests.get(url, params=params)
    if response.status_code == requests.codes.ok:
        print(json.dumps(response.json(), indent=2))
        return response.json()
    else:
        response.raise_for_status()


def test_get_job_results(_job_id, _out_json_file=None):
    job_result = get_job_results(_job_id)
    if job_result:
        print(json.dumps(job_result, indent=2))
        if _out_json_file:
            save_json(job_result, _out_json_file)
        return job_result
        
        
def handle_paper(pdf_file: Path, out_dir: Path, use_row_info=False):
    prefix = pdf_file.stem
    parent_name = pdf_file.parent.name
    paper_id = "{}_{}".format(parent_name, prefix)
    res = submit_a_pdf(paper_id, pdf_file, use_row_info=use_row_info)
    print(res)
    _job_id = int(res['job_id'])

    total_time = 0
    while True:
        time.sleep(2)
        total_time += 2
        result = test_get_job_results(_job_id)
        if result and result['job_status'] == 'finished':
            res = result['result']
            if len(res) > 0:
                out_file = out_dir / "{}_{}_tables.json".format(parent_name, prefix)
                test_get_job_results(_job_id, out_file)
            break
        if (result and result['job_status'] == "error") or total_time >= 30:
            break


def handle_sampled():
    root_dir = Path(HOME, "data/table_content_extract/bundle/sampled_pdfs")
    pdf_files = root_dir.glob("*.pdf")
    output_dir = Path('/tmp/extracted_key_resources_tables_with_row_info_sampled_v2')
    output_dir.mkdir(exist_ok=True)
    for pdf_file_path in pdf_files:
        print(pdf_file_path)
        handle_paper(pdf_file_path, output_dir, use_row_info=True)


def handle_bioarxiv():
    root_dir = Path(HOME, "data/czi_bioarxiv_April_2024")
    pdf_files = root_dir.glob("**/*.pdf")
    output_dir = Path('/tmp/extracted_key_resources_tables_with_row_info')
    output_dir.mkdir(exist_ok=True)
    with open("processed_files.txt", 'w') as f:
        for pdf_file_path in pdf_files:
            print(pdf_file_path)
            handle_paper(pdf_file_path, output_dir, use_row_info=True)
            f.write(str(pdf_file_path))
            f.write('\n')
            f.flush()


if __name__ == '__main__':
    # handle_bioarxiv()
    handle_sampled()

