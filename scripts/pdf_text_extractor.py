import os
import re
import subprocess

from pathlib import Path


def pdf_to_text(pdf_file_path, out_dir):
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)
    p = Path(pdf_file_path)
    pdf_file_stem = p.stem
    paper_id = p.parent.name
    out_file_name = "{}_{}.txt".format(paper_id, pdf_file_stem)
    out_path = os.path.join(out_dir, out_file_name)
    process = subprocess.run(['pdftotext', pdf_file_path, out_path], stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, universal_newlines=True)
    if process.returncode != 0:
        print(process.stderr)
        return None
    return out_path


def extract_text_from_papers(pdf_in_dir: str, out_dir, merged_file):
    paper_dirs = [Path(f.path) for f in os.scandir(Path(pdf_in_dir)) if f.is_dir()]
    out_files = []
    for pd in paper_dirs:
        pdf_files = pd.glob("*.pdf")
        for pdf_file in pdf_files:
            print(pdf_file)
            out_file = pdf_to_text(pdf_file, out_dir)
            if out_file:
                out_files.append(out_file)
    with open(merged_file, 'w') as out:
        for out_file in out_files:
            print(f"merging {out_file}")
            with open(out_file) as f:
                for line in f:
                    out.write(line)
        out.write("\n\n")
    print("done.")


def remove_line_numbers(in_file, out_file):
    with open(out_file, 'w') as out:
        with open(in_file) as f:
            for line in f:
                if re.search(r'^\d+$', line.strip()):
                    continue
                else:
                    out.write(line)
    print(f"wrote {out_file}")


if __name__ == "__main__":
    HOME = os.path.expanduser('~')
    czi_pdf_dir = os.path.join(HOME, "czi/rrid_papers_sample_200_03_07_2023")
    # extract_text_from_papers(czi_pdf_dir, "/tmp/czi_papers_text", "/tmp/czi_papers_corpus.txt")
    remove_line_numbers("/tmp/czi_papers_corpus.txt", "/tmp/czi_papers_corpus_cleaned.txt")
