from __future__ import annotations
import time
from typing import Tuple
from selenium.webdriver.common.by import By

from ..helpers import _set_input_value, _set_react_select_value


def fill_general_tab(driver, defaults: dict, timeout: int = 20) -> Tuple[bool, str]:
    """Fill the 'Datos Generales' tab using defaults dict. Returns (success,msg)."""
    second_tab_names = [
        "origin_country",
        "nationality",
        "marital_status",
        "profession_id",
        "sex",
        "client_kind",
    ]

    # Use values from defaults (caller can override)
    second_defaults = {k: defaults.get(k, "") for k in second_tab_names}

    for name, val in second_defaults.items():
        if not val:
            # still try to set empty values via hidden input if present
            try:
                _set_input_value(driver, name, val)
            except Exception:
                pass
            continue

        ok = False
        try:
            ok = _set_react_select_value(driver, name, val)
        except Exception:
            ok = False

        if ok:
            continue

        # fallback to hidden input set
        try:
            _set_input_value(driver, name, val)
        except Exception:
            pass

    # profession visible inputs (if any)
    try:
        els = driver.find_elements(By.NAME, "profession_id")
        for el in els:
            try:
                el.clear()
                el.send_keys(second_defaults.get("profession_id", ""))
            except Exception:
                _set_input_value(driver, "profession_id", second_defaults.get("profession_id", ""))
    except Exception:
        pass

    # allow JS to process
    try:
        time.sleep(0.2)
    except Exception:
        pass

    return True, ""
