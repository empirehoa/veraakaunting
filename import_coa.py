#!/usr/bin/env python3
"""
Import Empire Management Group Chart of Accounts from QBO into VeraKaunting.
Python 3.9 compatible.
"""
import json
import urllib.request
import urllib.error
import base64
import sys

BASE_URL = "http://localhost:8080"
USERNAME = "jrriestra@empirehoa.com"
PASSWORD = "Empire2026"

# Build basic auth header
_creds = base64.b64encode(f"{USERNAME}:{PASSWORD}".encode()).decode()
AUTH_HEADER = {"Authorization": f"Basic {_creds}", "Content-Type": "application/json"}


def api_get(path):
    req = urllib.request.Request(f"{BASE_URL}{path}", headers=AUTH_HEADER)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return json.loads(e.read())


def api_post(path, payload):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(f"{BASE_URL}{path}", data=data, headers=AUTH_HEADER, method="POST")
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return json.loads(e.read())


def get_existing_categories(company_id):
    resp = api_get(f"/api/categories?company_id={company_id}")
    existing = {}
    for c in resp.get("data", []):
        existing[c["name"].lower()] = c["id"]
    return existing


def get_existing_accounts(company_id):
    resp = api_get(f"/api/accounts?company_id={company_id}")
    existing = {}
    for a in resp.get("data", []):
        existing[a["name"].lower()] = a["id"]
    return existing


def create_category(company_id, name, cat_type, color, code=None):
    payload = {
        "company_id": company_id,
        "name": name,
        "type": cat_type,
        "color": color,
        "enabled": True,
    }
    if code:
        payload["code"] = code
    resp = api_post("/api/categories", payload)
    if "data" in resp:
        return True, resp["data"]["id"]
    return False, resp.get("message") or resp.get("errors") or str(resp)


def create_account(company_id, name, acc_type, number, opening_balance=0):
    payload = {
        "company_id": company_id,
        "name": name,
        "type": acc_type,
        "number": number,
        "currency_code": "USD",
        "opening_balance": opening_balance,
    }
    resp = api_post("/api/accounts", payload)
    if "data" in resp:
        return True, resp["data"]["id"]
    return False, resp.get("message") or resp.get("errors") or str(resp)


# -------------------------------------------------------------------------
# COA definitions derived from QBO P&L + Balance Sheet
# -------------------------------------------------------------------------

# Categories: (name, type, color, code)
# type must be one of: income, expense, item, other
EMPIRE_CATEGORIES = [
    # Income
    ("Management Fee",          "income",  "#6da252", "4000"),
    ("Billable Expense Income", "income",  "#5bb5a2", "4010"),
    ("Sales of Product Income", "income",  "#3d8bcd", "4020"),
    ("Services",                "income",  "#7952b3", "4030"),
    # COGS / item
    ("Supplies & Materials - COGS", "item", "#328aef", "5000"),
    # Expenses
    ("Advertising & Marketing", "expense", "#e55353", "6000"),
    ("Listing Fees",            "expense", "#e57b53", "6010"),
    ("Business Licenses",       "expense", "#e5a153", "6020"),
    ("Employee Benefits",       "expense", "#c0392b", "6030"),
    ("Employee Retirement Plans","expense","#d35400", "6040"),
    ("Health Insurance",        "expense", "#e74c3c", "6050"),
    ("Workers Comp Insurance",  "expense", "#c0392b", "6060"),
    ("General Business Expenses","expense","#95a5a6", "6070"),
    ("Bank Fees & Service Charges","expense","#7f8c8d","6080"),
    ("Memberships & Subscriptions","expense","#8e44ad","6090"),
]

# Accounts: (name, type, number, opening_balance)
# type must be one of: bank, revenue, expense, asset, liability, equity, receivable, payable
EMPIRE_ACCOUNTS = [
    # Bank accounts (operating)
    ("Operating Account (4449)",         "bank",  "1010", 233924.54),
    ("Spec Project Account (4457)",       "bank",  "1020", 137885.95),
    # Receivable
    ("Accounts Receivable (A/R)",         "bank",  "1100", 950.0),
    # Other current assets — use bank type as VK doesn't have generic asset
    ("Due From Riance Realty",            "bank",  "1200", 39500.0),
    ("Due From WFW",                      "bank",  "1210", 9000.0),
    ("Loans to Partners",                 "bank",  "1220", 90000.0),
    # Fixed assets
    ("Equipment",                         "bank",  "1500", 968639.58),
    ("Long-term Office Equipment",        "bank",  "1510", 13322.03),
    ("Vehicles - BenzGLS 2026",           "bank",  "1520", 105358.05),
    ("Vehicles - Buick Envista Fleet",    "bank",  "1530", 120104.52),  # sum of 3 Envistas
    ("Accumulated Depreciation",          "bank",  "1599", -170264.0),
]

# -------------------------------------------------------------------------
# Basic COA for subsidiaries (Riance Realty, WFW, FixIQ)
# -------------------------------------------------------------------------
BASIC_CATEGORIES = [
    ("Management Fee",      "income",  "#6da252", "4000"),
    ("Services",            "income",  "#7952b3", "4010"),
    ("Billable Expenses",   "income",  "#5bb5a2", "4020"),
    ("General Expenses",    "expense", "#95a5a6", "6000"),
    ("Bank Fees",           "expense", "#7f8c8d", "6010"),
    ("Payroll & Benefits",  "expense", "#c0392b", "6020"),
    ("Advertising",         "expense", "#e55353", "6030"),
    ("Licenses & Permits",  "expense", "#e5a153", "6040"),
]

BASIC_ACCOUNTS = [
    ("Operating Account",   "bank", "1010", 0),
    ("Accounts Receivable", "bank", "1100", 0),
    ("Equipment",           "bank", "1500", 0),
]

COMPANY_NAMES = {1: "Empire", 2: "Riance Realty", 3: "WFW", 4: "FixIQ"}


def import_company(company_id, categories, accounts):
    name = COMPANY_NAMES.get(company_id, f"Company {company_id}")
    print(f"\n{'='*60}")
    print(f"Importing COA for: {name} (company_id={company_id})")
    print(f"{'='*60}")

    existing_cats = get_existing_categories(company_id)
    existing_accts = get_existing_accounts(company_id)

    cat_created = 0
    cat_skipped = 0
    cat_errors = []

    for cat_name, cat_type, color, code in categories:
        if cat_name.lower() in existing_cats:
            print(f"  [SKIP] Category already exists: {cat_name}")
            cat_skipped += 1
            continue
        ok, result = create_category(company_id, cat_name, cat_type, color, code)
        if ok:
            print(f"  [OK]   Created category: {cat_name} ({cat_type}) → id={result}")
            cat_created += 1
        else:
            print(f"  [ERR]  Category {cat_name}: {result}")
            cat_errors.append((cat_name, result))

    acc_created = 0
    acc_skipped = 0
    acc_errors = []

    for acc_name, acc_type, number, opening_bal in accounts:
        if acc_name.lower() in existing_accts:
            print(f"  [SKIP] Account already exists: {acc_name}")
            acc_skipped += 1
            continue
        ok, result = create_account(company_id, acc_name, acc_type, number, opening_bal)
        if ok:
            print(f"  [OK]   Created account: {acc_name} ({acc_type}) #{number} → id={result}")
            acc_created += 1
        else:
            print(f"  [ERR]  Account {acc_name}: {result}")
            acc_errors.append((acc_name, result))

    print(f"\n  Summary: {cat_created} categories created, {cat_skipped} skipped, {len(cat_errors)} errors")
    print(f"           {acc_created} accounts created,  {acc_skipped} skipped,  {len(acc_errors)} errors")
    return cat_created, acc_created, cat_errors, acc_errors


def main():
    totals = {"cat_created": 0, "acc_created": 0, "errors": []}

    # Company 1: Empire — full QBO-derived COA
    cc, ac, cerr, aerr = import_company(1, EMPIRE_CATEGORIES, EMPIRE_ACCOUNTS)
    totals["cat_created"] += cc
    totals["acc_created"] += ac
    totals["errors"].extend(cerr + aerr)

    # Companies 2-4: basic COA structure
    for cid in [2, 3, 4]:
        cc, ac, cerr, aerr = import_company(cid, BASIC_CATEGORIES, BASIC_ACCOUNTS)
        totals["cat_created"] += cc
        totals["acc_created"] += ac
        totals["errors"].extend(cerr + aerr)

    print(f"\n{'='*60}")
    print(f"GRAND TOTAL: {totals['cat_created']} categories, {totals['acc_created']} accounts created")
    if totals["errors"]:
        print(f"ERRORS ({len(totals['errors'])}):")
        for item, msg in totals["errors"]:
            print(f"  - {item}: {msg}")
    else:
        print("No errors.")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
