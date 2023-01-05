#!/usr/bin/env python
"""Retrieve listed items"""

import json
from datetime import datetime
import os
import re
import pytz
from pytz import timezone
import requests
from flask import Flask
import firebase_admin
from firebase_admin import firestore

app = firebase_admin.initialize_app()
db = firestore.client()

listener = Flask(__name__)
endpoint = os.getenv('ENDPOINT')

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
            # Set PST timezone
            pacific = timezone('US/Pacific')
            end_time = pacific.localize(end_time)
            # convert PST to UTC
            utc = pytz.utc
            end_time = end_time.astimezone(utc)
            results.append( {
                "item_id": item["itemId"],
                "title": item["title"],
                "end_time": end_time,
                "image_url": image_url,
                "search_term": search_term,
                "category": category
            } )

    return results

def delete_sold_listings(current_listings):
    """
    Delete sold listings.
    Find the difference between current listings retrieved from shopgoodwill
    and what we have persisted in the database. Delete the difference.
    """
    persisted_listings = []
    db_docs = db.collection('listings').stream()
    for doc in db_docs:
        item_id = str(doc.to_dict()['item_id'])
        persisted_listings.append(item_id)

    persisted_listings_set = set(persisted_listings)
    current_listings_set = set(current_listings)
    sold_items_set = persisted_listings_set.difference(current_listings_set)
    sold_items = list(sold_items_set)
    print(sold_items)
    for item in sold_items:
        db.collection('listings').document(item).delete()

def delete_old_listings():
    """Delete all listing items older than 'now'"""
    eastern = timezone('US/Eastern')
    now = eastern.localize(datetime.now())
    expired_docs = db.collection('listings').where(
        'end_time', '<', now
    ).stream()
    for doc in expired_docs:
        item_id = str(doc.to_dict()['item_id'])
        db.collection('listings').document(item_id).delete()

@listener.route(f"/{endpoint}")
def trigger():
    """
    Hitting the endpoint will trigger a call to get_listings()
    It will also delete all expired listing items.
    """
    delete_old_listings()

    search_terms_doc_ref = db.collection('config').document('search_terms')
    search_terms = search_terms_doc_ref.get().to_dict()["terms"]

    current_listings = []
    for term in search_terms:
        listings = []
        listings.extend(get_listings(term))
        for listing in listings:
            item_id = str(listing['item_id'])
            listings_doc_ref = db.collection('listings').document(item_id)
            listings_doc_ref.set(listing)
            current_listings.append(item_id)
            print(listing)

    delete_sold_listings(current_listings)
    return "SUCCESS"


if __name__ == "__main__":
    listener.run(host="127.0.0.1", port=int(os.environ.get("PORT", 8080)), debug=True)
