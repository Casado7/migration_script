from __future__ import annotations
import re
from selenium.webdriver.common.by import By
from typing import Dict


def extract_credit_info(driver) -> Dict[str, str]:
    """Extrae la sección 'Información del Crédito' (primer tab) y devuelve un diccionario.
    Busca el contenedor que contiene el texto 'Información del Crédito' y parsea filas
    formateando la etiqueta en mayúsculas como clave y el valor como string.
    """
    try:
        # localizar bloque principal por el título visible
        xp = "//div[contains(normalize-space(.), 'Información del Crédito')]/ancestor::div[contains(@class,'form-layout')][1]"
        blk = driver.find_element(By.XPATH, xp)
    except Exception:
        # fallback: buscar por clase 'form-layout' que contenga 'Desarrollo' o 'Precio Venta'
        try:
            blk = driver.find_element(By.XPATH, "//div[contains(@class,'form-layout') and .//div[contains(., 'Desarrollo')]]")
        except Exception:
            return {}

    info: Dict[str, str] = {}
    # cada fila suele ser un div.row no-gutters con varias columnas
    try:
        rows = blk.find_elements(By.XPATH, ".//div[contains(@class,'row') and contains(@class,'no-gutters')]")
    except Exception:
        return info

    for r in rows:
        try:
            # recoger textos de columnas relevantes
            cols = r.find_elements(By.XPATH, "./div")
            texts = [c.text.strip() for c in cols if (c.text or '').strip()]
            if not texts:
                continue
            # ignorar filas que sean solo botones/acciones
            # identificar etiqueta = primer texto y valor = resto
            if len(texts) == 1:
                # a veces la fila contiene solo un título como 'Información del Crédito'
                continue
            label = texts[0]
            value = " ".join(texts[1:]).strip()
            # normalizar clave: mayúsculas y espacios simples
            key = re.sub(r"\s+", " ", label).strip().upper()
            info[key] = value
        except Exception:
            # si algo falla procesando esta fila, continuar con la siguiente
            continue

    return info
