from __future__ import annotations
import os
import time
import json
from dotenv import load_dotenv

from target_helppers.login import start_and_login
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from carousel_selector import select_project_in_carousel
from target_helppers.lote_selector import select_lote
from fill_payment_table import fill_payment_table


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

    def fill_and_generate(data: dict) -> None:
      # Accepts a data object (quote dict) and extracts the needed fields.
      try:
        # Ensure we're on the "add special quote" page before interacting
        add_page = os.getenv('TARGET_PAGE_ADD_SPECIAL_QUOTE_URL')
        if add_page:
          try:
            print('Navigating to add special-quote page for this quote:', add_page)
            driver.get(add_page)
            # small wait to allow page scripts to load
            time.sleep(1.5)
            print('Current URL (add page):', driver.current_url)
          except Exception as e:
            print('Error navigating to add special-quote URL inside fill_and_generate:', e)
        else:
          print('TARGET_PAGE_ADD_SPECIAL_QUOTE_URL not set; continuing on current page')

        # project selection moved to helper module
        # use the shared helper to select the project in the carousel
        time.sleep(5)
        selected_info = select_project_in_carousel(driver, 'ukuun', timeout=10)
        time.sleep(1)

        info = data.get('info_credito', {})
        lote_code = info.get('unidad') or info.get('lote') or ''
        # try selecting the lote using the shared helper
        try:
          clicked = select_lote(driver, lote_code, timeout=5)
        except Exception:
          clicked = False
          # salir del script e imprimir el nombre del lote que no se encontrado
          print(f"Lote no encontrado: {lote_code}")
          return
        print('Lote select result:', clicked)

        time.sleep(0.5)

        # derive values from the data object
        enganche_pct = info.get('enganche_%') or info.get('enganche') or ''
        apartado_amt = info.get('cuota_de_apertura') or info.get('apartado') or ''
        mensualidades = sum(1 for item in data.get('amortizacion', []) if item.get('tipo') == 'Mensualidad')

        # normalize numeric strings (remove commas, percent signs)
        def _normalize_num(x):
          if x is None:
            return ''
          s = str(x).strip()
          s = s.replace('%', '')
          s = s.replace(',', '')
          return s

        precio_lista = _normalize_num(info.get('precio_lista') or info.get('precioLista'))
        precio_venta = _normalize_num(info.get('precio_venta') or info.get('precioVenta'))

        # set Monto total del lote and Precio de Venta before other fields
        if precio_lista:
          _set_input_value_by_id('formMontoTotal', precio_lista)
          time.sleep(0.4)
        if precio_venta:
          _set_input_value_by_id('formPrecioVenta', precio_venta)
          time.sleep(0.4)

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

        # after generating, try to fill the payment table with amortizacion data
        try:
          time.sleep(1)
          amort = data.get('amortizacion', [])
          if amort:
            ok = fill_payment_table(driver, amort)
            print('fill_payment_table result:', ok)
            # After filling the payment table, click the "Ver corrida final" button
            try:
              time.sleep(0.5)
              vc_clicked = _click_element_by_text('Ver corrida final')
              print('Ver corrida final click by text result:', vc_clicked)
              if not vc_clicked:
                try:
                  btn = driver.find_element(By.CSS_SELECTOR, 'button.btn.btn-success')
                  driver.execute_script('arguments[0].scrollIntoView(true);', btn)
                  time.sleep(0.1)
                  btn.click()
                  print('Ver corrida final button clicked (fallback).')
                except Exception as e:
                  print('Failed to click Ver corrida final button (fallback):', e)
              time.sleep(1)
            except Exception as e:
              print('Error clicking Ver corrida final button:', e)
          else:
            print('No amortizacion data to fill payment table.')
        except Exception as e:
          print('Error filling payment table:', e)
        time.sleep(2)
        # despues de llenar la pagina hay que ir de cotizaciones TARGET_PAGE_QUOTES_URL
        driver.get(os.getenv('TARGET_PAGE_QUOTES_URL'))
        time.sleep(2)
      except Exception as e:
        print('Error in fill_and_generate:', e)

    # perform the fill+generate for each item loaded from rows_info.json (login only once)
    try:
      # Try to load `output/rows_info.json` relative to the repo or cwd
      rows_file = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'output', 'rows_info.json'))
      if not os.path.exists(rows_file):
        rows_file = os.path.abspath(os.path.join(os.getcwd(), 'output', 'rows_info.json'))

      data_list = None
      try:
        with open(rows_file, 'r', encoding='utf-8') as fh:
          data_list = json.load(fh)
          if isinstance(data_list, list):
            print(f'Loaded {len(data_list)} quotes from {rows_file}')
          else:
            print(f'Loaded data from {rows_file} (not a list)')
      except Exception as e:
        print('Failed to load rows_info.json:', e)

      # If file not found or empty, abort with a clear message
      if not data_list:
        print('No input data available: output/rows_info.json not found or empty. Exiting.')
        try:
          driver.quit()
        except Exception:
          pass
        return

      time.sleep(1)
      if isinstance(data_list, list):
        total = len(data_list)
        for idx, item in enumerate(data_list, start=1):
          print(f'Processing quote {idx}/{total}')
          try:
            fill_and_generate(item)
          except Exception as e:
            print(f'Error processing quote {idx}:', e)
          time.sleep(2)
      else:
        fill_and_generate(data_list)
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
