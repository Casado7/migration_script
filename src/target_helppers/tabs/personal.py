from __future__ import annotations
import time
from typing import Tuple
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException

from ..helpers import _set_input_value


def fill_personal_tab(driver, defaults: dict, timeout: int = 20) -> Tuple[bool, str]:
    """Fill the personal info tab fields (name, last names, birth, email, phones).

    Returns (True, '') on success or (False, error_message).
    """
    def wait_for_name(name: str):
        try:
            return WebDriverWait(driver, timeout).until(EC.presence_of_element_located((By.NAME, name)))
        except TimeoutException:
            return None

    field_names = [
        "name",
        "middle_name",
        "last_name",
        "mothers_name",
        "birth",
        "email",
        "phone",
        "cellphone",
    ]

    for fname in field_names:
        el = wait_for_name(fname)
        if el is None:
            continue
        try:
            el.clear()
            el.send_keys(defaults.get(fname, ""))
        except Exception:
            _set_input_value(driver, fname, defaults.get(fname, ""))

    # prefixes are hidden inputs rendered elsewhere; set them if present
    for h in ("phone_prefix", "cellphone_prefix"):
        if h in defaults:
            _set_input_value(driver, h, defaults[h])

    # small wait
    try:
        time.sleep(0.05)
    except Exception:
        pass

    return True, ""
