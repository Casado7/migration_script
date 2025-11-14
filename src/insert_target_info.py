from __future__ import annotations
import os
import time
from dotenv import load_dotenv
import json

from target_helppers.login import start_and_login
from target_helppers.insert_client import navigate_to_add_client_page, create_client


def insert_target_info(headless: bool = False, timeout: int = 20) -> None:
    """Start a browser, login to the target app, and (placeholder) insert info.

    Currently this function performs only the login and leaves a TODO where
    insertion logic should go.
    """
    load_dotenv()
    url = os.getenv('TARGET_PAGE_LOGIN_URL')
    if not url:
        print('TARGET_PAGE_LOGIN_URL not set in .env')
        return

    username = os.getenv('TARGET_USERNAME')
    password = os.getenv('TARGET_PASSWORD')
    if not username or not password:
        print('TARGET_USERNAME or TARGET_PASSWORD not set in .env')
        return

    driver, success, info = start_and_login(url, username, password, headless=headless, timeout=timeout)

    if driver is None:
        print('Failed to start driver or navigate:', info)
        return

    if not success:
        print('Login may have failed or stayed on page. Current URL/info:', info)
        # keep the browser open briefly so user can inspect
        time.sleep(2)
        try:
            driver.quit()
        except Exception:
            pass
        return

    # At this point, login succeeded
    print('Login successful, current URL:', info)

    # After successful login, load converted clients and create them one-by-one
    clients_path = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "output", "converted_clients.json"))
    clients = []
    try:
        with open(clients_path, "r", encoding="utf-8") as f:
            clients = json.load(f)
    except FileNotFoundError:
        print(f'Converted clients file not found: {clients_path}')
    except Exception as e:
        print('Error loading converted clients:', e)

    if not clients or not isinstance(clients, list):
        print('No clients to process. Exiting.')
    else:
        total = len(clients)
        for idx, client_data in enumerate(clients, start=1):
            name_disp = client_data.get('name') or client_data.get('full_name') or '(no name)'
            print(f'[{idx}/{total}] Creating client: {name_disp}')

            # navigate to add-client page for each client to ensure fresh form
            nav_success, nav_info = navigate_to_add_client_page(driver)
            if not nav_success:
                print('Navigation to add-client page failed:', nav_info)
                # try next client
                continue

            try:
                create_success, create_info = create_client(driver, client_data)
            except Exception as e:
                create_success, create_info = False, f'exception in create_client: {e}'

            if create_success:
                print(f'Client created successfully: {create_info}')
            else:
                print(f'Failed to create client: {create_info}')

            # small pause between creations
            try:
                time.sleep(0.5)
            except Exception:
                pass

    # TODO: Add logic here to insert target info after successful login.

    # keep the browser open briefly so user can inspect
    time.sleep(2)
    try:
        driver.quit()
    except Exception:
        pass


if __name__ == '__main__':
    insert_target_info(headless=False)
