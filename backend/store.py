"""
Minimal persistence layer. This is a single-tenant take-home app, so a
JSON file on disk is enough - no need for a real database. Keeps the
categorized DataFrame (including any user corrections) across restarts.
"""
import json
import os
import pandas as pd

STATE_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "state.json")


def save_state(df: pd.DataFrame) -> None:
    records = df.to_dict(orient="records")
    for r in records:
        if hasattr(r["date"], "isoformat"):
            r["date"] = r["date"].isoformat()
    with open(STATE_PATH, "w") as f:
        json.dump(records, f, default=str)


def load_state() -> pd.DataFrame | None:
    if not os.path.exists(STATE_PATH):
        return None
    with open(STATE_PATH) as f:
        records = json.load(f)
    df = pd.DataFrame(records)
    df["date"] = pd.to_datetime(df["date"])
    return df


def apply_correction(df: pd.DataFrame, transaction_id: str, new_subcategory: str) -> pd.DataFrame:
    from taxonomy import SUBCATEGORY_TO_TOP
    mask = df["id"] == transaction_id
    if not mask.any():
        raise ValueError(f"Transaction {transaction_id} not found")
    df.loc[mask, "subcategory"] = new_subcategory
    df.loc[mask, "top_category"] = SUBCATEGORY_TO_TOP.get(new_subcategory)
    df.loc[mask, "confidence"] = "high"
    df.loc[mask, "corrected"] = True
    df.loc[mask, "rationale"] = "Manually corrected by user."
    save_state(df)
    return df
