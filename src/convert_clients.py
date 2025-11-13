from __future__ import annotations
import os
import json
import re
import html as _html


def _get_repo_root() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))


def _resolve_output_path(path: str) -> str:
    if not path:
        return path
    if os.path.isabs(path):
        return path
    repo_root = _get_repo_root()
    return os.path.join(repo_root, path.replace('/', os.sep).replace('\\', os.sep))


def parse_row_html_to_cols(row_html: str) -> dict:
    """Turn a row HTML into a dict col_1..col_n and try to extract hidden inputs like codigo_venta."""
    col_map = {}
    try:
        # find all <td ...>...</td>
        tds = re.findall(r'<td\b[^>]*>(.*?)</td>', row_html, flags=re.IGNORECASE | re.DOTALL)

        # canonical order provided by user
        canonical = [
            "Temp.", "Sucursal", "Asesor", "Cliente", "Desarrollo", "Unidad",
            "Fecha Venta", "Estado", "Plan", "Acciones", "Codigo Venta",
        ]
        def _norm_key(s: str) -> str:
            return re.sub(r"[^0-9a-z]+", "_", (s or '').strip().lower()).strip('_')
        canonical_keys = [_norm_key(x) for x in canonical]

        for idx, td_html in enumerate(tds, start=1):
            # remove tags
            text = re.sub(r'<[^>]+>', '', td_html)
            text = _html.unescape(text).strip()
            if idx-1 < len(canonical_keys):
                key = canonical_keys[idx-1]
            else:
                key = f'col_{idx}'
            col_map[key] = text

        # try to extract codigo_venta from inputs (fallback)
        m = re.search(r"<input[^>]+name=[\"']codigo_venta[\"'][^>]*value=[\"']([^\"']+)[\"']", row_html, flags=re.IGNORECASE)
        if m:
            col_map.setdefault('codigo_venta', m.group(1).strip())
    except Exception:
        pass
    return col_map


def convert_file(out_path: str) -> tuple[int, int]:
    out_path = _resolve_output_path(out_path)
    if not os.path.exists(out_path):
        raise FileNotFoundError(out_path)

    with open(out_path, 'r', encoding='utf-8') as fh:
        data = json.load(fh)

    converted = 0
    for item in data:
        # if already converted, skip
        if isinstance(item, dict) and 'row' in item:
            continue

        # if it has row_html, parse
        if isinstance(item, dict) and 'row_html' in item:
            rh = item.get('row_html') or ''
            cols = parse_row_html_to_cols(rh)
            # replace
            item['row'] = cols or {'html': rh}
            item.pop('row_html', None)
            converted += 1
        else:
            # legacy: if top-level looks like cliente dict, wrap into row empty
            if isinstance(item, dict) and 'cliente' not in item:
                item_wrapped = {'row': {}, 'cliente': item}
                # mutate current item in-place by clearing and updating
                item.clear()
                item.update(item_wrapped)
                converted += 1

    # write back
    with open(out_path, 'w', encoding='utf-8') as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)

    return converted, len(data)


def _main():
    try:
        converted, total = convert_file('output/clients.json')
        print(f'Converted {converted} entries out of {total} in output/clients.json')
        return 0
    except Exception as e:
        print('Error:', e)
        return 1


if __name__ == '__main__':
    raise SystemExit(_main())
