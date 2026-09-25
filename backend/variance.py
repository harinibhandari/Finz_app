"""
Variance analysis.

Finding *that* something changed materially is deterministic (a diff over
the P&L table + a threshold). Explaining *why* it changed is where AI adds
value - it reads the actual transactions behind the change and narrates
what happened, with those transactions attached as evidence so the
explanation is traceable, not asserted.
"""
import os
import pandas as pd
from groq import Groq

MATERIALITY_THRESHOLD = 0.10  # 10% change on a P&L line counts as material
MIN_DOLLAR_THRESHOLD = 500.0  # ignore tiny swings even if % is large

LINES = ["Revenue", "COGS", "Payroll", "Operating Expenses", "Operating Profit"]


def detect_variances(pnl: pd.DataFrame) -> list[dict]:
    """Pure computation - compares each month to the prior month for each
    P&L line and flags material changes. No LLM involved."""
    months = list(pnl.index)
    variances = []
    for i in range(1, len(months)):
        prev_m, cur_m = months[i - 1], months[i]
        for line in LINES:
            prev_v = pnl.loc[prev_m, line]
            cur_v = pnl.loc[cur_m, line]
            delta = cur_v - prev_v
            pct = (delta / abs(prev_v)) if prev_v != 0 else (1.0 if delta != 0 else 0.0)
            if abs(delta) >= MIN_DOLLAR_THRESHOLD and abs(pct) >= MATERIALITY_THRESHOLD:
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


def _evidence_transactions(df: pd.DataFrame, line: str, month: str, top_n: int = 8) -> pd.DataFrame:
    """Pull the transactions driving a given P&L line in a given month,
    largest absolute amount first. This is the 'evidence' a variance
    explanation and the chat agent point back to."""
    top_cat_map = {
        "Revenue": "Revenue", "COGS": "COGS", "Payroll": "Payroll",
        "Operating Expenses": "Operating Expenses",
    }
    if line == "Operating Profit":
        sub = df[df["month"] == month].copy()
    else:
        top_cat = top_cat_map.get(line)
        sub = df[(df["month"] == month) & (df["top_category"] == top_cat)].copy()
    sub["abs_amount"] = sub["amount"].abs()
    return sub.sort_values("abs_amount", ascending=False).head(top_n)


def explain_variance(df: pd.DataFrame, variance: dict) -> str:
    """LLM narrates what drove a variance, given the real evidence transactions.
    The LLM only sees data we already computed - it cannot invent numbers here,
    it can only describe what's in the evidence table."""
    ev_cur = _evidence_transactions(df, variance["line"], variance["to_month"])
    ev_prev = _evidence_transactions(df, variance["line"], variance["from_month"])

    def _fmt(ev: pd.DataFrame) -> str:
        return "\n".join(
            f"- {r.date.date()} | {r.description} | {r.counterparty} | ${r.amount:,.2f} | {r.subcategory}"
            for r in ev.itertuples()
        )

    prompt = f"""P&L line "{variance['line']}" changed from ${variance['prev_value']:,.2f} in
{variance['from_month']} to ${variance['cur_value']:,.2f} in {variance['to_month']}
({variance['pct_change']:+.1f}%).

Top transactions in {variance['from_month']}:
{_fmt(ev_prev)}

Top transactions in {variance['to_month']}:
{_fmt(ev_cur)}

In 2-3 sentences, explain what likely drove this change, referencing specific
transactions/categories from the evidence above. Do not invent numbers not
shown above.

IMPORTANT: the lists above show only the largest transactions in each month,
not the complete set - a transaction can be real but simply too small to
appear in this list. Never claim a transaction, vendor, or category "is new,"
"disappeared," "was added," or "has no counterpart" in the other month - you
cannot verify absence from a partial list. Only make comparative claims about
transactions that appear in BOTH lists (their amounts changed) or describe
what's large in one month without asserting it's missing from the other.
Do not restate the totals, focus on the "why"."""

    client = Groq(api_key=os.environ["GROQ_API_KEY"])
    resp = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        temperature=0.2,
        messages=[
            {"role": "system", "content": "You are a financial analyst explaining P&L variances to a restaurant owner. Be concise and specific."},
            {"role": "user", "content": prompt},
        ],
    )
    return resp.choices[0].message.content.strip()

def variance_with_evidence(df: pd.DataFrame, variance: dict) -> dict:
    ev = _evidence_transactions(df, variance["line"], variance["to_month"])
    variance = dict(variance)
    variance["explanation"] = explain_variance(df, variance)
    variance["evidence_transaction_ids"] = ev["id"].tolist()
    return variance
