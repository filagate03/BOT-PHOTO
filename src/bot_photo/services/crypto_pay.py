from __future__ import annotations

from aiocryptopay import AioCryptoPay, Networks
from aiocryptopay.models.invoice import Invoice


class CryptoPayService:
    def __init__(self, token: str, network: str = "TEST_NET") -> None:
        resolved_network = Networks.TEST_NET
        try:
            resolved_network = Networks[network] if isinstance(network, str) else network
        except Exception:
            resolved_network = Networks.TEST_NET
        self._client = AioCryptoPay(token=token, network=resolved_network)

    async def create_invoice(
        self,
        amount: float,
        asset: str = "USDT",
        description: str | None = None,
        payload: str | None = None,
    ) -> Invoice:
        """
        Create a new invoice.
        :param amount: Amount of the invoice.
        :param currency_type: 'crypto' or 'fiat'.
        :param asset: Asset code (e.g. 'USDT', 'TON', 'USD', 'EUR').
        :param description: Description of the invoice.
        """
        return await self._client.create_invoice(
            amount=amount,
            asset=asset,
            description=description,
            payload=payload,
        )

    async def get_invoice(self, invoice_id: int) -> Invoice | None:
        invoices = await self._client.get_invoices(invoice_ids=[invoice_id])
        return invoices[0] if invoices else None

    async def get_invoices(self, invoice_ids: list[int]) -> list[Invoice]:
        return await self._client.get_invoices(invoice_ids=invoice_ids)

    async def close(self) -> None:
        await self._client.close()
