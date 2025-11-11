# Migración ERP -> ERP

Proyecto pequeño para migrar datos entre dos sistemas ERP.

Contenido:
- `src/migrate.py`: script principal (scaffold).
- `.env.example`: variables de entorno necesarias.
- `requirements.txt`: dependencias mínimas.

Requisitos (Windows PowerShell):
- Python 3.8+ instalado
- Git instalado

Instrucciones rápidas (PowerShell):

1) Verificar Python:
```powershell
python --version
```

Si no está instalado, dos opciones:
- Usar el instalador oficial desde https://www.python.org/downloads/
- Si tienes `winget`: 
```powershell
winget install -e --id Python.Python.3
```

2) Inicializar repo Git (si aún no):
```powershell
git init
git add .
git commit -m "Initial commit"
```

3) Crear y activar entorno virtual:
```powershell
python -m venv .venv
# Activar en PowerShell
.\.venv\Scripts\Activate.ps1
```

4) Instalar dependencias:
```powershell
pip install -r requirements.txt
```

5) Configurar variables de entorno:
- Copia `.env.example` a `.env` y edita las URLs/credenciales.

6) Ejecutar el script (modo dry-run para pruebas):
```powershell
python src\migrate.py --dry-run
```

Notas:
- Este repositorio contiene un scaffold inicial. El siguiente paso es definir las fuentes y destinos (tipo de base de datos, credenciales) y diseñar las transformaciones.
- Añade pruebas y backups antes de operarlo en producción.
