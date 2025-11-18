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
    """Fill the payment table on the page using the provided amortizacion list.

    For each item in amortizacion this will click the "Agregar Cuota" button
    to append a row, then set the select (Tipo), the concept (text input)
    and the amount (number input). Uses JS to set values and dispatch
    input/change events so React picks up the changes.

    Returns True on (likely) success, False otherwise.
    """
    try:
        if not amortizacion:
            return True

        mensual_count = 0

        for item in amortizacion:
            tipo = (item.get('tipo') or '').strip()
            monto = _normalize_num(item.get('monto') or item.get('monto_raw') or '')

            # click "Agregar Cuota" button (try common selector, fallback to searching by text)
            clicked = False
            try:
                clicked = bool(driver.execute_script(
                    "var b = document.querySelector('button.btn.btn-info'); if(b){ b.click(); return true; } return false;"
                ))
            except Exception:
                clicked = False

            if not clicked:
                try:
                    # fallback: click button by its text
                    clicked = bool(driver.execute_script(
                        "var items = Array.from(document.querySelectorAll('button')).filter(function(n){ return n.textContent && n.textContent.trim() === 'Agregar Cuota'; }); if(items.length){ items[0].click(); return true; } return false;"
                    ))
                except Exception:
                    clicked = False

            time.sleep(delay)

            # compute concept label
            if tipo.lower() == 'mensualidad':
                mensual_count += 1
                concept = f"Mensualidad {mensual_count}"
                tipo_val = 'Mensualidad'
            else:
                concept = tipo or ''
                tipo_val = tipo or ''

            # Fill the last row using JS: select, text input, number input
            script = (
                "var tb = document.querySelector('table.table tbody');"
                "if(!tb) return false;"
                "var rows = tb.querySelectorAll('tr');"
                "if(!rows.length) return false;"
                "var row = rows[rows.length-1];"
                "var sel = row.querySelector('select.form-select');"
                "if(sel && arguments[0]){ sel.value = arguments[0]; sel.dispatchEvent(new Event('change',{bubbles:true})); }"
                "var text = row.querySelector('input[type=text]');"
                "if(text && arguments[1]!==null){ text.focus && text.focus(); text.value = arguments[1]; text.dispatchEvent(new Event('input',{bubbles:true})); text.dispatchEvent(new Event('change',{bubbles:true})); text.blur && text.blur(); }"
                "var num = row.querySelector('input[type=number]');"
                "if(num && arguments[2]!==null){ num.focus && num.focus(); num.value = arguments[2]; num.dispatchEvent(new Event('input',{bubbles:true})); num.dispatchEvent(new Event('change',{bubbles:true})); num.blur && num.blur(); }"
                "return true;"
            )

            try:
                driver.execute_script(script, tipo_val, concept, monto)
            except Exception:
                # last resort: try to set via element references (less reliable across frameworks)
                try:
                    driver.execute_script(
                        "var tb = document.querySelector('table.table tbody'); if(!tb) return false; var rows = tb.querySelectorAll('tr'); var row = rows[rows.length-1]; row.querySelector('input[type=text]').value = arguments[0]; row.querySelector('input[type=number]').value = arguments[1]; return true;",
                        concept,
                        monto,
                    )
                except Exception:
                    pass

            time.sleep(delay)

        return True
    except Exception:
        return False
