"""Export item metadata without changing either input workbook."""
import argparse
import json
from pathlib import Path
import openpyxl

ROOT = Path(__file__).resolve().parents[1]


def export_catalog(original: Path, newitemp: Path, output: Path):
    records = {}
    for path, source in ((original, 'item'), (newitemp, 'newitemp')):
        workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
        try:
            for sheet in workbook.worksheets:
                rows = sheet.iter_rows(values_only=True)
                headers = next(rows, ())
                if 'itemCode' not in headers:
                    continue
                for values in rows:
                    item = dict(zip(headers, values))
                    if not item.get('itemCode'):
                        continue
                    code = int(item['itemCode'])
                    item.update(itemCode=code, sheet=sheet.title, base_source=source)
                    records[code] = item
        finally:
            workbook.close()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(list(records.values()), ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    return len(records)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--original', type=Path, default=ROOT / 'item.xlsx')
    parser.add_argument('--newitemp', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=ROOT / 'resources/item_catalog.json')
    args = parser.parse_args()
    print(f'{export_catalog(args.original, args.newitemp, args.output):,} items exported to {args.output}')
