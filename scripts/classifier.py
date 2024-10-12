import os

from sklearn.metrics import precision_recall_fscore_support, accuracy_score

os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
import random
from pathlib import Path
import argparse
import keras
import tensorflow as tf
import os.path
from os.path import expanduser

import numpy as np
from glove_handler import GloveHandler
from data_prep import load_all_instances, prep_data, prep_data_multi_input
from data_prep import save_stack_instances, save_list, load_list, StackInstance
from pg_config import get_work_dir, get_glove_db_dir
from keras.callbacks import EarlyStopping
import keras.ops as K

WD = get_work_dir()


def make_dataset(file_list, _glove_handler, _batch_size,
                 max_seq_len=40, gv_dim=100):
    instances = load_all_instances(file_list)
    xs, labels = prep_data(instances, _glove_handler, max_seq_len=max_seq_len)
    xs = xs.reshape(len(instances), max_seq_len, gv_dim)
    labels = np.array(labels)
    dataset = tf.data.Dataset.from_tensor_slices((xs, labels))
    return dataset.batch(_batch_size)


def make_dataset_multi(file_list, _glove_handler, _batch_size,
                       max_seq_len=40, gv_dim=100):
    instances = load_all_instances(file_list)
    xs, x2, labels = prep_data_multi_input(instances, _glove_handler, max_seq_len=max_seq_len)
    xs = xs.reshape(len(instances), max_seq_len, gv_dim)
    labels = np.array(labels)
    dataset_12 = tf.data.Dataset.from_tensor_slices((xs, x2))
    dataset_label = tf.data.Dataset.from_tensor_slices(labels)
    dataset = tf.data.Dataset.zip((dataset_12, dataset_label))
    return dataset.batch(_batch_size)


def make_dataset_multi_infer(file_list, _glove_handler, _batch_size,
                             max_seq_len=40, gv_dim=100):
    instances = load_all_instances(file_list)
    xs, x2, labels = prep_data_multi_input(instances, _glove_handler, max_seq_len=max_seq_len)
    xs = xs.reshape(len(instances), max_seq_len, gv_dim)
    labels = np.array(labels)
    dataset_12 = tf.data.Dataset.from_tensor_slices((xs, x2))
    dataset_label = tf.data.Dataset.from_tensor_slices(labels)
    dataset = tf.data.Dataset.zip((dataset_12, dataset_label))
    return dataset.batch(_batch_size), instances


def make_model(max_seq_len=40, gv_dim=100):
    model = keras.Sequential(
        [keras.layers.LSTM(24, dropout=0.2,
                           recurrent_dropout=0.1,
                           return_sequences=False,
                           input_shape=(max_seq_len, gv_dim)),
         keras.layers.Dense(1, activation="sigmoid"),
         ]
    )
    return model


def make_multi_inp_model(inp2_dim, max_seq_len=40, gv_dim=100):
    input1 = keras.layers.Input(shape=(max_seq_len, gv_dim,), name='lstm_input')
    # 24
    lstm = keras.layers.LSTM(64, dropout=0.3,
                             recurrent_dropout=0.2,
                             return_sequences=False,
                             input_shape=(max_seq_len, gv_dim))(input1)
    input2 = keras.layers.Input(shape=(inp2_dim,), name='wide_input')
    # hid1 = keras.layers.Dense(4, activation="relu")(input2)
    concat = keras.layers.concatenate([lstm, input2])
    output = keras.layers.Dense(1, activation="sigmoid")(concat)
    model = keras.Model(inputs=[input1, input2], outputs=[output])
    return model


def prep_file_list(root_dir, indices):
    return [os.path.join(root_dir, "media-{}_instances_annot.json".format(i)) for i in indices]


def prep_file_lists(_root_dir):
    train_indices = [2, 4, 5, 6, 7, 10, 11, 12, 13, 14, 15, 16]
    test_indices = [8, 9, 17]
    _train_paths = prep_file_list(_root_dir, train_indices)
    _test_paths = prep_file_list(_root_dir, test_indices)
    return _train_paths, _test_paths


def prep_tr_test_file_lists(_root_dir1, _root_dir2):
    train_indices1 = [2, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17]
    paths = list(Path(_root_dir2).glob("*.json"))
    random.seed(42)
    random.shuffle(paths)
    _train_paths = prep_file_list(_root_dir1, train_indices1)
    _test_paths = [str(p) for p in paths[:5]]
    for p in paths[5:]:
        _train_paths.append(str(p))
    return _train_paths, _test_paths


def prep_tr_test_file_lists_v3(_root_dir1, _root_dir2, _root_dir3):
    """prepare train/test split by combining three labeled datasets for table detection"""
    train_indices1 = [2, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17]
    paths = list(Path(_root_dir2).glob("*.json"))
    paths.extend(list(Path(_root_dir3).glob("*.json")))
    random.seed(42)
    random.shuffle(paths)
    _train_paths = prep_file_list(_root_dir1, train_indices1)
    _test_paths = [str(p) for p in paths[:10]]
    for p in paths[10:]:
        _train_paths.append(str(p))
    return _train_paths, _test_paths


def get_f1(y_true, y_pred):
    #  taken from old keras source code
    y_true = tf.cast(y_true, tf.float32)
    y_pred = tf.cast(y_pred, tf.float32)
    true_positives = K.sum(K.round(K.clip(y_true * y_pred, 0, 1)))
    possible_positives = K.sum(K.round(K.clip(y_true, 0, 1)))
    predicted_positives = K.sum(K.round(K.clip(y_pred, 0, 1)))
    precision = true_positives / (predicted_positives + keras.backend.epsilon())
    recall = true_positives / (possible_positives + keras.backend.epsilon())
    f1_val = 2 * (precision * recall) / (precision + recall + keras.backend.epsilon())
    return f1_val


def get_precision(y_true, y_pred):
    y_true = tf.cast(y_true, tf.float32)
    y_pred = tf.cast(y_pred, tf.float32)
    true_positives = K.sum(K.round(K.clip(y_true * y_pred, 0, 1)))
    predicted_positives = K.sum(K.round(K.clip(y_pred, 0, 1)))
    precision = true_positives / (predicted_positives + keras.backend.epsilon())
    return precision


def get_recall(y_true, y_pred):
    y_true = tf.cast(y_true, tf.float32)
    y_pred = tf.cast(y_pred, tf.float32)
    true_positives = K.sum(K.round(K.clip(y_true * y_pred, 0, 1)))
    possible_positives = K.sum(K.round(K.clip(y_true, 0, 1)))
    recall = true_positives / (possible_positives + keras.backend.epsilon())
    return recall


def classify_multi_inp_model(_model_path, _pdf_instance_file_paths, max_seq_len=40):
    model = keras.saving.load_model(_model_path,
                                    custom_objects={'get_f1': get_f1, 'get_recall': get_recall,
                                                    'get_precision': get_precision})
    batch_size = 64
    home = expanduser("~")
    db_file = os.path.join(home, "medline_glove_v2.db")
    glove_handler = GloveHandler(db_file)
    infer_dataset, instances = make_dataset_multi_infer(_pdf_instance_file_paths, glove_handler,
                                                        batch_size, max_seq_len=max_seq_len)
    preds = model.predict(infer_dataset)
    print(preds.shape)
    yt, ypred = [], []
    for i, pred in enumerate(preds):
        inst = instances[i]
        yt.append(1. if inst.label == 'in_table' else 0.)
        if pred >= 0.55:
            if len(inst.cur_line.strip()) < 3:
                ypred.append(0.)
                continue
            ypred.append(1.)
            if inst.label != 'in_table':
                print(f"****   {inst.cur_line} [{inst.page_id}]")
            else:
                print(f"{inst.cur_line} [{inst.page_id}]")
        else:
            ypred.append(0.)
    acc = accuracy_score(ypred, yt) * 100
    prec, recall, f1, _ = precision_recall_fscore_support(yt, ypred, average='binary')
    print(f'Testing accuracy: {acc:.2f}%')
    print(f'Testing precision:{prec:.2f} recall:{recall:.2f} f1:{f1:.2f}')


class PDFLineClassifier(object):
    def __init__(self, _model_path):
        self.model = keras.saving.load_model(_model_path,
                                             custom_objects={'get_f1': get_f1, 'get_recall': get_recall,
                                                             'get_precision': get_precision})
        self.batch_size = 64
        # home = expanduser("~")
        # db_file = os.path.join(home, "medline_glove_v2.db")
        db_file = get_glove_db_dir()
        self.glove_handler = GloveHandler(db_file)

    def prep_stack_instances(self, _pdf_instance_file_path, _out_json_file=None, max_seq_len=60):
        stack_instances = []
        infer_dataset, instances = make_dataset_multi_infer([_pdf_instance_file_path], self.glove_handler,
                                                            self.batch_size, max_seq_len=max_seq_len)
        print("prep_stack_instances:: before PDFLineClassifier prediction")
        preds = self.model.predict(infer_dataset)
        print("prep_stack_instances:: after PDFLineClassifier prediction")
        content = ''
        num_table_lines = 0
        cur_page_id = -1
        label = 'bad'
        paper_id = Path(_pdf_instance_file_path).stem
        for i, pred in enumerate(preds):
            inst = instances[i]
            if cur_page_id == -1:
                cur_page_id = inst.page_id
            elif cur_page_id != inst.page_id:
                if num_table_lines > 0 or label == 'good':
                    jsd = {'paper_id': paper_id, 'page_id': cur_page_id,
                           'label': label, 'content': content,
                           'num_table_lines': num_table_lines}
                    stack_instances.append(StackInstance(jsd))
                content = ''
                num_table_lines = 0
                label = 'bad'
                cur_page_id = inst.page_id

            content += inst.cur_line + '\n'
            if inst.label == 'in_table':
                label = 'good'
            if pred >= 0.55:
                num_table_lines += 1
        if num_table_lines > 0 or label == 'good':
            jsd = {'paper_id': paper_id, 'page_id': cur_page_id,
                   'label': label, 'content': content,
                   'num_table_lines': num_table_lines}
            stack_instances.append(StackInstance(jsd))
        if _out_json_file:
            save_stack_instances(stack_instances, _out_json_file)
        return stack_instances


def prep_stack_instances(_model_path, _pdf_instance_file_paths, _out_json_file, max_seq_len=40):
    model = keras.saving.load_model(_model_path,
                                    custom_objects={'get_f1': get_f1, 'get_recall': get_recall,
                                                    'get_precision': get_precision})
    batch_size = 64
    home = expanduser("~")
    db_file = os.path.join(home, "medline_glove_v2.db")
    glove_handler = GloveHandler(db_file)
    stack_instances = []
    for pdf_inst_file_path in _pdf_instance_file_paths:
        infer_dataset, instances = make_dataset_multi_infer([pdf_inst_file_path], glove_handler,
                                                            batch_size, max_seq_len=max_seq_len)
        preds = model.predict(infer_dataset)
        content = ''
        num_table_lines = 0
        cur_page_id = -1
        label = 'bad'
        paper_id = Path(pdf_inst_file_path).stem
        for i, pred in enumerate(preds):
            inst = instances[i]
            if cur_page_id == -1:
                cur_page_id = inst.page_id
            elif cur_page_id != inst.page_id:
                if num_table_lines > 0 or label == 'good':
                    jsd = {'paper_id': paper_id, 'page_id': cur_page_id,
                           'label': label, 'content': content,
                           'num_table_lines': num_table_lines}
                    stack_instances.append(StackInstance(jsd))
                content = ''
                num_table_lines = 0
                label = 'bad'
                cur_page_id = inst.page_id

            content += inst.cur_line + '\n'
            if inst.label == 'in_table':
                label = 'good'
            if pred >= 0.55:
                num_table_lines += 1
        if num_table_lines > 0 or label == 'good':
            jsd = {'paper_id': paper_id, 'page_id': cur_page_id,
                   'label': label, 'content': content,
                   'num_table_lines': num_table_lines}
            stack_instances.append(StackInstance(jsd))
    save_stack_instances(stack_instances, _out_json_file)


def handle_multi_inp_model():
    batch_size = 64
    home = expanduser("~")
    db_file = os.path.join(home, "medline_glove_v2.db")
    glove_handler = GloveHandler(db_file)
    msl = 60
    data_dir = os.path.join(home, 'dev/java/pdf_table_extractor/data/table_detection/annotated')
    train_paths, test_paths = prep_file_lists(data_dir)
    train_dataset = make_dataset_multi(train_paths, glove_handler, batch_size, max_seq_len=msl)
    test_dataset = make_dataset_multi(test_paths, glove_handler, batch_size, max_seq_len=msl)
    epochs = 10
    model = make_multi_inp_model(7, max_seq_len=msl)
    model.compile(loss="binary_crossentropy", optimizer="adam",
                  metrics=["accuracy", get_f1, get_precision, get_recall])
    history = model.fit(train_dataset, validation_data=test_dataset,
                        epochs=epochs, callbacks=[EarlyStopping(monitor='val_accuracy',
                                                                patience=3)])
    print(history.history)
    glove_handler.close()
    model_path = '/tmp/table_detect_classifier'
    model.save(model_path)
    print(f'saved model to {model_path}')


def handle_multi_inp_model_v2():
    batch_size = 64
    home = expanduser("~")
    db_file = os.path.join(home, "medline_glove_v2.db")
    glove_handler = GloveHandler(db_file)
    data_dir1 = os.path.join(WD, 'data/table_detection/annotated')
    data_dir2 = os.path.join(WD, 'data/table_detection_v2/annotated')
    train_paths, test_paths = prep_tr_test_file_lists(data_dir1, data_dir2)
    save_list(train_paths, "/tmp/train_paths.lst")
    save_list(test_paths, "/tmp/test_paths.lst")
    msl = 60
    train_dataset = make_dataset_multi(train_paths, glove_handler, batch_size, max_seq_len=msl)
    test_dataset = make_dataset_multi(test_paths, glove_handler, batch_size, max_seq_len=msl)
    epochs = 10
    model = make_multi_inp_model(7, max_seq_len=msl)
    model.compile(loss="binary_crossentropy", optimizer="adam",
                  metrics=["accuracy", get_f1, get_precision, get_recall])
    class_weight = {0: 1., 1: 50.}
    history = model.fit(train_dataset, validation_data=test_dataset,
                        epochs=epochs, class_weight=class_weight)
    print(history.history)
    glove_handler.close()
    model_path = '/tmp/table_detect_classifier.keras'
    model.save(model_path)
    # tf.saved_model.save(model, model_path) # Keras 3
    print(f'saved model to {model_path}')


def handle_lstm_model():
    batch_size = 64
    home = expanduser("~")
    db_file = os.path.join(home, "medline_glove_v2.db")
    glove_handler = GloveHandler(db_file)
    data_dir = os.path.join(home, 'dev/java/pdf_table_extractor/data/table_detection/annotated')
    train_paths, test_paths = prep_file_lists(data_dir)
    train_dataset = make_dataset(train_paths, glove_handler, batch_size)
    test_dataset = make_dataset(test_paths, glove_handler, batch_size)

    epochs = 5
    lstm_model = make_model()
    lstm_model.compile(loss="binary_crossentropy", optimizer="adam", metrics=["accuracy"])

    history = lstm_model.fit(train_dataset, validation_data=test_dataset, epochs=epochs)
    print(history.history)
    glove_handler.close()
    model_path = '/tmp/table_detect_classifier'

    lstm_model.save(model_path)
    print(f'saved model to {model_path}')


def handle_lstm_model_v2():
    batch_size = 64
    home = expanduser("~")
    db_file = os.path.join(home, "medline_glove_v2.db")
    glove_handler = GloveHandler(db_file)
    data_dir1 = os.path.join(home, 'dev/java/pdf_table_extractor/data/table_detection/annotated')
    data_dir2 = os.path.join(home, 'dev/java/pdf_table_extractor/data/table_detection_v2/annotated')
    train_paths, test_paths = prep_tr_test_file_lists(data_dir1, data_dir2)
    train_dataset = make_dataset(train_paths, glove_handler, batch_size)
    test_dataset = make_dataset(test_paths, glove_handler, batch_size)

    epochs = 5
    lstm_model = make_model()
    lstm_model.compile(loss="binary_crossentropy", optimizer="adam", metrics=["accuracy"])

    history = lstm_model.fit(train_dataset, validation_data=test_dataset, epochs=epochs)
    print(history.history)
    glove_handler.close()
    model_path = '/tmp/table_detect_classifier'
    lstm_model.save(model_path)
    print(f'saved model to {model_path}')


def do_classify():
    root_dir = os.path.join(WD, "data/table_detection_v2/annotated")
    test_files = ['2021_02_14_431158_main_instances_annot.json', '2022_10_19_512981_main_instances_annot.json',
                  '2021_06_01_446584_main_instances_annot.json', '2023_01_18_524631_media-1_instances_annot.json',
                  '2021_06_28_450131_main_instances_annot.json']
    model_path = '/tmp/table_detect_classifier.keras'
    for test_file in test_files:
        file_path = os.path.join(root_dir, test_file)
        print(file_path)
        print('-' * 80)
        classify_multi_inp_model(model_path, [file_path], max_seq_len=60)
        print('=' * 80)
        print("")


def do_prep_stack_instances():
    pdf_inst_file_paths = load_list('/tmp/train_paths.lst')
    model_path = '/tmp/table_detect_classifier.keras'
    out_json_file = '/tmp/stacked_gen_train_instances.json'
    prep_stack_instances(model_path, pdf_inst_file_paths, out_json_file, max_seq_len=60)

    test_pdf_inst_file_paths = load_list('/tmp/test_paths.lst')
    test_out_json_path = '/tmp/stacked_gen_test_instances.json'
    prep_stack_instances(model_path, test_pdf_inst_file_paths, test_out_json_path, max_seq_len=60)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", required=True, metavar="<command one of [train, test, stack-gen-prep]>")
    args = parser.parse_args()
    cmd = args.c
    if cmd == 'train':
        handle_multi_inp_model_v2()
    elif cmd == 'test':
        do_classify()
    elif cmd == 'stack-gen-prep':
        do_prep_stack_instances()
