from __future__ import annotations
import time
from typing import Tuple
from selenium.webdriver.common.by import By

from ..helpers import _set_input_value, _set_react_select_value


def fill_advertising_tab(driver, defaults: dict, timeout: int = 20) -> Tuple[bool, str]:
    """Fill the 'Publicidad' tab fields (`advertising` and `thirdparty_advertising`).

    Uses the same pattern as other tab-fillers: try react-select helper first,
    fallback to hidden input setter. Returns (True, '') on success.
    """
    names = ["advertising", "thirdparty_advertising"]

    for name in names:
        val = defaults.get(name, "Sí")

        # prefer react-select high-level setter (works when control is visible)
        ok = False
        try:
            ok = _set_react_select_value(driver, name, val)
        except Exception:
            ok = False

        if ok:
            continue

        # fallback: set hidden input value + dispatch events
        try:
            _set_input_value(driver, name, val)
        except Exception:
            # best-effort: try to locate visible inputs and send keys
            try:
                els = driver.find_elements(By.NAME, name)
                for el in els:
                    try:
                        el.clear()
                        el.send_keys(val)
                    except Exception:
                        pass
            except Exception:
                pass

    # let the app process changes
    try:
        time.sleep(0.15)
    except Exception:
        pass

    return True, ""
