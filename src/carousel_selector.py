from __future__ import annotations
import time
from selenium.webdriver.remote.webdriver import WebDriver


def select_project_in_carousel(driver: WebDriver, project_label: str, timeout: float = 10.0) -> dict:
    """Select a project in the react-multi-carousel by image alt or data-index.

    Returns a dict with keys:
      - selected: bool
      - result: whatever the last JS attempt returned
      - debug: debug info collected from the page (image alts and li indexes)

    This function uses JS executed in the page to avoid stale element issues.
    """
    # New behavior: count items in the carousel and select the last one.
    end = time.time() + timeout
    dbg = None
    last_res = None
    try:
        # wait for carousel items to appear
        while time.time() < end:
            try:
                dbg = driver.execute_script(
                    "var lis = document.querySelectorAll('.react-multi-carousel-track li');"
                    "return { count: lis.length, indexes: Array.from(lis).map(n=>n.getAttribute('data-index')) };"
                )
                if isinstance(dbg, dict) and dbg.get('count', 0) > 0:
                    break
            except Exception:
                dbg = None
            time.sleep(0.4)

        count = int(dbg.get('count', 0)) if isinstance(dbg, dict) else 0
        # print how many items there are in the carousel
        print('Carousel item count:', count)

        if count == 0:
            return {'selected': False, 'result': 'no-items', 'debug': dbg, 'count': 0}

        # click the last li
        js_click_last = (
            "var lis = document.querySelectorAll('.react-multi-carousel-track li');"
            "if(!lis || lis.length===0) return {ok:false};"
            "var last = lis[lis.length-1];"
            "var idx = last.getAttribute('data-index');"
            "try{ last.scrollIntoView({behavior:'auto', block:'center'}); }catch(e){};"
            "try{ last.click(); }catch(e){};"
            "try{ last.dispatchEvent(new MouseEvent('mouseover',{bubbles:true})); }catch(e){};"
            "try{ last.dispatchEvent(new MouseEvent('mousedown',{bubbles:true})); }catch(e){};"
            "try{ last.dispatchEvent(new MouseEvent('mouseup',{bubbles:true})); }catch(e){};"
            "try{ last.dispatchEvent(new MouseEvent('click',{bubbles:true})); }catch(e){};"
            "return {ok:true, index: idx};"
        )

        res = driver.execute_script(js_click_last)
        last_res = res
        clicked = False
        idx = None
        if isinstance(res, dict):
            clicked = bool(res.get('ok', False))
            idx = res.get('index')
        else:
            clicked = bool(res)

        return {'selected': clicked, 'result': res, 'debug': dbg, 'count': count, 'index': idx}
    except Exception as e:
        return {'selected': False, 'result': str(e), 'debug': dbg}
