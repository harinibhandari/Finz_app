
import re
import pandas as pd

from pnl import monthly_pnl, non_pnl_summary


MONTH_NAMES = {
    "january": "01",
    "february": "02",
    "march": "03",
    "april": "04",
    "may": "05",
    "june": "06",
    "july": "07",
    "august": "08",
    "september": "09",
    "october": "10",
    "november": "11",
    "december": "12",
}


def fmt_money(value):
    return f"${float(value):,.2f}"


def find_month(question: str, available_months: list[str]):
    """
    Find a month from:
      March
      March 2026
      2026-03
    """

    q = question.lower()

    # YYYY-MM
    match = re.search(r"\b(20\d{2})[-/](0[1-9]|1[0-2])\b", q)

    if match:
        month = f"{match.group(1)}-{match.group(2)}"

        if month in available_months:
            return month

    # Month name
    for name, number in MONTH_NAMES.items():

        if name not in q:
            continue

        year_match = re.search(r"\b(20\d{2})\b", q)

        if year_match:
            year = year_match.group(1)
        else:
            years = sorted(set(m[:4] for m in available_months))

            if len(years) == 1:
                year = years[0]
            else:
                return None

        month = f"{year}-{number}"

        if month in available_months:
            return month

    return None


def find_months(question: str, available_months: list[str]):
    """
    Find up to two months from a question.
    """

    found = []

    # YYYY-MM
    matches = re.findall(
        r"\b(20\d{2})[-/](0[1-9]|1[0-2])\b",
        question
    )

    for year, month in matches:
        value = f"{year}-{month}"

        if value in available_months and value not in found:
            found.append(value)

    # Month names
    q = question.lower()

    for name, number in MONTH_NAMES.items():

        if name not in q:
            continue

        year_match = re.search(rf"{name}\s+(20\d{{2}})", q)

        if year_match:
            year = year_match.group(1)
        else:
            years = sorted(set(m[:4] for m in available_months))

            if len(years) != 1:
                continue

            year = years[0]

        value = f"{year}-{number}"

        if value in available_months and value not in found:
            found.append(value)

    return found[:2]


def detect_intent(question: str):
    q = question.lower()

    if any(x in q for x in [
        "variance",
        "variances",
        "compare",
        "compared",
        "difference",
        "change",
        "changed",
        "increase",
        "increased",
        "decrease",
        "decreased",
        "between",
    ]):
        return "variance"

    if any(x in q for x in [
        "p&l",
        "pnl",
        "profit and loss",
        "profit & loss",
        "gross profit",
        "operating profit",
    ]):
        return "pnl"

    if any(x in q for x in [
        "transaction",
        "transactions",
        "sales",
        "expenses",
        "payroll",
        "cogs",
    ]):
        return "transactions"

    if any(x in q for x in [
        "non-p&l",
        "non pnl",
        "non-pnl",
        "owner distribution",
        "loan",
        "capital expenditure",
        "capex",
        "tax remittance",
        "gift card",
    ]):
        return "non_pnl"

    if any(x in q for x in [
        "review",
        "flagged",
        "needs review",
        "low confidence",
    ]):
        return "review"

    return "unknown"


def answer_pnl(df: pd.DataFrame, question: str):

    p = monthly_pnl(df)
    months = list(p.index)

    month = find_month(question, months)

    if month is None:

        if len(months) == 1:
            month = months[0]
        else:
            return {
                "answer": (
                    "Please specify a month, for example: "
                    "\"What is the P&L of March 2026?\""
                ),
                "evidence": [],
                "source": "monthly_pnl",
            }

    row = p.loc[month]

    answer = (
        f"### P&L — {month}\n\n"
        f"| Line | Amount |\n"
        f"|---|---:|\n"
        f"| Revenue | {fmt_money(row['Revenue'])} |\n"
        f"| COGS | {fmt_money(row['COGS'])} |\n"
        f"| Gross Profit | {fmt_money(row['Gross Profit'])} |\n"
        f"| Payroll | {fmt_money(row['Payroll'])} |\n"
        f"| Operating Expenses | {fmt_money(row['Operating Expenses'])} |\n"
        f"| **Operating Profit** | **{fmt_money(row['Operating Profit'])}** |"
    )

    evidence = {
        "month": month,
        "Revenue": float(row["Revenue"]),
        "COGS": float(row["COGS"]),
        "Gross Profit": float(row["Gross Profit"]),
        "Payroll": float(row["Payroll"]),
        "Operating Expenses": float(row["Operating Expenses"]),
        "Operating Profit": float(row["Operating Profit"]),
    }

    return {
        "answer": answer,
        "evidence": evidence,
        "source": "monthly_pnl",
    }


def answer_variance(df: pd.DataFrame, question: str):

    p = monthly_pnl(df)
    months = list(p.index)

    selected = find_months(question, months)

    if len(selected) == 2:

        from_month = selected[0]
        to_month = selected[1]

    elif len(selected) == 1:

        try:
            idx = months.index(selected[0])

            if idx == 0:
                return {
                    "answer": "There is no earlier month available for comparison.",
                    "evidence": [],
                    "source": "monthly_pnl",
                }

            from_month = months[idx - 1]
            to_month = selected[0]

        except ValueError:
            return {
                "answer": "Unable to determine the comparison months.",
                "evidence": [],
                "source": "monthly_pnl",
            }

    else:

        if len(months) < 2:
            return {
                "answer": "There are not enough months to calculate a variance.",
                "evidence": [],
                "source": "monthly_pnl",
            }

        from_month = months[-2]
        to_month = months[-1]

    previous = p.loc[from_month]
    current = p.loc[to_month]

    lines = [
        f"### Variance — {from_month} → {to_month}",
        "",
        "| P&L Line | Change | % Change |",
        "|---|---:|---:|",
    ]

    evidence = {}

    for line in p.columns:

        prev = float(previous[line])
        cur = float(current[line])

        delta = cur - prev

        pct = (
            delta / abs(prev) * 100
            if prev != 0
            else None
        )

        pct_text = (
            f"{pct:+.1f}%"
            if pct is not None
            else "N/A"
        )

        lines.append(
            f"| {line} | {fmt_money(delta)} | {pct_text} |"
        )

        evidence[line] = {
            "from": prev,
            "to": cur,
            "delta": delta,
            "pct_change": pct,
        }

    return {
        "answer": "\n".join(lines),
        "evidence": evidence,
        "source": "monthly_pnl",
    }


def answer_transactions(df: pd.DataFrame, question: str):

    sub = df.copy()

    p = monthly_pnl(df)
    month = find_month(question, list(p.index))

    if month:
        sub = sub[sub["month"] == month]

    q = question.lower()

    category = None

    if "revenue" in q or "sales" in q:
        category = "Revenue"

    elif "cogs" in q:
        category = "COGS"

    elif "payroll" in q or "salary" in q or "wages" in q:
        category = "Payroll"

    elif (
        "operating expense" in q
        or "operating expenses" in q
        or "opex" in q
    ):
        category = "Operating Expenses"

    elif "non-p&l" in q or "non pnl" in q:
        category = "Non-P&L"

    if category:
        sub = sub[sub["top_category"] == category]

    sub = sub.reindex(
        sub["amount"].abs().sort_values(ascending=False).index
    )

    cols = [
        "id",
        "date",
        "description",
        "counterparty",
        "amount",
        "subcategory",
        "confidence",
    ]

    out = sub[cols].head(15).copy()

    if out.empty:
        return {
            "answer": "No matching transactions were found.",
            "evidence": [],
            "source": "transactions",
        }

    lines = [
        "### Transactions",
        "",
        "| Date | Description | Amount | Category |",
        "|---|---|---:|---|",
    ]

    for _, row in out.iterrows():

        lines.append(
            f"| {row['date']} | "
            f"{row['description']} | "
            f"{fmt_money(row['amount'])} | "
            f"{row['subcategory'] or '-'} |"
        )

    return {
        "answer": "\n".join(lines),
        "evidence": out.to_dict(orient="records"),
        "source": "transactions",
    }


def answer_non_pnl(df: pd.DataFrame, question: str):

    summary = non_pnl_summary(df)

    if summary.empty:

        return {
            "answer": "There are no non-P&L activities.",
            "evidence": [],
            "source": "non_pnl_summary",
        }

    month = find_month(
        question,
        list(summary.index)
    )

    if month and month in summary.index:

        row = summary.loc[month]

        lines = [
            f"### Non-P&L Activity — {month}",
            "",
            "| Activity | Amount |",
            "|---|---:|",
        ]

        for name, value in row.items():

            lines.append(
                f"| {name} | {fmt_money(value)} |"
            )

        return {
            "answer": "\n".join(lines),
            "evidence": row.to_dict(),
            "source": "non_pnl_summary",
        }

    return {
        "answer": (
            "Non-P&L activity is available for: "
            + ", ".join(str(x) for x in summary.index)
        ),
        "evidence": summary.to_dict(),
        "source": "non_pnl_summary",
    }


def answer_review(df: pd.DataFrame):

    sub = df[
        df["confidence"] == "needs_review"
    ]

    if sub.empty:

        return {
            "answer": "There are currently no transactions flagged for review.",
            "evidence": [],
            "source": "review_items",
        }

    return {
        "answer": (
            f"There are {len(sub)} transactions "
            "currently flagged for review."
        ),
        "evidence": sub.to_dict(orient="records"),
        "source": "review_items",
    }


def ask(
    df: pd.DataFrame,
    question: str,
    history: list[dict] | None = None,
) -> dict:

    intent = detect_intent(question)

    if intent == "pnl":
        result = answer_pnl(df, question)

    elif intent == "variance":
        result = answer_variance(df, question)

    elif intent == "transactions":
        result = answer_transactions(df, question)

    elif intent == "non_pnl":
        result = answer_non_pnl(df, question)

    elif intent == "review":
        result = answer_review(df)

    else:

        result = {
            "answer": (
                "I can answer questions about P&L, variances, "
                "transactions, non-P&L activity, and review items."
            ),
            "evidence": [],
            "source": None,
        }

    return {
        "answer": result["answer"],
        "evidence": result["evidence"],
        "intent": intent,
        "source": result["source"],
        "llm_used": False,
        "tool_calls": [],
    }