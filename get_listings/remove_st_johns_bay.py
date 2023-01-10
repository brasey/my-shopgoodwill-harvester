import re
import firebase_admin
from firebase_admin import firestore

app = firebase_admin.initialize_app()
db = firestore.client()

docs = db.collection('listings').stream()

for doc in docs:
    listing = doc.to_dict()
    title = listing['title']
    title = title.lower()
    pattern = r"st\.* *john'*s* *bay"
    if bool(re.search(pattern, title)):
        print(listing)
        db.collection('listings').document(str(listing['item_id'])).delete()
