# Finz - AI-Native Financial Review

Finz is a financial review app made for NYC Restaurant Co.

It takes a bank transaction file and helps turn it into a clean monthly
P&L. It also finds transactions that may need review, shows changes
between months, and has an AI chat assistant for asking questions about
the financial data.

## What the app does

The main flow of the app is:

Upload transactions  
→ Categorize transactions  
→ Review flagged transactions  
→ Calculate P&L  
→ Find monthly changes  
→ Explain the changes  
→ Ask questions using AI

## Features

- Upload an Excel transaction file
- Automatically categorize transactions
- Use AI to help with transaction categorization
- Check AI results using simple rules
- Flag transactions that need review
- Manually change a transaction category
- Calculate monthly P&L
- Compare P&L between months
- Find important changes in revenue and expenses
- Show transactions behind a change
- Ask questions to the AI financial analyst
- Keep non-P&L transactions separate

---

# Setup

## Requirements

You need:

- Python 3.10 or newer
- Git

## 1. Clone the project

```bash
git clone https://github.com/harinibhandari/Finz_app.git
cd Finz_app
```

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

## 3. Install the required packages

```bash
pip install -r requirements.txt
```

## 5. Start the app

```bash
uvicorn backend.main:app --reload --port 8000
```

Then open:

```text
http://127.0.0.1:8000
```

Upload:

```text
data/transactions.xlsx
```

---

# How the app works

## 1. Upload

The user uploads the bank transaction Excel file.

The app reads the file and converts the rows into structured transaction
data.

This part is handled by:

```text
backend/ingest.py
```

## 2. Categorization

Each transaction is given a category.

The app uses both:

* Simple rules based on the transaction description
* AI classification

The two results are compared to help decide whether a transaction is
safe to accept or needs review.

Files used:

```text
backend/categorize.py
backend/rules.py
backend/taxonomy.py
```

## 3. Review

If the app is not confident about a transaction, it is shown for review.

The user can change the category from the transaction table.

After changing the category, the P&L is updated using the new category.

This makes the process human-controlled instead of fully depending on AI.

## 4. P&L

The P&L is calculated from the transaction data.

It includes:

* Revenue
* COGS
* Gross Profit
* Payroll
* Operating Expenses
* Operating Profit

The P&L is calculated using Python and pandas.

The AI does not calculate the financial totals.

The main file for this is:

```text
backend/pnl.py
```

## 5. Non-P&L transactions

Some bank transactions are not part of the normal P&L.

For example:

* Equipment purchases
* Loan proceeds
* Loan repayments
* Owner transactions
* Tax payments
* Other non-P&L cash movements

These are kept separate so they do not get counted as normal revenue or
expenses.

This is handled in:

```text
backend/taxonomy.py
```

## 6. Variance analysis

The app compares the P&L between months.

It looks for changes that are large enough to need attention.

The calculation is done using normal Python calculations.

AI is used only to explain the reason for the change.

This is handled by:

```text
backend/variance.py
```

## 7. AI financial analyst

The app also has a chat section where the user can ask questions about
the financial data.

For example:

```text
What was the revenue in March?

How much did payroll change?

Why did operating profit change?

What caused the increase in food costs?

Which transactions need review?

Show me the transactions behind this change.
```

The AI uses tools to get the actual data from the application.

It does not need to guess the numbers.

This is handled by:

```text
backend/agent.py
```

---

# Why I used AI

I used AI where understanding the transaction or explaining the data is
useful.

### Transaction categorization

Bank descriptions can be written in many different ways.

AI helps understand the description and choose a suitable category.

### Variance explanation

The app calculates the actual change using Python.

AI then looks at the related transactions and explains what may have
caused the change.

### Chat

Users can ask questions in normal language instead of looking through
the data manually.

---

# Where I did not use AI

Financial calculations should not depend on an AI-generated number.

The P&L is calculated directly from the transaction data using pandas.

The variance amount is also calculated using Python.

This makes the financial numbers easier to check and trust.

---

# Checking AI results

The app uses two checks for transaction categories:

1. A rule-based result
2. An AI result

If the results do not match, the transaction can be sent for review.

This helps avoid accepting an incorrect AI category without checking it.

The user can also change the category manually.

---

# Project Structure

```text
Finz_app/
│
├── backend/
│   ├── ingest.py
│   ├── taxonomy.py
│   ├── rules.py
│   ├── categorize.py
│   ├── pnl.py
│   ├── variance.py
│   ├── agent.py
│   ├── store.py
│   └── main.py
│
├── frontend/
│   └── index.html
│
├── data/
│   └── transactions.xlsx
│
├── .env.example
├── .gitignore
├── README.md
└── requirements.txt
```

---

# Tech Used

* Python
* FastAPI
* pandas
* openpyxl
* Groq
* LangChain
* LangGraph
* HTML
* JavaScript

---

# Main files

```text
ingest.py
Reads the Excel transaction file.

taxonomy.py
Contains the transaction categories.

rules.py
Contains the simple rules used to check transaction categories.

categorize.py
Uses AI to categorize transactions.

pnl.py
Calculates the monthly P&L.

variance.py
Finds changes between months and prepares the data for explanation.

agent.py
Handles the AI financial analyst.

store.py
Stores user corrections.

main.py
Runs the FastAPI application.
```

---

# Testing

Before submitting the project, I checked the main workflow:

1. Upload the transaction file
2. Check that transactions are loaded
3. Check transaction categories
4. Check transactions that need review
5. Change a transaction category
6. Check that the P&L updates
7. Check the monthly P&L
8. Check the monthly variances
9. Check the transactions behind a variance
10. Ask questions using the AI analyst

---

# Known Limitations

## Delivery platform commissions

Delivery platform commissions are treated as Operating Expenses instead
of being directly removed from delivery revenue.

This is a design choice for this project.

## Rule-based checking

The rule-based system mainly uses keywords and transaction descriptions.

It works well for the provided dataset, but it is not meant to handle
every possible bank transaction format.

The AI helps handle transaction descriptions that do not match the
simple rules.
