import os
import argparse
from pathlib import Path
import time
from datetime import timedelta
from tqdm import tqdm


from extract_tables_from_pdf import TableExtractor, pdf_to_images


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", required=True, metavar="<input-root-dir>")
    parser.add_argument("-o", required=True, metavar="out-root-dir")
    args = parser.parse_args()
    in_root_dir = args.i
    out_root_dir = args.o

    if not Path(in_root_dir).is_dir():
        raise argparse.ArgumentTypeError('input root directory is not available: ' + in_root_dir)
    Path(out_root_dir).mkdir(parents=True, exist_ok=True)

    tex = TableExtractor()
    in_paper_dirs = [f.path for f in os.scandir(in_root_dir) if f.is_dir()]
    all_start = time.perf_counter()
    for paper_path in tqdm(in_paper_dirs):
        paper_start = time.perf_counter()
        paper_stem = Path(paper_path).stem
        print(f'handling paper: {paper_stem}')
        paper_out_dir = os.path.join(out_root_dir, paper_stem)
        if Path(paper_out_dir).is_dir():
            print(f'Already processed. Skipping {paper_stem}...')
            continue
        Path(paper_out_dir).mkdir(parents=True, exist_ok=True)
        pdf_files = [f.path for f in os.scandir(paper_path) if f.is_file() and f.name.endswith('.pdf')]
        for pdf_file in pdf_files:
            pdf_file_path = os.path.join(paper_path, pdf_file)
            pdf_file_stem = Path(pdf_file).stem
            im_out_dir = os.path.join(paper_out_dir, pdf_file_stem)
            Path(im_out_dir).mkdir(parents=True, exist_ok=True)
            image_files = pdf_to_images(pdf_file_path, im_out_dir)
            for image_file in image_files:
                print(image_file)
                tex.extract_tables(image_file, out_dir=im_out_dir, prefix=pdf_file_stem, save_cell_images=True)
        print(f'finished paper: {paper_stem}')
        pt_delta = time.perf_counter() - paper_start
        print(f"processed {paper_stem} in {pt_delta:0.4f} seconds")
        print('-' * 80)
    at_delta = time.perf_counter() - all_start
    print(f"All processed in {at_delta:0.4f} seconds.")
    print(f"Total time elapsed: {timedelta(seconds=at_delta)}")
    print('=' * 80)


