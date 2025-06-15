# third-party
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.filters.base import Filter


class UserStates(StatesGroup):
    """
    Overall user states #?
    """

    choosing_entry = State()  # user is using /entries command to choose an entry.


class SettingsInputStates(StatesGroup):
    "User states used in /settings."

    waiting_interval = State()
    waiting_dnd = State()  # waiting DoNotDisturb
    waiting_tmz = State()
    waiting_lang = State()
    waiting_cr = State()  # custom reminders
    waiting_mm = State()  # morning message
    waiting_es = State()  # evening summary

    tmz_setup = State()  # when the user is setting up their TMZ for the first time.


class InSettingsInputStates(Filter):
    async def __call__(self, message: Message, state: FSMContext):
        curr = await state.get_state()
        return curr is not None and curr.startswith("SettingsInputStates:")
