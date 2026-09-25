"""
Deterministic rule-based categorizer.

This is intentionally dumb and literal: keyword/counterparty match -> category.
It exists for one reason: to cross-check the LLM's categorization. When the
rule and the LLM agree, we trust the category (high confidence). When they
disagree, or no rule matches, the transaction is flagged for human review.

This is the deterministic half of the "how are incorrect answers prevented"
story - categorization isn't trusted on a single LLM call alone.
"""
import re

# (regex on description, optional counterparty match) -> subcategory
RULES = [
    (r"^rent$", None, "Rent"),
    (r"food inventory purchase", None, "Food Inventory"),
    (r"large catering event food purchase", None, "Food Inventory"),
    (r"beverage inventory purchase", None, "Beverage Inventory"),
    (r"pos/software subscription", None, "Software & Subscriptions"),
    (r"insurance premium", None, "Insurance"),
    (r"accounting/bookkeeping", None, "Professional Services"),
    (r"annual license renewal", None, "Professional Services"),
    (r"pos batch deposit - food sales", None, "Food Sales"),
    (r"pos batch deposit - beverage sales", None, "Beverage Sales"),
    (r"catering invoice payment", None, "Catering Revenue"),
    (r"delivery marketplace payout", None, "Delivery Marketplace Revenue"),
    (r"delivery platform commission", None, "Delivery Platform Commission"),
    (r"cleaning and linen service", None, "Cleaning & Linen"),
    (r"refunds and discounts", None, "Refunds & Discounts"),
    (r"manager salary payroll", None, "Salaries"),
    (r"payroll - hourly", None, "Hourly Wages"),
    (r"payroll taxes and benefits", None, "Payroll Taxes & Benefits"),
    (r"equipment purchase", None, "Capital Expenditure"),
    (r"loan principal repayment", None, "Financing - Loan Repayment"),
    (r"owner distribution", None, "Owner Equity"),
    (r"sales tax remittance", None, "Tax Remittance"),
    (r"gift card sales deposit", None, "Deferred Revenue"),
    (r"utilities", None, "Utilities"),
    (r"internet and phone", None, "Utilities"),
    (r"marketing", None, "Marketing"),
    (r"repairs and maintenance", None, "Repairs & Maintenance"),
    (r"office/admin supplies", None, "Office & Admin Supplies"),
    (r"to-go packaging and disposables", None, "Packaging & Disposables"),
]

_COMPILED = [(re.compile(pat, re.IGNORECASE), cp, sub) for pat, cp, sub in RULES]


def rule_categorize(description: str, counterparty: str) -> str | None:
    """Return a subcategory name if a rule matches, else None."""
    for pattern, cp_match, sub in _COMPILED:
        if pattern.search(description or ""):
            if cp_match is None or cp_match.lower() == (counterparty or "").lower():
                return sub
    return None
