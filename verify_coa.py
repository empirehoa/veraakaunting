#!/usr/bin/env python3
"""Verify COA import results. Python 3.9 compatible."""
import json
import urllib.request
import base64

BASE_URL = "http://localhost:8080"
_creds = base64.b64encode("jrriestra@empirehoa.com:Empire2026".encode()).decode()
H = {"Authorization": "Basic " + _creds}


def api_get(path):
    req = urllib.request.Request(BASE_URL + path, headers=H)
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def check_category_by_id(cat_id):
    try:
        r = api_get("/api/categories/" + str(cat_id))
        c = r.get("data", {})
        if c:
            return "coy={}, id={}, {}, {}".format(c.get("company_id"), c.get("id"), c.get("name"), c.get("type"))
        return r.get("message", "not found")
    except Exception as e:
        return "error: " + str(e)


NAMES = {1: "Empire", 2: "Riance Realty", 3: "WFW", 4: "FixIQ"}

print("=== Categories by company_id filter ===")
for cid in [1, 2, 3, 4]:
    cats = api_get("/api/categories?company_id=" + str(cid))
    items = cats.get("data", [])
    print("\n{} (cid={}): {} categories total".format(NAMES[cid], cid, len(items)))
    for c in items:
        print("  id={} | {} | {} | coy={}".format(c["id"], c["name"], c["type"], c["company_id"]))

print("\n=== Accounts by company_id filter ===")
for cid in [1, 2, 3, 4]:
    accts = api_get("/api/accounts?company_id=" + str(cid))
    items = accts.get("data", [])
    print("\n{} (cid={}): {} accounts total".format(NAMES[cid], cid, len(items)))
    for a in items:
        print("  id={} | {} | {} | #{}".format(a["id"], a["name"], a["type"], a.get("number", "?")))

print("\n=== Spot-check individual category IDs 36-59 ===")
for cat_id in range(36, 60):
    print("  id={}: {}".format(cat_id, check_category_by_id(cat_id)))
