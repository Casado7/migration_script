from __future__ import annotations
import time
from typing import Any


def select_lote(driver: Any, lote_code: str, timeout: int = 10) -> bool:
    """Try to find a visible element matching `lote_code` and click it.

    Strategy:
    - try exact text match (trimmed)
    - fallback to partial contains match
    - retry until `timeout` seconds elapse

    Returns True if an element was clicked, False otherwise.
    """
    js_exact = (
        "var items = Array.from(document.querySelectorAll('*')).filter(function(n){"
        "  return n.textContent && n.textContent.trim() === arguments[0];"
        "});"
        "for(var i=0;i<items.length;i++){var r=items[i].getBoundingClientRect();"
        " if(r.width>0&&r.height>0){items[i].click();return true}} return false;"
    )

    js_contains = (
        "var items = Array.from(document.querySelectorAll('*')).filter(function(n){"
        "  return n.textContent && n.textContent.indexOf(arguments[0])>-1;"
        "});"
        "for(var i=0;i<items.length;i++){var r=items[i].getBoundingClientRect();"
        " if(r.width>0&&r.height>0){items[i].click();return true}} return false;"
    )

    end = time.time() + float(timeout)
    while time.time() < end:
        try:
            if bool(driver.execute_script(js_exact, lote_code)):
                return True
        except Exception:
            pass

        try:
            if bool(driver.execute_script(js_contains, lote_code)):
                return True
        except Exception:
            pass

        time.sleep(0.2)

    return False
