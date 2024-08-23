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

    print("Starting the airbnb scraper")

    response = requests.get(airbnbUrl, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    script_tag = soup.find('script', {'id': 'data-deferred-state-0'})

    if script_tag:
        print("The airbnb scraper found the data")
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

        print(hostName)
        print(rating)

        return {'hostName': hostName, 'rating': rating}
    else:
        print("Script tag with id 'data-deferred-state-0' not found.")

    return {'hostName': None, 'rating': None}


def startVrboScraper(vrboUrl):
    options = Options()
    ua = UserAgent()
    user_agent = ua.random
    options.add_argument(f'--user-agent={user_agent}')
    # options.add_argument('--no-sandbox')
    options.add_argument('--headless')
    # options.add_argument('--disable-gpu')
    # options.add_argument('--disable-dev-shm-usage')
    # options.add_argument('--disable-extensions')
    # options.add_argument('--disable-logging')
    # options.add_argument('--disable-infobars')

    print("Starting the vrbo scraper")
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
                    print(f"Index {key_or_index} out of range.")
                    return None
            elif isinstance(current_element, dict):
                if isinstance(key_or_index, str) and key_or_index in current_element:
                    current_element = current_element[key_or_index]
                elif key_or_index == 1:
                    # Check for keys starting with "PropertyInfo"
                    current_element = next((v for k, v in current_element.items() if k.startswith("PropertyInfo")),
                                           None)
                    if current_element is None:
                        print("No key starting with 'PropertyInfo' found.")
                        return None
                elif key_or_index == 4:
                    # Check for keys starting with 'propertyContentSectionGroups({"searchCriteria":'
                    current_element = next((v for k, v in current_element.items() if
                                            k.startswith('propertyContentSectionGroups({"searchCriteria":')), None)
                    if current_element is None:
                        print(
                            "No key starting with 'propertyContentSectionGroups({\"searchCriteria\":' found.")
                        return None
                else:
                    print(f"Key {key_or_index} not found.")
                    return None
            else:
                print(f"Key {key_or_index} not found in non-dict element.")
                return None
        return current_element

    print("Searching through 77 vrbo html elements")
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


def getAddressFromCoordinates(coordinates):
    params = {
        'key': 'pk.1cfe7480010580f8326a3a8affdb6d07',
        'lat': coordinates['lat'],
        'lon': coordinates['lng'],
        'format': 'json'
    }

    response = requests.get('https://us1.locationiq.com/v1/reverse', params=params)

    print(response.text)

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
        print("Checking the airdna response now")

        data = response.json()['payload']['listings']
        print(f"{len(data)} properties from AirDna")

        count = 0

        for property in data:
            if count > 200:
                break
            if int(property['revenue_ltm']) >= 100000:
                if property['airbnb_property_id'] is not None:
                    property['airbnbUrl'] = f'https://www.airbnb.com/rooms/{property['airbnb_property_id']}'
                    airbnbHostInfo = startAirbnbScraper(property['airbnbUrl'])
                    print(f'AirbnbHostInfo:\n{airbnbHostInfo}')
                    property['airbnbHostName'] = airbnbHostInfo['hostName']
                    property['airbnbHostRating'] = airbnbHostInfo['rating']

                if property['vrbo_property_id'] is not None:
                    property['vrboUrl'] = f'https://www.vrbo.com/{property['vrbo_property_id']}'
                    vrboHostInfo = startVrboScraper(property['vrboUrl'])

                    if vrboHostInfo['hostName'] is None:
                        vrboHostInfo = startVrboScraper(property['vrboUrl'])

                    print(f'VrboHostInfo:\n{vrboHostInfo}')
                    property['vrboHostName'] = vrboHostInfo['hostName']
                    property['vrboHostRating'] = vrboHostInfo['rating']

                addressInfo = getAddressFromCoordinates(property['location'])
                property['address'] = addressInfo['display_name']

                print("Getting data from tps")
                tpsData = getAllPeopleFromAddress(addressInfo)
                property['owners'] = tpsData
                count += 1

        return data
    else:
        return None

print(getSTRListings("airdna-493"))
print(getSTRListings("airdna-378"))
print(getSTRListings("airdna-442"))





# Sending request to airdna
# Got a response from airdna
# Checking the airdna response now
# 15079 properties from AirDna
# Starting the airbnb scraper
# The airbnb scraper found the data
# Jordan
# 5
# AirbnbHostInfo:
# {'hostName': 'Jordan', 'rating': 5}
# Starting the vrbo scraper
# Searching through 77 vrbo html elements
# VrboHostInfo:
# {'hostName': 'Hosted by The Horse Shoe Farm', 'rating': None}
# {"place_id":"331321356669","licence":"https:\/\/locationiq.com\/attribution","lat":"35.349772","lon":"-82.544817","display_name":"230, Horse Shoe Farm Drive, Hendersonville, Henderson County, North Carolina, 28791, USA","boundingbox":["35.349772","35.349772","-82.544817","-82.544817"],"importance":0.2,"address":{"house_number":"230","road":"Horse Shoe Farm Drive","city":"Hendersonville","county":"Henderson County","state":"North Carolina","postcode":"28791","country":"United States of America","country_code":"us"}}
# Getting data from tps
# Address Line: 230 Horse Shoe Farm Drive
# County: Henderson
# Sending request to tps
# Got a request from tps
# 1 TPS Results
# {'data': [], 'success': False}
# Starting the airbnb scraper
# The airbnb scraper found the data
# Yonder
# 4.82
# AirbnbHostInfo:
# {'hostName': 'Yonder', 'rating': 4.82}
# Starting the vrbo scraper
# Searching through 77 vrbo html elements
# VrboHostInfo:
# {'hostName': 'Hosted by Yonder', 'rating': None}
# {"place_id":"330158090851","licence":"https:\/\/locationiq.com\/attribution","lat":"35.224221","lon":"-83.299093","display_name":"300, Legacy Lane, Franklin, Macon County, North Carolina, 28734, USA","boundingbox":["35.224221","35.224221","-83.299093","-83.299093"],"importance":0.225,"address":{"house_number":"300","road":"Legacy Lane","city":"Franklin","county":"Macon County","state":"North Carolina","postcode":"28734","country":"United States of America","country_code":"us"}}
# Getting data from tps
# Address Line: 300 Legacy Lane
# County: Macon
# Sending request to tps
# Got a request from tps
# 3 TPS Results
# {'data': [], 'success': False}
# Starting the airbnb scraper
# The airbnb scraper found the data
# Edward
# 4.9
# AirbnbHostInfo:
# {'hostName': 'Edward', 'rating': 4.9}
# {"place_id":"333916032073","licence":"https:\/\/locationiq.com\/attribution","lat":"35.512867","lon":"-83.094898","display_name":"476, Rocky Top Road, Maggie Valley, Haywood County, North Carolina, 28751, USA","boundingbox":["35.512867","35.512867","-83.094898","-83.094898"],"importance":0.2,"address":{"house_number":"476","road":"Rocky Top Road","city":"Maggie Valley","county":"Haywood County","state":"North Carolina","postcode":"28751","country":"United States of America","country_code":"us"}}
# Getting data from tps
# Address Line: 476 Rocky Top Road
# County: Haywood
# Sending request to tps
# Got a request from tps
# 4 TPS Results
# {'data': [], 'success': False}
# Starting the airbnb scraper
# The airbnb scraper found the data
# Stonewood
# 4.84
# AirbnbHostInfo:
# {'hostName': 'Stonewood', 'rating': 4.84}
# Starting the vrbo scraper
# Searching through 77 vrbo html elements
# No key starting with 'PropertyInfo' found.
# VrboHostInfo:
# {'hostName': None, 'rating': None}
# {"place_id":"332023891648","licence":"https:\/\/locationiq.com\/attribution","lat":"35.370255","lon":"-83.600264","display_name":"743, Doubletree, Almond, Swain County, North Carolina, 28702, USA","boundingbox":["35.370255","35.370255","-83.600264","-83.600264"],"importance":0.2,"address":{"house_number":"743","road":"Doubletree","city":"Almond","county":"Swain County","state":"North Carolina","postcode":"28702","country":"United States of America","country_code":"us"}}
# Getting data from tps
# Address Line: 743 Doubletree
# County: Swain
# Sending request to tps
# Got a request from tps
# 0 TPS Results
# {'data': [], 'success': False}
# Starting the airbnb scraper
# The airbnb scraper found the data
# Brian
# 4.9
# AirbnbHostInfo:
# {'hostName': 'Brian', 'rating': 4.9}
# Starting the vrbo scraper
# Searching through 77 vrbo html elements
# VrboHostInfo:
# {'hostName': 'Hosted by Brian', 'rating': None}
# {"place_id":"330903300888","licence":"https:\/\/locationiq.com\/attribution","lat":"35.385331","lon":"-83.389864","display_name":"2450, Sam Dills, Whittier, Swain County, North Carolina, 28789, USA","boundingbox":["35.385331","35.385331","-83.389864","-83.389864"],"importance":0.175,"address":{"house_number":"2450","road":"Sam Dills","city":"Whittier","county":"Swain County","state":"North Carolina","postcode":"28789","country":"United States of America","country_code":"us"}}
# Getting data from tps
# Address Line: 2450 Sam Dills
# County: Swain
# Sending request to tps
# Got a request from tps
# 7 TPS Results
# {'data': [], 'success': False}
# Starting the airbnb scraper
# The airbnb scraper found the data
# Greg
# 5
# AirbnbHostInfo:
# {'hostName': 'Greg', 'rating': 5}
# Starting the vrbo scraper
# Traceback (most recent call last):
#   File "C:\Users\markh\PycharmProjects\airdna\NorthCarolina.py", line 247, in <module>
#     print(getSTRListings("airdna-493"))
#           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
#   File "C:\Users\markh\PycharmProjects\airdna\NorthCarolina.py", line 231, in getSTRListings
#     vrboHostInfo = startVrboScraper(property['vrboUrl'])
#                    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
#   File "C:\Users\markh\PycharmProjects\airdna\NorthCarolina.py", line 84, in startVrboScraper
#     driver.get(vrboUrl)
#   File "C:\Users\markh\PycharmProjects\airdna\venv\Lib\site-packages\selenium\webdriver\remote\webdriver.py", line 363, in get
#     self.execute(Command.GET, {"url": url})
#   File "C:\Users\markh\PycharmProjects\airdna\venv\Lib\site-packages\selenium\webdriver\remote\webdriver.py", line 352, in execute
#     response = self.command_executor.execute(driver_command, params)
#                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
#   File "C:\Users\markh\PycharmProjects\airdna\venv\Lib\site-packages\selenium\webdriver\remote\remote_connection.py", line 302, in execute
#     return self._request(command_info[0], url, body=data)
#            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
#   File "C:\Users\markh\PycharmProjects\airdna\venv\Lib\site-packages\selenium\webdriver\remote\remote_connection.py", line 322, in _request
#     response = self._conn.request(method, url, body=body, headers=headers)
#                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
#   File "C:\Users\markh\PycharmProjects\airdna\venv\Lib\site-packages\urllib3\_request_methods.py", line 144, in request
#     return self.request_encode_body(
#            ^^^^^^^^^^^^^^^^^^^^^^^^^
#   File "C:\Users\markh\PycharmProjects\airdna\venv\Lib\site-packages\urllib3\_request_methods.py", line 279, in request_encode_body
#     return self.urlopen(method, url, **extra_kw)
#            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
#   File "C:\Users\markh\PycharmProjects\airdna\venv\Lib\site-packages\urllib3\poolmanager.py", line 443, in urlopen
#     response = conn.urlopen(method, u.request_uri, **kw)
#                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
#   File "C:\Users\markh\PycharmProjects\airdna\venv\Lib\site-packages\urllib3\connectionpool.py", line 789, in urlopen
#     response = self._make_request(
#                ^^^^^^^^^^^^^^^^^^^
#   File "C:\Users\markh\PycharmProjects\airdna\venv\Lib\site-packages\urllib3\connectionpool.py", line 536, in _make_request
#     response = conn.getresponse()
#                ^^^^^^^^^^^^^^^^^^
#   File "C:\Users\markh\PycharmProjects\airdna\venv\Lib\site-packages\urllib3\connection.py", line 464, in getresponse
#     httplib_response = super().getresponse()
#                        ^^^^^^^^^^^^^^^^^^^^^
#   File "C:\Users\markh\AppData\Local\Programs\Python\Python312\Lib\http\client.py", line 1428, in getresponse
#     response.begin()
#   File "C:\Users\markh\AppData\Local\Programs\Python\Python312\Lib\http\client.py", line 331, in begin
#     version, status, reason = self._read_status()
#                               ^^^^^^^^^^^^^^^^^^^
#   File "C:\Users\markh\AppData\Local\Programs\Python\Python312\Lib\http\client.py", line 292, in _read_status
#     line = str(self.fp.readline(_MAXLINE + 1), "iso-8859-1")
#                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
# KeyboardInterrupt
#
# Process finished with exit code -1
