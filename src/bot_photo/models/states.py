from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class AdminState(StatesGroup):
    token_input_user_id = State()
    token_input_amount = State()
    admin_input_user_id = State()


class AgreementState(StatesGroup):
    awaiting_agreement = State()


class PhotoSessionState(StatesGroup):
    choosing_style = State()
    choosing_orientation = State()
    waiting_face = State()
    waiting_prompt = State()
    processing = State()


class PromptState(StatesGroup):
    waiting_face = State()
    waiting_text = State()
    processing = State()
