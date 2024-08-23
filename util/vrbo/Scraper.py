import json
from time import sleep

from fake_useragent import UserAgent
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from airdna.constants import VRBO_LISTING_BASE_URL


def startVrboScraper(vrboID):
    print("Starting vrbo Scraper")

    options = Options()
    ua = UserAgent()
    user_agent = ua.random
    options.add_argument(f'--user-agent={user_agent}')
    options.add_argument('--no-sandbox')
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-logging')
    options.add_argument('--disable-infobars')

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.maximize_window()
    driver.get(f'{VRBO_LISTING_BASE_URL}{vrboID}')
    wait = WebDriverWait(driver, 60)
    currentPos = 0
    counter = 0

    while counter < 10:
        currentPos += 1000
        driver.execute_script(f"window.scrollTo(0, {currentPos});")
        sleep(1)
        counter += 1

    path = [
        "apollo",
        "apolloState",
        1,
        4,
        "aboutThisHost",
        "sections",
        0,
        "bodySubSections",
        0,
        "elementsV2",
        0,
        "elements",
        0,
        "header",
        "text"
    ]

    def get_nested_value_with_patterns(data, path):
        current_element = data
        for key_or_index in path:
            if isinstance(current_element, list) and isinstance(key_or_index, int):
                if 0 <= key_or_index < len(current_element):
                    current_element = current_element[key_or_index]
                else:
                    raise IndexError(f"Index {key_or_index} out of range.")
            elif isinstance(current_element, dict):
                if isinstance(key_or_index, str) and key_or_index in current_element:
                    current_element = current_element[key_or_index]
                elif key_or_index == 1:
                    # Check for keys starting with "PropertyInfo"
                    current_element = next((v for k, v in current_element.items() if k.startswith("PropertyInfo")),
                                           None)
                    if current_element is None:
                        raise KeyError("No key starting with 'PropertyInfo' found.")
                elif key_or_index == 4:
                    # Check for keys starting with 'propertyContentSectionGroups({"searchCriteria":'
                    current_element = next((v for k, v in current_element.items() if
                                            k.startswith('propertyContentSectionGroups({"searchCriteria":')), None)
                    if current_element is None:
                        raise KeyError(
                            "No key starting with 'propertyContentSectionGroups({\"searchCriteria\":' found.")
                else:
                    raise KeyError(f"Key {key_or_index} not found.")
            else:
                raise KeyError(f"Key {key_or_index} not found in non-dict element.")
        return current_element

    for i in range(1, 77):
        script_tag = driver.find_element(By.XPATH, f"/html/body/script[{i}]")
        script_content = script_tag.get_attribute("innerHTML")

        if r'window.__PLUGIN_STATE__ = JSON.parse("{\"context\"' in script_content:
            # Extract the part of the script containing the JSON string
            json_str_start = script_content.find('window.__PLUGIN_STATE__ = JSON.parse("') + len(
                'window.__PLUGIN_STATE__ = JSON.parse("')
            json_str_end = script_content.find('")', json_str_start)
            json_str = script_content[json_str_start:json_str_end]

            # Unescape the JSON string
            json_str = json_str.encode().decode('unicode_escape')

            # Parse the JSON string
            json_data = json.loads(json_str)

            result = get_nested_value_with_patterns(json_data, path)

            driver.quit()

            return {'hostName': result, 'rating': None}

    driver.quit()

    return {'hostName': None, 'rating': None}
