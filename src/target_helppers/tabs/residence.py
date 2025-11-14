from __future__ import annotations
import time
from typing import Tuple
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException

from ..helpers import _set_input_value, _set_react_select_value


def fill_residence_tab(driver, defaults: dict, timeout: int = 20) -> Tuple[bool, str]:
    """Fill the 'Dirección de Residencia' tab fields from defaults.

    Returns (True, '') on success or (False, error_message).
    """
    try:
        res_present = WebDriverWait(driver, timeout).until(
            lambda d: len(d.find_elements(By.NAME, 'client_address[0].address')) > 0
            or len(d.find_elements(By.NAME, 'client_address[0].state')) > 0
        )
    except Exception:
        res_present = False

    if not res_present:
        return False, "Residence fields not present"

    # Country (react-select-like)
    country_name = 'client_address[0].country'
    country_val = defaults.get(country_name) or None
    if country_val:
        try:
            ok = _set_react_select_value(driver, country_name, country_val)
            if not ok:
                _set_input_value(driver, country_name, country_val)
        except Exception:
            _set_input_value(driver, country_name, country_val)

    # other visible fields
    residence_fields = [
        'client_address[0].state',
        'client_address[0].city',
        'client_address[0].postal_code',
        'client_address[0].address',
    ]

    def wait_for_name(name: str):
        try:
            return WebDriverWait(driver, timeout).until(EC.presence_of_element_located((By.NAME, name)))
        except TimeoutException:
            return None

    for rf in residence_fields:
        el = wait_for_name(rf)
        if el is None:
            _set_input_value(driver, rf, defaults.get(rf, ''))
            continue
        try:
            el.clear()
        except Exception:
            pass
        try:
            el.send_keys(defaults.get(rf, ''))
        except Exception:
            _set_input_value(driver, rf, defaults.get(rf, ''))

    try:
        time.sleep(0.2)
    except Exception:
        pass

    return True, ""
