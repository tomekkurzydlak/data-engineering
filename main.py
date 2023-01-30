#! /usr/bin/env python3

import pandas as pd
import json
import datetime
import apikeys
import requests as rq

# +++++ TWITTER API ++++#
API_KEY = apikeys.TWITTER_APIKEY
API_SECRET = apikeys.TWITTER_API_SECRET
BEARER = apikeys.TWITTER_BEARER_TOKEN

# +++++ TELEGRAM API ++++#
TELEGRAM_TOKEN = apikeys.TELEGRAM_TOKEN
TELEGRAM_ENDPOINT = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
CHAT_ID = apikeys.TELEGRAM_CHAT_ID

# +++++ AWS ++++++#
MY_BUCKET = apikeys.MY_BUCKET

headers = {
    "Authorization": f"Bearer {BEARER}"
}
before = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=300)
today = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=20)
to_date = today.isoformat()
from_date = before.isoformat()

endpoint_v2 = "https://api.twitter.com/2"
endpoint_search = "/tweets/search/recent"
search_query = {"query": "from:markets BTC "
                         "OR from:markets bitcoin"
                         "OR from:markets inflation OR from:markets interest rates"
                         "OR from:markets jobs OR from:markets fed OR from:markets cryptocurrency"
                         "OR from:FT btc OR from:FT bitcoin",
                "start_time": f"{from_date}", "end_time": f"{to_date}"}


def get_response(endpoint, query):
    response = rq.get(f"{endpoint_v2}{endpoint}", headers=headers, params=query)
    if response.status_code == 200:
        data = response.json()
        return data
    else:
        print(f"Error {response.status_code}: {response.text}")
        return response.json()


def run_twitter_etl():
    tweets = get_response(endpoint_search, search_query)
    arr = []
    if tweets:
        for any_tweet in tweets['data']:
            tweet = {
                'text': any_tweet['text']
            }
            arr.append(tweet)
        df = pd.DataFrame(arr)
        df.to_csv(f"{MY_BUCKET}/financial.csv")