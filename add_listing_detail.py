#!/usr/bin/env python
"""Add number of bids and price to listings"""

from datetime import datetime
import os
from pytz import timezone
import requests
from flask import Flask
import firebase_admin
from firebase_admin import firestore

app = firebase_admin.initialize_app()
db = firestore.client()

listener = Flask(__name__)
endpoint = os.getenv('ENDPOINT')

@listener.route(f"/{endpoint}")
def trigger():
    """Call shopgoodwill API to get item details for each item"""

    # Set end of "today" for query date range
    now = datetime.now()
    year = now.strftime("%Y")
    month = now.strftime("%m")
    day = now.strftime("%d")
    end_time = datetime.strptime(f"{year}-{month}-{day} 23:59:59", "%Y-%m-%d %H:%M:%S")
    eastern = timezone('US/Eastern')
    end_time = eastern.localize(end_time)

    firebase_docs = db.collection('listings').where(
            'end_time', '>=', now
        ).where(
            'end_time', '<=', end_time
        ).order_by(
            'end_time'
        ).stream()

    listings = []

    # Fetch all the listings for today.
    # If we don't do this, the "stream()" above will timeout
    # while we're looking up item details in the next loop.
    for doc in firebase_docs:
        listing = doc.to_dict()
        listings.append(listing)

    for listing in listings:
        # Look up bids and price for each item
        item_id = listing['item_id']
        headers = {'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36'}
        item_lookup = requests.get(f"https://buyerapi.shopgoodwill.com/api/ItemDetail/GetItemDetailModelByItemId/{item_id}", headers=headers)
        item_detail = item_lookup.json()
        listing['price'] = item_detail['currentPrice']
        listing['bids'] = item_detail['numberOfBids']
        db.collection('listings').document(str(item_id)).set(listing, merge=True)
        print(listing)

    return "SUCCESS"

if __name__ == "__main__":
    listener.run(host="127.0.0.1", port=int(os.environ.get("PORT", 8080)), debug=True)
