from __future__ import annotations
import re
from selenium.webdriver.common.by import By
from typing import Dict


def _first_number_token(s: str) -> str:
    """Return the first numeric token (digits, commas, dots) found in s, or empty string."""
    if not s:
        return ""
    m = re.findall(r"[\d.,]+", s)
    return m[0] if m else ""


def extract_credit_info(driver) -> Dict[str, str]:
    """Extrae la sección 'Información del Crédito' y la normaliza al esquema requerido.

    Devuelve un dict con claves en formato solicitado, p. ej.:

    {
      "desarrollo": "UKUUN",
      "unidad": "111",
      "etapa": "DIAMANTE II",
      "superficie": "235.15",
      "precio_m2": "2,229.58",
      ...
    }

    La función intenta ser tolerante con distintas estructuras de columnas: algunos
    renglones contienen 2 columnas (etiqueta, valor), otros 3 (etiqueta, %, monto).
    """
    try:
        xp = "//div[contains(normalize-space(.), 'Información del Crédito')]/ancestor::div[contains(@class,'form-layout')][1]"
        blk = driver.find_element(By.XPATH, xp)
    except Exception:
        try:
            blk = driver.find_element(By.XPATH, "//div[contains(@class,'form-layout') and .//div[contains(., 'Desarrollo')]]")
        except Exception:
            return {}

    info: Dict[str, str] = {
        "desarrollo": "",
        "unidad": "",
        "etapa": "",
        "superficie": "",
        "precio_m2": "",
        "precio_lista": "",
        "plan_de_pago": "",
        "cuota_de_apertura": "",
        "descuento_%": "",
        "descuento_m2": "",
        "moneda_del_contrato": "",
        "precio_venta": "",
        "enganche_%": "",
        "enganche": "",
        "financiamiento_%": "",
        "financiamiento": "",
        "costo_escritura": "",
    }

    try:
        rows = blk.find_elements(By.XPATH, ".//div[contains(@class,'row') and contains(@class,'no-gutters')]")
    except Exception:
        return info

    for r in rows:
        try:
            cols = r.find_elements(By.XPATH, "./div")
            texts = [c.text.strip() for c in cols if (c.text or '').strip()]
            if not texts or len(texts) == 1:
                continue
            label = re.sub(r"\s+", " ", texts[0]).strip().lower()

            # Helper to safely get nth text
            def t(n: int) -> str:
                return texts[n] if n < len(texts) else ""

            # Match common labels (lenient contains checks)
            if "desarrollo" in label:
                info["desarrollo"] = t(1)
            elif "no. unidad" in label or "no unidad" in label or label == "unidad":
                # sometimes there is a 'Cambiar' button as third column
                info["unidad"] = t(1)
            elif "etapa" in label:
                info["etapa"] = t(1)
            elif "superficie" in label:
                info["superficie"] = _first_number_token(t(1))
            elif "precio x m" in label or "precio x m" in label or "precio por m" in label or "precio x" in label and "m" in label:
                info["precio_m2"] = _first_number_token(t(1))
            elif "precio de lista" in label or "precio lista" in label:
                info["precio_lista"] = _first_number_token(t(1))
            elif "plan de pago" in label:
                info["plan_de_pago"] = t(1)
            elif "cuota de apertura" in label:
                info["cuota_de_apertura"] = _first_number_token(t(1))
            elif "descuento" in label and "%" in " ".join(texts):
                # row with discount: [label, percent, amount]
                info["descuento_%"] = _first_number_token(t(1))
                info["descuento_m2"] = _first_number_token(t(2))
            elif "moneda del contrato" in label or "moneda" == label:
                info["moneda_del_contrato"] = t(1)
            elif "precio venta" in label or "precio de venta" in label:
                info["precio_venta"] = _first_number_token(t(1))
            elif label.startswith("enganche"):
                # [label, percent, amount]
                info["enganche_%"] = _first_number_token(t(1))
                info["enganche"] = _first_number_token(t(2))
            elif "financiamiento" in label:
                info["financiamiento_%"] = _first_number_token(t(1))
                info["financiamiento"] = _first_number_token(t(2))
            elif "costo escritura" in label or "costo de escritura" in label:
                info["costo_escritura"] = _first_number_token(t(1))
            else:
                # fallback: try to detect if label contains any of the keywords
                if "precio" in label and "venta" in label and not info["precio_venta"]:
                    info["precio_venta"] = _first_number_token(t(1))
                # otherwise ignore unknown labels
        except Exception:
            continue

    return info
