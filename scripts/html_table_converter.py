import os
import json
from pathlib import Path
from html import escape

HOME = os.path.expanduser('~')


class TD:
    def __init__(self, content: str, colspan=1, rowspan=1):
        self.content = content
        self.colspan = colspan
        self.rowspan = rowspan

    def to_html(self):
        s = ""
        if self.colspan > 1 and self.rowspan > 1:
            s += '<td colspan="{}" rowspan="{}">'.format(self.colspan, self.rowspan)
        elif self.colspan > 1:
            s += '<td colspan="{}">'.format(self.colspan)
        elif self.rowspan > 1:
            s += '<td rowspan="{}">'.format(self.rowspan)
        else:
            s += "<td>"
        s += "{}</td>".format(escape(self.content))
        return s


class TR:
    def __init__(self):
        self.cells = []

    def add_cell(self, cell: TD):
        self.cells.append(cell)

    def to_html(self):
        s = "<tr>\n"
        for cell in self.cells:
            s += "{}\n".format(cell.to_html())
        s += "</tr>\n"
        return s


class HtmlTable:
    def __init__(self, name: str):
        self.name = name
        self.rows = []

    def add_row(self, row: TR):
        self.rows.append(row)

    def to_html(self):
        s = "<table>\n"
        for row in self.rows:
            s += "{}\n".format(row.to_html())
        s += "</table>\n"
        return s


def to_html_table(table_json_dict) -> HtmlTable:
    html_table = HtmlTable(table_json_dict["name"])
    for jrow in table_json_dict["rows"]:
        tr = TR()
        html_table.add_row(tr)
        for jcell in jrow:
            rowspan = 1
            colspan = int(jcell['colspan'])
            if 'rowspan' in jcell:
                rowspan = int(jcell['rowspan'])
            content = jcell['content'].strip()
            tr.add_cell(TD(content, colspan, rowspan))
    return html_table


def load_json(json_file_path):
    with open(json_file_path) as f:
        return json.load(f)


def from_json_to_html_table(in_json_path: Path, out_html_dir: Path):
    js_dict = load_json(in_json_path)
    html_table = to_html_table(js_dict)
    out_path = out_html_dir / "{}.html".format(html_table.name)
    with open(out_path, 'w') as f:
        f.write(html_table.to_html())
        print(f"wrote {out_path}")


if __name__ == '__main__':
    out_dir = Path("/tmp/gs_html_tables")
    out_dir.mkdir(parents=True, exist_ok=True)
    in_root = Path(HOME, "data/table_content_extract/gs_bioarxiv_extracted_key_resources_tables_sampled")
    json_table_files = in_root.glob("*.json")
    for json_table_file in json_table_files:
        from_json_to_html_table(json_table_file, out_dir)
        break
