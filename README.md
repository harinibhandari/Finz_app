# Finz AI-Native Financial Review

Finz is an AI-assisted financial review application built for NYC Restaurant Co.

The application takes a bank transaction file, categorizes the transactions,
builds a monthly P&L, identifies transactions that require review, detects
material month-to-month changes, and provides an AI financial analyst for
natural-language questions about the financial data.

The core design principle is:

> AI is used for understanding and explanation, while financial calculations
> are performed deterministically from the underlying transaction data.

---

# Links

* **GitHub repository:** [github.com/harinibhandari/Finz_app](https://github.com/harinibhandari/Finz_app)
* **Live deployed application:** [finz-app.onrender.com](https://finz-app.onrender.com/)

> Note: the live deployment is hosted on Render's free tier, so the
> instance may spin down after inactivity. The first request after a
> period of idleness can take up to ~30-60 seconds to wake up.

---

## What the app does

The main workflow is:

```text
Upload transactions
        ↓
Read and structure transaction data
        ↓
Apply deterministic categorization rules
        ↓
Use AI for transactions not matched by rules
        ↓
Flag AI-classified transactions for review
        ↓
Human review / manual correction
        ↓
Calculate monthly P&L
        ↓
Detect material month-to-month changes
        ↓
Ask questions using the AI financial analyst
```

---

# Features

* Upload an Excel transaction file
* Read and structure transaction data
* Automatically categorize transactions
* Use deterministic rules for known transaction patterns
* Use AI classification for transactions that do not match a rule
* Flag AI-classified transactions for manual review
* Manually recategorize transactions
* Persist corrected transaction categories
* Calculate monthly P&L using pandas
* Separate P&L and non-P&L transactions
* Detect material month-to-month changes
* Query transactions behind financial figures
* Ask questions using an AI financial analyst
* Filter transactions by month, category, and confidence
* Display the underlying transaction data used by the application

---

# Setup

## Requirements

You need:

* Python 3.10 or newer
* Git
* A Groq API key

---

## 1. Clone the project

```bash
git clone https://github.com/harinibhandari/Finz_app.git
cd Finz_app
```

---

## 2. Create a virtual environment

### Windows

```powershell
python -m venv venv
venv\Scripts\activate
```

### Mac / Linux

```bash
python -m venv venv
source venv/bin/activate
```

---

## 3. Install dependencies

```bash
pip install -r requirements.txt
```

---

## 4. Configure the API key

Create a `.env` file inside the `backend` directory:

```text
backend/.env
```

Add:

```env
GROQ_API_KEY=your_groq_api_key
```

The application uses the Groq API for:

* AI transaction categorization
* AI financial analyst chat
* AI variance explanations through the variance explanation function

Do not commit your real API key to GitHub.

---

## 5. Start the application

From the project root:

```bash
uvicorn backend.main:app --reload --port 8000
```

Then open:

```text
http://127.0.0.1:8000
```

---

# Input Data

The application accepts:

```text
.xlsx
.xls
.csv
```

The expected transaction data is loaded through:

```text
backend/ingest.py
```

The provided transaction workbook is:

```text
data/transactions.xlsx
```

---

# How the application works

## 1. Upload

The user uploads a transaction file through the web interface.

The backend saves the uploaded file as:

```text
data/transactions.xlsx
```

The transaction data is then loaded into a pandas DataFrame.

This part is handled by:

```text
backend/ingest.py
```

---

# 2. Transaction categorization

Finz uses a two-stage categorization process.

## Stage 1 — Deterministic rules

The application first checks each transaction against the rules defined in:

```text
backend/rules.py
```

The rules use transaction descriptions to identify known patterns.

Examples include:

```text
rent
food inventory purchase
beverage inventory purchase
POS batch deposits
catering invoice payments
payroll
utilities
marketing
equipment purchases
loan repayments
owner distributions
tax remittances
gift card sales
```

When a rule matches, the transaction is categorized directly.

These transactions receive:

```text
confidence = high
```

---

## Stage 2 — AI categorization

Transactions that do not match a deterministic rule are sent to the
LLM for classification.

The AI receives information such as:

* Transaction ID
* Description
* Counterparty
* Amount

The model selects a subcategory from the application's predefined taxonomy.

The AI also returns a short rationale.

The categorization is handled by:

```text
backend/categorize.py
```

The AI model used is:

```text
openai/gpt-oss-120b
```

through the Groq API.

---

# 3. Review workflow

Transactions that cannot be categorized by a deterministic rule are treated
as requiring review after AI classification.

They receive:

```text
confidence = needs_review
```

These transactions are displayed in the transaction table.

The user can:

* Filter for transactions needing review
* Inspect the transaction
* Select another category
* Correct the transaction manually

Manual corrections are marked as:

```text
corrected = True
confidence = high
```

The correction is then persisted using:

```text
backend/store.py
```

This creates a human-in-the-loop workflow rather than relying entirely on
the AI classification.

---

# 4. Transaction taxonomy

Finz uses a two-level accounting taxonomy.

## P&L categories

### Revenue

* Food Sales
* Beverage Sales
* Catering Revenue
* Delivery Marketplace Revenue
* Refunds & Discounts

### COGS

* Food Inventory
* Beverage Inventory

### Payroll

* Salaries
* Hourly Wages
* Payroll Taxes & Benefits

### Operating Expenses

* Rent
* Utilities
* Insurance
* Software & Subscriptions
* Marketing
* Repairs & Maintenance
* Cleaning & Linen
* Office & Admin Supplies
* Professional Services
* Delivery Platform Commission
* Packaging & Disposables

---

## Non-P&L categories

The application also separates transactions that represent cash movement
but should not be included directly in the operating P&L.

These include:

* Capital Expenditure
* Financing - Loan Proceeds
* Financing - Loan Repayment
* Owner Equity
* Tax Remittance
* Deferred Revenue

The taxonomy is defined in:

```text
backend/taxonomy.py
```

---

# 5. Monthly P&L

The P&L is calculated directly from the categorized transaction DataFrame.

The application uses pandas to calculate:

```text
Revenue
COGS
Gross Profit
Payroll
Operating Expenses
Operating Profit
```

The calculation is implemented in:

```text
backend/pnl.py
```

The P&L calculation does not use an LLM to generate financial totals.

The basic calculation is:

```text
Gross Profit
= Revenue - COGS

Operating Profit
= Gross Profit - Payroll - Operating Expenses
```

Expense categories are converted from their transaction cash-flow signs
into positive expense values for display.

---

# 6. Non-P&L activity

Some transactions represent cash movements but are not treated as normal
operating revenue or expenses.

Examples include:

```text
Equipment purchases
Loan proceeds
Loan repayments
Owner equity transactions
Tax remittances
Gift card sales / deferred revenue
```

These transactions are kept separate from the P&L.

The application provides a separate non-P&L summary through:

```text
backend/pnl.py
```

This prevents non-operating cash movements from being incorrectly included
in the operating P&L.

---

# 7. Variance analysis

Finz compares the monthly P&L and looks for material changes.

The variance calculation is deterministic.

The application checks:

```text
Revenue
COGS
Payroll
Operating Expenses
Operating Profit
```

A variance is flagged when both conditions are met:

```text
Absolute change >= $500
AND
Percentage change >= 10%
```

These thresholds are defined in:

```text
backend/variance.py
```

The variance calculation itself does not require an LLM.

For each detected variance, the application can identify the largest
transactions contributing to the relevant P&L line.

---

# 8. AI variance explanation

The project also contains an AI-based variance explanation function.

The function:

```text
variance_with_evidence()
```

uses the transaction data behind a variance and asks the LLM to explain
what may have driven the change.

The AI is instructed to:

* Use the provided transactions as evidence
* Reference specific transactions or categories
* Avoid inventing numbers
* Avoid claiming that a transaction appeared or disappeared when only a
  partial transaction list is available

The implementation is in:

```text
backend/variance.py
```

The variance calculation remains deterministic; AI is used for explanation.

---

# 9. AI financial analyst

Finz includes a chat interface for asking questions about the financial data.

Example questions:

```text
What was the revenue in March?

How much did payroll change?

Why did operating profit change?

What caused the increase in food costs?

Which transactions need review?

Show me the largest transactions in March.

What non-P&L activity occurred?
```

The AI financial analyst is implemented in:

```text
backend/agent.py
```

The agent is built using:

```text
LangChain
LangGraph
Groq
```

---

# 10. AI tools

The financial analyst has access to tools that retrieve information directly
from the current transaction DataFrame.

The available tools include:

### `get_pnl`

Retrieves monthly P&L data.

### `get_transactions`

Retrieves individual transactions filtered by:

* Category
* Month
* Number of transactions

### `get_variance_between`

Calculates the change between two selected months.

### `get_review_items`

Retrieves transactions currently marked:

```text
needs_review
```

### `get_non_pnl_activity`

Retrieves non-P&L cash movements.

The agent uses these tools to retrieve actual application data instead of
generating financial totals from its own reasoning.

---

# 11. Financial calculation safety

One of the main design principles of Finz is separating:

```text
Deterministic computation
```

from:

```text
AI interpretation
```

Financial totals are calculated using Python and pandas.

For example:

```text
Monthly Revenue
Monthly COGS
Gross Profit
Payroll
Operating Expenses
Operating Profit
Variance amount
Variance percentage
```

are calculated from the transaction data.

The LLM is used for tasks where language understanding is useful:

```text
Transaction classification
Variance explanation
Natural-language financial questions
```

This makes the numerical calculations traceable to the underlying
transactions.

---

# 12. Persistence

Finz is currently designed as a simple single-tenant application.

The categorized transaction DataFrame is persisted to:

```text
data/state.json
```

This allows user corrections to remain available after the application
restarts.

The persistence logic is implemented in:

```text
backend/store.py
```

The application does not currently require a database.

---

# 13. API endpoints

The FastAPI backend exposes the following endpoints.

### Upload transactions

```http
POST /api/upload
```

Uploads and categorizes a transaction file.

---

### Get transactions

```http
GET /api/transactions
```

Optional filters:

```text
month
category
confidence
```

---

### Correct a transaction

```http
POST /api/correct
```

Changes the subcategory of a transaction.

---

### Get P&L

```http
GET /api/pnl
```

Returns the calculated monthly P&L.

---

### Get non-P&L activity

```http
GET /api/non-pnl
```

Returns non-P&L cash movements.

---

### Get variances

```http
GET /api/variances
```

Returns material month-to-month P&L changes.

---

### Ask the AI analyst

```http
POST /api/chat
```

Example request:

```json
{
  "question": "Why did operating profit change between February and March?",
  "history": []
}
```

---

### Get categories

```http
GET /api/categories
```

Returns the available top-level categories and subcategories.

---

# Project Structure

```text
Finz_app/
│
├── backend/
│   ├── __pycache__/
│   ├── .env
│   ├── agent.py
│   ├── categorize.py
│   ├── ingest.py
│   ├── main.py
│   ├── pnl.py
│   ├── rules.py
│   ├── store.py
│   ├── taxonomy.py
│   └── variance.py
│
├── data/
│   ├── state.json
│   └── transactions.xlsx
│
├── frontend/
│   └── index.html
│
├── .env.example
├── .gitignore
├── README.md
└── requirements.txt
```

> `data/state.json` contains the persisted categorized state generated by
> the application. It should generally not be committed if it contains
> sensitive financial data.

---

# Main Files

| File                  | Purpose                                                          |
| --------------------- | ---------------------------------------------------------------- |
| `ingest.py`           | Reads and structures the uploaded transaction file               |
| `taxonomy.py`         | Defines P&L and non-P&L categories                               |
| `rules.py`            | Contains deterministic transaction categorization rules          |
| `categorize.py`       | Handles rule-based and AI-assisted categorization                |
| `pnl.py`              | Calculates monthly P&L and non-P&L summaries                     |
| `variance.py`         | Detects material changes and contains variance explanation logic |
| `agent.py`            | Implements the AI financial analyst                              |
| `store.py`            | Persists categorized data and user corrections                   |
| `main.py`             | FastAPI application and API endpoints                            |
| `frontend/index.html` | Web interface                                                    |

---

# Technology Stack

## Backend

* Python
* FastAPI
* pandas
* openpyxl

## AI

* Groq API
* `openai/gpt-oss-120b`
* LangChain
* LangGraph

## Frontend

* HTML
* CSS
* JavaScript
* Marked.js for rendering AI responses

---

# Testing

The main workflow was tested by checking:

1. Uploading the transaction file
2. Loading the transactions
3. Categorizing transactions
4. Identifying transactions requiring review
5. Manually changing a transaction category
6. Confirming that the correction is persisted
7. Checking the monthly P&L
8. Checking non-P&L activity
9. Checking monthly variance detection
10. Asking questions using the AI analyst

The key objective is to verify that financial totals remain based on the
underlying transaction data rather than being generated by the AI.

---

# Known Limitations

## Delivery platform commissions

Delivery platform commissions are currently treated as:

```text
Operating Expenses
```

rather than being directly deducted from delivery revenue.

This is a design choice for this project.

---

## Rule-based categorization

The deterministic categorization system primarily relies on transaction
descriptions and predefined keyword patterns.

It works well for the provided dataset but is not designed to handle every
possible bank transaction format.

Transactions that do not match a deterministic rule are sent to the AI
classification step and marked for review.

---

## Single-tenant storage

The application currently stores state in:

```text
data/state.json
```

rather than using a production database.

This is appropriate for the current take-home/project scope but would need
to be replaced or extended for a multi-user production system.

---

## File storage

Uploaded transactions are stored locally as:

```text
data/transactions.xlsx
```

A production deployment would typically use managed object storage and
database-backed persistence.

---

## AI dependency

AI-assisted categorization, variance explanation, and financial chat
require a valid Groq API key.

Deterministic P&L calculations do not depend on the AI model.

---

# Design Principle

The central design principle behind Finz is:

```text
                    ┌─────────────────────┐
                    │  Bank Transactions  │
                    └──────────┬──────────┘
                               ↓
                    ┌─────────────────────┐
                    │  Deterministic     │
                    │  Rules             │
                    └──────────┬──────────┘
                               │
                     unmatched transactions
                               ↓
                    ┌─────────────────────┐
                    │   AI Categorization │
                    └──────────┬──────────┘
                               ↓
                    ┌─────────────────────┐
                    │ Human Review        │
                    │ / Correction        │
                    └──────────┬──────────┘
                               ↓
                    ┌─────────────────────┐
                    │ Deterministic P&L   │
                    │ Calculation         │
                    └──────────┬──────────┘
                               ↓
                    ┌─────────────────────┐
                    │ Variance Detection  │
                    └──────────┬──────────┘
                               ↓
                    ┌─────────────────────┐
                    │ AI Explanation /    │
                    │ Financial Chat      │
                    └─────────────────────┘
```

The goal is to use AI where it adds value while keeping financial
calculations traceable and deterministic.
