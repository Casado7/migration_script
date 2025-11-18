from __future__ import annotations
import os
import time
from dotenv import load_dotenv

from target_helppers.login import start_and_login
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from carousel_selector import select_project_in_carousel
from target_helppers.lote_selector import select_lote

TEST_JSON = {
    "info_credito": {
      "desarrollo": "UKUUN",
      "unidad": "111",
      "etapa": "DIAMANTE II",
      "superficie": "235.15",
      "precio_m2": "2,229.58",
      "precio_lista": "524,285.74",
      "plan_de_pago": "Generador de ofertas",
      "cuota_de_apertura": "0.00",
      "descuento_%": "10.0000",
      "descuento_m2": "52,428.57",
      "moneda_del_contrato": "M.N",
      "precio_venta": "471,857.17",
      "enganche_%": "10.00",
      "enganche": "47,185.72",
      "financiamiento_%": "90.00",
      "financiamiento": "424,671.45",
      "costo_escritura": "0.00"
    },
    "amortizacion": [
      {
        "no": "1",
        "monto": "47,185.72",
        "monto_raw": "47,185.72",
        "fecha": "2025-01-31",
        "tipo": "Enganche",
        "pago_id": "pago_233354_2025-01-31"
      },
      {
        "no": "1",
        "monto": "4,718.57",
        "monto_raw": "4,718.57",
        "fecha": "2025-03-15",
        "tipo": "Mensualidad",
        "pago_id": "pago_233355_2025-03-15"
      },
      {
        "no": "2",
        "monto": "4,718.57",
        "monto_raw": "4,718.57",
        "fecha": "2025-04-15",
        "tipo": "Mensualidad",
        "pago_id": "pago_233356_2025-04-15"
      },
      {
        "no": "3",
        "monto": "4,718.57",
        "monto_raw": "4,718.57",
        "fecha": "2025-05-15",
        "tipo": "Mensualidad",
        "pago_id": "pago_233357_2025-05-15"
      },
      {
        "no": "4",
        "monto": "4,718.57",
        "monto_raw": "4,718.57",
        "fecha": "2025-06-15",
        "tipo": "Mensualidad",
        "pago_id": "pago_233358_2025-06-15"
      },
      {
        "no": "5",
        "monto": "4,718.57",
        "monto_raw": "4,718.57",
        "fecha": "2025-07-15",
        "tipo": "Mensualidad",
        "pago_id": "pago_233359_2025-07-15"
      },
      {
        "no": "6",
        "monto": "4,718.57",
        "monto_raw": "4,718.57",
        "fecha": "2025-08-15",
        "tipo": "Mensualidad",
        "pago_id": "pago_233360_2025-08-15"
      },
      {
        "no": "7",
        "monto": "4,718.57",
        "monto_raw": "4,718.57",
        "fecha": "2025-09-15",
        "tipo": "Mensualidad",
        "pago_id": "pago_233361_2025-09-15"
      },
      {
        "no": "8",
        "monto": "4,718.57",
        "monto_raw": "4,718.57",
        "fecha": "2025-10-15",
        "tipo": "Mensualidad",
        "pago_id": "pago_233362_2025-10-15"
      },
      {
        "no": "9",
        "monto": "4,718.57",
        "monto_raw": "4,718.57",
        "fecha": "2025-11-15",
        "tipo": "Mensualidad",
        "pago_id": "pago_233363_2025-11-15"
      },
      {
        "no": "10",
        "monto": "4,718.57",
        "monto_raw": "4,718.57",
        "fecha": "2025-12-15",
        "tipo": "Mensualidad",
        "pago_id": "pago_233364_2025-12-15"
      },
      {
        "no": "11",
        "monto": "4,718.57",
        "monto_raw": "4,718.57",
        "fecha": "2026-01-15",
        "tipo": "Mensualidad",
        "pago_id": "pago_233365_2026-01-15"
      },
      {
        "no": "12",
        "monto": "4,718.57",
        "monto_raw": "4,718.57",
        "fecha": "2026-02-15",
        "tipo": "Mensualidad",
        "pago_id": "pago_233366_2026-02-15"
      },
      {
        "no": "13",
        "monto": "28,311.43",
        "monto_raw": "28,311.43",
        "fecha": "2026-02-15",
        "tipo": "Mensualidad",
        "pago_id": "pago_233367_2026-02-15"
      },
      {
        "no": "14",
        "monto": "4,718.57",
        "monto_raw": "4,718.57",
        "fecha": "2026-03-15",
        "tipo": "Mensualidad",
        "pago_id": "pago_233368_2026-03-15"
      },
      {
        "no": "15",
        "monto": "4,718.57",
        "monto_raw": "4,718.57",
        "fecha": "2026-04-15",
        "tipo": "Mensualidad",
        "pago_id": "pago_233369_2026-04-15"
      },
      {
        "no": "16",
        "monto": "4,718.57",
        "monto_raw": "4,718.57",
        "fecha": "2026-05-15",
        "tipo": "Mensualidad",
        "pago_id": "pago_233370_2026-05-15"
      },
      {
        "no": "17",
        "monto": "4,718.57",
        "monto_raw": "4,718.57",
        "fecha": "2026-06-15",
        "tipo": "Mensualidad",
        "pago_id": "pago_233371_2026-06-15"
      },
      {
        "no": "18",
        "monto": "4,718.57",
        "monto_raw": "4,718.57",
        "fecha": "2026-07-15",
        "tipo": "Mensualidad",
        "pago_id": "pago_233372_2026-07-15"
      },
      {
        "no": "19",
        "monto": "4,718.57",
        "monto_raw": "4,718.57",
        "fecha": "2026-08-15",
        "tipo": "Mensualidad",
        "pago_id": "pago_233373_2026-08-15"
      },
      {
        "no": "20",
        "monto": "4,718.57",
        "monto_raw": "4,718.57",
        "fecha": "2026-09-15",
        "tipo": "Mensualidad",
        "pago_id": "pago_233374_2026-09-15"
      },
      {
        "no": "21",
        "monto": "4,718.57",
        "monto_raw": "4,718.57",
        "fecha": "2026-10-15",
        "tipo": "Mensualidad",
        "pago_id": "pago_233375_2026-10-15"
      },
      {
        "no": "22",
        "monto": "4,718.57",
        "monto_raw": "4,718.57",
        "fecha": "2026-11-15",
        "tipo": "Mensualidad",
        "pago_id": "pago_233376_2026-11-15"
      },
      {
        "no": "23",
        "monto": "4,718.57",
        "monto_raw": "4,718.57",
        "fecha": "2026-12-15",
        "tipo": "Mensualidad",
        "pago_id": "pago_233377_2026-12-15"
      },
      {
        "no": "24",
        "monto": "4,718.57",
        "monto_raw": "4,718.57",
        "fecha": "2027-01-15",
        "tipo": "Mensualidad",
        "pago_id": "pago_233378_2027-01-15"
      },
      {
        "no": "25",
        "monto": "4,718.57",
        "monto_raw": "4,718.57",
        "fecha": "2027-02-15",
        "tipo": "Mensualidad",
        "pago_id": "pago_233379_2027-02-15"
      },
      {
        "no": "26",
        "monto": "28,311.43",
        "monto_raw": "28,311.43",
        "fecha": "2027-02-15",
        "tipo": "Mensualidad",
        "pago_id": "pago_233380_2027-02-15"
      },
      {
        "no": "27",
        "monto": "4,718.57",
        "monto_raw": "4,718.57",
        "fecha": "2027-03-15",
        "tipo": "Mensualidad",
        "pago_id": "pago_233381_2027-03-15"
      },
      {
        "no": "28",
        "monto": "4,718.57",
        "monto_raw": "4,718.57",
        "fecha": "2027-04-15",
        "tipo": "Mensualidad",
        "pago_id": "pago_233382_2027-04-15"
      },
      {
        "no": "29",
        "monto": "4,718.57",
        "monto_raw": "4,718.57",
        "fecha": "2027-05-15",
        "tipo": "Mensualidad",
        "pago_id": "pago_233383_2027-05-15"
      },
      {
        "no": "30",
        "monto": "4,718.57",
        "monto_raw": "4,718.57",
        "fecha": "2027-06-15",
        "tipo": "Mensualidad",
        "pago_id": "pago_233384_2027-06-15"
      },
      {
        "no": "31",
        "monto": "4,718.57",
        "monto_raw": "4,718.57",
        "fecha": "2027-07-15",
        "tipo": "Mensualidad",
        "pago_id": "pago_233385_2027-07-15"
      },
      {
        "no": "32",
        "monto": "4,718.57",
        "monto_raw": "4,718.57",
        "fecha": "2027-08-15",
        "tipo": "Mensualidad",
        "pago_id": "pago_233386_2027-08-15"
      },
      {
        "no": "33",
        "monto": "4,718.57",
        "monto_raw": "4,718.57",
        "fecha": "2027-09-15",
        "tipo": "Mensualidad",
        "pago_id": "pago_233387_2027-09-15"
      },
      {
        "no": "34",
        "monto": "4,718.57",
        "monto_raw": "4,718.57",
        "fecha": "2027-10-15",
        "tipo": "Mensualidad",
        "pago_id": "pago_233388_2027-10-15"
      },
      {
        "no": "35",
        "monto": "4,718.57",
        "monto_raw": "4,718.57",
        "fecha": "2027-11-15",
        "tipo": "Mensualidad",
        "pago_id": "pago_233389_2027-11-15"
      },
      {
        "no": "36",
        "monto": "4,718.57",
        "monto_raw": "4,718.57",
        "fecha": "2027-12-15",
        "tipo": "Mensualidad",
        "pago_id": "pago_233390_2027-12-15"
      },
      {
        "no": "37",
        "monto": "4,718.57",
        "monto_raw": "4,718.57",
        "fecha": "2028-01-15",
        "tipo": "Mensualidad",
        "pago_id": "pago_233391_2028-01-15"
      },
      {
        "no": "38",
        "monto": "4,718.57",
        "monto_raw": "4,718.57",
        "fecha": "2028-02-15",
        "tipo": "Mensualidad",
        "pago_id": "pago_233392_2028-02-15"
      },
      {
        "no": "39",
        "monto": "28,311.43",
        "monto_raw": "28,311.43",
        "fecha": "2028-02-15",
        "tipo": "Mensualidad",
        "pago_id": "pago_233393_2028-02-15"
      },
      {
        "no": "40",
        "monto": "4,718.57",
        "monto_raw": "4,718.57",
        "fecha": "2028-03-15",
        "tipo": "Mensualidad",
        "pago_id": "pago_233394_2028-03-15"
      },
      {
        "no": "41",
        "monto": "4,718.57",
        "monto_raw": "4,718.57",
        "fecha": "2028-04-15",
        "tipo": "Mensualidad",
        "pago_id": "pago_233395_2028-04-15"
      },
      {
        "no": "42",
        "monto": "4,718.57",
        "monto_raw": "4,718.57",
        "fecha": "2028-05-15",
        "tipo": "Mensualidad",
        "pago_id": "pago_233396_2028-05-15"
      },
      {
        "no": "43",
        "monto": "4,718.57",
        "monto_raw": "4,718.57",
        "fecha": "2028-06-15",
        "tipo": "Mensualidad",
        "pago_id": "pago_233397_2028-06-15"
      },
      {
        "no": "44",
        "monto": "4,718.57",
        "monto_raw": "4,718.57",
        "fecha": "2028-07-15",
        "tipo": "Mensualidad",
        "pago_id": "pago_233398_2028-07-15"
      },
      {
        "no": "45",
        "monto": "4,718.57",
        "monto_raw": "4,718.57",
        "fecha": "2028-08-15",
        "tipo": "Mensualidad",
        "pago_id": "pago_233399_2028-08-15"
      },
      {
        "no": "46",
        "monto": "4,718.57",
        "monto_raw": "4,718.57",
        "fecha": "2028-09-15",
        "tipo": "Mensualidad",
        "pago_id": "pago_233400_2028-09-15"
      },
      {
        "no": "47",
        "monto": "4,718.57",
        "monto_raw": "4,718.57",
        "fecha": "2028-10-15",
        "tipo": "Mensualidad",
        "pago_id": "pago_233401_2028-10-15"
      },
      {
        "no": "48",
        "monto": "4,718.57",
        "monto_raw": "4,718.57",
        "fecha": "2028-11-15",
        "tipo": "Mensualidad",
        "pago_id": "pago_233402_2028-11-15"
      },
      {
        "no": "49",
        "monto": "4,718.57",
        "monto_raw": "4,718.57",
        "fecha": "2028-12-15",
        "tipo": "Mensualidad",
        "pago_id": "pago_233403_2028-12-15"
      },
      {
        "no": "50",
        "monto": "4,718.57",
        "monto_raw": "4,718.57",
        "fecha": "2029-01-15",
        "tipo": "Mensualidad",
        "pago_id": "pago_233404_2029-01-15"
      },
      {
        "no": "51",
        "monto": "4,718.57",
        "monto_raw": "4,718.57",
        "fecha": "2029-02-15",
        "tipo": "Mensualidad",
        "pago_id": "pago_233405_2029-02-15"
      },
      {
        "no": "52",
        "monto": "28,311.43",
        "monto_raw": "28,311.43",
        "fecha": "2029-02-15",
        "tipo": "Mensualidad",
        "pago_id": "pago_233406_2029-02-15"
      },
      {
        "no": "53",
        "monto": "4,718.57",
        "monto_raw": "4,718.57",
        "fecha": "2029-03-15",
        "tipo": "Mensualidad",
        "pago_id": "pago_233407_2029-03-15"
      },
      {
        "no": "54",
        "monto": "4,718.57",
        "monto_raw": "4,718.57",
        "fecha": "2029-04-15",
        "tipo": "Mensualidad",
        "pago_id": "pago_233408_2029-04-15"
      },
      {
        "no": "55",
        "monto": "4,718.57",
        "monto_raw": "4,718.57",
        "fecha": "2029-05-15",
        "tipo": "Mensualidad",
        "pago_id": "pago_233409_2029-05-15"
      },
      {
        "no": "56",
        "monto": "4,718.57",
        "monto_raw": "4,718.57",
        "fecha": "2029-06-15",
        "tipo": "Mensualidad",
        "pago_id": "pago_233410_2029-06-15"
      },
      {
        "no": "57",
        "monto": "4,718.57",
        "monto_raw": "4,718.57",
        "fecha": "2029-07-15",
        "tipo": "Mensualidad",
        "pago_id": "pago_233411_2029-07-15"
      },
      {
        "no": "58",
        "monto": "4,718.57",
        "monto_raw": "4,718.57",
        "fecha": "2029-08-15",
        "tipo": "Mensualidad",
        "pago_id": "pago_233412_2029-08-15"
      },
      {
        "no": "59",
        "monto": "4,718.57",
        "monto_raw": "4,718.57",
        "fecha": "2029-09-15",
        "tipo": "Mensualidad",
        "pago_id": "pago_233413_2029-09-15"
      },
      {
        "no": "60",
        "monto": "4,718.57",
        "monto_raw": "4,718.57",
        "fecha": "2029-10-15",
        "tipo": "Mensualidad",
        "pago_id": "pago_233414_2029-10-15"
      },
      {
        "no": "61",
        "monto": "4,718.57",
        "monto_raw": "4,718.57",
        "fecha": "2029-11-15",
        "tipo": "Mensualidad",
        "pago_id": "pago_233415_2029-11-15"
      },
      {
        "no": "62",
        "monto": "4,718.57",
        "monto_raw": "4,718.57",
        "fecha": "2029-12-15",
        "tipo": "Mensualidad",
        "pago_id": "pago_233416_2029-12-15"
      },
      {
        "no": "63",
        "monto": "4,718.57",
        "monto_raw": "4,718.57",
        "fecha": "2030-01-15",
        "tipo": "Mensualidad",
        "pago_id": "pago_233417_2030-01-15"
      },
      {
        "no": "64",
        "monto": "4,718.57",
        "monto_raw": "4,718.57",
        "fecha": "2030-02-15",
        "tipo": "Mensualidad",
        "pago_id": "pago_233418_2030-02-15"
      },
      {
        "no": "65",
        "monto": "28,311.53",
        "monto_raw": "28,311.53",
        "fecha": "2030-02-15",
        "tipo": "Mensualidad",
        "pago_id": "pago_233419_2030-02-15"
      }
    ]
  },

def add_special_quote(headless: bool = False, timeout: int = 20) -> None:
    """Login to target app and navigate to special-quote URL (minimal flow).

    Uses environment variables:
    - TARGET_PAGE_LOGIN_URL
    - TARGET_USERNAME
    - TARGET_PASSWORD
    - TARGET_PAGE_ADD_SPECIAL_QUOTE_URL
    After navigation it will try to select a lote and fill amounts then press "Generar".
    """
    load_dotenv()
    login_url = os.getenv('TARGET_PAGE_LOGIN_URL')
    if not login_url:
        print('TARGET_PAGE_LOGIN_URL not set in .env')
        return

    username = os.getenv('TARGET_USERNAME')
    password = os.getenv('TARGET_PASSWORD')
    if not username or not password:
        print('TARGET_USERNAME or TARGET_PASSWORD not set in .env')
        return

    driver, success, info = start_and_login(login_url, username, password, headless=headless, timeout=timeout)

    if driver is None:
        print('Failed to start driver or navigate:', info)
        return

    if not success:
        print('Login may have failed or stayed on page. Current URL/info:', info)
        time.sleep(2)
        try:
            driver.quit()
        except Exception:
            pass
        return

    print('Login successful, current URL:', info)

    target_url = os.getenv('TARGET_PAGE_ADD_SPECIAL_QUOTE_URL')
    if not target_url:
        print('TARGET_PAGE_ADD_SPECIAL_QUOTE_URL not set in .env')
        try:
            driver.quit()
        except Exception:
            pass
        return

    try:
        print('Navigating to special-quote page:', target_url)
        driver.get(target_url)
        time.sleep(2)
        print('Current URL after navigate:', driver.current_url)
    except Exception as e:
        print('Error navigating to special-quote URL:', e)

    def _set_input_value_by_id(el_id: str, value) -> None:
        # Try to simulate a real user typing so React picks up changes.
        try:
            el = driver.find_element(By.ID, el_id)
            # make sure element is visible
            try:
                driver.execute_script('arguments[0].scrollIntoView(true);', el)
            except Exception:
                pass
            time.sleep(0.05)
            try:
                el.click()
            except Exception:
                try:
                    driver.execute_script('arguments[0].focus && arguments[0].focus();', el)
                except Exception:
                    pass
            try:
                el.clear()
            except Exception:
                # some inputs may not support clear(); ignore
                pass
            s = str(value)
            for ch in s:
                try:
                    el.send_keys(ch)
                except Exception:
                    # if send_keys fails for this element, fall back to JS
                    raise
                time.sleep(0.04)
            # send a TAB to blur and trigger change handlers
            try:
                el.send_keys(Keys.TAB)
            except Exception:
                pass
            # Also dispatch input/change events via JS as extra assurance
            try:
                driver.execute_script(
                    "var e=arguments[0]; e.dispatchEvent(new Event('input', { bubbles: true })); e.dispatchEvent(new Event('change', { bubbles: true }));",
                    el,
                )
            except Exception:
                pass
            return
        except Exception:
            # fallback: set via JS (previous approach)
            js = (
                "var el = document.getElementById(arguments[0]);"
                "if(!el) return false;"
                "el.focus && el.focus();"
                "el.value = arguments[1];"
                "el.dispatchEvent(new Event('input', { bubbles: true }));"
                "el.dispatchEvent(new Event('change', { bubbles: true }));"
                "el.blur && el.blur();"
                "return true;"
            )
            try:
                driver.execute_script(js, el_id, value)
            except Exception:
                pass

    def _click_element_by_text(text: str) -> bool:
        # find a visible element containing the text and click it
        js = (
            "var items = Array.from(document.querySelectorAll('*')).filter(function(n){"
            "  return n.textContent && n.textContent.trim() === arguments[0];"
            "});"
            "for(var i=0;i<items.length;i++) {"
            "  var r = items[i].getBoundingClientRect();"
            "  if(r.width>0 && r.height>0) { items[i].click(); return true; }"
            "} return false;"
        )
        try:
            return bool(driver.execute_script(js, text))
        except Exception:
            return False

    def fill_and_generate(lote_code: str, enganche_pct: int, apartado_amt: int, mensualidades: int) -> None:
        # Try to open the lote select control
        try:
            # project selection moved to helper module
            # use the shared helper to select the project in the carousel
            time.sleep(2)
            selected_info = select_project_in_carousel(driver, 'ukuun', timeout=10)
            time.sleep(1)
            # try selecting the lote using the shared helper
            try:
                clicked = select_lote(driver, lote_code, timeout=5)
            except Exception:
                clicked = False
            print('Lote select result:', clicked)

            time.sleep(0.5)

            # set enganche porcentaje
            _set_input_value_by_id('formEnganchePorcentaje', str(enganche_pct))
            time.sleep(0.5)
            # set apartado
            _set_input_value_by_id('formApartado', str(apartado_amt))
            time.sleep(0.5)
            # set mensualidades
            _set_input_value_by_id('formMensualidades', str(mensualidades))
            time.sleep(0.5)

            # click Generar button (by text)
            gen_clicked = _click_element_by_text('Generar')
            print('Generar click by text result:', gen_clicked)
            if not gen_clicked:
                # fallback: click primary button
                try:
                    btn = driver.find_element(By.CSS_SELECTOR, 'button.btn.btn-primary')
                    driver.execute_script('arguments[0].scrollIntoView(true);', btn)
                    time.sleep(0.1)
                    btn.click()
                    print('Generar button clicked (fallback).')
                except Exception as e:
                    print('Failed to click Generar button:', e)
        except Exception as e:
            print('Error in fill_and_generate:', e)

    # perform the fill+generate with defaults (can be adjusted)
    try:
        # defaults requested by user
        lote_to_select = 'UK-00-0334'
        enganche_pct = 10
        apartado_amt = 10
        mensualidades = 10
        print(f"Filling special quote: lote={lote_to_select}, enganche={enganche_pct}, apartado={apartado_amt}, mensualidades={mensualidades}")
        time.sleep(1)
        fill_and_generate(lote_to_select, enganche_pct, apartado_amt, mensualidades)
        time.sleep(2)
    except Exception as e:
        print('Error performing actions on special-quote page:', e)

    # keep browser open briefly for inspection
    time.sleep(30)
    try:
        driver.quit()
    except Exception:
        pass


if __name__ == '__main__':
    add_special_quote(headless=False)
