"""
Deterministic P&L calculation.

No LLM anywhere in this file. Every number here is a pandas sum over
categorized transactions. This is the hard constraint from the spec:
"The P&L must be calculated from the underlying transaction data.
An LLM must not generate financial totals."
"""
import pandas as pd
from taxonomy import is_pnl


def monthly_pnl(df: pd.DataFrame) -> pd.DataFrame:
    """Build a monthly P&L table from categorized transactions.

    Only rows whose top_category is a P&L category are included -
    Non-P&L rows (capex, financing, equity, tax remittance, deferred revenue)
    are excluded from these totals by design.
    """
    pnl_rows = df[df["top_category"].apply(lambda c: is_pnl(c) if c else False)].copy()

    grouped = (
        pnl_rows.groupby(["month", "top_category"])["amount"]
        .sum()
        .unstack(fill_value=0.0)
    )

    for col in ["Revenue", "COGS", "Payroll", "Operating Expenses"]:
        if col not in grouped.columns:
            grouped[col] = 0.0

    # Revenue is stored with its natural sign (refunds are negative revenue rows,
    # already netted in via the groupby sum). COGS/Payroll/OpEx are stored as
    # negative amounts in the raw data (money leaving the account), so we flip
    # sign for display as positive expense figures.
    out = pd.DataFrame(index=grouped.index)
    out["Revenue"] = grouped["Revenue"]
    out["COGS"] = -grouped["COGS"]
    out["Gross Profit"] = out["Revenue"] - out["COGS"]
    out["Payroll"] = -grouped["Payroll"]
    out["Operating Expenses"] = -grouped["Operating Expenses"]
    out["Operating Profit"] = out["Gross Profit"] - out["Payroll"] - out["Operating Expenses"]

    return out.sort_index().round(2)


def non_pnl_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Summarize the non-P&L cash movements by month, for transparency
    (shown separately from the P&L, not folded into it)."""
    non_pnl_rows = df[df["top_category"].apply(lambda c: not is_pnl(c) if c else False)].copy()
    if non_pnl_rows.empty:
        return pd.DataFrame()
    grouped = (
        non_pnl_rows.groupby(["month", "subcategory"])["amount"]
        .sum()
        .unstack(fill_value=0.0)
        .round(2)
    )
    return grouped.sort_index()
