import os
import os.path
import glob
import tarfile
import random
import argparse
from os.path import expanduser


def load_list(_list_file):
    with open(_list_file) as f:
        lines = [line.rstrip() for line in f]
    return lines


def make_tarfile(output_filename, rr_paths):
    with tarfile.open(output_filename, "w:gz") as tar:
        for rr_path in rr_paths:
            tar.add(rr_path, arcname=os.path.basename(rr_path))
    print(f'saved {output_filename}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", type=int, metavar="<sample-size>", default=argparse.SUPPRESS)
    parser.add_argument("-o", metavar="<out-tar-file-path>", default=argparse.SUPPRESS)
    parser.add_argument("-e", metavar="<excluded-papers-list", default=argparse.SUPPRESS)

    args = parser.parse_args()
    sample_size = 100
    out_tar_path = None
    exc_file_path = None
    if 's' in args:
        sample_size = args.s
    if 'o' in args:
        out_tar_path = args.o
    if 'e' in args:
        exc_file_path = args.e

    if os.path.isfile(exc_file_path):
        exc_set = set( load_list(exc_file_path))

    home = expanduser('~')
    in_root = home + "/data/czi/tables_out"
    path = in_root + "**/*ocr_contents*.txt"
    paper_dirs = [os.path.join(in_root, f) for f in os.listdir(in_root) if os.path.isdir(os.path.join(in_root, f))]
    rrid_paper_paths = []
    for paper_dir in paper_dirs:
        path = paper_dir + "/**/*ocr_contents*.txt"
        found = False
        for filename in glob.iglob(path, recursive=True):
            with open(filename) as f:
                contents = f.read()
                if 'RRID:' in contents:
                    found = True
                    break
        if found:
            rrid_paper_paths.append(paper_dir)
    if exc_set:
        root_dir = home + "/data/czi/pdfs"
        lst = []
        for rpp in rrid_paper_paths:
            paper_id = os.path.basename(os.path.normpath(rpp))
            if paper_id not in exc_set:
                lst.append(os.path.join(root_dir, paper_id))
        rrid_paper_paths = lst

    for rpp in rrid_paper_paths:
        print(rpp)
    print(f"found {len(rrid_paper_paths)} papers with RRIDs in tables.")
    random.seed(42)
    if len(rrid_paper_paths) > sample_size:
        rrid_paper_paths = random.sample(rrid_paper_paths, sample_size)

    if out_tar_path:
        make_tarfile(out_tar_path, rrid_paper_paths)



