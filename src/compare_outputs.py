import re
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TABLE = ROOT / 'output' / 'table.html'
CLIENTS = ROOT / 'output' / 'clients.json'

if not TABLE.exists():
    print('MISSING_TABLE')
    raise SystemExit(1)
if not CLIENTS.exists():
    print('MISSING_CLIENTS')
    raise SystemExit(1)

html = TABLE.read_text(encoding='utf-8')
# find input name="codigo_venta" value="..."
codes_in_table = re.findall(r'name=["\']codigo_venta["\']\s+value=["\']([^"\']+)["\']', html)
# also capture any "codigo_venta" in other attributes just in case
codes_in_table += re.findall(r'value=["\']([^"\']+)["\']\s+name=["\']codigo_venta["\']', html)
# normalize
codes_in_table = [c.strip() for c in codes_in_table if c.strip()]

clients = json.loads(CLIENTS.read_text(encoding='utf-8'))
clients_codes = [c.get('codigo_venta') for c in clients if c.get('codigo_venta')]

set_table = set(codes_in_table)
set_clients = set(clients_codes)

missing = sorted(list(set_table - set_clients))
extra = sorted(list(set_clients - set_table))

print('table_count:', len(codes_in_table))
print('clients_count:', len(clients_codes))
print('unique_table:', len(set_table))
print('unique_clients:', len(set_clients))
print('\nMISSING IN clients.json (present in table but not in clients.json):')
for m in missing:
    print('-', m)

print('\nEXTRA IN clients.json (not present in table):')
for e in extra[:50]:
    print('-', e)

# print small sample mapping
print('\nSAMPLE clients.json entries (first 10 codes):')
for code in clients_codes[:10]:
    print('-', code)
