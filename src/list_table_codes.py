import re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
TABLE = ROOT / 'output' / 'table.html'
if not TABLE.exists():
    print('MISSING_TABLE')
    raise SystemExit(1)
html = TABLE.read_text(encoding='utf-8')
# split rows by <tr>
rows = re.split(r'<tr', html)[1:]
codes = []
for i, r in enumerate(rows):
    m = re.search(r'name=["\']codigo_venta["\']\s+value=["\']([^"\']+)["\']', r)
    if not m:
        m = re.search(r'value=["\']([^"\']+)["\']\s+name=["\']codigo_venta["\']', r)
    code = m.group(1).strip() if m else ''
    codes.append((i, code))

for idx, code in codes:
    print(f'{idx}: {code}')
print('\nTotal rows with detected code:', sum(1 for _,c in codes if c))
