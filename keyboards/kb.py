# third-party
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from util.constants import TIMEZONES


# local
# from handlers.settings import TIMEZONES

def build_and_adjust(markup: InlineKeyboardMarkup, adjust=tuple) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder().from_markup(markup).adjust(*adjust)
    return builder.as_markup()


settings_kb = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text="interval", callback_data='set:int'),
        InlineKeyboardButton(text="do not disturb hours",
                             callback_data='set:dnd'),
        InlineKeyboardButton(text="language", callback_data='set:lang'),
        InlineKeyboardButton(text='Timezone', callback_data='set:tmz')
    ]
])
settings_firsttime_kb = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text='Timezone', callback_data='set:tmz')
    ]
])

timezones_kb = InlineKeyboardMarkup(inline_keyboard=[*[[InlineKeyboardButton(
    text=name.upper(), callback_data=f"{name}:{offset}") for name, offset in TIMEZONES]]])
# settings_kb_builder = InlineKeyboardBuilder().from_markup(settings_kb).adjust(3, 2)
# damn
# inline keyboards
# timezones_kb_builder = InlineKeyboardBuilder().from_markup(timezones_kb).adjust(2, 2)
# timezones_kb_builder.adjust(3, 2)
