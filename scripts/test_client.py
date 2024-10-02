import json
import os
import time

import requests
import configparser
import click
from pathlib import Path
from pg_config import get_api_key

BASE_URL = "http://localhost:8001"

HOME = os.path.expanduser("~")

CFG_FILE_NAME = ".key_resource_table_extractor.ini"


def save_config(pdf_root_dir):
    cfg = configparser.ConfigParser()
    cfg['client'] = {'pdf-root-dir': pdf_root_dir}
    cfg_file = Path(HOME) / CFG_FILE_NAME
    with open(cfg_file, 'w') as f:
        cfg.write(f)


def load_pdf_root_dir():
    cfg_file = Path(HOME) / CFG_FILE_NAME
    if cfg_file.exists():
        cfg = configparser.ConfigParser()
        cfg.read(cfg_file)
        return cfg.get('client', 'pdf-root-dir')
    else:
        return None


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


@click.group()
def cli():
    pass


@cli.command(name="set-root", help="set PDF papers root directory")
@click.option('-d', '--pdf-root-dir', required=True)
def set_root_dir(pdf_root_dir):
    if pdf_root_dir is None or len(pdf_root_dir.strip()) == 0:
        print("PDF papers root directory cannot be empty string!")
        return
    p = Path(pdf_root_dir)
    if not p.exists():
        print(f"{pdf_root_dir} does not exists!")
        return
    save_config(pdf_root_dir)


@cli.command(name="show-root", help="shows the current PDF papers root directory")
def show_root_dir():
    pdf_root_dir = load_pdf_root_dir()
    if pdf_root_dir is None:
        print("No PDF papers root directory is set!")
    else:
        print(f"The current PDF papers root directory is '{pdf_root_dir}'.")


@cli.command(name='results')
@click.option('-j', '--job-id', required=True)
def get_job_results_command(job_id):
    return get_job_results(job_id)


def get_job_results(job_id):
    url = BASE_URL + "/pdf_table_extractor/get_job_results"
    params = {'job_id': job_id}
    response = requests.get(url, params=params)
    if response.status_code == requests.codes.ok:
        print(json.dumps(response.json(), indent=2))
        return response.json()
    else:
        response.raise_for_status()


@cli.command(name='list')
def list_jobs():
    url = BASE_URL + "/pdf_table_extractor/list_jobs"
    params = {"api_key": get_api_key()}
    response = requests.get(url, params=params)
    if response.status_code == requests.codes.ok:
        print(json.dumps(response.json(), indent=2))
    else:
        response.raise_for_status()


@cli.command(name='remove')
@click.option('-j', '--job-id', required=True)
def remove_job(job_id):
    url = BASE_URL + "/pdf_table_extractor/remove_job"
    params = {'job_id': job_id, "api_key": get_api_key()}
    response = requests.delete(url, params=params)
    if response.status_code == requests.codes.ok:
        # print(response.json())
        return response.json()
    else:
        response.raise_for_status()


@cli.command(name='remove-by')
@click.option('-p', '--paper-id', required=True)
def remove_jobs_by_paper_id(paper_id):
    url = BASE_URL + "/pdf_table_extractor/remove_jobs_by"
    params = {'paper_id': paper_id, "api_key": get_api_key()}
    response = requests.delete(url, params=params)
    if response.status_code == requests.codes.ok:
        # print(response.json())
        return response.json()
    else:
        response.raise_for_status()


def submit_a_pdf(_paper_id, _pdf_file, use_row_info=False):
    result = submit_paper(_paper_id, _pdf_file, _use_row_info=use_row_info)
    if result:
        print(f"job_id:{result['job_id']}")
    return result


def test_get_job_results(_job_id, _out_json_file=None):
    job_result = get_job_results(_job_id)
    if job_result:
        print(json.dumps(job_result, indent=2))
        if _out_json_file:
            save_json(job_result, _out_json_file)


def save_json(_data, _out_json_file):
    with open(_out_json_file, 'w') as f:
        json.dump(_data, f, indent=2)
        print(f"wrote {_out_json_file}.")


def handle_paper(pdf_file: Path, _job_id=None, use_row_info=False):
    prefix = pdf_file.stem
    parent_name = pdf_file.parent.name
    if not _job_id:
        res = submit_a_pdf(parent_name, pdf_file, use_row_info=use_row_info)
        print(res)
        _job_id = int(res['job_id'])
    Path('/tmp/extracted_tables').mkdir(parents=True, exist_ok=True)
    out_file = "/tmp/extracted_tables/{}_{}_tables.json".format(parent_name, prefix)
    print(f"job_id:{_job_id} -- {out_file}")
    time.sleep(30)
    test_get_job_results(_job_id, out_file)


@cli.command(name="submit")
@click.option('-p', '--pdf-rel-path', required=True)
@click.option('-j', '--job-id', default=None)
@click.option('-r', '--use-row-info', is_flag=True)
def handle_paper_by_rel_path(pdf_rel_path, job_id, use_row_info):
    # _in_dir = Path(HOME, 'czi/rrid_papers_sample_200_03_07_2023')
    # _in_dir = Path(HOME, 'data/czi_bioarxiv_April_2024')
    if Path(pdf_rel_path).is_absolute():
        pdf_file = Path(pdf_rel_path)
    else:
        pdf_root_dir = load_pdf_root_dir()
        if pdf_root_dir is not None:
            pdf_file = Path(pdf_root_dir, pdf_rel_path)
        else:
            print("No PDF paper root dir is specified!")
            return

    assert pdf_file.exists(), pdf_file
    handle_paper(pdf_file, _job_id=job_id, use_row_info=use_row_info)

    # pdf_file = Path(_in_dir, pdf_rel_path)
    # if not pdf_file.exists():
    #     _in_dir = Path(HOME, 'czi/test')
    #     pdf_file = Path(_in_dir, pdf_rel_path)
    # assert pdf_file.exists(), pdf_file
    # handle_paper(pdf_file, _job_id=job_id, use_row_info=use_row_info)


@cli.command(name='remaining', help="list papers not processed yet")
@click.option('-v', '--verbose', is_flag=True)
def find_remaining(verbose):
    pdf_list_file = Path(HOME, "dev/java/pdf_table_extractor/data/row_merge/pdfs_to_table_extract_full.lst")
    notes_file = Path(HOME, "dev/java/pdf_table_extractor/data/row_merge/extracted_tables/NOTES")
    existing = set()
    with open(notes_file) as f:
        for line in f:
            line = line.strip()
            if len(line) == 0:
                break
            tokens = line.split(' - ')
            prefix = tokens[0].replace('_tables.json', '')
            idx = prefix.rfind('_')
            rel_path = "{}/{}.pdf".format(prefix[:idx], prefix[idx+1:])
            existing.add(rel_path)
    if verbose:
        for e in existing:
            print(e)
        print('-' * 80)
    pdf_file_rel_paths = []
    with open(pdf_list_file) as f:
        for line in f:
            line = line.strip()
            if len(line) > 0 and line not in existing:
                pdf_file_rel_paths.append(line)
    for prp in pdf_file_rel_paths:
        print(prp)


def handle_papers(pdf_list_file):
    _in_dir = Path(HOME, 'czi/rrid_papers_sample_200_03_07_2023')
    pdf_file_rel_paths = []
    with open(pdf_list_file) as f:
        for line in f:
            line = line.strip()
            if len(line) > 0:
                pdf_file_rel_paths.append(line)
    for rp in pdf_file_rel_paths:
        pdf_file = Path(_in_dir, rp)
        handle_paper(pdf_file)
    print("done.")


def test_driver():
    in_dir = Path(HOME, 'czi/rrid_papers_sample_200_03_07_2023')
    # pdf_file = Path(in_dir, "2021_03_03_433762/main.pdf")
    # submit_a_pdf("2021_03_03_433762", pdf_file)
    # test_get_job_results(3, '/tmp/2021_03_03_433762_main_tables.json')
    pdf_file = Path(in_dir, "2020_08_28_271643/main.pdf")
    pdf_file = Path(in_dir, "2021_03_03_433772/main.pdf")
    pdf_file = Path(in_dir, "2020_07_15_204677/main.pdf")
    pdf_file = Path(in_dir, "2020_10_08_330258/main.pdf")
    pdf_file = Path(in_dir, "2023_04_18_537282/main.pdf")
    pdf_file = Path(in_dir, "2022_02_11_480021/media-1.pdf")
    pdf_file = Path(in_dir, "2021_10_22_465391/media-2.pdf")
    pdf_file = Path(in_dir, "2020_10_13_337915/main.pdf")
    handle_paper(pdf_file, use_row_info=True)
    # remove_job(6)


if __name__ == '__main__':
    cli()
    # remove_jobs_by_paper_id("2022_02_11_480021")
    # test_driver()
    # remove_job(45)
    _pdf_list_file = Path(HOME, "dev/java/pdf_table_extractor/data/row_merge/pdfs_to_table_extract.lst")
    # handle_papers(_pdf_list_file)
