from __future__ import annotations
from typing import Dict
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException


def extract_client_info(driver) -> Dict[str, str]:
    """Extrae la información del cliente desde la pestaña 'Cliente' en la página de detalle.

    Devuelve un diccionario con campos comunes (name, birth_date, rfc, curp, sexo, estado_civil,
    telefono_local, telefono_celular, email, id_cliente, codigo_venta). Los valores ausentes son cadenas vacías.
    """
    # Mapear labels (en minúsculas) a claves de salida
    fields = {
        "nombre": "name",
        "fecha nacimiento": "birth_date",
        "lugar de nacimiento": "lugar_nacimiento",
        "edad": "edad",
        "rfc": "rfc",
        "curp": "curp",
        "sexo": "sexo",
        "estado civil": "estado_civil",
        # DIRECCIÓN
        "calle": "calle",
        "num. interior": "num_interior",
        "num interior": "num_interior",
        "num. exterior": "num_exterior",
        "num exterior": "num_exterior",
        "nacionalidad": "nacionalidad",
        "país": "pais",
        "pais": "pais",
        "estado": "estado",
        "localidad": "localidad",
        "codigo postal": "codigo_postal",
        "colonia": "colonia",
        # CONTACTO
        "numero de telefono local": "telefono_local",
        "numero de telefono celular": "telefono_celular",
        "correo electronico": "email",
        # DATOS COMPLEMENTARIOS
        "ocupacion": "ocupacion",
        "actividad economica": "actividad_economica",
        "tipo de identificacion": "tipo_identificacion",
        "numero de identificacion": "numero_identificacion",
        "tipo de persona": "tipo_persona",
        # hidden / href-sourced
        "id_cliente": "id_cliente",
        "codigo_venta": "codigo_venta",
    }


    def find_by_label_text(label_text: str) -> str:
        # probar varias XPaths robustas
        xp_candidates = [
            f"//label[translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz') = '{label_text}']/following::p[1]",
            f"//label[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{label_text}')]/following::p[1]",
            f"//dt[translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz') = '{label_text}']/following::dd[1]",
            f"//div[translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz') = '{label_text}']/following::p[1]",
            f"//*[translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz') = '{label_text}']/following::p[1]",
        ]
        for xp in xp_candidates:
            try:
                el = driver.find_element(By.XPATH, xp)
                txt = el.text.strip()
                if txt:
                    return txt
            except NoSuchElementException:
                continue
            except Exception:
                continue
        return ""

    result = {v: "" for v in fields.values()}

    # Extraer inputs ocultos id_cliente y codigo_venta primero
    for hidden_name in ("id_cliente", "codigo_venta", "codigoVenta", "idCliente"):
        try:
            el = driver.find_element(By.XPATH, f"//input[@name='{hidden_name}']")
            val = el.get_attribute('value') or ""
            if val:
                if 'id_cliente' in hidden_name or hidden_name == 'idCliente':
                    result['id_cliente'] = val
                elif 'codigo' in hidden_name.lower():
                    result['codigo_venta'] = val
        except Exception:
            pass

    # Si no se obtuvieron id_cliente/codigo_venta desde inputs, intentar extraer del enlace 'Modificar Datos'
    if not result.get('id_cliente') or not result.get('codigo_venta'):
        try:
            anchors = driver.find_elements(By.XPATH, "//a[contains(@href,'Formulario_Cliente') or contains(@href,'Formulario_Cliente.php') or contains(@href,'Formulario_Cliente.php?id_cliente')]")
            for a in anchors:
                try:
                    href = a.get_attribute('href') or a.get_attribute('data-href') or ''
                    if not href:
                        continue
                    # parse query params
                    from urllib.parse import urlparse, parse_qs

                    parsed = urlparse(href)
                    qs = parse_qs(parsed.query)
                    idc = qs.get('id_cliente') or qs.get('idCliente') or qs.get('id')
                    cod = qs.get('codigo_venta') or qs.get('codigoVenta') or qs.get('codigo')
                    if idc and not result.get('id_cliente'):
                        result['id_cliente'] = idc[0]
                    if cod and not result.get('codigo_venta'):
                        result['codigo_venta'] = cod[0]
                    if result.get('id_cliente') and result.get('codigo_venta'):
                        break
                except Exception:
                    continue
        except Exception:
            pass

    # Extraer campos visibles por etiqueta
    for label, key in fields.items():
        if key in ("id_cliente", "codigo_venta"):
            # ya manejados
            continue
        try:
            val = find_by_label_text(label)
        except Exception:
            val = ""
        result[key] = val or ""

    # intento adicional para 'nombre' si quedó vacío
    if not result.get('name'):
        try:
            el = driver.find_element(By.XPATH, "//label[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'nombre')]/following::p[1]")
            result['name'] = el.text.strip()
        except Exception:
            pass

    return result
