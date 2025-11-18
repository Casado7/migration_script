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
    # Behavior: find an <img alt=project_label> inside the carousel and click its parent <li>.
    end = time.time() + timeout
    dbg = None
    try:
        # wait for any images under the carousel track
        while time.time() < end:
            try:
                dbg = driver.execute_script(
                    "var imgs = document.querySelectorAll('.react-multi-carousel-track img[alt]');"
                    "return { img_count: imgs.length, alts: Array.from(imgs).map(i=>i.alt) };"
                )
                if isinstance(dbg, dict) and dbg.get('img_count', 0) > 0:
                    break
            except Exception:
                dbg = None
            time.sleep(0.25)

        if not isinstance(dbg, dict):
            return {'selected': False, 'result': 'no-carousel-images', 'debug': dbg}

        # try to click the image whose alt exactly matches project_label
        js_click_img_by_alt = (
            "var alt = arguments[0] ? arguments[0].toString().toLowerCase() : '';"
            "var imgs = document.querySelectorAll('.react-multi-carousel-track img[alt]');"
            "for(var i=0;i<imgs.length;i++){"
            "  var imgAlt = imgs[i].alt?imgs[i].alt.toString().toLowerCase():'';"
            "  if(imgAlt===alt){"
            "    var img = imgs[i]; var li = img.closest('li');"
            "    if(!li) return {ok:false, reason:'no-li'};"
            "    var idx = li.getAttribute('data-index');"
            "    try{ li.scrollIntoView({behavior:'auto', block:'center'}); }catch(e){};"
            "    try{ img.scrollIntoView({behavior:'auto', block:'center'}); }catch(e){};"
            "    try{ li.dispatchEvent(new PointerEvent('pointerover',{bubbles:true})); }catch(e){};"
            "    try{ li.dispatchEvent(new MouseEvent('mouseover',{bubbles:true})); }catch(e){};"
            "    try{ li.dispatchEvent(new PointerEvent('pointerdown',{bubbles:true})); }catch(e){};"
            "    try{ li.dispatchEvent(new MouseEvent('mousedown',{bubbles:true})); }catch(e){};"
            "    try{ li.dispatchEvent(new MouseEvent('mouseup',{bubbles:true})); }catch(e){};"
            "    try{ li.dispatchEvent(new PointerEvent('pointerup',{bubbles:true})); }catch(e){};"
            "    try{ img.click(); }catch(e){};"
            "    try{ li.click(); }catch(e){};"
            "    try{ li.dispatchEvent(new MouseEvent('click',{bubbles:true})); }catch(e){};"
            "    return {ok:true, index: idx, alt: img.alt};"
            "  }"
            "}"
            "return {ok:false, reason:'not-found'};"
        )

        res = driver.execute_script(js_click_img_by_alt, project_label)
        clicked = False
        idx = None
        if isinstance(res, dict):
            clicked = bool(res.get('ok', False))
            idx = res.get('index')
        else:
            clicked = bool(res)

        return {'selected': clicked, 'result': res, 'debug': dbg, 'index': idx}
    except Exception as e:
        return {'selected': False, 'result': str(e), 'debug': dbg}
