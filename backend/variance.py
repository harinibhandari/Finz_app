"""
Deterministic variance analysis.

NO LLM.

Variance detection is based on P&L arithmetic.
Variance explanations are generated from actual transaction evidence.
"""

import pandas as pd


MATERIALITY_THRESHOLD = 0.10
MIN_DOLLAR_THRESHOLD = 500.0

LINES = [
    "Revenue",
    "COGS",
    "Payroll",
    "Operating Expenses",
    "Operating Profit",
]


def detect_variances(pnl: pd.DataFrame) -> list[dict]:

    months = list(pnl.index)

    variances = []

    for i in range(1, len(months)):

        prev_m = months[i - 1]
        cur_m = months[i]

        for line in LINES:

            prev_v = float(pnl.loc[prev_m, line])
            cur_v = float(pnl.loc[cur_m, line])

            delta = cur_v - prev_v

            pct = (
                delta / abs(prev_v)
                if prev_v != 0
                else (1.0 if delta != 0 else 0.0)
            )

            if (
                abs(delta) >= MIN_DOLLAR_THRESHOLD
                and abs(pct) >= MATERIALITY_THRESHOLD
            ):

                variances.append({
                    "line": line,
                    "from_month": prev_m,
                    "to_month": cur_m,
                    "prev_value": round(prev_v, 2),
                    "cur_value": round(cur_v, 2),
                    "delta": round(delta, 2),
                    "pct_change": round(pct * 100, 1),
                })

    return variances


def _evidence_transactions(
    df: pd.DataFrame,
    line: str,
    month: str,
    top_n: int = 8,
) -> pd.DataFrame:

    top_cat_map = {
        "Revenue": "Revenue",
        "COGS": "COGS",
        "Payroll": "Payroll",
        "Operating Expenses": "Operating Expenses",
    }

    if line == "Operating Profit":

        sub = df[df["month"] == month].copy()

    else:

        top_cat = top_cat_map.get(line)

        sub = df[
            (df["month"] == month)
            & (df["top_category"] == top_cat)
        ].copy()

    if sub.empty:
        return sub

    sub["abs_amount"] = sub["amount"].abs()

    return (
        sub
        .sort_values("abs_amount", ascending=False)
        .head(top_n)
    )


def _format_transaction(row):

    date = row["date"]

    if hasattr(date, "date"):
        date = date.date()

    return (
        f"{date} — "
        f"{row['description']} — "
        f"{row['counterparty']} — "
        f"${row['amount']:,.2f} — "
        f"{row['subcategory'] or 'Uncategorized'}"
    )


def _explain_line(
    df: pd.DataFrame,
    line: str,
    from_month: str,
    to_month: str,
):
    """
    Generate a deterministic explanation based only on transaction evidence.
    """

    current = _evidence_transactions(
        df,
        line,
        to_month,
    )

    previous = _evidence_transactions(
        df,
        line,
        from_month,
    )

    lines = []

    if current.empty and previous.empty:

        return (
            "No transaction-level evidence is available for this line."
        ), []

    lines.append(
        f"Top {line} transaction evidence for {to_month}:"
    )

    current_ids = []

    for _, row in current.head(3).iterrows():

        lines.append(
            f"- {_format_transaction(row)}"
        )

        current_ids.append(row["id"])

    if previous.empty:

        lines.append(
            f"No transaction evidence is available for {from_month}."
        )

    else:

        lines.append(
            f"Top {line} transaction evidence for {from_month}:"
        )

        for _, row in previous.head(3).iterrows():

            lines.append(
                f"- {_format_transaction(row)}"
            )

    return "\n".join(lines), current_ids


def variance_with_evidence(
    df: pd.DataFrame,
    variance: dict,
) -> dict:

    result = dict(variance)

    explanation, evidence_ids = _explain_line(
        df,
        variance["line"],
        variance["from_month"],
        variance["to_month"],
    )

    result["explanation"] = explanation
    result["evidence_transaction_ids"] = evidence_ids

    return result