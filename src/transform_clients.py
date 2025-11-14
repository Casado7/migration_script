#!/usr/bin/env python3
"""Transform extracted clients to TEST_CLIENT_DEFAULTS-like format.

Reads `output/clients.json` by default and writes `output/converted_clients.json`.
You can override input/output via CLI args.
"""
from __future__ import annotations
import argparse
import json
import os
import sys
from typing import Any, Dict, List
import uuid
import re
import unicodedata


def split_name(fullname: str) -> Dict[str, str]:
    # normalize and split, removing pure-punctuation tokens
    raw_parts = (fullname or "").strip().split()

    def is_noise(tok: str) -> bool:
        t = (tok or "").strip()
        if not t:
            return True
        # if token contains no alphanumeric letters, treat as noise (e.g. ".")
        for ch in t:
            if ch.isalnum() or ch.isalpha():
                return False
        return True

    parts = [p for p in raw_parts if not is_noise(p)]

    res = {"name": "", "middle_name": "", "last_name": "", "mothers_name": ""}
    if not parts:
        return res

    # Spanish name articles/prefixes that should attach to the following surname
    ARTICLES = {"DE", "DEL", "LA", "LAS", "LOS", "Y", "MC", "VON", "VAN"}

    if len(parts) == 1:
        res["name"] = parts[0]
        return res

    if len(parts) == 2:
        res["name"] = parts[0]
        res["last_name"] = parts[1]
        return res

    if len(parts) == 3:
        # assume: name, last_name, mothers_name (no middle name)
        res["name"] = parts[0]
        res["last_name"] = parts[1]
        res["mothers_name"] = parts[2]
        return res

    # 4+ parts: name, middle_name(s), last_name, mothers_name
    name_val = parts[0]
    mothers = parts[-1]
    last_tokens = [parts[-2]]
    middle_tokens = parts[1:-2]

    # If middle_tokens end with an article (or two-token article like DE LA), move it to last_name
    if middle_tokens:
        # check two-token article (DE LA / DE LAS / DE LOS)
        if len(middle_tokens) >= 2 and middle_tokens[-2].upper() == "DE" and middle_tokens[-1].upper() in {"LA", "LAS", "LOS"}:
            last_tokens.insert(0, middle_tokens.pop())
            last_tokens.insert(0, "DE")
        else:
            last_tok_upper = middle_tokens[-1].upper()
            if last_tok_upper in ARTICLES:
                last_tokens.insert(0, middle_tokens.pop())

    middle_val = " ".join(middle_tokens).strip()
    last_val = " ".join(last_tokens).strip()

    res["name"] = name_val
    res["middle_name"] = middle_val
    res["last_name"] = last_val
    res["mothers_name"] = mothers
    return res


def reformat_birth(birth: str) -> str:
    if not birth:
        return ""
    # expect YYYY-MM-DD -> convert to DD-MM-YYYY
    try:
        parts = birth.split("-")
        if len(parts) == 3 and len(parts[0]) == 4:
            return f"{parts[2]}-{parts[1]}-{parts[0]}"
    except Exception:
        pass
    return birth


def map_sex(val: str) -> str:
    if not val:
        return ""
    v = val.strip().upper()
    if v.startswith("M") and "MU" not in v:  # 'M' or 'MASC' -> male
        return "M"
    if v.startswith("MU") or v.startswith("F") or v == "MUJER":
        return "F"
    if v.startswith("H"):
        return "M"
    # fallback: take first letter
    return v[0]


def build_address(item: Dict[str, Any]) -> Dict[str, str]:
    calle = (item.get("calle") or "").strip()
    num_ext = (item.get("num_exterior") or "").strip()
    num_int = (item.get("num_interior") or "").strip()
    colonia = (item.get("colonia") or "").strip()
    parts = [calle]
    if num_ext:
        parts.append(num_ext)
    if num_int:
        parts.append(f"Int {num_int}")
    if colonia:
        parts.append(colonia)
    address = " ".join([p for p in parts if p])
    return {
        "country": item.get("pais") or item.get("nacionalidad") or "México",
        "state": item.get("estado") or "",
        "city": item.get("localidad") or "",
        "postal_code": item.get("codigo_postal") or "",
        "address": address,
    }


def transform_client(item: Dict[str, Any]) -> Dict[str, Any]:
    name_parts = split_name(item.get("name", ""))

    addr = build_address(item)

    raw_phone = (item.get("telefono_local") or "" ).strip()
    raw_cellphone = (item.get("telefono_celular") or "" ).strip()
    # keep only digits for phone fields
    phone = re.sub(r"\D+", "", raw_phone)
    cellphone = re.sub(r"\D+", "", raw_cellphone)
    # prefer cellphone for `cellphone` and phone for `phone`
    # apply defaults for required fields
    name_val = name_parts.get("name", "") or "Sin Nombre"
    last_name_val = name_parts.get("last_name", "") or "Sin Apellido"
    middle_val = name_parts.get("middle_name", "") or ""
    mothers_val = name_parts.get("mothers_name", "") or ""

    birth_val = reformat_birth(item.get("birth_date") or item.get("birth") or "")
    if not birth_val:
        birth_val = "01-01-1900"

    raw_email = (item.get("email") or "").strip()
    if raw_email:
        email_val = raw_email
    else:
        # generate a unique test email for missing emails
        email_val = f"{uuid.uuid4().hex}@test.com"

    cellphone_val = cellphone or "5555555"

    nationality_val = item.get("nacionalidad") or item.get("pais") or "Mexicano"

    def _norm(s: str) -> str:
        if not s:
            return ""
        s2 = str(s)
        s2 = unicodedata.normalize('NFD', s2)
        s2 = s2.encode('ascii', 'ignore').decode('ascii')
        return s2.lower().strip()

    def choose_profession(raw: str) -> str:
        """Map raw occupation text to one of the canonical categories.

        Uses simple keyword heuristics; returns fallback 'NO ESPECIFICADOS Y NO DECLARADOS'.
        """
        if not raw:
            return "NO ESPECIFICADOS Y NO DECLARADOS"
        t = _norm(raw)

        # Exact matches / common keywords
        if any(k in t for k in ("ama de casa", "ama", "ama_casa", "ama_de_casa")):
            return "AMA DE CASA"
        if any(k in t for k in ("estudiante", "alumno", "estudia")):
            return "ESTUDIANTE"
        if any(k in t for k in ("jubil", "retir", "pension")):
            return "RETIRADO/JUBILADO"

        # Professionals
        if any(k in t for k in ("ingenier", "abog", "medic", "doctor", "arquitect", "contad", "profesion", "profesional", "licenciad", "odontol")):
            return "PROFESIONISTAS"

        if any(k in t for k in ("tecnic", "tec ", "tecnico")):
            return "TECNICOS"

        # Education / arts / sports
        if any(k in t for k in ("docent", "profesor", "maestr", "educ")):
            return "TRABAJADORES DE LA EDUCACION"
        if any(k in t for k in ("artista", "actor", "musico", "music", "deport", "entrenador", "show", "espectac")):
            return "TRABAJADORES DEL ARTE, ESPECTACULOS Y DEPORTES"

        # Management / directors
        if any(k in t for k in ("director", "gerente", "gerencia", "jefe", "president", "coordinador", "administrador", "subdirector")):
            return "FUNCIONARIOS Y DIRECTIVOS DE LOS SECTORES PUBLICO, PRIVADO Y SOCIAL"

        # Agriculture / primary sector
        if any(k in t for k in ("agric", "ganad", "campo", "pesca", "silvic")):
            return "TRABAJADORES EN ACTIVIDADES AGRICOLAS, GANADERAS, SILVICOLAS Y DE CAZA Y PESCA"

        # Supervisors / production leaders
        if any(k in t for k in ("supervis", "supervisor", "encargado", "capataz")):
            return "JEFES, SUPERVISORES Y OTROS TRABAJADORES DE CONTROL EN LA FABRICACION ARTESANAL E INDUSTRIAL Y EN ACTIVIDADES DE REPARACION Y MANTENIMIENTO"

        # Artisans / factory workers
        if any(k in t for k in ("artesan", "fabril", "fabr", "operario", "obrero", "taller", "fabrica", "manufactur")):
            return "ARTESANOS Y TRABAJADORES FABRILES EN LA INDUSTRIA DE LA TRANSFORMACION Y TRABAJADORES EN ACTIVIDADES DE REPARACION Y MANTENIMIENTO"

        # Operators / machinery
        if any(k in t for k in ("operador", "maquinaria", "operar maquin", "maquin")):
            return "OPERADORES DE MAQUINARIA FIJA DE MOVIMIENTO CONTINUO Y EQUIPOS EN EL PROCESO DE FABRICACION INDUSTRAL"

        # Helpers / laborers
        if any(k in t for k in ("ayudante", "peon", "peon", "obreros", "ayudant")):
            return "AYUDANTES, PEONES Y SIMILARES EN EL PROCESO DE FABRICACION ARTESANAL E INDUSTRIAL Y EN ACTIVIDADES DE REPARACION Y MANTENIMIENTO"

        # Drivers
        if any(k in t for k in ("chofer", "conductor", "taxi", "camion", "camionero")):
            return "CONDUCTORES Y AYUDANTES DE CONDUCTORES DE MAQUINARIA MOVIL Y MEDIOS DE TRANSPORTE"

        # Administrative / service supervisors
        if any(k in t for k in ("coordinador", "jefe de departamento", "coordinacion", "jefe de")):
            return "JEFES DE DEPARTAMENTO, COORDINADORES Y SUPERVISORES EN ACTIVIDADES ADMINISTRATIVAS Y DE SERVICIOS"

        # Administrative support
        if any(k in t for k in ("administrativ", "auxiliar", "secretar", "asistente")):
            return "TRABAJADORES DE APOYO EN ACTIVIDADES ADMINISTRATIVAS"

        # Commerce / sales
        if any(k in t for k in ("comerc", "venta", "vendedor", "ventas", "empleado de comercio", "agente")):
            return "COMERCIANTES, EMPLEADOS DE COMERCIO Y AGENTES DE VENTAS"

        if any(k in t for k in ("ambulant", "ambulante", "vendedor ambulante")):
            return "VENDEDORES AMBULANTES Y TRABAJADORES AMBULANTES EN SERVICIOS"

        # Personal services
        if any(k in t for k in ("estetica", "peluquer", "salon", "restaurante", "hotel", "servicio")):
            return "TRABAJADORES EN SERVICIOS PERSONALES EN ESTABLECIMIENTOS"

        # Domestic services
        if any(k in t for k in ("domestic", "servicios domesticos", "empleada domestica", "domestic")):
            return "TRABAJADORES EN SERVICIOS DOMESTICOS"

        # Protection / security
        if any(k in t for k in ("segurid", "vigilant", "policia", "militar", "fuerza armada")):
            return "TRABAJADORES EN SERVICIOS DE PROTECCION Y VIGILANCIA Y FUERZAS ARMADAS"

        # Support to production
        if any(k in t for k in ("produccion", "mantenimiento", "apoyo a la produccion", "soporte de produccion")):
            return "TRABAJADORES EN SERVICIOS DE APOYO A LA PRODUCCIÓN"

        # Default fallback
        return "NO ESPECIFICADOS Y NO DECLARADOS"

    profession_val = choose_profession(item.get("ocupacion") or item.get("actividad_economica") or "")

    out = {
        "name": name_val,
        "middle_name": middle_val,
        "last_name": last_name_val,
        "mothers_name": mothers_val,
        "birth": birth_val,
        "email": email_val,
        "phone_prefix": "52",
        "phone": phone,
        "cellphone_prefix": "52",
        "cellphone": cellphone_val,
        # address fields as expected by the inserter
        "client_address[0].country": addr["country"] or "México",
        "client_address[0].state": addr["state"],
        "client_address[0].city": addr["city"],
        "client_address[0].postal_code": addr["postal_code"],
        "client_address[0].address": addr["address"],
        # other mappings
        "origin_country": item.get("pais") or nationality_val,
        "nationality": nationality_val,
        "marital_status": item.get("estado_civil") or "",
        "profession_id": profession_val,
        "sex": map_sex(item.get("sexo") or ""),
        "client_kind": "M",
    }

    return out


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Transform clients into form-ready objects")
    parser.add_argument("input", nargs="?", help="input JSON file (defaults to ../output/clients.json)")
    parser.add_argument("-o", "--output", help="output file (defaults to ../output/converted_clients.json)")
    args = parser.parse_args(argv)

    default_input = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "output", "clients.json"))
    default_output = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "output", "converted_clients.json"))

    try:
        if args.input:
            with open(args.input, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            with open(default_input, "r", encoding="utf-8") as f:
                data = json.load(f)
    except Exception as e:
        print(f"Error reading input JSON: {e}", file=sys.stderr)
        return 2

    if not isinstance(data, list):
        print("Input must be a JSON array", file=sys.stderr)
        return 3

    transformed: List[Dict[str, Any]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        transformed.append(transform_client(item))

    out_path = args.output if args.output else default_output
    try:
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(transformed, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error writing output JSON: {e}", file=sys.stderr)
        return 4

    print(f"Transformed {len(transformed)} clients -> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
