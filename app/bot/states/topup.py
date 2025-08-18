from aiogram.fsm.state import State, StatesGroup

class TopupFlow(StatesGroup):
    waiting_syp_amount = State()
    waiting_syriatel_txid = State()
    waiting_usdt_amount = State()
    waiting_usdt_txid = State()
