import os
import shutil
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from ingest import load_transactions
from categorize import categorize_all
from pnl import monthly_pnl, non_pnl_summary
from variance import detect_variances, variance_with_evidence
from store import save_state, load_state, apply_correction
from taxonomy import ALL_TOP_LEVEL, SUBCATEGORY_TO_TOP
import agent as agent_module

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

app = FastAPI(title="Finz AI Financial Review")

# in-memory working copy of the categorized data; store.py mirrors it to disk
STATE = {"df": None}


def _get_df():
    if STATE["df"] is None:
        loaded = load_state()
        if loaded is not None:
            STATE["df"] = loaded
        else:
            raise HTTPException(400, "No data loaded yet. Upload a transaction file first.")
    return STATE["df"]


@app.on_event("startup")
def _startup():
    existing = load_state()
    if existing is not None:
        STATE["df"] = existing

@app.post("/api/upload")
async def upload(file: UploadFile = File(...)):
    try:
        dest = DATA_DIR / "transactions.xlsx"

        with open(dest, "wb") as f:
            shutil.copyfileobj(file.file, f)

        print("1. File saved")

        df = load_transactions(str(dest))
        print("2. File loaded:", len(df), "rows")

        df = categorize_all(df)
        print("3. Categorization completed")

        STATE["df"] = df
        save_state(df)
        print("4. State saved")

        needs_review = int(
            (df["confidence"] == "needs_review").sum()
        )

        return {
            "rows_ingested": len(df),
            "months": sorted(df["month"].unique().tolist()),
            "needs_review": needs_review,
        }

    except Exception as e:
        import traceback

        print("\n========== UPLOAD ERROR ==========")
        traceback.print_exc()
        print("==================================\n")

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
    
@app.get("/api/transactions")
def get_transactions(month: str | None = None, category: str | None = None,
                      confidence: str | None = None):
    df = _get_df().copy()
    if month:
        df = df[df["month"] == month]
    if category:
        df = df[df["top_category"] == category]
    if confidence:
        df = df[df["confidence"] == confidence]
    df = df.sort_values("date")
    out = df.copy()
    out["date"] = out["date"].astype(str)
    return out.to_dict(orient="records")


class Correction(BaseModel):
    transaction_id: str
    subcategory: str


@app.post("/api/correct")
def correct_transaction(body: Correction):
    if body.subcategory not in SUBCATEGORY_TO_TOP:
        raise HTTPException(400, f"Unknown subcategory: {body.subcategory}")
    df = _get_df()
    df = apply_correction(df, body.transaction_id, body.subcategory)
    STATE["df"] = df
    return {"status": "ok"}


@app.get("/api/pnl")
def get_pnl():
    df = _get_df()
    p = monthly_pnl(df)
    return {"pnl": p.reset_index().to_dict(orient="records")}


@app.get("/api/non-pnl")
def get_non_pnl():
    df = _get_df()
    s = non_pnl_summary(df)
    if s.empty:
        return {"non_pnl": []}
    return {"non_pnl": s.reset_index().to_dict(orient="records")}


@app.get("/api/variances")
def get_variances():
    df = _get_df()
    p = monthly_pnl(df)

    variances = detect_variances(p)

    results = []
    for variance in variances:
        results.append(variance_with_evidence(df, variance))

    return {"variances": results}

class ChatRequest(BaseModel):
    question: str
    history: list[dict] = []


@app.post("/api/chat")
def chat(body: ChatRequest):
    try:
        df = _get_df()
        result = agent_module.ask(df, body.question, body.history)
        return result

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
    
@app.get("/api/categories")
def get_categories():
    return {"categories": ALL_TOP_LEVEL, "subcategories": list(SUBCATEGORY_TO_TOP.keys())}


# serve the frontend
FRONTEND_DIR = BASE_DIR / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")