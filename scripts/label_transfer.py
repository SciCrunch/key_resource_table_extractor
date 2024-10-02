import os
from pathlib import Path
from data_prep import load_instances
from data_prep_2 import load_instances as load_instances2
from data_prep_2 import save_instances


HOME = os.path.expanduser("~")
WD = os.path.join(HOME, "dev/java/pdf_table_extractor")


def transfer_labels(label_json_file, instance2_json_file, out_json_file):
    labeled_list = load_instances(label_json_file)
    inst2_list = load_instances2(instance2_json_file)
    print(f"labeled_list: {len(labeled_list)} inst2_list: {len(inst2_list)}")
    for i, inst2 in enumerate(inst2_list):
        labeled = labeled_list[i+1]
        inst2.label = labeled.label
    save_instances(inst2_list, out_json_file)


def do_label_transfer(labeled_dir, inst2_dir, out_dir):
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    labeled_files = list(Path(labeled_dir).glob("*.json"))
    for lf in labeled_files:
        lf_name = str(lf.name)
        inst2_name = lf_name.replace('_annot', '')
        inst2_path = Path(inst2_dir, inst2_name)
        out_path = Path(out_dir, lf_name)
        print(f"lf: {lf}")
        print(f"inst2: {inst2_path}")
        transfer_labels(lf, inst2_path, out_path)
    print('done.')


def handle_v2():
    lj_file = os.path.join(WD, "data//table_detection_v2/annotated/2022_10_19_512839_main_instances_annot.json")
    i2_file = '/tmp/out/2022_10_19_512839_main_instances.json'
    out_file = '/tmp/2022_10_19_512839_main_instances_labeled.json'
    # transfer_labels(lj_file, i2_file, out_file)
    labeled_dir = os.path.join(WD, 'data/table_detection_v2/annotated')
    inst2_dir = '/tmp/out'
    out_dir = '/tmp/labeled'
    do_label_transfer(labeled_dir, inst2_dir, out_dir)


def handle_v1():
    labeled_dir = os.path.join(WD, 'data/table_detection/annotated')
    inst2_dir = '/tmp/out_v1'
    out_dir = '/tmp/labeled_v1'
    do_label_transfer(labeled_dir, inst2_dir, out_dir)


if __name__ == '__main__':
    # handle_v1()
    handle_v2()

