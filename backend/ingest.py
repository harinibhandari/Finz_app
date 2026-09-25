import pandas as pd


def load_transactions(path: str) -> pd.DataFrame:
    """Load the raw transaction file into a structured DataFrame.

    Adds derived fields (month, id-as-string) needed across the rest of the app.
    Everything downstream (categorization, P&L, variance, chat) reads from this
    structure, not from the raw file, so there's one source of truth.
    """
    df = pd.read_excel(path)
    df = df.rename(columns={
        "Transaction ID": "id",
        "Date": "date",
        "Description": "description",
        "Counterparty": "counterparty",
        "Amount": "amount",
        "Method": "method",
    })
    df["date"] = pd.to_datetime(df["date"])
    df["month"] = df["date"].dt.strftime("%Y-%m")
    df["id"] = df["id"].astype(str)

    # categorization fields, filled in by the categorizer step
    df["top_category"] = None
    df["subcategory"] = None
    df["confidence"] = None          # "high" | "needs_review"
    df["rule_suggestion"] = None
    df["llm_suggestion"] = None
    df["rationale"] = None
    df["corrected"] = False          # True once a human overrides the category

    return df.sort_values("date").reset_index(drop=True)
