from __future__ import annotations
import os
import sys
import time
import json
from typing import Dict, Any
import re
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait, Select
from helppers.extract_credit import extract_credit_info
from helppers.extract_client import extract_client_info
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import WebDriverException, TimeoutException, NoSuchElementException
from selenium.common.exceptions import StaleElementReferenceException


# Helpers to make output paths deterministic (always under repo root/output)
def _get_repo_root() -> str:
	# file is src/migrate.py -> repo root is parent of src
	return os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))


def _resolve_output_path(path: str) -> str:
	"""Return an absolute path inside the repository for a given relative output path.

	If `path` is absolute, returns it unchanged. If relative, it's joined to the repo root.
	This ensures all output files go to <repo_root>/output/... regardless of CWD.
	"""
	if not path:
		return path
	if os.path.isabs(path):
		return path
	# normalize slashes and join to repo root
	repo_root = _get_repo_root()
	return os.path.join(repo_root, path.replace('/', os.sep).replace('\\', os.sep))


def extract_all_clients(driver, out_path: str = "output/clients.json", max_rows: int | None = None, max_pages: int | None = None, timeout: int = 30):
	"""Recorre todas las filas de la tabla principal, abre cada detalle (clic en Ver más),
	extrae la información del cliente y la agrega a out_path.

	Deduplicamos por `codigo_venta` cuando esté disponible.

	max_pages: si no es None, limita el número de páginas a recorrer (1 = solo la primera página).
	"""
	# ensure out_path is absolute and points to repo-root/output
	out_path = _resolve_output_path(out_path)

	clients = []
	seen_codes = set()
	skipped_rows = []  # collect diagnostics about skipped rows

	# cargar existentes si hay y normalizarlas al nuevo esquema {'row': {...}, 'cliente': {...}}
	try:
		if os.path.exists(out_path):
			with open(out_path, "r", encoding="utf-8") as fh:
				existing = json.load(fh)
				for item in existing:
					# si ya está en nuevo formato, conservar
					if isinstance(item, dict) and 'row' in item and 'cliente' in item:
						clients.append(item)
						continue
					# si es un dict que parece cliente (tiene 'name' o 'id_cliente'), envolver
					if isinstance(item, dict):
						if 'name' in item or 'id_cliente' in item or 'codigo_venta' in item:
							clients.append({'row': {}, 'cliente': item, 'info_credito': {}})
							continue
					# otherwise, append as-is
					clients.append(item)
	except Exception:
		# ignorar errores de carga
		pass

	# localizar tabla
	table = detect_main_table(driver)
	if table is None:
		print("No se encontró tabla para iterar filas")
		return clients

	processed = 0
	page_index = 1
	# loop over pages until no next page
	while True:
		try:
			rows = driver.find_elements(By.XPATH, "//table//tr[td]")
		except Exception:
			rows = []

		total_in_page = len(rows)
		# compute remaining allowed if max_rows provided
		remaining = None if max_rows is None else max(0, max_rows - processed)
		to_process = total_in_page if remaining is None else min(total_in_page, remaining)

		print(f"Found {total_in_page} data rows on page {page_index}; extracting up to {to_process} this page")

		for i in range(to_process):
			try:
				# re-evaluar filas cada iteración para evitar StaleElementReference
				rows = driver.find_elements(By.XPATH, "//table//tr[td]")
				if i >= len(rows):
					break
				row = rows[i]
			except Exception as e:
				# si no podemos acceder a las filas, saltar esta iteración
				print(f"Warning: no se pudo acceder a la fila {i} en la página {page_index}: {e}")
				continue

			# construir mapeo de columnas para esta fila (usaremos el orden canónico)
			col_map = {}
			try:
				canonical = [
					"Temp.", "Sucursal", "Asesor", "Cliente", "Desarrollo", "Unidad",
					"Fecha Venta", "Estado", "Plan", "Acciones", "Codigo Venta",
				]
				def _norm_key(s: str) -> str:
					return re.sub(r"[^0-9a-z]+", "_", (s or '').strip().lower()).strip('_')
				keys = [_norm_key(x) for x in canonical]
				cells = row.find_elements(By.XPATH, "./td")
				for idx, cell in enumerate(cells, start=1):
					try:
						val = cell.text.strip()
					except Exception:
						val = ""
					if idx-1 < len(keys):
						k = keys[idx-1]
					else:
						k = f"col_{idx}"
					col_map[k] = val
			except Exception:
				col_map = {}
			# localizar la última celda y tratar de obtener codigo_venta desde la fila
			try:
				last_td = row.find_element(By.XPATH, "./td[last()]")
			except Exception:
				continue

			# intentar leer codigo_venta directamente desde inputs en la fila (evita navegar cuando ya visto)
			code_from_row = ""
			try:
				# buscar input hidden dentro de la última celda o en la fila
				try:
					inp = last_td.find_element(By.XPATH, ".//input[@name='codigo_venta']")
					code_from_row = (inp.get_attribute('value') or "").strip()
				except Exception:
					# buscar en la fila entero
					try:
						inp = row.find_element(By.XPATH, ".//input[@name='codigo_venta']")
						code_from_row = (inp.get_attribute('value') or "").strip()
					except Exception:
						# fallback: buscar cualquier hidden input with 'codigo' in name
						try:
							inp = row.find_element(By.XPATH, ".//input[contains(translate(@name,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'codigo')]")
							code_from_row = (inp.get_attribute('value') or "").strip()
						except Exception:
							code_from_row = ""
			except Exception:
				code_from_row = ""

			# do not skip rows based on previously seen codes; allow duplicates
			# (we still attempt to read code_from_row for diagnostics)

			el = None
			try:
				el = last_td.find_element(By.XPATH, ".//button[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'ver m') or contains(.,'Ver m')]")
			except Exception:
				try:
					candidates = last_td.find_elements(By.XPATH, ".//a | .//button | .//input[@type='button'] | .//input[@type='submit']")
					if candidates:
						el = candidates[0]
				except Exception:
					el = None

			if el is None:
				# nada para clicar en esta fila
				row_html = ""
				try:
					row_html = row.get_attribute('outerHTML')[:2000]
				except Exception:
					row_html = "<unable to get row html>"
				# still, if code_from_row exists and not seen, add a placeholder client with only code
				if code_from_row and code_from_row not in seen_codes:
					client = {k: "" for k in ("name","birth_date","rfc","curp","sexo","estado_civil","telefono_local","telefono_celular","email","id_cliente","codigo_venta")}
					client['codigo_venta'] = code_from_row
					# append as wrapped object with row info
					clients.append({'row': col_map or {'html': row_html}, 'cliente': client, 'info_credito': {}})
					seen_codes.add(code_from_row)
					try:
						dirname = os.path.dirname(out_path)
						if dirname and not os.path.exists(dirname):
							os.makedirs(dirname, exist_ok=True)
						with open(out_path, 'w', encoding='utf-8') as fh:
							json.dump(clients, fh, ensure_ascii=False, indent=2)
					except Exception:
						print('Warning: could not write placeholder client to file')
					# record this event for diagnostics
					skipped_rows.append({
						"row_index": i,
						"reason": "no_clickable_element_but_code_placeholder_created",
						"codigo_venta": code_from_row,
						"row_html": row_html,
					})
					continue
				# no code and no clickable element -> log and continue
				skipped_rows.append({"row_index": i, "reason": "no_clickable_element_no_code", "row_html": row_html})
				print(f"Row {i} skipped: no clickable element and no code found")
				continue

			# click y manejar si abre en nueva ventana/pestaña
			prev_handles = driver.window_handles
			try:
				driver.execute_script('arguments[0].scrollIntoView(true);', el)
				driver.execute_script('arguments[0].click();', el)
			except Exception:
				try:
					el.click()
				except Exception:
					print(f"No se pudo clickear Ver más en fila {i}")
					try:
						row_html = row.get_attribute('outerHTML')[:2000]
					except Exception:
						row_html = "<unable to get row html>"
					skipped_rows.append({"row_index": i, "reason": "click_failed", "row_html": row_html})
					continue

			# esperar breve para que cambie readyState o se abra nueva ventana
			time.sleep(0.5)
			new_handles = driver.window_handles

			opened_new_window = False
			original_handle = None
			if len(new_handles) > len(prev_handles):
				# una nueva ventana/pestaña se abrió
				opened_new_window = True
				# elegir el handle nuevo
				new_handle = [h for h in new_handles if h not in prev_handles][0]
				try:
					original_handle = driver.current_window_handle
				except Exception:
					original_handle = prev_handles[0] if prev_handles else None
				try:
					driver.switch_to.window(new_handle)
				except Exception:
					# si no es posible, continuar con la ventana actual
					opened_new_window = False

			# si no se abrió nueva ventana, esperar la carga en la misma pestaña
			if not opened_new_window:
				try:
					WebDriverWait(driver, timeout).until(lambda d: d.execute_script("return document.readyState") == "complete")
				except Exception:
					time.sleep(0.8)

			# intentar cerrar modales rápidos (misma heurística que antes)
			try:
				close_xpaths = [
					"//button[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'cerrar')]",
					"//button[contains(@class,'close')]",
					"//a[contains(@class,'close')]",
					"//button[@aria-label='Close' or @aria-label='close']",
				]
				for xp in close_xpaths:
					btns = driver.find_elements(By.XPATH, xp)
					if btns:
						try:
							driver.execute_script('arguments[0].click();', btns[0])
							time.sleep(0.2)
							break
						except Exception:
							continue
			except Exception:
				pass

			# intentar activar la pestaña 'Cliente'
			# extraer la sección 'Información del Crédito' antes de cambiar a la pestaña Cliente
			credit_info = {}
			try:
				credit_info = extract_credit_info(driver)
			except Exception:
				credit_info = {}

			# intentar activar la pestaña 'Cliente'
			try:
				tab_xpaths = [
					"//a[normalize-space(.)='Cliente']",
					"//button[normalize-space(.)='Cliente']",
					"//*[@role='tab' and contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'cliente')]",
					"//ul[contains(@class,'nav') or contains(@class,'tabs')]//a[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'cliente')]",
				]
				clicked_tab = False
				for xp in tab_xpaths:
					els = driver.find_elements(By.XPATH, xp)
					if not els:
						continue
					for el_tab in els:
						try:
							driver.execute_script('arguments[0].scrollIntoView({block:"center",inline:"nearest"});', el_tab)
							driver.execute_script('arguments[0].click();', el_tab)
							clicked_tab = True
							time.sleep(0.2)
							break
						except Exception:
							continue
					if clicked_tab:
						break
			except Exception:
				pass

			# extraer cliente
			try:
				client = extract_client_info(driver)
			except Exception as e:
				print(f"Error extrayendo cliente en fila {i}: {e}")
				client = {}
				try:
					row_html = row.get_attribute('outerHTML')[:2000]
				except Exception:
					row_html = "<unable to get row html>"
				skipped_rows.append({"row_index": i, "reason": "extraction_exception", "error": str(e), "row_html": row_html})

			code = client.get('codigo_venta') or client.get('codigo') or ''
			# always append the extracted client (allow duplicates) including credit info
			clients.append({'row': col_map or {}, 'cliente': client, 'info_credito': credit_info})
			if code:
				seen_codes.add(code)
			# escribir incrementalmente
			try:
				dirname = os.path.dirname(out_path)
				if dirname and not os.path.exists(dirname):
					os.makedirs(dirname, exist_ok=True)
				with open(out_path, 'w', encoding='utf-8') as fh:
					json.dump(clients, fh, ensure_ascii=False, indent=2)
			except Exception as e:
				print('Warning: could not write clients file:', e)

			# cerrar ventana nueva si abrimos una y volver a la original
			try:
				if opened_new_window and original_handle:
					try:
						# cerrar la ventana actual (detalle)
						driver.close()
					except Exception:
						pass
					try:
						driver.switch_to.window(original_handle)
					except Exception:
						# fallback: recargar la página fuente
						try:
							url = os.getenv('SOURCE_PAGE_URL')
							if url:
								driver.get(url)
								WebDriverWait(driver, 5).until(lambda d: detect_main_table(d) is not None)
								time.sleep(0.6)
						except Exception:
							pass
				else:
					# navegación en la misma pestaña: intentar back
					try:
						driver.back()
						WebDriverWait(driver, 5).until(lambda d: detect_main_table(d) is not None)
						time.sleep(0.4)
					except Exception:
						try:
							url = os.getenv('SOURCE_PAGE_URL')
							if url:
								driver.get(url)
								WebDriverWait(driver, 5).until(lambda d: detect_main_table(d) is not None)
								time.sleep(0.6)
						except Exception:
							pass
			except Exception:
				# en caso de cualquier fallo no bloquear la iteración
				try:
					url = os.getenv('SOURCE_PAGE_URL')
					if url:
						driver.get(url)
						WebDriverWait(driver, 5).until(lambda d: detect_main_table(d) is not None)
						time.sleep(0.6)
				except Exception:
					pass

				except Exception as e:
					print(f"Warning: fila {i} fallo: {e}")
					continue


        # finished rows on this page (or reached max_rows)
		processed = len(clients)
		# if max_rows limit reached, stop pagination
		if max_rows is not None and processed >= max_rows:
			break

		# if max_pages limit reached, stop pagination
		if max_pages is not None and page_index >= max_pages:
			break

		# intentar navegar a la siguiente página
		moved = go_to_next_page(driver, timeout=timeout)
		if not moved:
			break
		# permitir que la nueva página cargue
		time.sleep(0.6)
		page_index += 1

	print(f"Extraction finished: {len(clients)} clients (including pre-existing)")
	# escribir diagnóstico de filas saltadas para inspección
	try:
		dirname = os.path.dirname(out_path) or 'output'
		if dirname and not os.path.exists(dirname):
			os.makedirs(dirname, exist_ok=True)
		with open(os.path.join(dirname, 'skip_rows_debug.json'), 'w', encoding='utf-8') as fh:
			json.dump(skipped_rows, fh, ensure_ascii=False, indent=2)
		print(f"Wrote skip_rows_debug.json with {len(skipped_rows)} records for diagnosis")
	except Exception as e:
		print('Warning: could not write skip_rows_debug.json:', e)
	return clients

def detect_main_table(driver):
	"""Intenta localizar la tabla principal de ventas en la página.

	Devuelve el elemento WebElement de la primera tabla que parece contener filas de datos,
	o None si no se encontró ninguna.
	"""
	tables = driver.find_elements(By.XPATH, "//table")
	if not tables:
		return None

	# Heurística: elegir la primera tabla que tenga al menos una fila con celdas (<tr><td>)
	for t in tables:
		try:
			rows = t.find_elements(By.XPATH, ".//tr[td]")
			if rows and len(rows) >= 1:
				return t
		except Exception:
			continue
	return None


def _get_active_page_number(driver):
	"""Return the current active page number from the pagination, or None if not found."""
	try:
		el = driver.find_element(By.XPATH, "//li[contains(@class,'page-item') and contains(@class,'active')]//a[contains(@class,'Pagina') or contains(@class,'page-link')]")
		val = el.get_attribute('data-valor') or el.text
		val = (val or '').strip()
		return int(val)
	except Exception:
		return None


def go_to_next_page(driver, timeout: int = 8) -> bool:
	"""Try to navigate to the next page of the table.

	Returns True if navigation to a different page was performed, False if there is no next page.
	"""
	try:
		prev = _get_active_page_number(driver)
		# prefer clicking the next numeric page (current + 1)
		if prev is not None:
			target = prev + 1
			try:
				xpath = f"//a[contains(@class,'Pagina') and (@data-valor='{target}' or normalize-space(.)='{target}') ]"
				el = driver.find_element(By.XPATH, xpath)
				# skip if element appears disabled
				cls = (el.get_attribute('class') or '')
				if 'disabled' in cls or 'cursor-cancel' in cls:
					raise Exception('page link disabled')
				driver.execute_script('arguments[0].scrollIntoView(true);', el)
				driver.execute_script('arguments[0].click();', el)
				WebDriverWait(driver, timeout).until(lambda d: _get_active_page_number(d) != prev)
				print(f"Navigated to page {target}")
				return True
			except Exception:
				# fallback to use the 'siguiente' control
				pass

		# try 'siguiente' control (data-accion='siguiente') if numeric next not found
		try:
			next_btn = driver.find_element(By.XPATH, "//a[contains(@class,'page-link') and @data-accion='siguiente']")
			cls = (next_btn.get_attribute('class') or '')
			if 'cursor-cancel' in cls:
				return False
			driver.execute_script('arguments[0].scrollIntoView(true);', next_btn)
			driver.execute_script('arguments[0].click();', next_btn)
			WebDriverWait(driver, timeout).until(lambda d: _get_active_page_number(d) != prev)
			print("Clicked 'siguiente' pagination control")
			return True
		except Exception:
			pass

		# try jump-control to next block (a10sig)
		try:
			a10 = driver.find_element(By.XPATH, "//a[contains(@class,'page-link') and @data-accion='a10sig']")
			cls = (a10.get_attribute('class') or '')
			if 'cursor-cancel' in cls:
				return False
			driver.execute_script('arguments[0].scrollIntoView(true);', a10)
			driver.execute_script('arguments[0].click();', a10)
			WebDriverWait(driver, timeout).until(lambda d: _get_active_page_number(d) != prev)
			print("Clicked 'a10sig' pagination control (next block)")
			return True
		except Exception:
			pass

		return False
	except Exception:
		return False


def dump_table_html(driver, out_path: str = "output/table.html") -> str:
	"""Guarda el outerHTML de la tabla principal en `out_path` y retorna un preview (primeros 4000 chars).
	Crea el directorio `output/` si no existe.
	"""
	table = detect_main_table(driver)
	if table is None:
		return "<NO_TABLE_FOUND>"

	html = table.get_attribute("outerHTML")
	# resolve to repo-rooted output path and ensure directory exists
	out_path = _resolve_output_path(out_path)
	dirname = os.path.dirname(out_path)
	if dirname and not os.path.exists(dirname):
		os.makedirs(dirname, exist_ok=True)

	with open(out_path, "w", encoding="utf-8") as fh:
		fh.write(html)

	return html[:4000]

	first_row = rows[0]
	# obtener la última celda
	try:
		cells = first_row.find_elements(By.XPATH, "./td")
		if not cells:
			return False
		last_td = cells[-1]
		# intentar buscar específicamente el botón 'Ver más' dentro de la última celda
		try:
			el = last_td.find_element(By.XPATH, ".//button[contains(.,'Ver más') or contains(.,'Ver mas') or contains(.,'ver mas') or contains(.,'VER MAS')]")
		except Exception:
			# fallback: buscar el primer elemento clickeable dentro
			candidates = last_td.find_elements(By.XPATH, ".//a | .//button | .//input[@type='button'] | .//input[@type='submit']")
			if not candidates:
				return False
			el = candidates[0]
		# click seguro
		driver.execute_script('arguments[0].scrollIntoView(true);', el)
		el.click()
		time.sleep(0.8)
		return True
	except StaleElementReferenceException:
		return False
	except Exception:
		return False



def fetch_source_page(headless: bool = False, timeout: int = 30) -> Dict[str, Any]:
	"""Carga SOURCE_PAGE_URL desde .env y la abre con Selenium.

	Nota: por defecto abre el navegador en modo visible (headless=False) para
	facilitar la verificación manual.

	Retorna un dict con keys: url, title, html (str, truncated a 10000 chars), error (si aplica).
	"""
	load_dotenv()
	url = os.getenv("SOURCE_PAGE_URL")
	if not url:
		return {"error": "SOURCE_PAGE_URL no encontrada en .env"}

	options = Options()
	# Usar el nuevo modo headless de Chrome si está disponible
	if headless:
		try:
			options.add_argument("--headless=new")
		except Exception:
			options.add_argument("--headless")

	# Opciones útiles para entornos sin UI
	options.add_argument("--no-sandbox")
	options.add_argument("--disable-dev-shm-usage")
	options.add_argument("--disable-gpu")
	options.add_argument("--window-size=1200,900")
	# Un user-agent básico
	options.add_argument(
		"user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
		"AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
	)

	driver = None
	try:
		driver = webdriver.Chrome(options=options)
		driver.set_page_load_timeout(timeout)
		driver.get(url)

		# Si la página redirige a un formulario de login, intentaremos autenticarnos
		def _attempt_login_if_needed() -> bool:
			try:
				pwd_inputs = driver.find_elements(By.XPATH, "//input[@type='password']")
			except Exception:
				pwd_inputs = []

			if not pwd_inputs:
				return False

			# necesitaremos credenciales en env
			username = os.getenv("HOST_USERNAME")
			password = os.getenv("HOST_PASSWORD")
			if not username or not password:
				raise RuntimeError("LOGIN_REQUIRED: falta HOST_USERNAME o HOST_PASSWORD en .env")

			# heurísticas para localizar el campo de usuario
			username_candidate = None
			# primero intentar buscar dentro del mismo form que el campo password
			try:
				form = pwd_inputs[0].find_element(By.XPATH, "./ancestor::form")
			except Exception:
				form = None

			search_xpaths = []
			if form is not None:
				# buscar inputs relevantes dentro del form
				search_xpaths = [
					".//input[@type='text']",
					".//input[@type='email']",
					".//input[contains(translate(@name,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'user')]",
					".//input[contains(translate(@name,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'username')]",
					".//input[contains(translate(@id,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'user')]",
					".//input[contains(translate(@id,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'username')]",
				]
				for xp in search_xpaths:
					try:
						el = form.find_elements(By.XPATH, xp)
						if el:
							username_candidate = el[0]
							break
					except Exception:
						continue

			# si no encontramos en el form, buscar globalmente
			if username_candidate is None:
				global_xps = [
					"//input[@type='text']",
					"//input[@type='email']",
					"//input[contains(translate(@name,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'user')]",
					"//input[contains(translate(@name,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'username')]",
					"//input[contains(translate(@id,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'user')]",
					"//input[contains(translate(@id,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'username')]",
					"//input[contains(translate(@name,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'email')]",
				]
				for xp in global_xps:
					try:
						el = driver.find_elements(By.XPATH, xp)
						if el:
							# elegir el primero visible/enable
							username_candidate = el[0]
							break
					except Exception:
						continue

			if username_candidate is None:
				raise RuntimeError("LOGIN_REQUIRED: no se encontró campo de usuario automáticamente")

			# escribir credenciales
			try:
				username_candidate.clear()
				username_candidate.send_keys(username)
			except Exception:
				pass

			try:
				pwd = pwd_inputs[0]
				pwd.clear()
				pwd.send_keys(password)
			except Exception:
				raise RuntimeError("LOGIN_FAILED: no se pudo escribir la contraseña")

			# intentar submit: buscar botón dentro del form, si existe
			submitted = False
			try:
				if form is not None:
					btns = form.find_elements(By.XPATH, ".//button[@type='submit'] | .//input[@type='submit']")
					if btns:
						try:
							btns[0].click()
							submitted = True
						except Exception:
							pass
			except Exception:
				pass

			if not submitted:
				# fallback: enviar ENTER en el campo password
				try:
					pwd_inputs[0].send_keys(Keys.ENTER)
					submitted = True
				except Exception:
					pass

			# esperar a cambio de URL o readyState
			try:
				original_url = driver.current_url
				WebDriverWait(driver, min(timeout, 20)).until(
					lambda d: d.current_url != original_url or d.execute_script("return document.readyState") == "complete"
				)
			except Exception:
				# tolerar tiempo de espera; continuamos
				pass

			return submitted

		# intentar login si detectamos formulario de password
		try:
			login_submitted = _attempt_login_if_needed()
		except Exception as e:
			return {"error": str(e)}

		# Si tras el login la URL actual no es la que queremos, navegar explícitamente
		try:
			if driver.current_url.rstrip('/') != url.rstrip('/') or login_submitted:
				# navegar al recurso objetivo
				driver.get(url)
				try:
					WebDriverWait(driver, min(timeout, 20)).until(
						lambda d: d.execute_script("return document.readyState") == "complete"
					)
				except Exception:
					pass

			# Si tras navegar seguimos encontrando un formulario de login, intentar login una vez más
			try:
				pwd_inputs_now = driver.find_elements(By.XPATH, "//input[@type='password']")
			except Exception:
				pwd_inputs_now = []

			if pwd_inputs_now:
				try:
					second_submitted = _attempt_login_if_needed()
				except Exception as e:
					return {"error": str(e)}

				if second_submitted:
						driver.get(url)
						try:
							WebDriverWait(driver, min(timeout, 20)).until(
								lambda d: d.execute_script("return document.readyState") == "complete"
							)
						except Exception:
							pass
		except Exception:
			# no crítico, continuamos y devolveremos el html actual (posiblemente de la home)
			pass

		# Esperar hasta que document.readyState sea 'complete' o hasta timeout
		try:
			WebDriverWait(driver, min(timeout, 20)).until(
				lambda d: d.execute_script("return document.readyState") == "complete"
			)
		except TimeoutException:
			# tolerar, seguiremos y tomaremos el HTML parcial
			pass

		# pequeña espera para permitir JS adicional (ajustable)
		time.sleep(1)
		title = driver.title

		# Volcar HTML de la tabla principal para inspección humana
		try:
			table_preview = dump_table_html(driver, out_path="output/table.html")
			# table saved for inspection; do not print full HTML to console to avoid noisy output
			print("Table preview saved to output/table.html")
		except Exception as e:
			print("Warning: could not dump table html:", e)

		# Intentar seleccionar el filtro 'Desarrollo' a la opción 'UKUUN'
		try:
			# primero intentar con el <select> real
			try:
				sel_el = driver.find_element(By.ID, "desarrollots")
				# intentar seleccionar por texto visible
				try:
					Select(sel_el).select_by_visible_text("UKUUN")
				except Exception:
					# fallback a seleccionar por value (6 según el HTML suministrado)
					try:
						Select(sel_el).select_by_value("6")
					except Exception:
						# como último recurso, establecer value y disparar change via JS
						driver.execute_script("arguments[0].value = arguments[1]; arguments[0].dispatchEvent(new Event('change'));", sel_el, "6")
				# también intentar actualizar el contenedor select2 si está presente
				try:
					driver.execute_script("var c=document.getElementById('select2-desarrollots-container'); if(c){c.textContent=arguments[0]; c.setAttribute('title', arguments[0]);}", "UKUUN")
				except Exception:
					pass
				# esperar un poco a que la tabla se recargue
				try:
					WebDriverWait(driver, 5).until(lambda d: detect_main_table(d) is not None)
					time.sleep(0.8)
				except Exception:
					time.sleep(1)
				print("Selected 'UKUUN' in Desarrollo filter")
			except Exception as e:
				print("Warning: could not set Desarrollo filter to UKUUN:", e)
		except Exception:
			pass

		# Extraer clientes para todas las filas de la tabla
		try:
			# final run: limit pages to 21 (full run)
			clients = extract_all_clients(driver, out_path="output/clients.json", max_rows=None, max_pages=2, timeout=timeout)
			print(f"Extracted {len(clients)} clients (saved to output/clients.json)")
		except Exception as e:
			print("Warning: could not extract clients from all rows:", e)

		html = driver.page_source

		return {"url": url, "title": title, "html": html[:10000]}

	except WebDriverException as e:
		return {"error": f"WebDriverException: {e}"}
	except Exception as e:  # noqa: BLE001 - informar cualquier excepción inesperada
		return {"error": f"Unexpected error: {e}"}
	finally:
		if driver:
			try:
				driver.quit()
			except Exception:
				pass


def _main() -> int:
	# Fuerza abrir el navegador visible
	out = fetch_source_page(headless=False)
	if "error" in out:
		print("ERROR:", out["error"])
		return 1

	print("URL:", out.get("url"))
	print("Title:", out.get("title"))
	# do not print HTML preview to console (can be very large)
	return 0


if __name__ == "__main__":
	raise SystemExit(_main())

