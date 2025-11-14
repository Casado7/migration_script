#!/usr/bin/env python3
"""extract_clients.py

Usage:
  - Read from file and write to stdout:
      python src/extract_clients.py input.json

  - Read from stdin and write to stdout:
      cat input.json | python src/extract_clients.py

  - Write output to file:
      python src/extract_clients.py input.json -o clients.json

This script expects a top-level JSON array where each item is an object
that may contain a `cliente` key. It returns a JSON array containing the
`cliente` values found (skipping entries without that key).
"""
from __future__ import annotations
import argparse
import json
import sys
from typing import Any, List


def extract_clients(data: Any) -> List[Any]:
    """Return a list with the `cliente` value for each item in `data`.

    - If `data` is not a list, raises ValueError.
    - Skips items that don't contain `cliente` or where it's null/empty.
    """
    if not isinstance(data, list):
        raise ValueError("input JSON must be an array of objects")

    out = []
    for item in data:
        if not isinstance(item, dict):
            continue
        c = item.get("cliente")
        if c is None:
            continue
        out.append(c)

    return out


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Extract 'cliente' objects from array JSON")
    parser.add_argument("input", nargs="?", help="input JSON file (defaults to stdin)")
    parser.add_argument("-o", "--output", help="output file (defaults to stdout)")
    parser.add_argument("--pretty", action="store_true", help="pretty-print JSON output")

    args = parser.parse_args(argv)

    try:
        if args.input:
            with open(args.input, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            # read from stdin
            data = json.load(sys.stdin)
    except Exception as e:
        print(f"Error reading input JSON: {e}", file=sys.stderr)
        return 2

    try:
        clients = extract_clients(data)
    except ValueError as e:
        print(f"Invalid input: {e}", file=sys.stderr)
        return 3

    out_json = None
    if args.pretty:
        out_json = json.dumps(clients, ensure_ascii=False, indent=2)
    else:
        out_json = json.dumps(clients, ensure_ascii=False, separators=(",", ":"))

    try:
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(out_json)
        else:
            sys.stdout.write(out_json)
    except Exception as e:
        print(f"Error writing output: {e}", file=sys.stderr)
        return 4

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
