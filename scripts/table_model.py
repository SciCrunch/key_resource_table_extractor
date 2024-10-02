import json
import os.path
import pickle
import pytesseract
from PIL import ImageEnhance


class Rectangle(object):
    def __init__(self, _left, _top, _right, _bottom):
        self.left = _left
        self.top = _top
        self.right = _right
        self.bottom = _bottom

    def contains(self, other):
        return (self.left <= other.left and self.right >= other.right and
                self.top <= other.top and self.bottom >= other.bottom)


class TableCell(object):
    def __init__(self, _left, _top, _right, _bottom, _span=1):
        self.left = _left
        self.top = _top
        self.right = _right
        self.bottom = _bottom
        self.span = _span
        self.text = ""

    def to_html(self):
        return '<td>' + self.text + '</td>'

    def to_csv(self):
        return self.text

    def to_json(self):
        return {'span': self.span, 'text': self.text, 'left': self.left, 'top': self.top,
                'right': self.right, 'bottom': self.bottom}

    @classmethod
    def from_json(cls, data):
        c = cls(data['left'], data['top'], data['right'], data['bottom'], data['span'])
        c.text = data['text']
        return c


class ColumnHeader(object):
    def __init__(self, _left, _top, _right, _bottom):
        self.left = _left
        self.top = _top
        self.right = _right
        self.bottom = _bottom
        self.text = ""


class TableRow(object):
    def __init__(self, _left, _top, _right, _bottom):
        self.left = _left
        self.top = _top
        self.right = _right
        self.bottom = _bottom
        self.cells = []

    def add_cell(self, cell: TableCell):
        self.cells.append(cell)

    def to_html(self):
        s = '<tr>\n'
        for cell in self.cells:
            s += "\t" + cell.to_html() + "\n"
        s += '</tr>'
        return s

    def to_csv(self):
        return [cell.to_csv() for cell in self.cells]

    def to_json(self):
        cells_js = [c.to_json() for c in self.cells]
        return {'left': self.left, 'top': self.top, 'right': self.right,
                'bottom': self.bottom, 'cells': cells_js}

    @classmethod
    def from_json(cls, data):
        c = cls(data['left'], data['top'], data['right'], data['bottom'])
        cells = data['cells']
        for cell in cells:
            c.add_cell(TableCell.from_json(cell))
        return c


class HeaderRow(object):
    def __init__(self, _left, _top, _right, _bottom):
        self.left = _left
        self.top = _top
        self.right = _right
        self.bottom = _bottom
        self.headers = []

    def add_header(self, header: ColumnHeader):
        self.headers.append(header)


class Table(object):
    def __init__(self, left, top, right, bottom):
        self.table_image = None
        self.header = None
        self.rows = []
        self.left = left
        self.top = top
        self.right = right
        self.bottom = bottom
        self.page_width = None
        self.page_height = None

    def add_row(self, row: TableRow):
        self.rows.append(row)

    def set_page_info(self, pw, ph):
        self.page_height = ph
        self.page_width = pw

    def merge_overlapping_rows(self):
        lst = list(self.rows)
        m_lst = []
        ok = True
        while ok:
            i = 0
            merged = False
            while i + 1 < len(lst):
                row = lst[i]
                next_row = lst[i + 1]
                if overlaps(row, next_row):
                    m_row = merge(row, next_row)
                    m_lst.append(m_row)
                    merged = True
                    i += 2
                else:
                    m_lst.append(row)
                    if i + 2 == len(lst):
                        m_lst.append(next_row)
                    i += 1
            lst = list(m_lst)
            m_lst = []
            break
            if not merged:
                break
        self.rows = lst

    def to_html(self):
        s = '<table>\n'
        for row in self.rows:
            s += row.to_html() + '\n'
        s += '</table>\n'
        return s

    def to_csv(self):
        return [row.to_csv() for row in self.rows]

    def to_json(self):
        data = {'left': self.left, 'top': self.top, 'right': self.right, 'bottom': self.bottom,
                'rows': [r.to_json() for r in self.rows]}
        if self.page_height:
            data['page_height'] = self.page_height
            data['page_width'] = self.page_width
        return data

    @classmethod
    def from_json(cls, data):
        c = cls()
        rows = data['rows']
        for row in rows:
            c.add_row(TableRow.from_json(row))
        return c


def overlaps(row1: TableRow, row2: TableRow):
    return row1.bottom > row2.top + 10


def merge(row1: TableRow, row2: TableRow):
    row = TableRow(row1.left, row1.top, row1.right, row2.bottom)
    for cell1, cell2 in zip(row1.cells, row2.cells):
        cell = TableCell(cell1.left, cell1.top, cell1.right, cell2.top, cell1.span)
        cell.text = cell1.text + ' ' + cell2.text
        row.add_cell(cell)
    return row


def build_row(row_r: Rectangle, col_rs, span_cell_rs):
    row = TableRow(row_r.left, row_r.top, row_r.right, row_r.bottom)
    if len(col_rs) == 0:
        print('empty row (no column info)')
        return row

    rsc_list = []
    for scr in span_cell_rs:
        if row_r.contains(scr):
            rsc_list.append(scr)
    for spr in rsc_list:
        span_cell_rs.remove(spr)
    rsc_list = sorted(rsc_list, key=lambda r: r.left)

    cw_list = [c.left for c in col_rs]
    cw_list.append(col_rs[-1].right)

    if len(rsc_list) == 0:
        prev = cw_list[0]
        for i in range(1, len(cw_list)):
            right = cw_list[i]
            cell = TableCell(prev, row_r.top, right, row_r.bottom)
            row.add_cell(cell)
            prev = cw_list[i]
    else:
        prev = cw_list[0]
        sc_idx, i = 0, 1
        while i < len(cw_list):
            if sc_idx < len(rsc_list):
                sc = rsc_list[sc_idx]
                right = cw_list[i]
                if sc.left <= prev and sc.right >= right:
                    cell = TableCell(sc.left, row_r.top, sc.right, row_r.bottom)
                    row.add_cell(cell)
                    sc_idx += 1
                    while i + 1 < len(cw_list) and sc.right > cw_list[i + 1]:
                        i += 1
                else:
                    cell = TableCell(prev, row_r.top, right, row_r.bottom)
                    row.add_cell(cell)
                    i += 1
                prev = cw_list[i - 1]
            else:
                right = cw_list[i]
                cell = TableCell(prev, row_r.top, right, row_r.bottom)
                row.add_cell(cell)
                i += 1
                prev = cw_list[i - 1]
    return row


def build_table(_boxes, _labels, table_image):
    """
    {0: 'table',
     1: 'table column',
     2: 'table row',
     3: 'table column header',
     4: 'table projected row header',
     5: 'table spanning cell'}
    :param _boxes:
    :param _labels:
    :param table_image
    :return:
    """
    row_rs, col_rs, col_header_rs = [], [], []
    span_cell_rs = []

    for label, (left, top, right, bottom) in zip(_labels.tolist(), _boxes.tolist()):
        rect = Rectangle(left, top, right, bottom)
        if label == 1:
            col_rs.append(rect)
        elif label == 2:
            row_rs.append(rect)
        elif label == 3:
            col_header_rs.append(rect)
        elif label == 5:
            span_cell_rs.append(rect)

    col_rs = sorted(col_rs, key=lambda r: r.left)
    row_rs = sorted(row_rs, key=lambda r: r.top)
    _table = Table(left=table_image.left, top=table_image.top, right=table_image.right,
                   bottom=table_image.bottom)
    for row_r in row_rs:
        row = build_row(row_r, col_rs, span_cell_rs)
        _table.add_row(row)
    return _table


def extract_table_region_text(pil_img):
    text = pytesseract.image_to_string(pil_img, config="--psm 6")
    text = str(text).strip().replace('|', '')
    return text


def extract_table_text(pil_img, _table: Table, out_dir=None):
    for i, row in enumerate(_table.rows):
        for j, cell in enumerate(row.cells):
            try:
                im = pil_img.crop((cell.left, cell.top, cell.right, cell.bottom))
                # to gray scale
                im = im.convert('L')
                contraster = ImageEnhance.Contrast(im)
                im = contraster.enhance(1.8)

                text = pytesseract.image_to_string(im, config="--psm 6")
                cell.text = str(text).strip().replace('|', '')
                if out_dir is not None:
                    ci_name = "row_{}_cell_{}.jpg".format(i,j)
                    ci_fpath = os.path.join(out_dir, ci_name)
                    im.save(ci_fpath)
            except BaseException as e:
                print("Exception in cell text extraction: {}".format(e))
                cell.text = ''


def test_drive():
    with open('/tmp/table_labels_boxes.pickle', 'rb') as f:
        labels = pickle.load(f)
        boxes = pickle.load(f)
    table = build_table(boxes, labels)
    print(table.to_html())


def test_merge():
    with open("/tmp/tables/media-15/media-15_page_3_table_1_pretty.json") as f:
        data = json.load(f)
    table = Table.from_json(data)
    print(f'# rows (before): {len(table.rows)}')
    # table.merge_overlapping_rows()
    print(f'# rows (after): {len(table.rows)}')
    from PIL import Image
    table_im = Image.open('/tmp/tables/media-15/media-15_page_3_table_1.jpg')
    extract_table_text(table_im, table)

    for row in table.rows:
        for cell in row.cells:
            print(cell.text.replace('\n', ' ').replace('\r', '') + " | ", end='')
        print('\n-------------------------')


if __name__ == '__main__':
    test_merge()
