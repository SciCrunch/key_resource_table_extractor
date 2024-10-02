import csv
import os
import re
import json
from datetime import datetime
import shutil
import subprocess
from pathlib import Path
import torch
import PIL
from PIL import Image
from os.path import expanduser
from transformers import DetrFeatureExtractor
from transformers import TableTransformerForObjectDetection
from collections import namedtuple

from table_model import build_table, extract_table_text, extract_table_region_text


TableImage = namedtuple('TableImage', ['image', 'left', 'top', 'right', 'bottom'])
PIL.Image.MAX_IMAGE_PIXELS = 933120000


def extract_table_images(pil_img, boxes, offset=25):
    table_images = []
    for (xmin, ymin, xmax, ymax) in boxes.tolist():
        print("xmin:{} ymin:{} xmax:{} ymax:{}".format(xmin, ymin, xmax, ymax))
        table_im = pil_img.crop((xmin - offset, ymin - offset, xmax + offset, ymax + offset))
        table_images.append(TableImage(image=table_im, left=xmin - offset, top=ymin - offset,
                                       right=xmax + offset, bottom=ymax + offset))
    return table_images


class TableExtractor(object):
    def __init__(self):
        self.device = "cuda:0" if torch.cuda.is_available() else "cpu"
        print(f"device: {self.device}")
        self.td_model = TableTransformerForObjectDetection.from_pretrained(
            "microsoft/table-transformer-detection")
        self.tsr_model = TableTransformerForObjectDetection.from_pretrained(
            "microsoft/table-transformer-structure-recognition")
        self.td_model.to(self.device)
        self.tsr_model.to(self.device)

    def extract_tables(self, page_jpg_file, out_dir=None, prefix=None, save_cell_images=False):
        result = self.detect_table_regions(page_jpg_file)
        if result:
            page_num = re.search(r"-(\d+)\.jpg", page_jpg_file).group(1)
            table_images, page_width, page_height = result
            return self.extract_table_contents(table_images, page_num, out_dir, prefix,
                                               pw=page_width, ph=page_height,
                                               save_cell_images=save_cell_images)
        return None

    def extract_tables_structures(self, page_jpg_file, out_dir=None, prefix = None):
        result = self.detect_table_regions(page_jpg_file)
        if result:
            page_num = re.search(r"-(\d+)\.jpg", page_jpg_file).group(1)
            table_images, page_width, page_height = result
            return self.extract_table_structures(table_images, page_num, out_dir, prefix,
                                                 pw=page_width, ph=page_height)
        return None

    def detect_table_regions(self, page_jpg_file):
        image = Image.open(page_jpg_file).convert("RGB")
        width, height = image.size
        image.resize((int(width * 0.5), int(height * 0.5)))
        fex = DetrFeatureExtractor()
        encoding = fex(image, return_tensors="pt")
        encoding.to(self.device)
        with torch.no_grad():
            outputs = self.td_model(**encoding)
        results = fex.post_process_object_detection(outputs, threshold=0.7,
                                                    target_sizes=[(height, width)])[0]
        print(f'page height: {height} width: {width}')
        if results and len(results['boxes']) > 0:
            table_images = extract_table_images(image, results['boxes'])
            return table_images, width, height
        return None

    def extract_table_content(self, table_image, save_cell_images=False, out_dir=None):
        width, height = table_image.image.size
        table_image.image.resize((int(width * 0.5), int(height * 0.5)))
        fex = DetrFeatureExtractor()
        table_encoding = fex(table_image.image, return_tensors="pt")
        table_encoding.to(self.device)
        with torch.no_grad():
            outputs = self.tsr_model(**table_encoding)
        target_sizes = [table_image.image.size[::-1]]
        results = fex.post_process_object_detection(outputs, threshold=0.6,
                                                    target_sizes=target_sizes)[0]
        _table = build_table(results['boxes'], results['labels'], table_image)
        start_time = datetime.now()
        if save_cell_images:
            extract_table_text(table_image.image, _table, out_dir=out_dir)
        else:
            extract_table_text(table_image.image, _table)
        time_elapsed = datetime.now() - start_time
        print(f">>> time for OCR: {time_elapsed.total_seconds()} seconds.")
        return _table

    def extract_table_structure(self, table_image):
        width, height = table_image.image.size
        table_image.image.resize((int(width * 0.5), int(height * 0.5)))
        fex = DetrFeatureExtractor()
        table_encoding = fex(table_image.image, return_tensors="pt")
        table_encoding.to(self.device)
        with torch.no_grad():
            outputs = self.tsr_model(**table_encoding)
        target_sizes = [table_image.image.size[::-1]]
        results = fex.post_process_object_detection(outputs, threshold=0.6,
                                                    target_sizes=target_sizes)[0]
        _table = build_table(results['boxes'], results['labels'], table_image)
        return _table

    def extract_table_contents(self, table_images, page_num=None, out_dir=None, prefix=None,
                               pw=None, ph=None, save_cell_images=False):
        _tables = []
        for i, table_image in enumerate(table_images):
            if save_cell_images and out_dir:
                cell_img_dirname = "{}_page_{}_table_{}_cells".format(prefix, page_num, (i + 1))
                cell_img_dir = Path(out_dir, cell_img_dirname)
                cell_img_dir.mkdir(parents=True, exist_ok=True)
                _table = self.extract_table_content(table_image, save_cell_images=save_cell_images,
                                                    out_dir=cell_img_dir)
            else:
                _table = self.extract_table_content(table_image)
            if pw and ph:
                _table.set_page_info(pw, ph)
            if out_dir:
                im_filename = "{}_page_{}_table_{}.jpg".format(prefix, page_num, (i + 1))
                filename = "{}_page_{}_table_{}.json".format(prefix, page_num, (i + 1))
                content_filename = "{}_page_{}_table_ocr_contents_{}.txt".format(prefix, page_num, (i + 1))
                csv_filename = "{}_page_{}_table_{}.csv".format(prefix, page_num, (i + 1))
                fpath = os.path.join(out_dir, filename)
                csv_path = os.path.join(out_dir, csv_filename)
                with open(fpath, 'w') as f:
                    json.dump(_table.to_json(), f, indent=2)
                    print(f'wrote {fpath}')
                with open(csv_path, 'w') as f:
                    writer = csv.writer(f, delimiter=',')
                    writer.writerows(_table.to_csv())
                    print(f'wrote CSV file {csv_path}')
                im_fpath = os.path.join(out_dir, im_filename)
                table_image.image.save(im_fpath)
                print(f'saved {im_fpath}')
                region_text = extract_table_region_text(table_image.image)
                content_fpath = os.path.join(out_dir, content_filename)
                with open(content_fpath, 'w') as f:
                    f.write(region_text)
                print(f'saved table region content to {content_fpath}')
            _tables.append(_table)
        return _tables

    def extract_table_structures(self, table_images, page_num=None, out_dir=None, prefix=None, pw=None, ph=None):
        _tables = []
        for i, table_image in enumerate(table_images):
            _table = self.extract_table_structure(table_image)
            if pw and ph:
                _table.set_page_info(pw, ph)
            if out_dir:
                im_filename = "{}_page_{}_table_{}.jpg".format(prefix, page_num, (i + 1))
                filename = "{}_page_{}_table_{}.json".format(prefix, page_num, (i + 1))
                struct_dir = Path(out_dir, 'structure')
                struct_dir.mkdir(parents=True, exist_ok=True)
                im_dir = Path(out_dir, "table_images")
                im_dir.mkdir(parents=True, exist_ok=True)
                fpath = Path(struct_dir, filename)
                with open(fpath, 'w') as f:
                    json.dump(_table.to_json(), f, indent=2)
                    print(f"wrote {fpath}")
                # save table image for debugging
                im_fpath = Path(im_dir, im_filename)
                table_image.image.save(im_fpath)
                print(f'saved {im_fpath}')

            _tables.append(_table)
        return _tables

    def save_table_images(self, page_jpg_list, out_dir, prefix):
        all_table_images = []
        for page_jpg in page_jpg_list:
            page_num = re.search(r"-(\d+)\.jpg", page_jpg).group(1)
            table_images = self.detect_table_regions(page_jpg)
            if table_images:
                for tim in table_images:
                    all_table_images.append((page_num, tim))
        if all_table_images:
            for i, (page_num, table_im) in enumerate(all_table_images):
                filename = "{}_page_{}_table_{}.jpg".format(prefix, page_num, (i+1))
                fpath = os.path.join(out_dir, filename)
                table_im.save(fpath)
                print(f"saved {fpath}.")


def pdf_to_images(pdf_file_path, out_dir):
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)
    pdf_file = os.path.basename(pdf_file_path)
    pdf_file_stem = Path(pdf_file_path).stem
    new_path = os.path.join(out_dir, pdf_file)
    shutil.copyfile(pdf_file_path, new_path)
    process = subprocess.run(['pdftoppm', pdf_file, pdf_file_stem, '-jpeg'], cwd=out_dir,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             universal_newlines=True)

    if process.returncode != 0:
        print(process.stderr)
        return []

    def page_num_order(el):
        return int(re.search(r"-(\d+)\.jpg", el).group(1))

    image_files = [os.path.join(out_dir, f) for f in os.listdir(out_dir) if re.match(r'.+\.jpg', f)]
    image_files.sort(key=page_num_order)
    return image_files


def extract_save_tables(in_root_dir):
    pdf_files = ["media-2.pdf", "media-4.pdf", "media-5.pdf", "media-6.pdf", "media-7.pdf",
                 "media-8.pdf", "media-9.pdf", "media-10.pdf", "media-11.pdf", "media-12.pdf",
                 "media-13.pdf", "media-14.pdf", "media-15.pdf", "media-16.pdf", "media-17.pdf"]
    pdf_files = ["media-8.pdf", "media-12.pdf", "media-9.pdf"]
    out_root_dir = "/tmp/tables"
    Path(out_root_dir).mkdir(parents=True, exist_ok=True)
    tex = TableExtractor()
    for pdf_file in pdf_files:
        pdf_file_path = os.path.join(in_root_dir, pdf_file)
        pdf_file_stem = Path(pdf_file).stem
        im_out_dir = os.path.join(out_root_dir, pdf_file_stem)
        Path(im_out_dir).mkdir(parents=True, exist_ok=True)
        image_files = pdf_to_images(pdf_file_path, im_out_dir)
        for image_file in image_files:
            print(image_file)
            tex.extract_tables(image_file, out_dir=im_out_dir, prefix=pdf_file_stem)


def test_driver():
    # pdf_fp = home_dir + "/dev/java/pdf_table_extractor/src/test/resources/data/media-2.pdf"
    pdf_fp = home_dir + "/dev/java/pdf_table_extractor/src/test/resources/data/media-15.pdf"
    # image_out_dir = "/tmp/media-2"
    image_out_dir = "/tmp/media-15"
    im_files = pdf_to_images(pdf_fp, image_out_dir)
    # im_files = [os.path.join(image_out_dir, f) for f in os.listdir(image_out_dir) if re.match(r'.+\.jpg', f)]
    te = TableExtractor()
    for im_file in im_files:
        print(im_file)
        tables = te.extract_tables(im_file)
        if tables:
            for table in tables:
                print(table.to_html())
                print('-' * 80)
    te.save_table_images(im_files, out_dir="/tmp", prefix="media-15")


if __name__ == '__main__':
    home_dir = expanduser('~')
    root_dir = home_dir + "/dev/java/pdf_table_extractor/src/test/resources/data"
    extract_save_tables(root_dir)
