import requests
from django.shortcuts import render
from django.http import JsonResponse
from fake_useragent import UserAgent

from airdna.settings import ZIPCODE_KEY, LOCATION_IP_KEY
from airdna.constants import SUBMARKETS_INFO
from airdna.constants import AIRBNB_LISTING_BASE_URL
from airdna.constants import VRBO_LISTING_BASE_URL
from airdna.constants import LOCATION_IP_BASE_URL
from util.airbnb.Scraper import startAirbnbScraper
from util.tps.EndatoAPI import startTpsScraper, getAllPeopleFromAddress
from util.vrbo.Scraper import startVrboScraper


def getMarketIDFromZipCode(zipcode):
    print("Sending a request to zipcodestack")

    params = {
        'codes': f"{zipcode}"
    }
    headers = {
        'apikey': f"{ZIPCODE_KEY}"
    }
    response = requests.get(f"https://api.zipcodestack.com/v1/search", headers=headers, params=params)

    if response.status_code == 200:
        # print(response.text)
        data = response.json()

        if 'results' in data and len(data['results'][zipcode]) != 0:
            results = data['results'][zipcode]

            for result in results:
                for submarket in SUBMARKETS_INFO:
                    if submarket['name'] == str(result['state']).strip() or submarket['name'] == str(result['city']).strip():
                        print(f"Found the submarket id and the parent id is {submarket['market_id']}")
                        return submarket['market_id']

            return None
        else:
            print(f"ERROR: No matching places for the specified zipcode {zipcode}")
            return None
    else:
        print(f"ERROR: Couldn't send a request to zipcodestack.com to get the city/state from the specified zipcode {zipcode}")
        return None


def getAddressFromCoordinates(coordinates):
    params = {
        'key': LOCATION_IP_KEY,
        'lat': coordinates['lat'],
        'lon': coordinates['lng'],
        'format': 'json'
    }

    response = requests.get(f'{LOCATION_IP_BASE_URL}/reverse', params=params)

    print(response.text)

    if response.status_code == 200:
        return response.json()
    else:
        return None


def getFirstTwoSTRListings(marketID):
    ua = UserAgent()
    print("Sending request to airdna")
    headers = {
        "Cookie": "intercom-id-kgkrrbqi=6a204052-fe05-4769-b71e-b0367e74fc97; intercom-device-id-kgkrrbqi=9f19c529-ce57-4367-91a8-044b8a96898e; idr-token=jOtr0nrhWqROhHeteKhuLA82EEma7p_mk_ssT8Lz8Fa-MjURqkgM5g; mmm-cookie=MjE0MjM2Mg|55183e7be4e544f9817265e37e570d36; intercom-session-kgkrrbqi=dnc0UWg0RWl3aEJyeUdLT0Fid3JGSVE2MHBQbG1KR2ZibHljQjkzWlRMRUUrUTFwUmxYSitmdFlMcHVhWkZ2Vy0tSjRvNld4cndXeUxyM09Lb3JsMlNmZz09--0fca2fac3187771dc9945c8da0a0828292f6be79; id-token=eyJhbGciOiJIUzM4NCIsInR5cCI6IkpXVCIsImtpZCI6Ii1xRUFDM1daM2hPNWoxWlZISWRBQ252c01yQmt1YmxHIn0.eyJhdWQiOiI1ZjA0MDQ2NC0wYWVmLTQ4YTEtYTFkMS1kYWE5ZmJmODE0MTUiLCJleHAiOjE3MjIxMDIyMTUsImlhdCI6MTcyMjA5ODYxNSwiaXNzIjoicHJvZC5haXJkbmEuY28iLCJzdWIiOiIwNWYxOTRlMS00OWM5LTQxNTUtODUyZi1lYjI5OWRmZTZkZjgiLCJqdGkiOiI1MjhiYjA3ZC1jODUxLTQ1OTgtOGYyYi1iMjBiNWIzZmY2ZTgiLCJhdXRoZW50aWNhdGlvblR5cGUiOiJSRUZSRVNIX1RPS0VOIiwiZW1haWwiOiJtYXJrLmdiZXNAZ21haWwuY29tIiwiZW1haWxfdmVyaWZpZWQiOnRydWUsInByZWZlcnJlZF91c2VybmFtZSI6Im1hcmsuZ2Jlc0BnbWFpbC5jb20iLCJhcHBsaWNhdGlvbklkIjoiNWYwNDA0NjQtMGFlZi00OGExLWExZDEtZGFhOWZiZjgxNDE1IiwidGlkIjoiMWZiMjA2YTgtMTc3Yi00Njg0LWFmMWYtOGZmZjdjYzE1M2EwIiwicm9sZXMiOlsiVXNlciJdLCJhdXRoX3RpbWUiOjE3MjIwOTg0NTQsInNpZCI6IjA2MzlkOGRjLWJlZmYtNDk5ZC1iZTUzLTNhNzIyZjNhOGZmZiJ9.jU8vlK-1aLuO_0GttOhoktb885zbUEAsISM47G_vFTFKDTe7e6beA1dD52cSZ9SL; mmm-access-jwt-cookie=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJlbmNvZGVkX2FjY2Vzc190b2tlbiI6IjU1MTgzZTdiZTRlNTQ0Zjk4MTcyNjVlMzdlNTcwZDM2IiwiZXhwIjoxNzIyMTg1MDE1LCJwZXJtaXNzaW9ucyI6eyJjaXR5IjpbNTkwNTNdLCJyZWdpb24iOltdLCJjb3VudHJ5IjpbXSwic3RhdGUiOltdLCJ3b3JsZCI6ZmFsc2V9fQ.NZ9RfW_sVXRrlgJROrSeIJa2KsU3mBY_0F82L7G-cMk; mmm-access-jwt-refresh-cookie=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJlbmNvZGVkX2FjY2Vzc190b2tlbiI6IjU1MTgzZTdiZTRlNTQ0Zjk4MTcyNjVlMzdlNTcwZDM2IiwiZXhwIjoxNzI0NjkwNjE1fQ.ace01TXwAIa3XuQmjBE5KGozIy8mVpeKd63Jtn6pwGI; mm-csrf=051c09dc706d55816e62819919440d2fd886708239fb851ef937873e09b3db45",
        "User-Agent": ua.random
    }

    payload = {
        "pagination": {
            "offset": 0,
            "page_size": 2
        },
    }

    response = requests.post(f"https://api.airdna.co/api/explorer/v1/market/{marketID}/listings", headers=headers, json=payload)
    # print(response.text)

    if response.status_code == 200:
        data = response.json()['payload']['listings']

        for property in data:
            if property['airbnb_property_id'] is not None:
                property['airbnbUrl'] = f'{AIRBNB_LISTING_BASE_URL}{property['airbnb_property_id']}'
                airbnbHostInfo = startAirbnbScraper(property['airbnbUrl'])
                print(f'AirbnbHostInfo:\n{airbnbHostInfo}')
                property['airbnbHostName'] = airbnbHostInfo['hostName']
                property['airbnbHostRating'] = airbnbHostInfo['rating']

            if property['vrbo_property_id'] is not None:
                property['vrboUrl'] = f'{VRBO_LISTING_BASE_URL}{property['vrbo_property_id']}'
                vrboHostInfo = startVrboScraper(property['vrboUrl'])
                print(f'VrboHostInfo:\n{vrboHostInfo}')
                property['vrboHostName'] = vrboHostInfo['hostName']
                property['vrboHostRating'] = vrboHostInfo['rating']

            addressInfo = getAddressFromCoordinates(property['location'])
            property['address'] = addressInfo['display_name']

            tpsData = getAllPeopleFromAddress(addressInfo)
            property['owners'] = tpsData
        return data
    else:
        return None


def searchForPropertiesUsingZipCode(request):
    if request.method == 'GET':
        zipcode = request.GET.get('zipcode', '')

        marketID = getMarketIDFromZipCode(zipcode)
        print(f"Market ID: {marketID}")

        if marketID is not None:
            data = getFirstTwoSTRListings(marketID)

            if data is not None:
                return JsonResponse(data, status=200, safe=False)
            else:
                return JsonResponse({"error": "No data found"}, status=404)
        else:
            return JsonResponse({"error": "Invalid zipcode"}, status=400)
    else:
        return JsonResponse({"error": "Invalid request method"}, status=405)

def showSearchPage(request):
    return render(request, 'search.html')
