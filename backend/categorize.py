"""
Deterministic transaction categorization.

NO LLM.

Transactions are classified using the accounting rules in rules.py.

If no deterministic rule matches, the transaction is flagged for
manual review instead of guessing a category.
"""

import pandas as pd

from taxonomy import SUBCATEGORY_TO_TOP
from rules import rule_categorize


def categorize_all(df: pd.DataFrame, batch_size: int = 20) -> pd.DataFrame:
    """
    Categorize all transactions using deterministic rules only.

    Rules that match:
        confidence = high

    Rules that do not match:
        confidence = needs_review
        category remains unset

    No category is invented for unmatched transactions.
    """

    df = df.copy()

    rule_matches = []

    for _, row in df.iterrows():

        rule_sub = rule_categorize(
            row["description"],
            row["counterparty"],
        )

        rule_matches.append(rule_sub)

    df["rule_suggestion"] = rule_matches

    for idx, row in df.iterrows():

        rule_sub = row["rule_suggestion"]

        if rule_sub:

            df.at[idx, "subcategory"] = rule_sub
            df.at[idx, "top_category"] = SUBCATEGORY_TO_TOP.get(
                rule_sub
            )
            df.at[idx, "confidence"] = "high"
            df.at[idx, "llm_suggestion"] = None
            df.at[idx, "rationale"] = (
                "Classified using deterministic accounting rule."
            )

        else:

            # IMPORTANT:
            # Do not guess a category.
            df.at[idx, "subcategory"] = None
            df.at[idx, "top_category"] = None
            df.at[idx, "confidence"] = "needs_review"
            df.at[idx, "llm_suggestion"] = None
            df.at[idx, "rationale"] = (
                "No deterministic accounting rule matched. "
                "Manual review required."
            )

    return df