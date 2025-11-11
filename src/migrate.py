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

from dotenv import load_dotenv

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait

from selenium.common.exceptions import WebDriverException, TimeoutException


def fetch_source_page(headless: bool = True, timeout: int = 30) -> Dict[str, Any]:
	"""Carga SOURCE_PAGE_URL desde .env y la abre con Selenium.

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
	out = fetch_source_page(headless=True)
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

