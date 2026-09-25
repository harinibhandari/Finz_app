# Finz — AI-Native Financial Review

Turns NYC Restaurant Co.'s raw bank transactions into a categorized, explainable
monthly P&L with variance analysis and a conversational AI analyst.

## Setup

```bash
cd finz-app
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env   # then put your real Groq API key in .env
uvicorn backend.main:app --reload --port 8000
```

Open `http://127.0.0.1:8000`. Upload `data/transactions.xlsx` (the provided
dataset) in the UI. That single upload runs ingestion + AI categorization; the
P&L, variance, and chat views populate immediately after.

Get a free Groq API key at https://console.groq.com/keys.

## Workflow demonstrated

1. **Upload** the transaction file → parsed into a structured table.
2. **Categorized automatically** — each transaction gets an AI-assigned
   category, cross-checked against a rule-based signal for confidence.
3. **Correct** a flagged transaction from the dropdown in the transaction
   table — the correction persists and instantly recalculates the P&L.
4. **P&L** — deterministic monthly Revenue / COGS / Gross Profit / Payroll /
   Operating Expenses / Operating Profit.
5. **Variances** — material month-over-month changes, each with an AI
   explanation grounded in the actual transactions (linked by ID).
6. **Chat** — ask the AI analyst questions; it answers by calling tools over
   the real data, not from memory.

## Key technical decisions

### Where AI is used, and why
- **Categorization**: matching a free-text bank description ("Delivery
  marketplace payout week 3") to an accounting category is a judgment call —
  exactly the kind of task an LLM is suited for and a lookup table isn't.
- **Variance explanation**: *detecting* a material change is arithmetic, but
  *explaining* why it happened requires reading and synthesizing several
  transactions in context — that's AI's job.
- **Chat analyst**: open-ended natural-language questions about the data need
  an LLM to interpret intent and decide which data to pull.

### Where deterministic logic is used, and why
- **The P&L itself** (`backend/pnl.py`) is pure pandas — grouping categorized
  transactions by month and summing. No LLM call is in this path at all, per
  the spec's hard requirement that an LLM must never generate financial
  totals.
- **Variance detection** (`backend/variance.py`) — *finding* a material
  change is a deterministic diff against a materiality threshold (10% and
  $500 minimum). Only the *explanation* of a detected variance goes to the
  LLM.
- **Chart-of-accounts classification of non-P&L items** — equipment
  purchases, loan proceeds/repayments, owner distributions, sales tax
  remittance, and gift card deposits are structurally excluded from the P&L
  (see `taxonomy.py`, the `NON_PNL_CATEGORIES` bucket) rather than left to
  the LLM to remember not to include them. This is deliberate: those five
  transaction types in the dataset are real cash movements but not P&L
  revenue/expense, and keeping them in a separate, visible bucket (rather
  than silently dropping them) is what makes the P&L trustworthy.

### How incorrect or unsupported financial answers are prevented
- **Dual-check categorization**: every transaction gets both a rule-based
  suggestion (deterministic keyword/counterparty match, `rules.py`) and an
  LLM suggestion. They only get marked "high confidence" when they agree.
  Any disagreement — or anything the rules don't recognize — is flagged
  `needs_review` and surfaced in the UI rather than silently trusted.
- **The chat agent cannot state a number it didn't just fetch.** It's a
  LangGraph tool-calling agent (`backend/agent.py`) with tools that query the
  same P&L/transaction data structures the rest of the app uses
  (`get_pnl`, `get_transactions`, `get_variance_between`, etc.). The system
  prompt instructs it to only cite figures returned by a tool call, and every
  tool call made is shown under the answer in the UI so the user can see
  exactly what was queried.
- **Variance explanations are grounded**: the LLM is given only the actual
  evidence transactions behind a variance and instructed not to invent
  numbers beyond what's in that evidence — the prompt is a closed-book
  summarization task, not open-ended generation.

### How output is verified
- The P&L was checked against manual pandas aggregation of the raw dataset
  independent of the app's own code path, using the real provided
  transaction file, before wiring in the categorization step.
- Every UI surface that shows a number (P&L, variance, review flags) links
  back to the specific transaction IDs behind it, so any figure can be
  traced to source rows in the original file.
- The correction flow is round-tripped: correcting a transaction's category
  immediately recalculates and re-displays the P&L, so a wrong AI
  categorization is always human-correctable and its effect is visible.

## Project structure

```
backend/
  ingest.py      — load raw xlsx into structured DataFrame
  taxonomy.py    — chart of accounts (P&L categories + non-P&L categories)
  rules.py       — deterministic keyword categorizer (cross-check signal)
  categorize.py  — LLM categorization + confidence scoring
  pnl.py         — deterministic P&L calculation (no LLM)
  variance.py    — deterministic variance detection + LLM explanation
  agent.py       — LangGraph chat agent with tools over the real data
  store.py       — simple JSON persistence for corrections
  main.py        — FastAPI app / routes
frontend/
  index.html     — single-page UI (upload, transactions, P&L, variances, chat)
data/
  transactions.xlsx — provided dataset
```

## Known limitations / judgment calls

- Delivery platform commissions are categorized as an Operating Expense
  rather than netted directly against delivery revenue — a defensible
  alternative treatment, flagged here rather than hidden.
- The rule-based cross-check is intentionally literal (regex on description
  text). It's a safety net for *this* dataset's transaction patterns, not a
  general-purpose classifier — the LLM is what actually generalizes to new,
  differently-worded transactions.
