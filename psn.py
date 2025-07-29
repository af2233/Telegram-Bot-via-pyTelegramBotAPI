from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from webdriver_manager.firefox import GeckoDriverManager
from bs4 import BeautifulSoup
import time


def get_psn_status():
    options = Options()
    options.headless = True
    driver = webdriver.Firefox(service=Service(GeckoDriverManager().install()), options=options)

    try:
        driver.get('https://status.playstation.com/ru-RU/')
        time.sleep(5)
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        status_el = soup.select_one('.status-text div')
        return status_el.get_text(strip=True) if status_el else "Статус не найден"
    finally:
        driver.quit()
