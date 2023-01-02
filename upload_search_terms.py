#!/usr/bin/env python
"""Manage search terms for my-shopgoodwill"""

import firebase_admin
from firebase_admin import firestore

with open('search_terms.txt', encoding='UTF-8') as f:
    terms = f.read().splitlines()
    f.close()

app = firebase_admin.initialize_app()
db = firestore.client()

doc_ref = db.collection('config').document('search_terms')
doc_ref.set({
    "terms": terms
})

search_terms = doc_ref.get().to_dict()["terms"]
for term in search_terms:
    print(term)
