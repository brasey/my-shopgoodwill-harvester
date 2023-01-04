#!/usr/bin/env python
"""Retrieve listed items"""

import json
from datetime import datetime, timedelta
import re
import requests
import firebase_admin
from firebase_admin import firestore

app = firebase_admin.initialize_app()
db = firestore.client()

def get_listings(search_term):
    """Call ItemListing endpoint and return results"""
    url = "https://buyerapi.shopgoodwill.com/api/Search/ItemListing"

    categories = ('clothing', 'jewelry')
    results = []

    for category in categories:
        # Read in the request payload for the category,
        # inserting the search term. Then convert to a dict.
        payload_file = f"{category}_payload.json"
        with open(payload_file, encoding='UTF-8') as file:
            file = file.read()
            file = re.sub('SEARCH_TERM', search_term, file)
            request_body = file

        request_body = json.loads(request_body)

        response_json = requests.post(url, json=request_body)
        response = json.loads(response_json.text)

        for item in response["searchResults"]["items"]:
            # imageURL returns with a mix of forward and backward slashes. Make them all forward.
            image_url = item["imageURL"].replace('\\', '/')
            # sometimes endTime has trailing fractions of a second, e.g. "0.75"
            end_time = re.sub(r"\.\d*$", '', item["endTime"])
            # convert time format with "T" separator
            end_time = datetime.strptime(end_time, "%Y-%m-%dT%H:%M:%S")
            # convert PST to EST
            end_time = end_time + timedelta(hours=3)
            results.append( {
                "item_id": item["itemId"],
                "title": item["title"],
                "end_time": end_time,
                "image_url": image_url,
                "search_term": search_term,
                "category": category
            } )

    return results

search_terms_doc_ref = db.collection('config').document('search_terms')
search_terms = search_terms_doc_ref.get().to_dict()["terms"]

for term in search_terms:
    listings = []
    listings.extend(get_listings(term))
    for listing in listings:
        listings_doc_ref = db.collection('listings').document(str(listing["item_id"]))
        listings_doc_ref.set(listing)
        print(listing)