import csv
import re
import numpy as np

from collections import namedtuple
from statistics import mean

from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from sklearn.preprocessing import KBinsDiscretizer, LabelEncoder, OneHotEncoder
from sklearn import svm
from sklearn.metrics import accuracy_score, precision_recall_fscore_support
from scipy.sparse import hstack
from matplotlib import pyplot as plt

Instance = namedtuple('Instance', "paper_name table_name label content has_line_numbers length")


def load_data(_csv_file):
    _instances = []
    with open(_csv_file, 'r') as f:
        reader = csv.reader(f, delimiter=',')
        first = True
        for row in reader:
            if first:
                first = False
                continue
            paper_name = row[0]
            table_name = row[1]
            file_path = row[2]
            label = row[3]
            with open(file_path, 'r') as fp:
                content = fp.read()
            _has_line_numbers = has_line_numbers(content)
            inst = Instance(paper_name=paper_name, table_name=table_name, label=label,
                            content=content, has_line_numbers=_has_line_numbers, length=len(content))
            _instances.append(inst)
    return _instances


def show_good_pdfs(_instances):
    good_ones = [i for i in _instances if i.label == 'good']

    pdf_paths = set()
    for inst in good_ones:
        # print(f"{inst.paper_name} -- {inst.table_name}")
        pdf_name = inst.table_name.split('_')[0]
        pdf_path = inst.paper_name + "/" + pdf_name + '/' + pdf_name + '.pdf'
        pdf_paths.add(pdf_path)
    pdf_paths = sorted(pdf_paths)
    print('-' * 80)
    for pdf_path in pdf_paths:
        print(pdf_path)
    print('-' * 80)
    print(f"# of pdfs: {len(pdf_paths)}")


def has_line_numbers(_content):
    if len(_content) == 0:
        return False
    lines = _content.split('\n')
    count = 0
    for line in lines:
        line = line.strip()
        m = re.search(r"^\d+$", line)
        if m:
            count += 1
    if count > len(lines) / 3:
        return True

    return False


def plot_coefficients(classifier, feature_names, top_features=20):
    coef = classifier.coef_.toarray().transpose().flatten()

    top_positive_coefficients = np.argsort(coef)[-top_features:]
    top_negative_coefficients = np.argsort(coef)[:top_features]
    top_coefficients = np.hstack([top_negative_coefficients, top_positive_coefficients])
    # create plot
    # plt.figure(figsize=(15, 5))
    colors = ['red' if c < 0 else 'blue' for c in coef[top_coefficients]]
    plt.bar(np.arange(2 * top_features), coef[top_coefficients], color=colors)
    feature_names = np.array(feature_names)
    plt.xticks(np.arange(1, 1 + 2 * top_features), feature_names[top_coefficients], rotation=60, ha='right')
    plt.show()


def train_bow_svm(_instances):
    contents = [i.content for i in _instances]
    text_labels = [i.label for i in _instances]
    vectorizer = TfidfVectorizer(sublinear_tf=True, max_df=0.5, min_df=1)
    #                             stop_words="english")
    features = vectorizer.fit_transform(contents)
    print(features.shape)
    encoder = LabelEncoder()
    y = encoder.fit_transform(text_labels)
    clf = svm.SVC(C=100.0, kernel='linear', class_weight={1: 5})
    clf.fit(features, y)

    plot_coefficients(clf, vectorizer.get_feature_names_out())
    preds = clf.predict(features)
    acc = accuracy_score(preds, y) * 100
    prec, recall, f1, _ = precision_recall_fscore_support(y, preds, average='binary')
    print(f'Training accuracy: {acc:.2f}%')
    print(f'Training precision:{prec:.2f} recall:{recall:.2f} f1:{f1:.2f}')


def train_ngram_svm(_instances):
    contents = [i.content for i in _instances]
    text_labels = [i.label for i in _instances]
    vectorizer = CountVectorizer(ngram_range=(1, 2), max_df=0.5, min_df=1,
                                 stop_words="english")
    features = vectorizer.fit_transform(contents)
    print(features.shape)
    encoder = LabelEncoder()
    y = encoder.fit_transform(text_labels)
    clf = svm.SVC(C=1.0, kernel='linear', class_weight={1: 5})
    clf.fit(features, y)
    plot_coefficients(clf, vectorizer.get_feature_names_out())
    preds = clf.predict(features)
    acc = accuracy_score(preds, y) * 100
    prec, recall, f1, _ = precision_recall_fscore_support(y, preds, average='binary')
    print(f'Training accuracy: {acc:.2f}%')
    print(f'Training precision:{prec:.2f} recall:{recall:.2f} f1:{f1:.2f}')


def train_bow_svm2(_instances):
    contents = [i.content for i in _instances]
    text_labels = [i.label for i in _instances]
    vectorizer = TfidfVectorizer(sublinear_tf=True, max_df=0.5, min_df=1,
                                 stop_words="english")
    features = vectorizer.fit_transform(contents)
    len_list = [i.length for i in instances]
    est = KBinsDiscretizer(n_bins=10, encode='onehot')
    X = np.array(len_list).reshape(-1, 1)
    est.fit(X)
    lent = est.transform(X)
    oh_enc = OneHotEncoder()
    hln_list = [i.has_line_numbers for i in _instances]
    X = np.array(hln_list).reshape(-1, 1)
    hln_one_hot = oh_enc.fit_transform(X)
    features = hstack((features, lent, hln_one_hot))
    # features = features.todense()
    print(features.shape)
    encoder = LabelEncoder()
    y = encoder.fit_transform(text_labels)
    clf = svm.SVC(C=10.0, kernel='linear', class_weight={1: 10})
    clf.fit(features, y)
    preds = clf.predict(features)
    acc = accuracy_score(preds, y) * 100
    prec, recall, f1, _ = precision_recall_fscore_support(y, preds, average='binary')
    print(f'Training accuracy: {acc:.2f}%')
    print(f'Training precision:{prec:.2f} recall:{recall:.2f} f1:{f1:.2f}')


if __name__ == '__main__':
    tr_csv_file = '/tmp/table_type_annotations/table_type_annotations.csv'
    instances = load_data(tr_csv_file)
    print(f"loaded {len(instances)} instances.")
    show_good_pdfs(instances)
    len_list = [i.length for i in instances]
    min_len = min(len_list)
    max_len = max(len_list)
    avg_len = mean(len_list)
    print(f"Content length min: {min_len} max: {max_len} avg: {avg_len}")
    est = KBinsDiscretizer(n_bins=5, encode='onehot', strategy='kmeans')
    X = np.array(len_list).reshape(-1, 1)
    est.fit(X)
    lent = est.transform(X)
    train_ngram_svm(instances)