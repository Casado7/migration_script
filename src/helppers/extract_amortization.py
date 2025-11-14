from __future__ import annotations
import re
import time
from typing import List, Dict
from selenium.webdriver.common.by import By


def _first_number_token(s: str) -> str:
    if not s:
        return ""
    m = re.findall(r"[\d.,]+", s)
    return m[0] if m else ""


def extract_amortization_table(driver) -> List[Dict[str, str]]:
    """Extracts the "Tabla de Amortización" table from the current page.

    Returns a list of rows with keys:
      - `no`: index/No. column (string)
      - `monto`: numeric token as string (commas/dots preserved)
      - `fecha`: date string as shown (e.g. '2025-01-31')
      - `tipo`: type string (e.g. 'Enganche' or 'Mensualidad')
      - `pago_id`: id attribute of the anchor in the fecha column if present (or '')

    The function uses small retries and text-content fallbacks to tolerate
    slight DOM differences and late JS population.
    """
    try:
        # try to locate the card that contains the Tabla de Amortización
        xp = "//div[contains(normalize-space(.), 'Tabla de Amortización')]/ancestor::div[contains(@class,'card')][1]"
        card = driver.find_element(By.XPATH, xp)
    except Exception:
        # fallback: search anywhere for a table header with that exact text
        try:
            card = driver.find_element(By.XPATH, "//table[.//th[contains(., 'Monto')] and .//tbody]//ancestor::div[contains(@class,'card')][1]")
        except Exception:
            return []

    rows = []
    # retry reading rows a few times to tolerate late rendering
    for attempt in range(3):
        try:
            tr_elems = card.find_elements(By.XPATH, ".//table//tbody//tr")
        except Exception:
            tr_elems = []

        if tr_elems:
            # quick content check: accept if any row contains a date-like token or amount
            ok = False
            for tr in tr_elems:
                try:
                    txt = (tr.text or "").strip()
                    if not txt:
                        continue
                    if re.search(r"\d{4}-\d{2}-\d{2}", txt) or "$" in txt or re.search(r"\d+[.,]\d{2}", txt):
                        ok = True
                        break
                except Exception:
                    continue
            if ok or attempt == 2:
                rows = tr_elems
                break
        time.sleep(0.35)

    result: List[Dict[str, str]] = []
    for tr in rows:
        try:
            # select both th and td children (No. may be in a th)
            cols = tr.find_elements(By.XPATH, "./th|./td")
            cells = []
            for c in cols:
                try:
                    txt = (c.text or c.get_attribute('textContent') or c.get_attribute('innerText') or '').strip()
                except Exception:
                    txt = ''
                cells.append(txt)

            if not cells:
                continue

            # expected columns: [No., Monto, Fecha (anchor), Tipo, ...]
            no = cells[0] if len(cells) > 0 else ""
            monto = cells[1] if len(cells) > 1 else ""
            fecha = cells[2] if len(cells) > 2 else ""
            tipo = cells[3] if len(cells) > 3 else ""

            # attempt to grab anchor id inside fecha cell
            pago_id = ""
            try:
                a = tr.find_element(By.XPATH, "./td[3]//a | ./th[3]//a")
                pago_id = a.get_attribute('id') or ''
                # anchor text may be the fecha
                if a.text and a.text.strip():
                    fecha = a.text.strip()
            except Exception:
                # try alternative: any anchor in the row
                try:
                    a = tr.find_element(By.XPATH, ".//a")
                    pago_id = a.get_attribute('id') or ''
                except Exception:
                    pago_id = ''

            result.append({
                'no': no,
                'monto': _first_number_token(monto),
                'monto_raw': monto,
                'fecha': fecha,
                'tipo': tipo.strip(),
                'pago_id': pago_id,
            })
        except Exception:
            # ignore malformed rows but continue
            continue

    return result
