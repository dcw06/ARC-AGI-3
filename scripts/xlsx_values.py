"""Read cell values from an .xlsx workbook with the standard library only (no formulas evaluated, no styles).

  python scripts/xlsx_values.py WORKBOOK.xlsx       list the sheets with their row counts

Used to check reviewer-returned workbooks offline without third-party packages.
"""
import re
import sys
import zipfile
import xml.etree.ElementTree as ET

NS = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main',
      'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}


def column_index(reference):
    letters = re.match(r'[A-Z]+', reference).group(0)
    index = 0
    for letter in letters:
        index = index * 26 + ord(letter) - 64
    return index - 1


def read_sheets(path):
    """{sheet name: [row values as strings]} in workbook order; missing cells are ''."""
    with zipfile.ZipFile(path) as z:
        shared = []
        if 'xl/sharedStrings.xml' in z.namelist():
            for item in ET.fromstring(z.read('xl/sharedStrings.xml')).findall('m:si', NS):
                shared.append(''.join(t.text or '' for t in item.iter('{%s}t' % NS['m'])))
        workbook = ET.fromstring(z.read('xl/workbook.xml'))
        targets = {r.get('Id'): r.get('Target') for r in ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))}
        sheets = {}
        for sheet in workbook.find('m:sheets', NS):
            target = targets[sheet.get('{%s}id' % NS['r'])].lstrip('/')
            part = target if target.startswith('xl/') else 'xl/' + target
            rows = []
            for row in ET.fromstring(z.read(part)).iter('{%s}row' % NS['m']):
                values = {}
                for cell in row.findall('m:c', NS):
                    kind, value = cell.get('t'), cell.find('m:v', NS)
                    if kind == 's' and value is not None:
                        text = shared[int(value.text)]
                    elif kind == 'inlineStr':
                        text = ''.join(t.text or '' for t in cell.iter('{%s}t' % NS['m']))
                    else:
                        text = value.text if value is not None and value.text is not None else ''
                    values[column_index(cell.get('r'))] = text
                rows.append([values.get(i, '') for i in range(max(values) + 1)] if values else [])
            sheets[sheet.get('name')] = rows
    return sheets


if __name__ == '__main__':
    for name, rows in read_sheets(sys.argv[1]).items():
        print(f'{name}: {len(rows)} rows')
