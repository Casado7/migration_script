"""migrate.py

Utilidad mínima para abrir la URL definida en .env (SOURCE_PAGE_URL)
usando Selenium. Devuelve título y HTML (parcial) como comprobación.

Uso:
	python src/migrate.py

Requisitos: selenium, python-dotenv
"""
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
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from selenium.common.exceptions import WebDriverException, TimeoutException, NoSuchElementException
from selenium.common.exceptions import StaleElementReferenceException


def expand_view_more_in_table(driver, timeout: int = 30) -> None:
	"""Recorre filas de tablas y hace click en botones/enlaces "Ver más" dentro de cada fila.

	La función usa heurísticas para encontrar los elementos y intenta cerrar modales
	(enviando ESC) después de abrirlos para continuar con la siguiente fila.
	"""
	# Buscar filas en tablas
	rows = driver.find_elements(By.XPATH, "//table//tr")
	if not rows:
		# intentar buscar contenedores con clase 'tabla' o 'tabla-ventas'
		rows = driver.find_elements(By.XPATH, "//*[contains(@class,'tabla') or contains(@class,'table')]//tr")
		if not rows:
			return

	for i, row in enumerate(rows):
		# obtener botones/enlaces dentro de la fila
		try:
			candidates = row.find_elements(By.XPATH, ".//a | .//button | .//input[@type='button'] | .//input[@type='submit']")
		except StaleElementReferenceException:
			continue

		for el in candidates:
			# obtener texto (manejar elementos input)
			try:
				text = (el.text or el.get_attribute('value') or '').strip()
			except StaleElementReferenceException:
				continue

			if not text:
				continue

			# normalizar y buscar 'ver mas' (sin acento)
			text_norm = text.lower()
			text_norm = text_norm.replace('á', 'a').replace('é', 'e').replace('í', 'i').replace('ó', 'o').replace('ú', 'u')

			if re.search(r"\bver\s*mas\b", text_norm):
				# intentar click y manejo simple de modal
				try:
					driver.execute_script('arguments[0].scrollIntoView(true);', el)
					el.click()
					time.sleep(0.8)
					# intentar cerrar modal o enviar ESC
					try:
						close_btns = driver.find_elements(By.XPATH, "//button[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'cerrar')] | //button[contains(@class,'close')] | //a[contains(@class,'close')]")
						if close_btns:
							close_btns[0].click()
						else:
							body = driver.find_element(By.TAG_NAME, 'body')
							body.send_keys(Keys.ESCAPE)
						time.sleep(0.3)
					except Exception:
						# ignorar errores al cerrar modal
						pass
				except Exception:
					# ignorar errores en click y seguir
					pass

				# dar un pequeño retardo para evitar acciones demasiado rápidas
				time.sleep(0.2)


def click_first_ver_mas_in_last_column(driver, timeout: int = 30) -> bool:
	"""Click en el primer botón/enlace dentro de la última columna de la primera fila de datos.

	Retorna True si realizó el click, False si no encontró el elemento.
	"""
	# seleccionar filas que contienen celdas (evitar encabezados)
	rows = driver.find_elements(By.XPATH, "//table//tr[td]")
	if not rows:
		return False

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

def click_first_ver_mas_and_capture(driver, timeout: int = 30, out_path: str = "output/detail.html") -> str:
	"""Clica el primer 'Ver más' en la última columna de la primera fila y captura la página destino.

	Devuelve un preview del HTML destino (primeros 4000 chars) o '<NO_NAV>' si no navegó.
	"""
	current = None
	try:
		current = driver.current_url
		# Intentar un selector XPath directo a la primera fila, última celda, botón 'Ver más'
		direct_xpath = "(//table//tr[td])[1]/td[last()]//button[contains(normalize-space(.),'Ver m') or contains(normalize-space(.),'Ver más') or contains(normalize-space(.),'Ver mas')]"
		try:
			elem = driver.find_element(By.XPATH, direct_xpath)
			elem.click()
			success = True
		except Exception:
			# fallback a la heurística anterior
			success = click_first_ver_mas_in_last_column(driver, timeout=timeout)
		if not success:
			return "<NO_CLICK>"
		# esperar cambio de URL o carga
		try:
			WebDriverWait(driver, timeout).until(lambda d: d.current_url != current)
		except Exception:
			# si no cambió URL, esperar un poco más por la navegación completa
			time.sleep(1)
		# intentar cerrar modal(s) comunes en la página destino antes de guardar
		try:
			# lista de XPaths comunes para botones de cerrar (español/ingles)
			close_xpaths = [
				"//button[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'cerrar')]",
				"//button[contains(@class,'close')]",
				"//a[contains(@class,'close')]",
				"//button[@aria-label='Close' or @aria-label='close']",
				"//button[contains(.,'\u00d7') or contains(.,'×') or normalize-space(.)='x']",
				"//*[contains(@class,'modal') or contains(@class,'dialog')]//button[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'cerrar') or contains(@class,'close')]",
			]
			clicked = False
			for xp in close_xpaths:
				btns = driver.find_elements(By.XPATH, xp)
				for b in btns:
					try:
						driver.execute_script('arguments[0].scrollIntoView(true);', b)
						b.click()
						clicked = True
						time.sleep(0.4)
						break
					except Exception:
						# ignorar errores al clicar este botón y probar siguiente
						continue
				if clicked:
					break
			# si no encontramos botón, intentar enviar ESC
			if not clicked:
				try:
					body = driver.find_element(By.TAG_NAME, 'body')
					body.send_keys(Keys.ESCAPE)
					time.sleep(0.3)
				except Exception:
					pass
		except Exception:
			# ignorar cualquier fallo en el intento de cerrar modal
			pass

		# intentar clicar la pestaña 'Cliente' si está presente (después de cerrar modales)
		try:
			clicked_tab = False
			# XPaths comunes para la pestaña 'Cliente'
			tab_xpaths = [
				"//a[normalize-space(.)='Cliente']",
				"//button[normalize-space(.)='Cliente']",
				"//li[normalize-space(.)='Cliente']",
				"//a[contains(normalize-space(.),'Cliente')]",
				"//button[contains(normalize-space(.),'Cliente')]",
				"//*[@role='tab' and contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'cliente')]",
				"//ul[contains(@class,'nav') or contains(@class,'tabs')]//a[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'cliente')]",
			]
			for xp in tab_xpaths:
				els = driver.find_elements(By.XPATH, xp)
				if els:
					for el in els:
						try:
							# asegurar visible / scrollear
							driver.execute_script('arguments[0].scrollIntoView({block:"center",inline:"nearest"});', el)
							# usar click vía JS para disparar handlers ligados por jQuery/bootstrap
							driver.execute_script('arguments[0].click();', el)
							# si hay función tab_seleccionado, llamarla como fallback
							try:
								driver.execute_script("if(typeof tab_seleccionado === 'function'){ tab_seleccionado(1,'cliente'); }")
							except Exception:
								pass
							clicked_tab = True
							# esperar hasta que el enlace tenga la clase 'active' (Bootstrap) o hasta timeout corto
							try:
								WebDriverWait(driver, 3).until(
									lambda d, el=el: 'active' in (d.execute_script('return arguments[0].className;', el) or '')
								)
							except Exception:
								# fallback: intentar llamar a la función JS que activa pestañas si existe
								try:
									driver.execute_script("if(typeof tab_seleccionado === 'function'){ tab_seleccionado(1,'cliente'); }")
									# esperar un poquito tras la invocación
									WebDriverWait(driver, 3).until(lambda d: 'active' in (d.find_element(By.ID, 'cliente').get_attribute('class') or ''))
								except Exception:
									pass
							time.sleep(0.2)
						except Exception:
							# ignorar fallos y seguir probando otras coincidencias
							continue
				if clicked_tab:
					break
			if clicked_tab:
				# esperar por la carga si hubo navegación parcial
				try:
					WebDriverWait(driver, min(timeout, 10)).until(lambda d: d.execute_script("return document.readyState") == "complete")
				except Exception:
					time.sleep(0.5)
		except Exception:
			# ignorar cualquier fallo al intentar clicar la pestaña
			pass

		# ahora guardar page_source
		html = driver.page_source
		# asegurar directorio
		import os as _os
		dirname = _os.path.dirname(out_path)
		if dirname and not _os.path.exists(dirname):
			_os.makedirs(dirname, exist_ok=True)
		with open(out_path, "w", encoding="utf-8") as fh:
			fh.write(html)
		return html[:4000]
	except Exception as e:
		return f"<ERROR: {e}>"




def extract_client_info(driver):
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

	def find_by_label_text(label_text):
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


def dump_table_html(driver, out_path: str = "output/table.html") -> str:
	"""Guarda el outerHTML de la tabla principal en `out_path` y retorna un preview (primeros 4000 chars).
	Crea el directorio `output/` si no existe.
	"""
	table = detect_main_table(driver)
	if table is None:
		return "<NO_TABLE_FOUND>"

	html = table.get_attribute("outerHTML")
	# asegurar directorio
	import os as _os
	dirname = _os.path.dirname(out_path)
	if dirname and not _os.path.exists(dirname):
		_os.makedirs(dirname, exist_ok=True)

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
			print("Table preview saved to output/table.html (first 4000 chars):\n")
			print(table_preview)
		except Exception as e:
			print("Warning: could not dump table html:", e)

		# Intentar clicar el primer 'Ver más' y capturar la página destino
		try:
			detail_preview = click_first_ver_mas_and_capture(driver, timeout=timeout, out_path="output/detail.html")
			print("Detail page saved to output/detail.html (first 4000 chars or status):\n")
			print(detail_preview)
			# Extraer información del cliente desde la página ya cargada y guardar como JSON
			try:
				client = extract_client_info(driver)
				# preparar directorio
				outdir = os.path.dirname("output/clients.json") or "output"
				if outdir and not os.path.exists(outdir):
					os.makedirs(outdir, exist_ok=True)
				clients_path = os.path.join(outdir, "clients.json")
				clients_list = []
				# si existe, cargar y añadir
				if os.path.exists(clients_path):
					try:
						with open(clients_path, "r", encoding="utf-8") as fh:
							clients_list = json.load(fh)
					except Exception:
						clients_list = []
				clients_list.append(client)
				with open(clients_path, "w", encoding="utf-8") as fh:
					json.dump(clients_list, fh, ensure_ascii=False, indent=2)
				print(f"Client data written to {clients_path} (keys: {list(client.keys())})")
			except Exception as e:
				print("Warning: could not extract or write client info:", e)
		except Exception as e:
			print("Warning: could not click first 'Ver más' and capture:", e)

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
	print("HTML preview (first 1000 chars):\n")
	print(out.get("html", "")[:1000])
	return 0


if __name__ == "__main__":
	raise SystemExit(_main())

