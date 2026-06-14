"""Tap Payments API client for ClearJournal billing."""
import hashlib
import logging
from decimal import Decimal
from typing import Optional, Dict, Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

TAP_BASE_URL = "https://api.tap.company/v2"


class TapClient:
    """Client for Tap Payments API."""

    def __init__(self):
        self._api_key: Optional[str] = None

    @property
    def api_key(self) -> str:
        if self._api_key is None:
            self._api_key = settings.TAP_API_KEY
        return self._api_key

    @property
    def is_sandbox(self) -> bool:
        return "sk_test" in self.api_key

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    # ── Charge API ────────────────────────────────────────────────────────────

    def create_charge(
        self,
        amount: Decimal,
        currency: str,
        customer_email: str,
        customer_name: str,
        customer_phone: Optional[str] = None,
        source_id: str = "src_all",
        redirect_url: Optional[str] = None,
        webhook_url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        lang_code: str = "en",
    ) -> Dict[str, Any]:
        """Create a Tap charge (hosted checkout)."""
        payload: Dict[str, Any] = {
            "amount": float(amount),
            "currency": currency,
            "customer_initiated": True,
            "threeDSecure": True,
            "save_card": False,
            "customer": {
                "first_name": customer_name.split(" ")[0],
                "last_name": " ".join(customer_name.split(" ")[1:]) or customer_name.split(" ")[0],
                "email": customer_email,
            },
            "source": {"id": source_id},
            "redirect": {"url": redirect_url or ""},
            "lang_code": lang_code,
        }

        if customer_phone:
            payload["customer"]["phone"] = {
                "country_code": customer_phone[:4],
                "number": customer_phone[4:],
            }

        if webhook_url:
            payload["post"] = {"url": webhook_url}

        if metadata:
            payload["metadata"] = metadata

        with httpx.Client(timeout=30.0) as client:
            resp = client.post(
                f"{TAP_BASE_URL}/charges/",
                json=payload,
                headers=self._headers(),
            )
            resp.raise_for_status()
            return resp.json()

    def get_charge(self, charge_id: str) -> Dict[str, Any]:
        """Get charge details by ID."""
        with httpx.Client(timeout=30.0) as client:
            resp = client.get(
                f"{TAP_BASE_URL}/charges/{charge_id}",
                headers=self._headers(),
            )
            resp.raise_for_status()
            return resp.json()

    # ── Refund API ────────────────────────────────────────────────────────────

    def create_refund(
        self, charge_id: str, amount: Optional[Decimal] = None
    ) -> Dict[str, Any]:
        """Create a refund for a charge."""
        payload: Dict[str, Any] = {"charge_id": charge_id}
        if amount is not None:
            payload["amount"] = float(amount)

        with httpx.Client(timeout=30.0) as client:
            resp = client.post(
                f"{TAP_BASE_URL}/refunds/",
                json=payload,
                headers=self._headers(),
            )
            resp.raise_for_status()
            return resp.json()

    # ── Webhook Verification ──────────────────────────────────────────────────

    def verify_webhook(self, body: bytes, received_hash: str) -> bool:
        """Verify a Tap webhook using hashstring header."""
        computed = hashlib.sha256(body + self.api_key.encode()).hexdigest()
        return hashlib.compare_digest(computed, received_hash)

    # ── Subscription Management ───────────────────────────────────────────────

    def cancel_subscription(self, subscription_id: str) -> Dict[str, Any]:
        """Cancel a recurring subscription at Tap."""
        with httpx.Client(timeout=30.0) as client:
            resp = client.put(
                f"{TAP_BASE_URL}/subscriptions/{subscription_id}/cancel",
                headers=self._headers(),
            )
            resp.raise_for_status()
            return resp.json()

    def reactivate_subscription(self, subscription_id: str) -> Dict[str, Any]:
        """Reactivate a canceled subscription."""
        with httpx.Client(timeout=30.0) as client:
            resp = client.put(
                f"{TAP_BASE_URL}/subscriptions/{subscription_id}/reactivate",
                headers=self._headers(),
            )
            resp.raise_for_status()
            return resp.json()


# Singleton instance
tap_client = TapClient()
