import requests
import logging
from airdna.constants import STATES_ABBREVIATION

# Configure logging
logging.basicConfig(filename='scraper.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

def getAllPeopleFromAddress(addressInfo):
    finalData = {'data': [], 'success': False}
    addressComp = addressInfo['address']

    if 'house_number' not in addressComp or 'road' not in addressComp:
        logging.warning("Incomplete address info, cannot perform search")
        return finalData

    addressLine = f"{addressComp['house_number']} {addressComp['road']}"
    logging.info(f"Address Line: {addressLine}")

    county = ""
    countyComp = addressInfo['address']['county'].split(" ")

    for i in range(0, len(countyComp) - 1):
        county += countyComp[i]

    logging.info(f"County: {county}")

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

    logging.info("Sending request to TPS")
    response = requests.post(url, json=payload, headers=headers)

    if response.status_code != 200:
        logging.error(f"TPS request failed with status code {response.status_code}")
        return finalData

    logging.info("Got response from TPS")
    data = response.json()

    if 'counts' in data['counts'] and 'searchResults' in data['counts'] and data['counts']['searchResults'] == 0:
        logging.warning("No results from TPS")
        return finalData

    logging.info(f"{data['counts']['searchResults']} TPS Results")
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

    logging.info(finalData)

    return finalData
