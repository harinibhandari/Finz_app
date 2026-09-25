"""
Chart of accounts for NYC Restaurant Co.

Two-tier taxonomy:
  - top-level bucket -> feeds the P&L directly
  - "NON_PNL" bucket  -> real cash movement, but not a P&L revenue/expense line
                         (capex, financing, equity, tax remittance, deferred revenue)

Keeping non-P&L items in their own bucket (rather than quietly excluding them)
is what satisfies "distinguish transactions that belong in the P&L from
transactions that may require different accounting treatment."
"""

PNL_CATEGORIES = {
    "Revenue": [
        "Food Sales",
        "Beverage Sales",
        "Catering Revenue",
        "Delivery Marketplace Revenue",
        "Refunds & Discounts",  # contra-revenue, negative
    ],
    "COGS": [
        "Food Inventory",
        "Beverage Inventory",
    ],
    "Payroll": [
        "Salaries",
        "Hourly Wages",
        "Payroll Taxes & Benefits",
    ],
    "Operating Expenses": [
        "Rent",
        "Utilities",
        "Insurance",
        "Software & Subscriptions",
        "Marketing",
        "Repairs & Maintenance",
        "Cleaning & Linen",
        "Office & Admin Supplies",
        "Professional Services",
        "Delivery Platform Commission",
        "Packaging & Disposables",
    ],
}

NON_PNL_CATEGORIES = {
    "Non-P&L": [
        "Capital Expenditure",       # equipment purchases - depreciated, not expensed at once
        "Financing - Loan Proceeds",
        "Financing - Loan Repayment",
        "Owner Equity",              # distributions to owner
        "Tax Remittance",            # sales tax collected & remitted - pass-through liability
        "Deferred Revenue",          # gift cards - cash in now, revenue recognized later
    ]
}

ALL_TOP_LEVEL = list(PNL_CATEGORIES.keys()) + list(NON_PNL_CATEGORIES.keys())

SUBCATEGORY_TO_TOP = {}
for top, subs in {**PNL_CATEGORIES, **NON_PNL_CATEGORIES}.items():
    for s in subs:
        SUBCATEGORY_TO_TOP[s] = top

PNL_TOP_LEVELS = set(PNL_CATEGORIES.keys())


def is_pnl(top_level: str) -> bool:
    return top_level in PNL_TOP_LEVELS
