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
from typing import Dict, Any
import re

from dotenv import load_dotenv

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from selenium.common.exceptions import WebDriverException, TimeoutException
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

		# intentar expandir cada 'Ver más' dentro de la tabla de ventas
		try:
			expand_view_more_in_table(driver, timeout=timeout)
		except Exception:
			# no crítico, continuar
			pass

		title = driver.title
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

