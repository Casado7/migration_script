from __future__ import annotations
import time
from typing import Any

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def select_lote(driver: Any, lote_code: str, timeout: int = 10) -> bool:
    """Open the react-select 'Lote' control, type `lote_code` and select the first option.

    Steps:
    - find the combobox input associated with the 'Lote' label
    - click to open the dropdown
    - type the lote_code
    - wait for the listbox/options and click the first option

    Returns True if selection succeeded, False otherwise.
    """
    end = time.time() + float(timeout)

    try:
        # Try to locate the combobox input linked to the label 'Lote'
        try:
            input_el = driver.find_element(By.XPATH, "//label[normalize-space(text())='Lote']/following::input[@role='combobox'][1]")
        except Exception:
            # fallback: any input with role=combobox inside the form
            try:
                input_el = driver.find_element(By.CSS_SELECTOR, "form input[role='combobox']")
            except Exception:
                # last resort: any input whose id starts with react-select
                try:
                    input_el = driver.find_element(By.CSS_SELECTOR, "input[id^='react-select']")
                except Exception:
                    return False

        # click the control to open dropdown
        try:
            input_el.click()
        except Exception:
            pass

        # clear and type the lote code
        try:
            input_el.clear()
        except Exception:
            pass
        input_el.send_keys(lote_code)
        time.sleep(0.2)

        # Wait for options to appear: role=listbox with role=option children
        wait = WebDriverWait(driver, max(1, timeout))
        try:
            listbox = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "[role='listbox']")))
        except Exception:
            # maybe options render elsewhere, try small retry loop
            while time.time() < end:
                try:
                    listbox = driver.find_element(By.CSS_SELECTOR, "[role='listbox']")
                    break
                except Exception:
                    time.sleep(0.1)
            else:
                return False

        # find first option inside listbox
        try:
            option = listbox.find_element(By.CSS_SELECTOR, "[role='option']")
            # scroll into view and click
            driver.execute_script('arguments[0].scrollIntoView(true);', option)
            time.sleep(0.05)
            option.click()
            return True
        except Exception:
            # fallback: try to send Enter to choose first
            try:
                input_el.send_keys(Keys.ENTER)
                return True
            except Exception:
                return False

    except Exception:
        return False

