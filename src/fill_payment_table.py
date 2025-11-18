from __future__ import annotations
import time
from typing import List, Dict
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException


def _normalize_num(x) -> str:
    if x is None:
        return ''
    s = str(x).strip()
    s = s.replace('%', '')
    s = s.replace(',', '')
    return s


def fill_payment_table(driver, amortizacion: List[Dict], delay: float = 0.4) -> bool:
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

        # debug: dump table rows before filling
        try:
            rows_before = driver.execute_script(
                "var tb=document.querySelector('table.table tbody'); if(!tb) return []; return Array.from(tb.querySelectorAll('tr')).map(function(r){ var sel=r.querySelector('select.form-select'); var tipo=sel?sel.value:(r.querySelector('select')?r.querySelector('select').value:''); var text=r.querySelector('input[type=text]'); var concept=text?text.value:''; var num=r.querySelector('input[type=number]'); var monto=num?num.value:''; return {tipo:tipo, concept:concept, monto:monto}; });"
            )
        except Exception:
            rows_before = []
        print('Payment table BEFORE:', rows_before)

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

        # Fill rows one-by-one with a short delay and capture per-row before/after snapshots
        try:
            rows_count = driver.execute_script("var tb=document.querySelector('table.table tbody'); if(!tb) return 0; return tb.querySelectorAll('tr').length;")
        except Exception:
            rows_count = 0

        n = min(rows_count, len(tipos))
        per_row_changes = []

        def _type_into(el, value: str):
            """Click/clear/type into an element so React receives native events."""
            try:
                el.click()
            except Exception:
                try:
                    driver.execute_script('arguments[0].scrollIntoView(true);', el)
                    driver.execute_script('arguments[0].focus && arguments[0].focus();', el)
                except Exception:
                    pass
            try:
                el.clear()
            except Exception:
                pass
            s = '' if value is None else str(value)
            for ch in s:
                try:
                    el.send_keys(ch)
                except Exception:
                    # can't type into this element
                    raise
                time.sleep(0.02)
            try:
                el.send_keys(Keys.TAB)
            except Exception:
                pass

        for i in range(n):
            before = None
            after = None
            try:
                rows = driver.find_elements(By.CSS_SELECTOR, 'table.table tbody tr')
                if i >= len(rows):
                    break
                row = rows[i]
                # snapshot before
                try:
                    sel = row.find_element(By.CSS_SELECTOR, 'select.form-select')
                    tipo_before = sel.get_attribute('value')
                except NoSuchElementException:
                    tipo_before = ''
                try:
                    txt = row.find_element(By.CSS_SELECTOR, "input[type='text']")
                    concept_before = txt.get_attribute('value')
                except NoSuchElementException:
                    concept_before = ''
                try:
                    num = row.find_element(By.CSS_SELECTOR, "input[type='number']")
                    monto_before = num.get_attribute('value')
                except NoSuchElementException:
                    monto_before = ''
                before = {'index': i, 'tipo': tipo_before, 'concept': concept_before, 'monto': monto_before}

                # set select
                wanted = tipos[i]
                if wanted:
                    try:
                        sel = row.find_element(By.CSS_SELECTOR, 'select.form-select')
                        try:
                            Select(sel).select_by_visible_text(wanted)
                            driver.execute_script('arguments[0].dispatchEvent(new Event("change", { bubbles: true }));', sel)
                        except Exception:
                            try:
                                Select(sel).select_by_value(wanted)
                                driver.execute_script('arguments[0].dispatchEvent(new Event("change", { bubbles: true }));', sel)
                            except Exception:
                                # last resort: set via JS
                                driver.execute_script('var s=arguments[0]; s.value=arguments[1]; s.dispatchEvent(new Event("change",{bubbles:true}));', sel, wanted)
                    except NoSuchElementException:
                        pass

                # set concept (text)
                try:
                    txt = row.find_element(By.CSS_SELECTOR, "input[type='text']")
                    try:
                        _type_into(txt, conceptos[i])
                        driver.execute_script('arguments[0].dispatchEvent(new Event("input",{bubbles:true})); arguments[0].dispatchEvent(new Event("change",{bubbles:true}));', txt)
                    except Exception as e:
                        print(f"Failed typing text in row {i}:", e)
                except NoSuchElementException:
                    pass

                # set monto (number)
                try:
                    num = row.find_element(By.CSS_SELECTOR, "input[type='number']")
                    try:
                        _type_into(num, montos[i])
                        driver.execute_script('arguments[0].dispatchEvent(new Event("input",{bubbles:true})); arguments[0].dispatchEvent(new Event("change",{bubbles:true}));', num)
                    except Exception as e:
                        print(f"Failed typing number in row {i}:", e)
                except NoSuchElementException:
                    pass

                time.sleep(delay)

                # snapshot after
                try:
                    sel = row.find_element(By.CSS_SELECTOR, 'select.form-select')
                    tipo_after = sel.get_attribute('value')
                except NoSuchElementException:
                    tipo_after = ''
                try:
                    txt = row.find_element(By.CSS_SELECTOR, "input[type='text']")
                    concept_after = txt.get_attribute('value')
                except NoSuchElementException:
                    concept_after = ''
                try:
                    num = row.find_element(By.CSS_SELECTOR, "input[type='number']")
                    monto_after = num.get_attribute('value')
                except NoSuchElementException:
                    monto_after = ''
                after = {'index': i, 'tipo': tipo_after, 'concept': concept_after, 'monto': monto_after}

            except StaleElementReferenceException:
                print(f"Stale element at row {i}, skipping")
            except Exception as e:
                print(f"Error processing row {i}:", e)

            per_row_changes.append({
                'index': i,
                'before': before,
                'after': after,
                'wanted': {'tipo': tipos[i], 'concept': conceptos[i], 'monto': montos[i]},
            })

        # After filling, re-check total rows
        try:
            final_rows = driver.execute_script("var tb=document.querySelector('table.table tbody'); if(!tb) return 0; return tb.querySelectorAll('tr').length;")
        except Exception:
            final_rows = rows_count

        # debug: dump table rows after filling (summary)
        try:
            rows_after = driver.execute_script(
                "var tb=document.querySelector('table.table tbody'); if(!tb) return []; return Array.from(tb.querySelectorAll('tr')).map(function(r){ var sel=r.querySelector('select.form-select'); var tipo=sel?sel.value:(r.querySelector('select')?r.querySelector('select').value:''); var text=r.querySelector('input[type=text]'); var concept=text?text.value:''; var num=r.querySelector('input[type=number]'); var monto=num?num.value:''; return {tipo:tipo, concept:concept, monto:monto}; });"
            )
        except Exception:
            rows_after = []
        print('Payment table AFTER:', rows_after)
        print('Per-row changes:')
        for ch in per_row_changes:
            print(ch)

        res = {'rows': final_rows, 'filled': len(per_row_changes)}
        # debug: dump table rows after filling
        try:
            rows_after = driver.execute_script(
                "var tb=document.querySelector('table.table tbody'); if(!tb) return []; return Array.from(tb.querySelectorAll('tr')).map(function(r){ var sel=r.querySelector('select.form-select'); var tipo=sel?sel.value:(r.querySelector('select')?r.querySelector('select').value:''); var text=r.querySelector('input[type=text]'); var concept=text?text.value:''; var num=r.querySelector('input[type=number]'); var monto=num?num.value:''; return {tipo:tipo, concept:concept, monto:monto}; });"
            )
        except Exception:
            rows_after = []
        print('Payment table AFTER:', rows_after)
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
