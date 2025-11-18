from __future__ import annotations
import time
from typing import List, Dict


def _normalize_num(x) -> str:
    if x is None:
        return ''
    s = str(x).strip()
    s = s.replace('%', '')
    s = s.replace(',', '')
    return s


def fill_payment_table(driver, amortizacion: List[Dict], delay: float = 0.25) -> bool:
    """Fill the payment table using the rows already created on the page.

    The page already generates rows after "Generar" — this function will
    locate the existing rows and populate each row with the corresponding
    entry from `amortizacion`. It will NOT click "Agregar Cuota".

    Behavior:
    - If number of rows != len(amortizacion) it will fill up to the smaller
      of the two and return False (but still populate values).
    - It sets the select (Tipo), the concept text and the numeric monto,
      dispatching `input`/`change` events so React can detect changes.

    Returns True when rows count matches amortizacion length and filling
    completed; otherwise False.
    """
    try:
        if not amortizacion:
            return True

        amort_len = len(amortizacion)

        # Build arrays for JS: tipo, concepto, monto
        tipos = []
        conceptos = []
        montos = []
        mens_count = 0
        for item in amortizacion:
            tipo = (item.get('tipo') or '').strip()
            if tipo.lower() == 'mensualidad':
                mens_count += 1
                concepto = f"Mensualidad {mens_count}"
                tipo_val = 'Mensualidad'
            else:
                concepto = tipo or ''
                tipo_val = tipo or ''

            monto = _normalize_num(item.get('monto') or item.get('monto_raw') or '')
            tipos.append(tipo_val)
            conceptos.append(concepto)
            montos.append(monto)

        # JS: fill existing rows up to min(rows, amort_len)
        script = (
            "var tb = document.querySelector('table.table tbody');"
            "if(!tb) return {rows:0, filled:0};"
            "var rows = tb.querySelectorAll('tr');"
            "var n = Math.min(rows.length, arguments[0].length);"
            "for(var i=0;i<n;i++){"
            "  var row = rows[i];"
            "  var sel = row.querySelector('select.form-select');"
            "  if(sel && arguments[0][i]){ sel.value = arguments[0][i]; sel.dispatchEvent(new Event('change',{bubbles:true})); }"
            "  var text = row.querySelector('input[type=text]');"
            "  if(text){ text.focus && text.focus(); text.value = arguments[1][i]; text.dispatchEvent(new Event('input',{bubbles:true})); text.dispatchEvent(new Event('change',{bubbles:true})); text.blur && text.blur(); }"
            "  var num = row.querySelector('input[type=number]');"
            "  if(num){ num.focus && num.focus(); num.value = arguments[2][i]; num.dispatchEvent(new Event('input',{bubbles:true})); num.dispatchEvent(new Event('change',{bubbles:true})); num.blur && num.blur(); }"
            "} return {rows: rows.length, filled: n};"
        )

        res = driver.execute_script(script, tipos, conceptos, montos)
        # res should be a dict-like object with keys 'rows' and 'filled'
        rows_count = 0
        filled = 0
        try:
            rows_count = int(res.get('rows', 0))
            filled = int(res.get('filled', 0))
        except Exception:
            # fallback if driver returns a WebElement-mapped object
            try:
                rows_count = int(res['rows'])
                filled = int(res['filled'])
            except Exception:
                pass

        if rows_count != amort_len:
            print(f"Warning: payment table rows ({rows_count}) != amortizacion items ({amort_len}). Filled {filled} rows.")
            return False

        return True
    except Exception as e:
        print('Error in fill_payment_table:', e)
        return False
