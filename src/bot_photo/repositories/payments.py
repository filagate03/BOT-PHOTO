from __future__ import annotations

from datetime import datetime
from typing import Any

from .base import BaseRepository
from ..models import Payment


class PaymentRepository(BaseRepository):
    async def save_invoice(
        self,
        *,
        invoice_id: int,
        user_id: int,
        amount_usdt: float,
        tokens: int,
        status: str,
        invoice_url: str | None = None,
        payload: str | None = None,
        paid_at: datetime | None = None,
    ) -> Payment:
        paid_at_str = paid_at.isoformat() if isinstance(paid_at, datetime) else paid_at
        await self.db.execute(
            """
            INSERT INTO payments(invoice_id, user_id, amount_usdt, tokens, status, invoice_url, payload, paid_at)
            VALUES(?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(invoice_id) DO UPDATE SET
                status=excluded.status,
                invoice_url=COALESCE(excluded.invoice_url, payments.invoice_url),
                payload=COALESCE(excluded.payload, payments.payload),
                paid_at=COALESCE(excluded.paid_at, payments.paid_at)
            """,
            (invoice_id, user_id, amount_usdt, tokens, status, invoice_url, payload, paid_at_str),
        )
        payment = await self.get(invoice_id)
        if not payment:
            raise RuntimeError("Failed to persist payment")
        return payment

    async def mark_credited(self, invoice_id: int) -> Payment | None:
        await self.db.execute(
            """
            UPDATE payments
            SET status='credited',
                paid_at=COALESCE(paid_at, CURRENT_TIMESTAMP),
                credited_at=CURRENT_TIMESTAMP
            WHERE invoice_id=?
            """,
            (invoice_id,),
        )
        return await self.get(invoice_id)

    async def get(self, invoice_id: int) -> Payment | None:
        row = await self.db.fetchone("SELECT * FROM payments WHERE invoice_id=?", (invoice_id,))
        return self._row_to_payment(row) if row else None

    def _row_to_payment(self, row: dict[str, Any]) -> Payment:
        return Payment(
            invoice_id=row["invoice_id"],
            user_id=row["user_id"],
            amount_usdt=row["amount_usdt"],
            tokens=row["tokens"],
            status=row["status"],
            invoice_url=row.get("invoice_url"),
            payload=row.get("payload"),
            created_at=self._parse_datetime(row.get("created_at")),
            paid_at=self._parse_datetime(row.get("paid_at")),
            credited_at=self._parse_datetime(row.get("credited_at")),
        )

    @staticmethod
    def _parse_datetime(value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None


__all__ = ["PaymentRepository"]
