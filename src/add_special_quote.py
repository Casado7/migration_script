from __future__ import annotations
import os
import time
from dotenv import load_dotenv

from target_helppers.login import start_and_login
from selenium.webdriver.common.by import By
from carousel_selector import select_project_in_carousel
from target_helppers.lote_selector import select_lote


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
        # set value and dispatch events so React picks it up
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
