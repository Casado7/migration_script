from __future__ import annotations
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys


def _set_input_value(driver, name: str, value: str) -> bool:
    """Set the value of an input by name. Returns True if set, False otherwise."""
    try:
        el = driver.find_element(By.NAME, name)
        driver.execute_script(
            "arguments[0].value = arguments[1]; arguments[0].dispatchEvent(new Event('input')); arguments[0].dispatchEvent(new Event('change'));",
            el,
            value,
        )
        return True
    except Exception:
        return False


def _set_react_select_value(driver, name: str, value: str) -> bool:
    """Robustly try to set a react-select-like control which keeps a hidden
    input with `name`. Strategy: open control and click option by text, then
    type+ENTER, then force hidden input + dispatch events."""
    try:
        hidden = driver.find_element(By.NAME, name)
    except Exception:
        return False

    # Strategy A: open container and click option by text
    try:
        container = driver.execute_script(
            "const h = arguments[0];"
            "let c = h.previousElementSibling;"
            "if(!c && h.parentElement) c = h.parentElement.querySelector('.css-b62m3t-container');"
            "if(!c && h.parentElement) c = h.parentElement.querySelector('.css-my3gbk-control');"
            "return c;",
            hidden,
        )

        if container:
            try:
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", container)
            except Exception:
                pass

            try:
                container.click()
            except Exception:
                try:
                    driver.execute_script("arguments[0].click();", container)
                except Exception:
                    try:
                        inp = container.find_element(By.TAG_NAME, "input")
                        inp.click()
                    except Exception:
                        pass

            time.sleep(0.18)

            try:
                candidates = driver.find_elements(By.XPATH, f"//*[normalize-space(text())=\"{value}\"]")
                for c in candidates:
                    try:
                        if c.is_displayed():
                            c.click()
                            time.sleep(0.12)
                            return True
                    except Exception:
                        continue
            except Exception:
                pass

    except Exception:
        pass

    # Strategy B: type into visible input + ENTER
    try:
        input_el = driver.execute_script(
            "const hidden = arguments[0];"
            "let container = hidden.previousElementSibling;"
            "if(!container) container = hidden.parentElement && hidden.parentElement.querySelector('.css-b62m3t-container');"
            "if(!container) return null;"
            "const inp = container.querySelector('input');"
            "return inp;",
            hidden,
        )
        if input_el:
            try:
                input_el.click()
            except Exception:
                try:
                    driver.execute_script("arguments[0].focus();", input_el)
                except Exception:
                    pass

            try:
                input_el.clear()
            except Exception:
                pass

            try:
                input_el.send_keys(value)
                input_el.send_keys(Keys.ENTER)
                time.sleep(0.12)
                return True
            except Exception:
                pass

    except Exception:
        pass

    # Strategy C: force hidden input value and dispatch events
    try:
        driver.execute_script(
            "const hidden = arguments[0]; const v = arguments[1];"
            "hidden.value = v;"
            "hidden.dispatchEvent(new Event('input', {bubbles:true}));"
            "hidden.dispatchEvent(new Event('change', {bubbles:true}));"
            "let container = hidden.previousElementSibling;"
            "if(!container && hidden.parentElement) container = hidden.parentElement.querySelector('.css-b62m3t-container');"
            "if(container){ const sv = container.querySelector('.css-1dimb5e-singleValue'); if(sv) { sv.innerText = v; } }",
            hidden,
            value,
        )
        time.sleep(0.12)
        return True
    except Exception:
        return False


