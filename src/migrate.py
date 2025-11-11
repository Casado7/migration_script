#!/usr/bin/env python3
"""Scaffold para script de migración ERP -> ERP.

Modo de uso:
    python src\migrate.py --dry-run
"""
import os
import argparse
import webbrowser
from dotenv import load_dotenv


def load_config():
    load_dotenv()
    return {
        'SOURCE_DB_URL': os.getenv('SOURCE_DB_URL'),
        'SOURCE_PAGE_URL': os.getenv('SOURCE_PAGE_URL'),
        'TARGET_DB_URL': os.getenv('TARGET_DB_URL'),
        'LOG_LEVEL': os.getenv('LOG_LEVEL', 'INFO'),
        'DRY_RUN': os.getenv('DRY_RUN', 'true').lower() in ('1', 'true', 'yes')
    }


def main():
    cfg = load_config()

    parser = argparse.ArgumentParser(description='Migración de datos ERP')
    parser.add_argument('--dry-run', action='store_true', help='No escribe en el destino; solo simula')
    parser.add_argument('--open-source', action='store_true', help='Abrir la página SOURCE en el navegador por defecto')
    args = parser.parse_args()

    # Si el usuario pidió abrir la página source, abrirla y salir
    if getattr(args, 'open_source', False):
        source_page = cfg.get('SOURCE_PAGE_URL')
        if not source_page:
            print('ERROR: SOURCE_PAGE_URL no está definida en .env')
            return
        print(f'Abrir en el navegador: {source_page}')
        try:
            webbrowser.open(source_page, new=2)
            print('Se intentó abrir la URL en el navegador por defecto.')
        except Exception as e:
            print('Error al intentar abrir el navegador:', e)
        return

    dry_run = args.dry_run or cfg.get('DRY_RUN')

    print('Configuración cargada:')
    for k, v in cfg.items():
        print(f'  {k} = {v}')
    print('Dry run final:', dry_run)

    # Punto de entrada: conectar a orígenes/destinos y ejecutar migraciones
    # TODO: implementar conectores para la base de datos origen y destino
    # Ejemplo de pasos:
    # 1) Conectar a SOURCE_DB_URL y leer datos (por lotes)
    # 2) Mapear/transformar según reglas necesarias
    # 3) Insertar en TARGET_DB_URL (o simular si dry_run=True)

    print('\n[NOTA] Este es un scaffold. Implementa las funciones de conexión y transformación.')


if __name__ == '__main__':
    main()
