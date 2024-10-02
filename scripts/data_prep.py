import json
import re

import numpy as np
import nltk
from nltk.tokenize import word_tokenize
from tqdm import tqdm

# make sure 
try:
    word_tokenize('this is a test')
except LookupError:
    nltk.download('punkt_tab')


class Instance(object):
    def __init__(self, jsd):
        self.id = jsd['id']
        self.cur_line = jsd['currentLine']
        self.prev_line = jsd['previousLine']
        self.label = jsd['label']
        self.page_id = int(jsd['pageId'])
        self.has_vt_lines = jsd['hasVerticalLines']
        self.has_vt_lines2 = jsd['hasVerticalLines2']
        self.has_ht_lines = jsd['hasHorizontalLines']
        self.has_ht_lines2 = jsd['hasHorizontalLines2']

    def has_line_number(self):
        return re.search(r"^\d+\s+", self.cur_line) is not None


def load_all_instances(json_files):
    instances = []
    for json_file in json_files:
        print(f" loading {json_file}")
        instances.extend(load_instances(json_file))
    print(f"loaded {len(instances)} instances.")
    return instances


def load_instances(json_file):
    with open(json_file) as f:
        data = json.load(f)
    instances = []
    for rec in data:
        inst = Instance(rec)
        instances.append(inst)
    return instances


def tokenize(instance, prev_page_id):
    s = ''
    if instance.page_id != prev_page_id:
        s += '<PS> '
    tokens = word_tokenize(instance.prev_line)
    if len(tokens) == 0:
        s += '<EL> '
    else:
        s += ' '.join(tokens)
        s += '<EOL> '
    tokens = word_tokenize(instance.cur_line)
    if len(tokens) == 0:
        s += '<EL> '
    else:
        s += ' '.join(tokens)
    return s.split()


def get_glove_vec(token, glove_handler):
    vec = glove_handler.get_glove_vec(token)
    if vec:
        return vec
    else:
        if token == '<EL>':
            return glove_handler.get_glove_vec('unk1')
        elif token == '<EOL>':
            return glove_handler.get_glove_vec('unk2')
        elif token == '<PS>':
            return glove_handler.get_glove_vec('unk3')
        else:
            return glove_handler.get_glove_vec('unk4')


def prep_data(instances, glove_handler, max_seq_len=40, gv_dim=100):
    xs = np.zeros((len(instances), max_seq_len * gv_dim), dtype='float32')
    labels = []
    prev_page_id = None
    long_count = 0
    for i, inst in enumerate(tqdm(instances)):
        if not prev_page_id:
            prev_page_id = inst.page_id
        tokens = tokenize(inst, prev_page_id)
        for j, token in enumerate(tokens):
            if j >= max_seq_len:
                long_count += 1
                break
            offset = j * gv_dim
            vec = get_glove_vec(token, glove_handler)
            xs[i, offset:offset + gv_dim] = vec
        prev_page_id = inst.page_id
        label = 1 if inst.label == 'in_table' else 0
        labels.append(label)
    print(f"# of truncated instances: {long_count} out of {len(instances)}")
    return xs, labels


def has_rrid(line):
    m = re.match('\brrid', line.lower())
    return m


def prep_data_multi_input(instances, glove_handler, max_seq_len=40, gv_dim=100):
    xs = np.zeros((len(instances), max_seq_len * gv_dim), dtype='float32')
    x2 = np.zeros((len(instances), 7), dtype='float32')
    labels = []
    prev_page_id = None
    long_count = 0
    for i, inst in enumerate(tqdm(instances)):
        if not prev_page_id:
            prev_page_id = inst.page_id
        tokens = tokenize(inst, prev_page_id)
        for j, token in enumerate(tokens):
            if j >= max_seq_len:
                long_count += 1
                break
            offset = j * gv_dim
            vec = get_glove_vec(token, glove_handler)
            xs[i, offset:offset + gv_dim] = vec
        prev_page_id = inst.page_id
        label = 1 if inst.label == 'in_table' else 0
        labels.append(label)
        if inst.has_vt_lines:
            x2[i, 0] = 1.0
        if inst.has_vt_lines2:
            x2[i, 1] = 1.0
        if inst.has_ht_lines:
            x2[i, 2] = 1.0
        if inst.has_ht_lines2:
            x2[i, 3] = 1.0
        if has_rrid(inst.cur_line):
            x2[i, 4] = 1.0
        if has_rrid(inst.prev_line):
            x2[i, 5] = 1.0
        if inst.has_line_number():
            x2[i, 6] = 1.0
    print(f"# of truncated instances: {long_count} out of {len(instances)}")
    return xs, x2, labels


class StackInstance:
    def __init__(self, jsd):
        self.paper_id = jsd['paper_id']
        self.page_id = jsd['page_id']
        self.label = jsd['label']
        self.content = jsd['content']
        self.num_table_lines = jsd['num_table_lines']

    def to_json(self):
        return {'paper_id': self.paper_id, 'page_id': self.page_id,
                'label': self.label, 'content': self.content,
                'num_table_lines': self.num_table_lines}


def load_stack_instances(json_file):
    with open(json_file) as f:
        data = json.load(f)
    instances = []
    for rec in data:
        inst = StackInstance(rec)
        instances.append(inst)
    return instances


def save_stack_instances(_instances, out_json_file):
    lst = [inst.to_json() for inst in _instances]
    with open(out_json_file, 'w') as f:
        json.dump(lst, f, indent=2)
        print(f"wrote {out_json_file}")


def load_list(_list_file):
    with open(_list_file) as f:
        lines = [line.rstrip() for line in f]
    return lines


def save_list(_list, _list_file):
    with open(_list_file, 'w') as f:
        for el in _list:
            f.write(el + '\n')
        print(f"wrote {_list_file}")

