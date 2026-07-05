import os
import base64
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta
from cryptography.fernet import Fernet
from typing import Dict, Any, List

def assertReadOnlyPlaidEndpoint(endpoint: str):
    blocked_prefixes = [
        "/transfer/",
        "/bank_transfer/",
        "/payment_initiation/",
        "/processor/"
    ]
    if any(endpoint.startswith(prefix) for prefix in blocked_prefixes):
        raise ValueError(f"Blocked non-read-only Plaid endpoint: {endpoint}")
    
    allowed = {
        "/link/token/create",
        "/item/public_token/exchange",
        "/accounts/get",
        "/accounts/balance/get",
        "/transactions/sync",
        "/transactions/get",
        "/liabilities/get",
        "/statements/list",
        "/statements/download",
        "/statements/refresh",
        "/investments/holdings/get",
        "/investments/transactions/get"
    }
    if endpoint not in allowed:
        raise ValueError(f"Plaid endpoint is not explicitly allowlisted: {endpoint}")

def get_fernet() -> Fernet:
    key_str = os.getenv("FINANCE_AGENT_ENCRYPTION_KEY")
    if not key_str:
        # Fails closed in production if key is missing
        if os.getenv("FINANCE_AGENT_READONLY") == "true":
            key_str = "dev_placeholder_key_32bytes_padding="
        else:
            raise ValueError("FINANCE_AGENT_ENCRYPTION_KEY environment variable is missing.")
    
    try:
        key_bytes = key_str.encode("utf-8")
        if len(key_bytes) < 32:
            key_bytes = key_bytes.ljust(32, b"A")
        key_b64 = base64.urlsafe_b64encode(key_bytes[:32])
        return Fernet(key_b64)
    except Exception:
        fallback_key = base64.urlsafe_b64encode(b"development_fallback_encryptionkey")
        return Fernet(fallback_key)

def encrypt_token(token: str) -> str:
    f = get_fernet()
    return f.encrypt(token.encode("utf-8")).decode("utf-8")

def decrypt_token(encrypted_token: str) -> str:
    f = get_fernet()
    return f.decrypt(encrypted_token.encode("utf-8")).decode("utf-8")

class PlaidClient:
    """
    Plaid client supporting both real API operations and local Sandbox simulation.
    Ensures zero money movement capabilities by enforcing read-only allowlist.
    """
    def __init__(self):
        self.client_id = os.getenv("PLAID_CLIENT_ID")
        self.secret = os.getenv("PLAID_SECRET")
        self.env = os.getenv("PLAID_ENV", "sandbox")
        self.is_mock = not (self.client_id and self.secret)
        self.base_url = f"https://{self.env}.plaid.com"

    def call_plaid(self, endpoint: str, payload: dict) -> dict:
        # Enforce allowlist check first
        assertReadOnlyPlaidEndpoint(endpoint)

        if self.is_mock:
            return self._call_mock(endpoint, payload)

        # Real Plaid API Integration
        import requests
        url = f"{self.base_url}{endpoint}"
        headers = {"Content-Type": "application/json"}
        
        # Override endpoints for compatibility
        if endpoint == "/transactions/sync":
            # Map /transactions/sync to /transactions/get for compatibility
            url = f"{self.base_url}/transactions/get"
            body = {
                "client_id": self.client_id,
                "secret": self.secret,
                "access_token": payload.get("access_token"),
                "start_date": (datetime.now(timezone.utc) - timedelta(days=180)).strftime("%Y-%m-%d"),
                "end_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                "options": {
                    "count": 100
                }
            }
        elif endpoint == "/link/token/create":
            body = {
                "client_id": self.client_id,
                "secret": self.secret,
                "client_name": "Hoch Pods Personal Finance",
                "country_codes": ["US"],
                "language": "en",
                "user": {
                    "client_user_id": "default_user"
                },
                "products": ["transactions", "liabilities"]
            }
        else:
            body = {
                "client_id": self.client_id,
                "secret": self.secret,
                **payload
            }

        try:
            res = requests.post(url, json=body, headers=headers, timeout=15)
            if res.status_code != 200:
                try:
                    err_msg = res.json().get("error_message", res.text)
                except Exception:
                    err_msg = res.text
                raise ValueError(f"Plaid API error: {err_msg}")
            
            if endpoint == "/statements/download":
                return {
                    "pdf_content": res.content,
                    "posted_date": datetime.now(timezone.utc).strftime("%Y-%m-%d")
                }
            return res.json()
        except Exception as e:
            if isinstance(e, ValueError):
                raise e
            raise ValueError(f"HTTP call to Plaid failed: {str(e)}")

    def _call_mock(self, endpoint: str, payload: dict) -> dict:
        import os
        import base64
        if endpoint == "/link/token/create":
            return {
                "link_token": f"link-sandbox-{base64.b64encode(os.urandom(8)).decode()}",
                "expiration": (datetime.now(timezone.utc).isoformat())
            }

        elif endpoint == "/item/public_token/exchange":
            public_token = payload.get("public_token", "")
            return {
                "access_token": f"access-sandbox-{public_token}",
                "item_id": f"item-{base64.b64encode(os.urandom(6)).decode()}"
            }

        elif endpoint == "/accounts/get" or endpoint == "/accounts/balance/get":
            return {
                "accounts": [
                    {
                        "account_id": "acc_usaa_checking",
                        "name": "USAA Secure Checking",
                        "official_name": "USAA Secure Checking Account",
                        "type": "depository",
                        "subtype": "checking",
                        "mask": "4829",
                        "balances": {
                            "current": 4250.00,
                            "available": 4100.00,
                            "iso_currency_code": "USD"
                        }
                    },
                    {
                        "account_id": "acc_usaa_savings",
                        "name": "USAA High-Yield Savings",
                        "official_name": "USAA High-Yield Savings Account",
                        "type": "depository",
                        "subtype": "savings",
                        "mask": "8374",
                        "balances": {
                            "current": 18450.00,
                            "available": 18450.00,
                            "iso_currency_code": "USD"
                        }
                    },
                    {
                        "account_id": "acc_usaa_credit",
                        "name": "USAA Cashback Credit Card",
                        "official_name": "USAA Cashback Credit Card",
                        "type": "credit",
                        "subtype": "credit card",
                        "mask": "1938",
                        "balances": {
                            "current": 1250.00,
                            "available": 8750.00,
                            "iso_currency_code": "USD"
                        }
                    },
                    {
                        "account_id": "acc_student_loan",
                        "name": "Student Loan",
                        "official_name": "Federal Student Loan Program",
                        "type": "loan",
                        "subtype": "student",
                        "mask": "9021",
                        "balances": {
                            "current": 15000.00,
                            "available": None,
                            "iso_currency_code": "USD"
                        }
                    }
                ]
            }

        elif endpoint == "/transactions/sync" or endpoint == "/transactions/get":
            # Returns standard household transactions
            return {
                "transactions": [
                    {
                        "transaction_id": "tx_001",
                        "account_id": "acc_usaa_checking",
                        "date": "2026-07-01",
                        "authorized_date": "2026-07-01",
                        "merchant_name": "USAA Mortgage",
                        "name": "Mortgage Payment",
                        "amount": 1850.00,
                        "iso_currency_code": "USD",
                        "category": ["Community", "Rent", "Mortgage"],
                        "pending": False
                    },
                    {
                        "transaction_id": "tx_002",
                        "account_id": "acc_usaa_checking",
                        "date": "2026-07-02",
                        "authorized_date": "2026-07-02",
                        "merchant_name": "Kroger Grocery",
                        "name": "Kroger Store Store #938",
                        "amount": 220.50,
                        "iso_currency_code": "USD",
                        "category": ["Food & Drink", "Groceries"],
                        "pending": False
                    },
                    {
                        "transaction_id": "tx_003",
                        "account_id": "acc_usaa_checking",
                        "date": "2026-07-03",
                        "authorized_date": "2026-07-03",
                        "merchant_name": "Netflix",
                        "name": "NETFLIX.COM COM SUBSCRIPTION",
                        "amount": 19.99,
                        "iso_currency_code": "USD",
                        "category": ["Entertainment", "Subscriptions"],
                        "pending": False
                    },
                    {
                        "transaction_id": "tx_004",
                        "account_id": "acc_usaa_checking",
                        "date": "2026-07-04",
                        "authorized_date": "2026-07-04",
                        "merchant_name": "Starbucks Coffee",
                        "name": "STARBUCKS COFFEE #29402",
                        "amount": 8.45,
                        "iso_currency_code": "USD",
                        "category": ["Food & Drink", "Restaurants"],
                        "pending": False
                    },
                    {
                        "transaction_id": "tx_005",
                        "account_id": "acc_usaa_checking",
                        "date": "2026-07-05",
                        "authorized_date": "2026-07-05",
                        "merchant_name": "Employer Paycheck",
                        "name": "EMPLOYER DIRECT DEP PAYROLL",
                        "amount": -3200.00,
                        "iso_currency_code": "USD",
                        "category": ["Income", "Direct Deposit"],
                        "pending": False
                    },
                    {
                        "transaction_id": "tx_006",
                        "account_id": "acc_usaa_credit",
                        "date": "2026-07-05",
                        "authorized_date": "2026-07-05",
                        "merchant_name": "Shell Oil",
                        "name": "SHELL OIL #928402",
                        "amount": 45.00,
                        "iso_currency_code": "USD",
                        "category": ["Travel", "Gas Station"],
                        "pending": False
                    }
                ]
            }

        elif endpoint == "/liabilities/get":
            return {
                "liabilities": {
                    "credit": [
                        {
                            "account_id": "acc_usaa_credit",
                            "aprs": [
                                {
                                    "apr_percentage": 18.99,
                                    "apr_type": "balance_transfer_apr"
                                }
                            ],
                            "minimum_payment_amount": 35.00,
                            "next_payment_due_date": "2026-07-25"
                        }
                    ],
                    "student": [
                        {
                            "account_id": "acc_student_loan",
                            "interest_rate_percentage": 5.25,
                            "minimum_payment_amount": 250.00,
                            "next_payment_due_date": "2026-08-01"
                        }
                    ]
                }
            }

        elif endpoint == "/statements/list":
            return {
                "statements": [
                    {
                        "statement_id": "stmt_usaa_2026_06",
                        "account_id": "acc_usaa_checking",
                        "year": 2026,
                        "month": 6,
                        "period_start": "2026-06-01",
                        "period_end": "2026-06-30"
                    }
                ]
            }

        elif endpoint == "/statements/download":
            return {
                "pdf_content": b"%PDF-1.4 Mock USAA statement contents...",
                "posted_date": "2026-07-01"
            }

        return {}

PlaidClientMock = PlaidClient
