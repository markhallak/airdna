import json
from time import sleep

import requests
from fake_useragent import UserAgent
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from urllib import parse
from airdna.constants import STATES_ABBREVIATION

def getPersonInfo(driver, wait, addressInfo):
    wait.until(lambda driver: driver.execute_script('return document.readyState') == 'complete')

    print("Page has fully loaded")

    data = {}

    rows = driver.find_elements(By.XPATH, "//*[normalize-space(@class)='row pl-md-1']")

    for row in rows:
            title = row.find_element(By.CLASS_NAME, 'h5').text

            if len(title) == 0:
                data['Name'] = row.find_element(By.CLASS_NAME, 'oh1').text
                data['Date of Birth'] = row.find_element(By.XPATH, './/span').text
                continue


            if title == 'Current Address':
                currentAddress = row.find_element(By.XPATH, "//*[normalize-space(@class)='dt-hd link-to-more olnk']").text

                coordinates = getCoordinatesFromAddress(currentAddress)

                if (coordinates['lat'] != addressInfo['lat'] and coordinates['lon'] != addressInfo['lon']) or coordinates['display_name'] != addressInfo['display_name']:
                    return {'data': None, 'success': False}
            elif title == 'Also Seen As':
                otherNames = row.find_elements(By.XPATH, "//*[normalize-space(@class)='row pl-sm-2']")
                data['Other names'] = []

                for name in otherNames:
                    data['Other names'].append(name.text)
            elif title == 'Phone Numbers':
                try:
                    row.find_element(By.XPATH, './/button').click()
                except Exception as e:
                    print(e)

                data['Phone Numbers'] = []
                numbers = row.find_elements(By.XPATH, './/a')

                for number in numbers:
                    data['Phone Numbers'].append(number)
            elif title == "Email Addresses":
                emails = row.find_elements(By.XPATH, "//*[normalize-space(@class)='row pl-sm-2']")
                data['Email Addresses'] = []

                for email in emails:
                    data['Email Addresses'].append(email.text)

    return {'data': data, 'success': True}



def startTpsScraper(addressInfo):
    addressNameComp = addressInfo['address']
    print(addressNameComp)
    url = f'https://www.truepeoplesearch.com/resultaddress?streetaddress={addressNameComp["house_number"] if 'house_number' in addressNameComp else ''} {addressNameComp["road"]} {addressNameComp["neighbourhood"]}&citystatezip={addressNameComp["city"]} {addressNameComp["state"]} {addressNameComp["postcode"]}'

    encodedUrl = parse.quote(url, safe=':/?=&')

    options = Options()
    ua = UserAgent()
    user_agent = ua.random
    options.add_argument(f'--user-agent={user_agent}')
    options.add_argument('--no-sandbox')
    # options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-logging')
    options.add_argument('--disable-infobars')

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.maximize_window()
    driver.get(encodedUrl)
    wait = WebDriverWait(driver, 60)

    try:
        consentPopup = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'body > div.fc-consent-root')))

        # Execute JavaScript to check and modify the style attribute
        driver.execute_script("""
            var element = arguments[0];
            if (element.style.display !== 'none') {
                element.style.display = 'none';
            }
        """, consentPopup)
    except Exception as e:
        print(e)

    bodyElement = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'body')))

    # Execute JavaScript to remove the style attribute
    driver.execute_script("""
        var element = arguments[0];
        element.removeAttribute('style');
    """, bodyElement)


    searchSummary = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'body > div:nth-child(8) > div > div.content-center > div.row.hidden-left-side-visible.record-count.pl-1')))
    print(searchSummary.text)

    if searchSummary.text.startswith("We could not find any records associated with that address.") or driver.find_element(By.CSS_SELECTOR, '#searchForm-m > div.row.mt-2.text-center > div > span').get_attribute('display') != 'none':
        driver.quit()
        return None

    peopleData = []

    for i in range(6, 33, 2):
        result = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'body > div:nth-child(8) > div > div.content-center > div:nth-child(6)')))
        result.find_element(By.CSS_SELECTOR, 'body > div:nth-child(8) > div > div.content-center > div:nth-child(6) > div:nth-child(1) > div.col-md-4.hidden-mobile.text-center.align-self-center > a').click()

        personDetails = getPersonInfo(driver, wait, addressInfo)

        if personDetails['success']:
            peopleData.append(personDetails['data'])
        else:
            break
        driver.back()

    return peopleData


def getAllPeopleFromAddress(addressInfo):
    finalData = {'data': [], 'success': False}
    addressComp = addressInfo['address']

    if 'house_number' not in addressComp or 'road' not in addressComp:
        return finalData

    addressLine = f"{addressComp['house_number']} {addressComp['road']}"
    print(f"Address Line: {addressLine}")

    county = ""
    countyComp = addressInfo['address']['county'].split(" ")

    for i in range(0, len(countyComp) - 1):
        county += countyComp[i]

    print(f"County: {county}")

    url = "https://devapi.endato.com/PersonSearch"

    payload = {
        "FirstName": "",
        "MiddleName": "",
        "LastName": "",
        "Addresses": [
            {
                "City": county,
                "State": addressInfo['address']['state'],
                "Zip": addressInfo['address']['postcode'],
                "AddressLine1": addressLine,
                "AddressLine2": ""
            }
        ],
        "Dob": "",
        "Age": None,
        "AgeRange": "",
        "Phone": "",
        "Email": "",
        "Includes": ["Addresses", "PhoneNumbers", "EmailAddresses", "DatesOfBirth"],
        "FilterOptions": [],
        "ResultsPerPage": 200
    }

    headers = {
        "accept": "application/json",
        "galaxy-ap-name": "c2167a0b-2c8b-4bff-a978-53e1a3507d88",
        "galaxy-ap-password": "be7202af68514701a75cc480da2ea2e5",
        "galaxy-search-type": "Person",
        "content-type": "application/json"
    }

    print("Sending request to tps")
    response = requests.post(url, json=payload, headers=headers)

    if response.status_code != 200:
        return finalData

    print("Got a request from tps")
    data = response.json()

    if 'counts' in data['counts'] and 'searchResults' in data['counts'] and data['counts']['searchResults'] == 0:
        return finalData

    print(f"{data['counts']['searchResults']} TPS Results")
    for person in data['persons']:
        personData = {'Name': None, 'Other Names': [], "Age": None, 'Date Of Birth': None, 'Email Addresses': [], 'Phone Numbers': []}

        personValid = False

        if 'addresses' in person and len(person['addresses']) > 0:
            for address in person['addresses']:
                if 'addressOrder' not in address or address['addressOrder'] != 1:
                    continue

                if 'houseNumber' in address and address['houseNumber'] == addressComp['house_number'] and 'streetName' in address and address['streetName'].startswith(addressComp['road']) and 'state' in address and address['state'] == STATES_ABBREVIATION[addressComp['state']] and 'zip' in address and address['zip'] == addressComp['postcode']:
                    personValid = True
                    break

        if personValid:
            if 'name' in person and 'rawNames' in person and len(person['name']['rawNames']) > 0:
                personData['Name'] = person['name']['rawNames'][0]

            if 'age' in person:
                personData['Age'] = person['age']

            if 'dob' in person and len(person['dob']) > 0:
                personData['Date Of Birth'] = person['dob']

            if 'akas' in person and len(person['akas']) > 0:
                for aka in person['akas']:
                    for raw_name in aka['rawNames']:
                        personData['Other Names'].append(raw_name)

            for emailAddress in person['emailAddresses']:
                personData['Email Addresses'].append(emailAddress['emailAddress'])

            for phoneNumber in person['phoneNumbers']:
                personData['Phone Numbers'].append(phoneNumber['phoneNumber'])

            finalData['data'].append(personData)

            finalData['success'] = True

    print(finalData)

    return finalData
