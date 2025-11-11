#!/usr/bin/env python3
"""Simple utility: count clients in output/clients.json

Usage:
    python src/count_clients.py

Prints total objects and unique counts by codigo_venta and id_cliente.
"""
import json
import os
import sys

# Resolve clients.json relative to repo root (script lives in src/)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CLIENTS_PATH = os.path.normpath(os.path.join(SCRIPT_DIR, '..', 'output', 'clients.json'))

if not os.path.exists(CLIENTS_PATH):
    print(f"File not found: {CLIENTS_PATH}")
    sys.exit(2)

try:
    with open(CLIENTS_PATH, 'r', encoding='utf-8') as fh:
        data = json.load(fh)
except Exception as e:
    print(f"Failed to read/parse {CLIENTS_PATH}: {e}")
    sys.exit(3)

if not isinstance(data, list):
    print(f"Unexpected format: expected a JSON array at {CLIENTS_PATH}")
    sys.exit(4)

total = len(data)
unique_codes = set()
unique_ids = set()

for item in data:
    if not isinstance(item, dict):
        continue
    code = (item.get('codigo_venta') or '').strip()
    if code:
        unique_codes.add(code)
    cid = (item.get('id_cliente') or '').strip()
    if cid:
        unique_ids.add(cid)

print(f"Clients file: {CLIENTS_PATH}")
print(f"Total objects in array: {total}")
print(f"Unique codigo_venta (non-empty): {len(unique_codes)}")
print(f"Unique id_cliente (non-empty): {len(unique_ids)}")

# Optionally print a brief sample
if total > 0:
    sample = data[0]
    if isinstance(sample, dict):
        keys = sorted(sample.keys())
        print(f"Sample keys: {keys}")

sys.exit(0)
