import re
import firebase_admin
from firebase_admin import firestore

app = firebase_admin.initialize_app()
db = firestore.client()

docs = db.collection('listings').stream()

for doc in docs:
    listing = doc.to_dict()
    if bool(re.search(' ', listing['image_url'])):
        print(listing)
        listing['image_url'] = listing['image_url'].replace(' ', '')
        listings_doc_ref = db.collection('listings').document(str(listing["item_id"]))
        listings_doc_ref.set(listing, merge=True)
