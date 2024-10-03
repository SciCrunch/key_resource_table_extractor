import pickle
import os.path
import numpy as np
import joblib
from scipy.sparse import hstack
from sklearn import svm
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import accuracy_score, precision_recall_fscore_support
from sklearn.preprocessing import LabelEncoder, OneHotEncoder

from data_prep import load_stack_instances
from pg_config import get_work_dir

# HOME = os.path.expanduser('~')
# WD = os.path.join(HOME, "dev/java/pdf_table_extractor")
WD = get_work_dir()


def train_bow_svm(_instances, _tst_instances):
    contents = [i.content for i in _instances]
    text_labels = [i.label for i in _instances]
    vectorizer = TfidfVectorizer(sublinear_tf=True, max_df=0.5, min_df=1)
    features = vectorizer.fit_transform(contents)
    print(features.shape)
    encoder = LabelEncoder()
    y = encoder.fit_transform(text_labels)
    clf = svm.SVC(C=1.0, kernel='linear', class_weight={1: 5})
    clf.fit(features, y)
    joblib.dump(clf, '/tmp/stacked_gen_rel_table_page_detect.sav')

    test_contents = [i.content for i in _tst_instances]
    test_labels = [i.label for i in _tst_instances]
    test_features = vectorizer.transform(test_contents)
    yt = encoder.transform(test_labels)
    preds = clf.predict(test_features)
    for i, pred in enumerate(preds):
        ti = _tst_instances[i]
        true_label = yt[i]
        if true_label == 1:
            print(f"{ti.paper_id}:{ti.page_id} true_label: {true_label} pred: {pred}")
    print('-' * 80)

    acc = accuracy_score(preds, yt) * 100
    prec, recall, f1, _ = precision_recall_fscore_support(yt, preds, average='binary')
    print(f'Testing accuracy: {acc:.2f}%')
    print(f'Testing precision:{prec:.2f} recall:{recall:.2f} f1:{f1:.2f}')


def train_stacked_gen_bow_svm(_instances, _tst_instances):
    contents = [i.content for i in _instances]
    text_labels = [i.label for i in _instances]
    vectorizer = TfidfVectorizer(sublinear_tf=True, max_df=0.5, min_df=1)
    features = vectorizer.fit_transform(contents)
    with open('/tmp/stacked_gen_vectorizer.pk', 'wb') as f:
        pickle.dump(vectorizer, f)

    oh_enc1 = OneHotEncoder(handle_unknown='ignore')
    oh_enc2 = OneHotEncoder(handle_unknown='ignore')
    htl_list = [i.num_table_lines > 0 for i in _instances]
    mhtl_list = [i.num_table_lines > 3 for i in _instances]
    htl_one_hot = oh_enc1.fit_transform(np.array(htl_list).reshape(-1, 1))
    mhtl_one_hot = oh_enc2.fit_transform(np.array(mhtl_list).reshape(-1, 1))
    joblib.dump(oh_enc1, "/tmp/htl_one_hot.sav")
    joblib.dump(oh_enc2, "/tmp/mhtl_one_hot.sav")
    features = hstack((htl_one_hot, mhtl_one_hot, features))
    print(features.shape)
    encoder = LabelEncoder()
    y = encoder.fit_transform(text_labels)
    clf = svm.SVC(C=1.0, kernel='linear', class_weight={1: 5})
    clf.fit(features, y)
    joblib.dump(clf, '/tmp/stacked_gen_rel_table_page_detect.sav')

    test_contents = [i.content for i in _tst_instances]
    test_labels = [i.label for i in _tst_instances]
    test_features = vectorizer.transform(test_contents)
    test_htl_list = [i.num_table_lines > 0 for i in _tst_instances]
    test_mhtl_list = [i.num_table_lines > 3 for i in _tst_instances]
    test_htl_one_hot = oh_enc1.transform(np.array(test_htl_list).reshape(-1, 1))
    test_mhtl_one_host = oh_enc2.transform(np.array(test_mhtl_list).reshape(-1, 1))
    test_features = hstack((test_htl_one_hot, test_mhtl_one_host, test_features))

    yt = encoder.transform(test_labels)
    preds = clf.predict(test_features)
    acc = accuracy_score(preds, yt) * 100
    prec, recall, f1, _ = precision_recall_fscore_support(yt, preds, average='binary')
    print(f'Testing accuracy: {acc:.2f}%')
    print(f'Testing precision:{prec:.2f} recall:{recall:.2f} f1:{f1:.2f}')


class RelTablePageClassifier(object):
    def __init__(self):
        clf_path = os.path.join(WD, "models/stacked_gen_rel_table_page_detect.sav")
        vectorizer_path = os.path.join(WD, "models/stacked_gen_vectorizer.pk")
        self.oh_enc1 = joblib.load(os.path.join(WD, "models/htl_one_hot.sav"))
        self.oh_enc2 = joblib.load(os.path.join(WD, "models/mhtl_one_hot.sav"))
        with open(vectorizer_path, 'rb') as f:
            self.vectorizer = pickle.load(f)
        self.clf = joblib.load(clf_path)

    def get_detected_pages(self, _instances):
        contents = [i.content for i in _instances]
        features = self.vectorizer.transform(contents)
        htl_list = [i.num_table_lines > 0 for i in _instances]
        mhtl_list = [i.num_table_lines > 4 for i in _instances]
        htl_one_hot = self.oh_enc1.transform(np.array(htl_list).reshape(-1, 1))
        mhtl_one_host = self.oh_enc2.transform(np.array(mhtl_list).reshape(-1, 1))
        features = hstack((htl_one_hot, mhtl_one_host, features))
        preds = self.clf.predict(features)
        pages = []
        for i, pred in enumerate(preds):
            inst = _instances[i]
            if pred > 0:
                print(f"{inst.paper_id} page:{inst.page_id} ")
                pages.append({"paper_id": inst.paper_id, "page": inst.page_id})
        return pages


def do_train():
    instances = load_stack_instances('/tmp/stacked_gen_train_instances.json')
    test_instances = load_stack_instances('/tmp/stacked_gen_test_instances.json')
    # train_bow_svm(instances, test_instances)
    train_stacked_gen_bow_svm(instances, test_instances)


def do_bow_only_train():
    instances = load_stack_instances('/tmp/stacked_gen_train_instances.json')
    test_instances = load_stack_instances('/tmp/stacked_gen_test_instances.json')
    train_bow_svm(instances, test_instances)


def test_classifier():
    clf = RelTablePageClassifier()
    test_instances = load_stack_instances('/tmp/stacked_gen_test_instances.json')
    clf.get_detected_pages(test_instances)


if __name__ == '__main__':
    # do_bow_only_train()
    do_train()
    # test_classifier()
