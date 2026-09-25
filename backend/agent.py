"""
The AI financial analyst chat interface.

Design principle: the agent NEVER computes or states a number from its own
reasoning. It has tools that query the real pnl/transactions data (the same
data structures pnl.py and variance.py use), and it must call a tool to get
any number before mentioning it. This is what "traceable evidence" and
"never hallucinating numbers" mean in practice - the numbers literally come
from tool outputs, not from the model's text generation.
"""
import os
import json
import pandas as pd
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage
from langchain_groq import ChatGroq
from langgraph.prebuilt import create_react_agent

from pnl import monthly_pnl, non_pnl_summary

SYSTEM_PROMPT = """You are an AI financial analyst for NYC Restaurant Co.
You answer questions about their P&L, transactions, and variances using ONLY
the tools provided - never state a dollar figure you did not just retrieve
from a tool call. When explaining a number, mention which transactions or
category it comes from so the user can trace it. Be concise and direct,
like a sharp analyst, not a chatbot. Dollar amounts should be formatted like
$12,345.67."""


def build_agent(df: pd.DataFrame):
    """df is the current categorized transactions DataFrame (closed over by
    the tools below, so the agent always sees the latest corrected data)."""

    @tool
    def get_pnl(month: str = "") -> str:
        """Get the monthly P&L (Revenue, COGS, Gross Profit, Payroll, Operating
        Expenses, Operating Profit). Pass month as 'YYYY-MM' (e.g. '2026-03')
        to get one month, or leave blank for all months."""
        p = monthly_pnl(df)
        if month:
            if month not in p.index:
                return f"No data for month {month}. Available months: {list(p.index)}"
            return p.loc[[month]].to_json(orient="index")
        return p.to_json(orient="index")

    @tool
    def get_transactions(category: str = "", month: str = "", limit: int = 15) -> str:
        """Get individual transactions, optionally filtered by top-level category
        ('Revenue', 'COGS', 'Payroll', 'Operating Expenses', 'Non-P&L') and/or
        month ('YYYY-MM'). Returns up to `limit` transactions sorted by absolute
        amount descending. Use this to find what's behind a number."""
        sub = df.copy()
        if category:
            sub = sub[sub["top_category"] == category]
        if month:
            sub = sub[sub["month"] == month]
        sub = sub.reindex(sub["amount"].abs().sort_values(ascending=False).index)
        cols = ["id", "date", "description", "counterparty", "amount", "subcategory", "confidence"]
        out = sub[cols].head(limit).copy()
        out["date"] = out["date"].astype(str)
        return out.to_json(orient="records")

    @tool
    def get_variance_between(from_month: str, to_month: str) -> str:
        """Get the dollar and percent change for every P&L line between two
        months ('YYYY-MM' format)."""
        p = monthly_pnl(df)
        if from_month not in p.index or to_month not in p.index:
            return f"Available months: {list(p.index)}"
        prev, cur = p.loc[from_month], p.loc[to_month]
        result = {}
        for line in p.columns:
            delta = cur[line] - prev[line]
            pct = (delta / abs(prev[line]) * 100) if prev[line] != 0 else None
            result[line] = {"from": round(prev[line], 2), "to": round(cur[line], 2),
                             "delta": round(delta, 2), "pct_change": round(pct, 1) if pct is not None else None}
        return json.dumps(result)

    @tool
    def get_review_items() -> str:
        """Get transactions currently flagged as needing review (low-confidence
        categorization, i.e. the rule-based check and the AI category disagreed)."""
        sub = df[df["confidence"] == "needs_review"]
        cols = ["id", "date", "description", "counterparty", "amount", "subcategory",
                "rule_suggestion", "llm_suggestion"]
        out = sub[cols].copy()
        out["date"] = out["date"].astype(str)
        return out.to_json(orient="records")

    @tool
    def get_non_pnl_activity(month: str = "") -> str:
        """Get non-P&L cash movements (capital expenditure, loan proceeds/
        repayment, owner distributions, tax remittance, gift card deposits) -
        real cash flow that is deliberately excluded from the P&L."""
        s = non_pnl_summary(df)
        if s.empty:
            return "No non-P&L transactions."
        if month:
            if month not in s.index:
                return f"No data for {month}."
            return s.loc[[month]].to_json(orient="index")
        return s.to_json(orient="index")

    tools = [get_pnl, get_transactions, get_variance_between, get_review_items, get_non_pnl_activity]

    llm = ChatGroq(model="openai/gpt-oss-120b", temperature=0,
                    api_key=os.environ["GROQ_API_KEY"])

    agent = create_react_agent(llm, tools, prompt=SystemMessage(content=SYSTEM_PROMPT))
    return agent


def ask(df: pd.DataFrame, question: str, history: list[dict] | None = None) -> dict:
    """Run one turn of the agent. history is a list of {role, content} dicts
    from prior turns (optional, for follow-up questions)."""
    agent = build_agent(df)
    messages = []
    for h in (history or []):
        messages.append((h["role"], h["content"]))
    messages.append(("user", question))

    result = agent.invoke({"messages": messages})
    final = result["messages"][-1]

    tool_calls_made = []
    for m in result["messages"]:
        if getattr(m, "tool_calls", None):
            for tc in m.tool_calls:
                tool_calls_made.append({"tool": tc["name"], "args": tc["args"]})

    return {"answer": final.content, "tool_calls": tool_calls_made}
