#!/usr/bin/env python3
"""Transform extracted clients to TEST_CLIENT_DEFAULTS-like format.

Reads `output/clients.json` by default and writes `output/converted_clients.json`.
You can override input/output via CLI args.
"""
from __future__ import annotations
import argparse
import json
import os
import sys
from typing import Any, Dict, List


def split_name(fullname: str) -> Dict[str, str]:
    parts = [p for p in (fullname or "").strip().split() if p]
    res = {"name": "", "middle_name": "", "last_name": "", "mothers_name": ""}
    if not parts:
        return res
    if len(parts) == 1:
        res["name"] = parts[0]
        return res
    if len(parts) == 2:
        res["name"] = parts[0]
        res["last_name"] = parts[1]
        return res
    if len(parts) == 3:
        res["name"] = parts[0]
        res["middle_name"] = parts[1]
        res["last_name"] = parts[2]
        return res
    # 4+ parts: assume first, second, last-1, last
    res["name"] = parts[0]
    res["middle_name"] = parts[1]
    res["last_name"] = parts[-2]
    res["mothers_name"] = parts[-1]
    return res


def reformat_birth(birth: str) -> str:
    if not birth:
        return ""
    # expect YYYY-MM-DD -> convert to DD-MM-YYYY
    try:
        parts = birth.split("-")
        if len(parts) == 3 and len(parts[0]) == 4:
            return f"{parts[2]}-{parts[1]}-{parts[0]}"
    except Exception:
        pass
    return birth


def map_sex(val: str) -> str:
    if not val:
        return ""
    v = val.strip().upper()
    if v.startswith("M") and "MU" not in v:  # 'M' or 'MASC' -> male
        return "M"
    if v.startswith("MU") or v.startswith("F") or v == "MUJER":
        return "F"
    if v.startswith("H"):
        return "M"
    # fallback: take first letter
    return v[0]


def build_address(item: Dict[str, Any]) -> Dict[str, str]:
    calle = (item.get("calle") or "").strip()
    num_ext = (item.get("num_exterior") or "").strip()
    num_int = (item.get("num_interior") or "").strip()
    colonia = (item.get("colonia") or "").strip()
    parts = [calle]
    if num_ext:
        parts.append(num_ext)
    if num_int:
        parts.append(f"Int {num_int}")
    if colonia:
        parts.append(colonia)
    address = " ".join([p for p in parts if p])
    return {
        "country": item.get("pais") or item.get("nacionalidad") or "México",
        "state": item.get("estado") or "",
        "city": item.get("localidad") or "",
        "postal_code": item.get("codigo_postal") or "",
        "address": address,
    }


def transform_client(item: Dict[str, Any]) -> Dict[str, Any]:
    name_parts = split_name(item.get("name", ""))

    addr = build_address(item)

    phone = (item.get("telefono_local") or "" ).strip()
    cellphone = (item.get("telefono_celular") or "" ).strip()
    # prefer cellphone for `cellphone` and phone for `phone`

    out = {
        "name": name_parts.get("name", ""),
        "middle_name": name_parts.get("middle_name", ""),
        "last_name": name_parts.get("last_name", ""),
        "mothers_name": name_parts.get("mothers_name", ""),
        "birth": reformat_birth(item.get("birth_date") or item.get("birth") or ""),
        "email": (item.get("email") or "").strip(),
        "phone_prefix": "52",
        "phone": phone,
        "cellphone_prefix": "52",
        "cellphone": cellphone,
        # address fields as expected by the inserter
        "client_address[0].country": addr["country"],
        "client_address[0].state": addr["state"],
        "client_address[0].city": addr["city"],
        "client_address[0].postal_code": addr["postal_code"],
        "client_address[0].address": addr["address"],
        # other mappings
        "origin_country": item.get("pais") or item.get("nacionalidad") or "",
        "nationality": item.get("nacionalidad") or "",
        "marital_status": item.get("estado_civil") or "",
        "profession_id": item.get("ocupacion") or "",
        "sex": map_sex(item.get("sexo") or ""),
        "client_kind": "M",
    }

    return out


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Transform clients into form-ready objects")
    parser.add_argument("input", nargs="?", help="input JSON file (defaults to ../output/clients.json)")
    parser.add_argument("-o", "--output", help="output file (defaults to ../output/converted_clients.json)")
    args = parser.parse_args(argv)

    default_input = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "output", "clients.json"))
    default_output = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "output", "converted_clients.json"))

    try:
        if args.input:
            with open(args.input, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            with open(default_input, "r", encoding="utf-8") as f:
                data = json.load(f)
    except Exception as e:
        print(f"Error reading input JSON: {e}", file=sys.stderr)
        return 2

    if not isinstance(data, list):
        print("Input must be a JSON array", file=sys.stderr)
        return 3

    transformed: List[Dict[str, Any]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        transformed.append(transform_client(item))

    out_path = args.output if args.output else default_output
    try:
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(transformed, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error writing output JSON: {e}", file=sys.stderr)
        return 4

    print(f"Transformed {len(transformed)} clients -> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
