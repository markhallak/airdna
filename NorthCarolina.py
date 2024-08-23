import csv
import json
from time import sleep
import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from util.tps.EndatoAPI import getAllPeopleFromAddress


# Function to append data to CSV
def append_to_csv(file_name, fieldnames, property_data):
    file_exists = False
    try:
        with open(file_name, 'r') as f:
            file_exists = True
    except FileNotFoundError:
        pass

    with open(file_name, mode='a', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)

        # Write headers only if the file doesn't exist
        if not file_exists:
            writer.writeheader()

        # Write the property data
        writer.writerow(property_data)


def startAirbnbScraper(airbnbUrl):
    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "en",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": UserAgent().random
    }

    response = requests.get(airbnbUrl, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    script_tag = soup.find('script', {'id': 'data-deferred-state-0'})

    if script_tag:
        json_data = script_tag.string
        jsonData = json.loads(json_data)
        jsonData = \
        jsonData['niobeMinimalClientData'][0][1]['data']['presentation']['stayProductDetailPage']['sections'][
            'sections']

        hostName = ''
        rating = ''

        for section in jsonData:
            if section['sectionComponentType'] == 'MEET_YOUR_HOST':
                data = section['section']['cardData']
                hostName = data['name']
                rating = data['ratingAverage']

        return {'hostName': hostName, 'rating': rating}

    return {'hostName': None, 'rating': None}


def startVrboScraper(vrboUrl):
    options = Options()
    ua = UserAgent()
    user_agent = ua.random
    options.add_argument(f'--user-agent={user_agent}')
    options.add_argument('--headless')

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.maximize_window()
    driver.get(vrboUrl)
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
                    return None
            elif isinstance(current_element, dict):
                if isinstance(key_or_index, str) and key_or_index in current_element:
                    current_element = current_element[key_or_index]
                elif key_or_index == 1:
                    current_element = next((v for k, v in current_element.items() if k.startswith("PropertyInfo")),
                                           None)
                    if current_element is None:
                        return None
                elif key_or_index == 4:
                    current_element = next((v for k, v in current_element.items() if
                                            k.startswith('propertyContentSectionGroups({"searchCriteria":')), None)
                    if current_element is None:
                        return None
                else:
                    return None
            else:
                return None
        return current_element

    for i in range(1, 77):
        script_tag = driver.find_element(By.XPATH, f"/html/body/script[{i}]")
        script_content = script_tag.get_attribute("innerHTML")

        if r'window.__PLUGIN_STATE__ = JSON.parse("{\"context\"' in script_content:
            json_str_start = script_content.find('window.__PLUGIN_STATE__ = JSON.parse("') + len(
                'window.__PLUGIN_STATE__ = JSON.parse("')
            json_str_end = script_content.find('")', json_str_start)
            json_str = script_content[json_str_start:json_str_end]
            json_str = json_str.encode().decode('unicode_escape')
            json_data = json.loads(json_str)
            result = get_nested_value_with_patterns(json_data, path)
            driver.quit()
            return {'hostName': result, 'rating': None}

    driver.quit()
    return {'hostName': None, 'rating': None}


def getAddressFromCoordinates(coordinates):
    params = {
        'key': 'pk.1cfe7480010580f8326a3a8affdb6d07',
        'lat': coordinates['lat'],
        'lon': coordinates['lng'],
        'format': 'json'
    }

    response = requests.get('https://us1.locationiq.com/v1/reverse', params=params)
    if response.status_code == 200:
        return response.json()
    else:
        return None


def getSTRListings(marketID):
    ua = UserAgent()
    headers = {
        "Cookie": "intercom-id-kgkrrbqi=6a204052-fe05-4769-b71e-b0367e74fc97; intercom-device-id-kgkrrbqi=9f19c529-ce57-4367-91a8-044b8a96898e; idr-token=jOtr0nrhWqROhHeteKhuLA82EEma7p_mk_ssT8Lz8Fa-MjURqkgM5g; mmm-cookie=MjE0MjM2Mg|55183e7be4e544f9817265e37e570d36; intercom-session-kgkrrbqi=dnc0UWg0RWl3aEJyeUdLT0Fid3JGSVE2MHBQbG1KR2ZibHljQjkzWlRMRUUrUTFwUmxYSitmdFlMcHVhWkZ2Vy0tSjRvNld4cndXeUxyM09Lb3JsMlNmZz09--0fca2fac3187771dc9945c8da0a0828292f6be79; id-token=eyJhbGciOiJIUzM4NCIsInR5cCI6IkpXVCIsImtpZCI6Ii1xRUFDM1daM2hPNWoxWlZISWRBQ252c01yQmt1YmxHIn0.eyJhdWQiOiI1ZjA0MDQ2NC0wYWVmLTQ4YTEtYTFkMS1kYWE5ZmJmODE0MTUiLCJleHAiOjE3MjIxMDIyMTUsImlhdCI6MTcyMjA5ODYxNSwiaXNzIjoicHJvZC5haXJkbmEuY28iLCJzdWIiOiIwNWYxOTRlMS00OWM5LTQxNTUtODUyZi1lYjI5OWRmZTZkZjgiLCJqdGkiOiI1MjhiYjA3ZC1jODUxLTQ1OTgtOGYyYi1iMjBiNWIzZmY2ZTgiLCJhdXRoZW50aWNhdGlvblR5cGUiOiJSRUZSRVNIX1RPS0VOIiwiZW1haWwiOiJtYXJrLmdiZXNAZ21haWwuY29tIiwiZW1haWxfdmVyaWZpZWQiOnRydWUsInByZWZlcnJlZF91c2VybmFtZSI6Im1hcmsuZ2Jlc0BnbWFpbC5jb20iLCJhcHBsaWNhdGlvbklkIjoiNWYwNDA0NjQtMGFlZi00OGExLWExZDEtZGFhOWZiZjgxNDE1IiwidGlkIjoiMWZiMjA2YTgtMTc3Yi00Njg0LWFmMWYtOGZmZjdjYzE1M2EwIiwicm9sZXMiOlsiVXNlciJdLCJhdXRoX3RpbWUiOjE3MjIwOTg0NTQsInNpZCI6IjA2MzlkOGRjLWJlZmYtNDk5ZC1iZTUzLTNhNzIyZjNhOGZmZiJ9.jU8vlK-1aLuO_0GttOhoktb885zbUEAsISM47G_vFTFKDTe7e6beA1dD52cSZ9SL; mmm-access-jwt-cookie=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJlbmNvZGVkX2FjY2Vzc190b2tlbiI6IjU1MTgzZTdiZTRlNTQ0Zjk4MTcyNjVlMzdlNTcwZDM2IiwiZXhwIjoxNzIyMTg1MDE1LCJwZXJtaXNzaW9ucyI6eyJjaXR5IjpbNTkwNTNdLCJyZWdpb24iOltdLCJjb3VudHJ5IjpbXSwic3RhdGUiOltdLCJ3b3JsZCI6ZmFsc2V9fQ.NZ9RfW_sVXRrlgJROrSeIJa2KsU3mBY_0F82L7G-cMk; mmm-access-jwt-refresh-cookie=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJlbmNvZGVkX2FjY2Vzc190b2tlbiI6IjU1MTgzZTdiZTRlNTQ0Zjk4MTcyNjVlMzdlNTcwZDM2IiwiZXhwIjoxNzI0NjkwNjE1fQ.ace01TXwAIa3XuQmjBE5KGozIy8mVpeKd63Jtn6pwGI; mm-csrf=051c09dc706d55816e62819919440d2fd886708239fb851ef937873e09b3db45",
        "User-Agent": ua.random
    }

    payload = {
        "pagination": {
            "offset": 0,
            "page_size": 10000000
        },
    }

    print("Sending request to airdna")
    response = requests.post(f"https://api.airdna.co/api/explorer/v1/market/{marketID}/listings", headers=headers,
                             json=payload)
    print("Got a response from airdna")

    if response.status_code == 200:
        data = response.json()['payload']['listings']
        print(f"{len(data)} properties from AirDna")

        count = 0
        csv_file = "properties.csv"

        for property in data:
            if count > 200:
                break
            if int(property['revenue_ltm']) >= 100000:
                if property['airbnb_property_id'] is not None:
                    property['airbnbUrl'] = f'https://www.airbnb.com/rooms/{property["airbnb_property_id"]}'
                    airbnbHostInfo = startAirbnbScraper(property['airbnbUrl'])
                    property['airbnbHostName'] = airbnbHostInfo['hostName']
                    property['airbnbHostRating'] = airbnbHostInfo['rating']

                if property['vrbo_property_id'] is not None:
                    property['vrboUrl'] = f'https://www.vrbo.com/{property["vrbo_property_id"]}'
                    vrboHostInfo = startVrboScraper(property['vrboUrl'])

                    if vrboHostInfo['hostName'] is None:
                        vrboHostInfo = startVrboScraper(property['vrboUrl'])

                    property['vrboHostName'] = vrboHostInfo['hostName']
                    property['vrboHostRating'] = vrboHostInfo['rating']

                addressInfo = getAddressFromCoordinates(property['location'])
                property['address'] = addressInfo['display_name']

                print("Getting data from tps")
                tpsData = getAllPeopleFromAddress(addressInfo)
                property['owners'] = tpsData

                # Write to CSV after processing each property
                append_to_csv(csv_file, property.keys(), property)
                count += 1

            print(property)
        return data
    else:
        return None


getSTRListings("airdna-442")
getSTRListings("airdna-493")
getSTRListings("airdna-378")
