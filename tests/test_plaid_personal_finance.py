import os
os.environ["FINANCE_AGENT_ENCRYPTION_KEY"] = "mock_encryption_key_for_testing_purposes"
import json
import sqlite3
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.connectors.plaid_connector import assertReadOnlyPlaidEndpoint
from backend.hochster_cluster import DB_PATH
from backend.runtime_truth.collector import collect_and_store_all

def get_database_connection():
    return sqlite3.connect(DB_PATH, timeout=30)

@pytest.fixture(autouse=True)
def clean_db():
    # Ensure a fresh state for each test run if needed
    conn = get_database_connection()
    conn.execute("DELETE FROM finance_plaid_items")
    conn.execute("DELETE FROM finance_accounts")
    conn.execute("DELETE FROM finance_balances")
    conn.execute("DELETE FROM finance_transactions")
    conn.execute("DELETE FROM finance_liabilities")
    conn.execute("DELETE FROM finance_statements")
    conn.commit()

def test_blocked_endpoints_enforcement():
    # Verify that read-only check passes for permitted endpoints and raises ValueError for blocked ones
    assertReadOnlyPlaidEndpoint("/accounts/get")
    assertReadOnlyPlaidEndpoint("/transactions/get")
    assertReadOnlyPlaidEndpoint("/liabilities/get")
    assertReadOnlyPlaidEndpoint("/statements/list")
    assertReadOnlyPlaidEndpoint("/statements/download")
    
    with pytest.raises(ValueError):
        assertReadOnlyPlaidEndpoint("/transfer/initiate")
    with pytest.raises(ValueError):
        assertReadOnlyPlaidEndpoint("/payment_initiation/payment/create")
    with pytest.raises(ValueError):
        assertReadOnlyPlaidEndpoint("/sandbox/item/fire_webhook")

def test_plaid_link_tokens_exchange():
    client = TestClient(app)
    
    res = client.post("/api/plaid/create-link-token")
    print("STATUS:", res.status_code)
    print("RESPONSE:", res.text)
    assert res.status_code == 200
    
    # 2. Exchange Public Token
    payload = {
        "public_token": "public-sandbox-mock-12345",
        "institution_name": "USAA Bank Sandbox"
    }
    res_exch = client.post("/api/plaid/exchange-public-token", json=payload)
    print("EXCH STATUS:", res_exch.status_code)
    print("EXCH RESPONSE:", res_exch.text)
    assert res_exch.status_code == 200
    exch_data = res_exch.json()
    assert exch_data["status"] == "success"
    assert "item_id" in exch_data
    
    # Verify DB contains item
    conn = get_database_connection()
    row = conn.execute("SELECT institution_name, consent_status FROM finance_plaid_items LIMIT 1").fetchone()
    assert row is not None
    assert row[0] == "USAA Bank Sandbox"
    assert row[1] == "consented"

def test_finance_sync_and_data_retrieval():
    client = TestClient(app)
    
    # Pre-exchange an item to enable syncing
    client.post("/api/plaid/exchange-public-token", json={
        "public_token": "public-sandbox-mock-12345",
        "institution_name": "USAA Bank Sandbox"
    })
    
    # Trigger Sync
    res_sync = client.post("/api/finance/sync", json={"user_id": "default_user"})
    assert res_sync.status_code == 200
    assert res_sync.json()["status"] == "success"
    
    # Get Accounts
    res_accts = client.get("/api/finance/accounts")
    assert res_accts.status_code == 200
    accts = res_accts.json()
    assert len(accts) > 0
    # Must have USAA Checking and USAA credit card/mortgages
    assert any(a["name"] == "USAA Secure Checking" for a in accts)
    assert any(a["type"] == "credit" for a in accts)
    
    # Get Transactions
    res_txs = client.get("/api/finance/transactions")
    assert res_txs.status_code == 200
    txs = res_txs.json()
    assert len(txs) > 0
    assert any(t["merchant_name"] == "Netflix" for t in txs)
    
    # Get Statements list
    res_stmts = client.get("/api/finance/statements")
    assert res_stmts.status_code == 200
    stmts = res_stmts.json()
    assert len(stmts) > 0
    
    # Download statement
    stmt_id = stmts[0]["plaid_statement_id"]
    res_dl = client.post("/api/finance/statements/download", json={"statement_id": stmt_id})
    assert res_dl.status_code == 200
    dl_data = res_dl.json()
    assert dl_data["status"] == "success"
    assert "sha256_hash" in dl_data
    assert "evidence_path" in dl_data

def test_budget_variance_and_debt_planning():
    client = TestClient(app)
    
    # Setup data
    client.post("/api/plaid/exchange-public-token", json={
        "public_token": "public-sandbox-mock-12345",
        "institution_name": "USAA Bank Sandbox"
    })
    client.post("/api/finance/sync", json={"user_id": "default_user"})
    
    # 1. Budget Variance
    res_budget = client.get("/api/finance/budget/monthly")
    assert res_budget.status_code == 200
    budget = res_budget.json()
    assert "budget_variance" in budget
    # Check category values
    assert "Mortgage / Rent" in budget["budget_variance"]
    assert "Groceries" in budget["budget_variance"]
    assert "Savings / Investing" in budget["budget_variance"]
    
    # 2. Debt Plan
    res_debt = client.get("/api/finance/debt-plan")
    assert res_debt.status_code == 200
    debt_plans = res_debt.json()
    # Must have Avalanche, Snowball, and Hybrid plans
    strategies = [p["strategy"] for p in debt_plans]
    assert "Avalanche" in strategies
    assert "Snowball" in strategies
    assert "Hybrid" in strategies
    
    # 3. Monthly Closeout Report
    res_report = client.get("/api/finance/reports/monthly-closeout")
    assert res_report.status_code == 200
    report_data = res_report.json()
    assert "report" in report_data
    report_txt = report_data["report"]
    assert "ADVISORY DISCLAIMER" in report_txt
    assert "USAA Bank" in report_txt

def test_runtime_truth_signals_collection():
    # Sync and collect truth signals
    client = TestClient(app)
    client.post("/api/plaid/exchange-public-token", json={
        "public_token": "public-sandbox-mock-12345",
        "institution_name": "USAA Bank Sandbox"
    })
    client.post("/api/finance/sync", json={"user_id": "default_user"})
    
    # Trigger collection
    collect_and_store_all()
    
    # Check DB signals
    conn = get_database_connection()
    signals = conn.execute("SELECT signal_id, value FROM runtime_truth_signals").fetchall()
    signal_dict = dict(signals)
    
    assert "plaid_configured" in signal_dict
    assert "plaid_connected" in signal_dict
    assert "last_transaction_sync" in signal_dict
    assert "last_balance_sync" in signal_dict
    assert "last_liability_sync" in signal_dict
    assert "statement_support_status" in signal_dict
    assert "blocked_endpoint_test_status" in signal_dict
    assert "evidence_ledger_status" in signal_dict
    
    assert signal_dict["plaid_connected"] == "CONNECTED"
    assert signal_dict["blocked_endpoint_test_status"] == "PASS"
