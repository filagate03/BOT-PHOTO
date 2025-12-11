from __future__ import annotations

import re
from dataclasses import dataclass

from aiogram import Router, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiocryptopay.exceptions import CryptoPayAPIError

from ..utils import get_crypto_pay_service, get_payments_repo, get_token_service, get_settings

router = Router(name="payment")


@dataclass(frozen=True)
class Package:
    code: str
    title: str
    photos: int
    tokens: int
    price_rub: int
    label: str
    highlight: bool = False
    bonus: str | None = None


PACKAGES: list[Package] = [
    Package("dose", "Тест-драйв", photos=1, tokens=5, price_rub=99, label="🍌", highlight=False),
    Package("sample", "Мини-сет", photos=3, tokens=15, price_rub=290, label="🥉", highlight=False),
    Package("ego", 'ХИТ: "Tinder King"', photos=15, tokens=75, price_rub=890, label="🥇", highlight=True),
    Package(
        "influencer",
        "Блогер",
        photos=50,
        tokens=250,
        price_rub=1990,
        label="💎",
        bonus="Приоритетная генерация (без очереди)",
    ),
    Package(
        "godmode",
        "Бог Контента",
        photos=150,
        tokens=750,
        price_rub=4990,
        label="👑",
        bonus="Промты + личная консультация 5 минут",
    ),
]


def _format_package(pkg: Package) -> str:
    base = f"{pkg.label} {pkg.title} — {pkg.photos} фото ({pkg.tokens} токенов) — {pkg.price_rub}₽"
    if pkg.highlight:
        base = f"<b>{base}</b> 🔥"
    if pkg.bonus:
        base += f"\n• {pkg.bonus}"
    return base


def _packages_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=f"{pkg.label} {pkg.title} — {pkg.photos} фото — {pkg.price_rub}₽",
                callback_data=f"payment:pkg:{pkg.code}",
            )
        ]
        for pkg in PACKAGES
    ]
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="menu:profile")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.callback_query(lambda c: c.data == "payment:sbp")
async def payment_sbp(callback: types.CallbackQuery) -> None:
    user_id = callback.from_user.id
    text_lines = ["<b>Оплата через СБП (Ozon Банк)</b>\n"]
    text_lines.append("Банк: Ozon Банк")
    text_lines.append("Номер: <code>+79102402003</code> (Guliya K.)\n")
    text_lines.append("1 фото = 5 токенов = 99₽. Выберите пакет и переведите сумму:")
    for pkg in PACKAGES:
        text_lines.append(f"• {pkg.title}: {pkg.price_rub}₽ ({pkg.photos} фото / {pkg.tokens} токенов)")
    text_lines.append("\nПосле перевода отправьте чек менеджеру: @hunt_tg")
    text_lines.append(f"Обязательно укажите свой ID: <code>{user_id}</code>")
    text_lines.append("Баланс пополним вручную после подтверждения.")

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="profile:topup")]]
    )
    await callback.message.edit_text("\n".join(text_lines), reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.callback_query(lambda c: c.data == "payment:crypto")
async def payment_crypto(callback: types.CallbackQuery) -> None:
    text = (
        "<b>Оплата через CryptoBot</b>\n\n"
        "Выберите пакет. Счёт будет в USDT (TestNet). После оплаты нажмите "
        "«Проверить оплату», чтобы начислить токены автоматически."
    )
    await callback.message.edit_text(text, reply_markup=_packages_keyboard(), parse_mode="HTML")
    await callback.answer()


def _get_package(code: str) -> Package | None:
    return next((p for p in PACKAGES if p.code == code), None)


def _tokens_from_payload(payload: str | None) -> int | None:
    if not payload:
        return None
    match = re.search(r"tokens:(\d+)", payload)
    if match:
        return int(match.group(1))
    return None


@router.callback_query(lambda c: c.data and c.data.startswith("payment:pkg:"))
async def payment_select_package(callback: types.CallbackQuery) -> None:
    code = callback.data.split(":")[2]
    pkg = _get_package(code)
    if not pkg:
        await callback.answer("Пакет не найден.", show_alert=True)
        return

    settings = get_settings(callback.message.bot)
    crypto_amount = round(pkg.price_rub / settings.crypto_rub_rate, 2)

    text = (
        f"{pkg.label} <b>{pkg.title}</b>\n"
        f"{pkg.photos} фото / {pkg.tokens} токенов\n"
        f"Цена: {pkg.price_rub}₽ (~{crypto_amount} USDT)\n\n"
        "Выберите способ оплаты:"
    )
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💳 СБП (Ozon Банк)", callback_data=f"payment:sbp")],
            [
                InlineKeyboardButton(
                    text=f"💠 CryptoBot (~{crypto_amount} USDT)", callback_data=f"payment:crypto:create:{code}"
                )
            ],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="payment:crypto")],
        ]
    )
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("payment:crypto:create:"))
async def payment_crypto_create(callback: types.CallbackQuery) -> None:
    code = callback.data.split(":")[3]
    pkg = _get_package(code)
    if not pkg:
        await callback.answer("Пакет не найден.", show_alert=True)
        return

    settings = get_settings(callback.message.bot)
    crypto_amount = round(pkg.price_rub / settings.crypto_rub_rate, 2)
    crypto_service = get_crypto_pay_service(callback.message.bot)
    payments_repo = get_payments_repo(callback.message.bot)

    try:
        payload = f"user:{callback.from_user.id}|tokens:{pkg.tokens}|pkg:{pkg.code}"
        invoice = await crypto_service.create_invoice(
            amount=crypto_amount,
            asset="USDT",
            description=f"{pkg.title}: {pkg.tokens} tokens for {callback.from_user.id}",
            payload=payload,
        )

        await payments_repo.save_invoice(
            invoice_id=invoice.invoice_id,
            user_id=callback.from_user.id,
            amount_usdt=float(invoice.amount),
            tokens=pkg.tokens,
            status=str(invoice.status),
            invoice_url=invoice.bot_invoice_url,
            payload=invoice.payload,
            paid_at=invoice.paid_at,
        )

        text = (
            f"{pkg.label} <b>{pkg.title}</b>\n"
            f"{pkg.photos} фото / {pkg.tokens} токенов\n"
            f"Сумма: {invoice.amount} USDT\n\n"
            "Оплатите счёт и нажмите «Проверить оплату», чтобы зачислить токены."
        )
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="💳 Оплатить", url=invoice.bot_invoice_url)],
                [
                    InlineKeyboardButton(
                        text="🔄 Проверить оплату", callback_data=f"payment:check:{invoice.invoice_id}"
                    )
                ],
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="payment:crypto")],
            ]
        )
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer()
    except CryptoPayAPIError as exc:
        await callback.answer(f"Ошибка CryptoBot: {exc}", show_alert=True)
    except Exception as exc:
        await callback.answer(f"Не удалось создать счёт: {exc}", show_alert=True)


@router.callback_query(lambda c: c.data and c.data.startswith("payment:check:"))
async def payment_check(callback: types.CallbackQuery) -> None:
    invoice_id = int(callback.data.split(":")[2])
    crypto_service = get_crypto_pay_service(callback.message.bot)
    payments_repo = get_payments_repo(callback.message.bot)
    token_service = get_token_service(callback.message.bot)

    try:
        invoice = await crypto_service.get_invoice(invoice_id)
        if not invoice:
            await callback.answer("Счёт не найден.", show_alert=True)
            return

        payment = await payments_repo.get(invoice_id)
        tokens = payment.tokens if payment else None
        if tokens is None:
            tokens = _tokens_from_payload(invoice.payload)
        if tokens is None:
            await callback.answer("Не удалось определить пакет. Напишите в поддержку.", show_alert=True)
            return

        await payments_repo.save_invoice(
            invoice_id=invoice.invoice_id,
            user_id=callback.from_user.id,
            amount_usdt=float(invoice.amount),
            tokens=tokens,
            status=str(invoice.status),
            invoice_url=invoice.bot_invoice_url,
            payload=invoice.payload,
            paid_at=invoice.paid_at,
        )

        status = str(invoice.status).lower()
        if status == "paid":
            already_credited = payment.status == "credited" if payment else False
            if not already_credited:
                new_balance = await token_service.add(callback.from_user.id, tokens)
                updated = await payments_repo.mark_credited(invoice_id)
                credited_tokens = updated.tokens if updated else tokens
                text = (
                    "<b>Оплата прошла ✅</b>\n\n"
                    f"Зачислено: {credited_tokens} токенов\n"
                    f"Баланс: {new_balance} токенов"
                )
            else:
                balance = await token_service.balance(callback.from_user.id)
                text = (
                    "<b>Оплата уже зачислена</b>\n\n"
                    f"Баланс: {balance} токенов"
                )

            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="⬅️ В профиль", callback_data="menu:profile")],
                    [InlineKeyboardButton(text="🏠 В меню", callback_data="menu:home")],
                ]
            )
            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
            await callback.answer()
        else:
            await callback.answer(f"Статус счёта: {invoice.status}", show_alert=True)
    except Exception as exc:
        await callback.answer(f"Ошибка при проверке оплаты: {exc}", show_alert=True)
