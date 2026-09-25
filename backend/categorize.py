"""
AI categorization step.

The LLM does the actual classification (this is the "understanding" part -
matching a free-text description + counterparty to the right accounting
category is a judgment call, which is why it's AI and not a lookup table).

The rule-based suggestion from rules.py is used only as a cross-check:
  - LLM category == rule suggestion  -> confidence = "high"
  - LLM category != rule suggestion, or no rule matched -> "needs_review"

This means no single LLM call is blindly trusted into the P&L - it has to
agree with an independent deterministic signal, or a human sees it.
"""
import json
import os
from typing import List

import pandas as pd
from groq import Groq

from taxonomy import ALL_TOP_LEVEL, SUBCATEGORY_TO_TOP, PNL_CATEGORIES, NON_PNL_CATEGORIES
from rules import rule_categorize

MODEL = "openai/gpt-oss-120b"

_SUBCATS = []
for _cats in (PNL_CATEGORIES, NON_PNL_CATEGORIES):
    for _top, _subs in _cats.items():
        _SUBCATS.extend(_subs)

SYSTEM_PROMPT = f"""You are an accounting classification assistant for a restaurant's bank transactions.

Classify each transaction into exactly one of these subcategories:
{json.dumps(_SUBCATS)}

Rules of thumb:
- Sales deposits (POS, catering, delivery marketplace) are Revenue.
- Inventory purchases (food, beverage) are COGS.
- Wages/salaries/payroll taxes are Payroll.
- Rent, utilities, insurance, subscriptions, marketing, repairs, supplies, professional
  services, delivery commissions, packaging are Operating Expenses.
- Equipment purchases are Capital Expenditure (NOT an operating expense - it's a fixed asset).
- Loan repayments are Financing - Loan Repayment. Loan proceeds are Financing - Loan Proceeds.
- Owner distributions are Owner Equity.
- Sales tax remittance is Tax Remittance (a pass-through liability, not an expense).
- Gift card sales are Deferred Revenue (cash received now, revenue recognized when redeemed),
  NOT immediate Revenue.

Respond ONLY with a JSON array, one object per transaction in the same order given, each:
{{"id": "<transaction id>", "subcategory": "<one of the list above>", "rationale": "<one short sentence>"}}
No prose, no markdown fences, just the JSON array.
"""


def _client() -> Groq:
    return Groq(api_key=os.environ["GROQ_API_KEY"])


def _format_batch(rows: pd.DataFrame) -> str:
    lines = []
    for _, r in rows.iterrows():
        lines.append(f'{{"id": "{r.id}", "description": "{r.description}", '
                      f'"counterparty": "{r.counterparty}", "amount": {r.amount}}}')
    return "[" + ",\n".join(lines) + "]"


def categorize_batch(rows: pd.DataFrame) -> List[dict]:
    """Call the LLM for one batch of transactions. Returns list of
    {id, subcategory, rationale} dicts."""
    client = _client()
    resp = client.chat.completions.create(
        model=MODEL,
        temperature=0,
        reasoning_effort="low",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": _format_batch(rows)},
        ],
    )
    text = resp.choices[0].message.content.strip()
    # strip accidental markdown fences
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text)


def categorize_all(df: pd.DataFrame, batch_size: int = 20) -> pd.DataFrame:
    """Categorize every transaction in df. Mutates and returns df."""
    for start in range(0, len(df), batch_size):
        batch = df.iloc[start:start + batch_size]
        results = categorize_batch(batch)
        by_id = {r["id"]: r for r in results}

        for idx, row in batch.iterrows():
            llm_result = by_id.get(row["id"])
            rule_sub = rule_categorize(row["description"], row["counterparty"])

            if llm_result and llm_result.get("subcategory") in SUBCATEGORY_TO_TOP:
                llm_sub = llm_result["subcategory"]
                rationale = llm_result.get("rationale", "")
            else:
                # LLM gave an unusable/unknown category - fall back to rule if any
                llm_sub = rule_sub
                rationale = "Fell back to rule-based match (LLM output unusable)."

            final_sub = llm_sub or rule_sub
            confidence = "high" if (rule_sub and llm_sub and rule_sub == llm_sub) else "needs_review"

            if final_sub is None:
                final_sub = "Office & Admin Supplies"  # last-resort bucket, always flagged
                confidence = "needs_review"
                rationale = "No rule or LLM match found - defaulted, needs manual review."

            df.at[idx, "subcategory"] = final_sub
            df.at[idx, "top_category"] = SUBCATEGORY_TO_TOP.get(final_sub)
            df.at[idx, "confidence"] = confidence
            df.at[idx, "rule_suggestion"] = rule_sub
            df.at[idx, "llm_suggestion"] = llm_sub
            df.at[idx, "rationale"] = rationale

    return df
