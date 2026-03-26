#!/usr/bin/env python3
"""
Fix COA import:
- Delete duplicate categories/accounts on company 1 that belong to subsidiaries
- Create correct categories and accounts for companies 2, 3, 4
Python 3.9 compatible.
"""
import json
import urllib.request
import urllib.error
import base64
import time

BASE_URL = "http://localhost:8080"
USERNAME = "jrriestra@empirehoa.com"
PASSWORD = "Empire2026"
_creds = base64.b64encode((USERNAME + ":" + PASSWORD).encode()).decode()
AUTH_HEADER = {
    "Authorization": "Basic " + _creds,
    "Content-Type": "application/json",
}


def api_get(path):
    req = urllib.request.Request(BASE_URL + path, headers=AUTH_HEADER)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read()
        try:
            return json.loads(body)
        except Exception:
            return {"error": str(e)}


def api_post(path, payload):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(BASE_URL + path, data=data, headers=AUTH_HEADER, method="POST")
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read()
        try:
            return json.loads(body)
        except Exception:
            return {"error": str(e)}


def api_delete(path):
    req = urllib.request.Request(BASE_URL + path, headers=AUTH_HEADER, method="DELETE")
    try:
        with urllib.request.urlopen(req) as resp:
            content = resp.read()
            if content:
                return json.loads(content)
            return {"ok": True}
    except urllib.error.HTTPError as e:
        body = e.read()
        try:
            return json.loads(body)
        except Exception:
            return {"error": str(e)}


def get_all_categories(company_id):
    resp = api_get("/api/categories?company_id=" + str(company_id) + "&per_page=100")
    return resp.get("data", [])


def get_all_accounts(company_id):
    resp = api_get("/api/accounts?company_id=" + str(company_id) + "&per_page=100")
    return resp.get("data", [])


# -----------------------------------------------------------------------
# Step 1: Delete duplicates from company 1
# IDs 36-59 were incorrectly created under company 1 (intended for 2-4)
# IDs 16-25 accounts were also incorrectly created under company 1
# Keep only the legit company 1 items:
#   Categories 1-35 (seeds + Empire-specific)
#   Accounts 1-15 + 22 (Accumulated Depreciation)
# -----------------------------------------------------------------------

DUPLICATE_CAT_IDS = list(range(36, 60))  # 36-59 inclusive
DUPLICATE_ACCT_IDS = [16, 17, 18, 19, 20, 21, 23, 24, 25]  # subsidiary accounts on coy1
# Also delete the test Riance cat id=60 - we'll recreate it properly
DUPLICATE_CAT_IDS.append(60)


def cleanup_company1():
    print("\n=== Cleanup: Removing cross-company duplicates from Company 1 ===")

    cat_deleted = 0
    cat_failed = 0
    for cat_id in DUPLICATE_CAT_IDS:
        time.sleep(0.4)
        r = api_delete("/api/categories/" + str(cat_id))
        if "error" in r or r.get("status_code", 200) >= 400:
            print("  [SKIP] cat id={}: {}".format(cat_id, r.get("message", r)))
            cat_failed += 1
        else:
            print("  [DEL]  cat id={}".format(cat_id))
            cat_deleted += 1

    acct_deleted = 0
    acct_failed = 0
    for acct_id in DUPLICATE_ACCT_IDS:
        time.sleep(0.4)
        r = api_delete("/api/accounts/" + str(acct_id))
        if "error" in r or r.get("status_code", 200) >= 400:
            print("  [SKIP] acct id={}: {}".format(acct_id, r.get("message", r)))
            acct_failed += 1
        else:
            print("  [DEL]  acct id={}".format(acct_id))
            acct_deleted += 1

    print("  Deleted {} categories ({} failed), {} accounts ({} failed)".format(
        cat_deleted, cat_failed, acct_deleted, acct_failed))


# -----------------------------------------------------------------------
# Step 2: Create correct records for companies 2, 3, 4
# -----------------------------------------------------------------------

BASIC_CATEGORIES = [
    ("Management Fee",       "income",  "#6da252", "4000"),
    ("Services",             "income",  "#7952b3", "4010"),
    ("Billable Expenses",    "income",  "#5bb5a2", "4020"),
    ("General Expenses",     "expense", "#95a5a6", "6000"),
    ("Bank Fees",            "expense", "#7f8c8d", "6010"),
    ("Payroll & Benefits",   "expense", "#c0392b", "6020"),
    ("Advertising",          "expense", "#e55353", "6030"),
    ("Licenses & Permits",   "expense", "#e5a153", "6040"),
]

BASIC_ACCOUNTS = [
    ("Operating Account",    "bank", "1010", 0),
    ("Accounts Receivable",  "bank", "1100", 0),
    ("Equipment",            "bank", "1500", 0),
]

COMPANY_NAMES = {2: "Riance Realty", 3: "WFW", 4: "FixIQ"}


def create_for_company(company_id):
    name = COMPANY_NAMES[company_id]
    print("\n=== Creating COA for {} (company_id={}) ===".format(name, company_id))

    existing_cats = set(c["name"].lower() for c in get_all_categories(company_id))
    existing_accts = set(a["name"].lower() for a in get_all_accounts(company_id))

    cat_created = 0
    cat_errors = []
    for cat_name, cat_type, color, code in BASIC_CATEGORIES:
        if cat_name.lower() in existing_cats:
            print("  [SKIP] category: {}".format(cat_name))
            continue
        time.sleep(1.2)
        r = api_post("/api/categories?company_id=" + str(company_id), {
            "name": cat_name,
            "type": cat_type,
            "color": color,
            "code": code,
            "enabled": True,
        })
        if "data" in r:
            coy = r["data"].get("company_id")
            cid = r["data"].get("id")
            print("  [OK]  category: {} -> id={} coy={}".format(cat_name, cid, coy))
            cat_created += 1
        else:
            print("  [ERR] category {}: {}".format(cat_name, r.get("message", r)))
            cat_errors.append((cat_name, r))

    acct_created = 0
    acct_errors = []
    for acc_name, acc_type, number, opening_bal in BASIC_ACCOUNTS:
        if acc_name.lower() in existing_accts:
            print("  [SKIP] account: {}".format(acc_name))
            continue
        time.sleep(1.2)
        r = api_post("/api/accounts?company_id=" + str(company_id), {
            "name": acc_name,
            "type": acc_type,
            "number": number,
            "currency_code": "USD",
            "opening_balance": opening_bal,
        })
        if "data" in r:
            coy = r["data"].get("company_id")
            aid = r["data"].get("id")
            print("  [OK]  account: {} -> id={} coy={}".format(acc_name, aid, coy))
            acct_created += 1
        else:
            print("  [ERR] account {}: {}".format(acc_name, r.get("message", r)))
            acct_errors.append((acc_name, r))

    print("  {} categories created, {} accounts created, {} errors".format(
        cat_created, acct_created, len(cat_errors) + len(acct_errors)))
    return cat_created, acct_created


def main():
    cleanup_company1()

    time.sleep(3)

    total_cats = 0
    total_accts = 0
    for cid in [2, 3, 4]:
        cc, ac = create_for_company(cid)
        total_cats += cc
        total_accts += ac

    print("\n=== Final verification ===")
    time.sleep(2)
    for cid in [1, 2, 3, 4]:
        cats = get_all_categories(cid)
        accts = get_all_accounts(cid)
        inc = [c["name"] for c in cats if c["type"] == "income"]
        exp = [c["name"] for c in cats if c["type"] == "expense"]
        print("\n  Company {} | {} cats | {} accts".format(cid, len(cats), len(accts)))
        print("    Income:  {}".format(inc))
        print("    Expense: {}".format(exp))
        print("    Accounts:{}".format([a["name"] for a in accts]))

    print("\n=== DONE: {} categories and {} accounts created for companies 2-4 ===".format(
        total_cats, total_accts))


if __name__ == "__main__":
    main()
