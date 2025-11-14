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
import os
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

    # Default to workspace `output/rows_info.json` (located next to `src/`)
    default_input = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "output", "rows_info.json"))
    default_output = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "output", "clients.json"))

    try:
        if args.input:
            input_path = args.input
            with open(input_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            # try to read default file from repo/output
            try:
                with open(default_input, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except FileNotFoundError:
                # fallback to stdin if default not present
                data = json.load(sys.stdin)
    except Exception as e:
        print(f"Error reading input JSON: {e}", file=sys.stderr)
        return 2

    try:
        clients = extract_clients(data)
    except ValueError as e:
        print(f"Invalid input: {e}", file=sys.stderr)
        return 3

    # Write pretty-printed JSON by default so output file is readable
    out_json = json.dumps(clients, ensure_ascii=False, indent=2)

    try:
        # if user provided an output path, use it; otherwise write to default output/clients.json
        out_path = args.output if args.output else default_output
        # ensure output dir exists
        out_dir = os.path.dirname(out_path)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)

        with open(out_path, "w", encoding="utf-8") as f:
            f.write(out_json)
    except Exception as e:
        print(f"Error writing output: {e}", file=sys.stderr)
        return 4

    # print summary to stdout
    try:
        print(f"Extracted {len(clients)} cliente objects -> {out_path}")
    except Exception:
        pass

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
