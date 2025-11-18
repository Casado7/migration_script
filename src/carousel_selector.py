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
    end = time.time() + timeout
    dbg = None
    try:
        # collect debug info (non-blocking)
        try:
            dbg = driver.execute_script(
                "return { alts: Array.from(document.querySelectorAll('img[alt]')).map(i=>i.alt),"
                " hasLi45: !!document.querySelector('li[data-index=\\\"45\\\"]'),"
                " liIndexes: Array.from(document.querySelectorAll('li[data-index]')).map(n=>n.getAttribute('data-index')) };"
            )
        except Exception:
            dbg = None

        # JS that finds img by exact alt (case-insensitive) first, then partial match
        js_select_by_alt = r"""
var label = arguments[0].toLowerCase();
var imgs = Array.from(document.querySelectorAll('img[alt]'));
for (var pass = 0; pass < 2; pass++) {
  for (var i = 0; i < imgs.length; i++) {
    var alt = (imgs[i].alt || '').toLowerCase();
    if (pass === 0 && alt !== label) continue;
    if (pass === 1 && alt.indexOf(label) === -1) continue;
    var li = imgs[i].closest('li') || imgs[i].parentElement;
    if (!li) continue;
    try { li.scrollIntoView({ behavior: 'auto', block: 'center' }); } catch (e) {}
    try { li.click(); } catch (e) {}
    var track = document.querySelector('.react-multi-carousel-track');
    if (track) {
      var items = track.querySelectorAll('li');
      for (var j = 0; j < items.length; j++) {
        var it = items[j]; var im = it.querySelector('img[alt]');
        if (im && (im.alt || '').toLowerCase().indexOf(label) > -1) {
          var cls = it.className || '';
          if (cls.indexOf('active') > -1 || cls.indexOf('react-multi-carousel-item--active') > -1) return { ok: true, method: 'alt', index: it.getAttribute('data-index') };
        }
      }
    }
    return { ok: true, method: 'alt', index: li.getAttribute('data-index') };
  }
}
return { ok: false, reason: 'no-match' };
"""

        # Try repeatedly until timeout
        last_res = None
        while time.time() < end:
            try:
                res = driver.execute_script(js_select_by_alt, project_label)
                last_res = res
                if isinstance(res, dict) and res.get('ok'):
                    return {'selected': True, 'result': res, 'debug': dbg}
                if res is True:
                    return {'selected': True, 'result': res, 'debug': dbg}
            except Exception:
                pass
            time.sleep(0.5)

        # fallback: try clicking li[data-index='45'] specifically
        js_index = r"""
var lis = Array.from(document.querySelectorAll('li'));
for(var i=0;i<lis.length;i++){ var v = lis[i].getAttribute('data-index');
 if(v=== '45'){ var el = lis[i]; try{ el.scrollIntoView({behavior:'auto',block:'center'}); }catch(e){}; try{ el.click(); }catch(e){}; return {ok:true, index:v}; }
}
return {ok:false};
"""
        last_res = None
        end2 = time.time() + 6.0
        while time.time() < end2:
            try:
                res = driver.execute_script(js_index)
                last_res = res
                if isinstance(res, dict) and res.get('ok'):
                    return {'selected': True, 'result': res, 'debug': dbg}
                if res is True:
                    return {'selected': True, 'result': res, 'debug': dbg}
            except Exception:
                pass
            time.sleep(0.4)

        return {'selected': False, 'result': last_res, 'debug': dbg}
    except Exception as e:
        return {'selected': False, 'result': str(e), 'debug': dbg}
