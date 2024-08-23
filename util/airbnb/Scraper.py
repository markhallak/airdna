import json

import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from airdna.constants import AIRBNB_LISTING_BASE_URL


def startAirbnbScraper(airbnbUrl):
    print("Starting Airbnb Scraper")
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

    print(f'{airbnbUrl}')
    response = requests.get(f'{airbnbUrl}', headers=headers)
    print(response.text)
    soup = BeautifulSoup(response.text, 'html.parser')
    script_tag = soup.find('script', {'id': 'data-deferred-state-0'})

    if script_tag:
        json_data = script_tag.string

        jsonData = json.loads(json_data)

        jsonData = jsonData['niobeMinimalClientData'][0][1]['data']['presentation']['stayProductDetailPage']['sections'][
            'sections']

        for section in jsonData:
            if section['sectionComponentType'] == 'MEET_YOUR_HOST':
                data = section['section']['cardData']
                print(f"HOST INFO:\n{data}")

                hostData = {}

                if 'name' in data:
                    hostData['hostName'] = data['name']

                if 'ratingAverage' in data:
                    hostData['rating'] = data['ratingAverage']

                if 'ratingCount' in data:
                    hostData['numberOfReviews'] = data['ratingCount']

                stats = data['stats']

                for stat in stats:
                    if 'label' in stat and stat['label'] == 'Years hosting':
                        if 'value' in stat:
                            hostData['yearsHosting'] = stat['value']
                        break

                print(hostData)

                return hostData
    else:
        print("Script tag with id 'data-deferred-state-0' not found.")

    return None
