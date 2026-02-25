import sqlite3
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

# --- SOZLAMALAR ---
BOT_TOKEN = '8509571152:AAFw5GXdZRyuiqTOzm3znlQCa_S4JQXcnvU'
ADMIN_ID = 5775388579 
ADMIN_USERNAME = "@Sardorbeko008"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# --- BAZA BILAN ISHLASH ---
def db_query(query, params=(), fetch=False):
    conn = sqlite3.connect("vigen_bot.db")
    cursor = conn.cursor()
    cursor.execute(query, params)
    res = cursor.fetchall() if fetch else None
    conn.commit()
    conn.close()
    return res

def init_db():
    db_query("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, limit_count INTEGER DEFAULT 2)")
    db_query("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
    db_query("INSERT OR IGNORE INTO settings (key, value) VALUES ('card', 'Hali kiritilmagan')")

# --- HOLATLAR ---
class AdminStates(StatesGroup):
    waiting_for_card = State()
    waiting_for_premium_id = State()

class UserStates(StatesGroup):
    waiting_for_prompt = State()

# --- KLAVIATURALAR ---
def get_main_kb(user_id):
    kb = [[KeyboardButton(text="🎥 Video yaratish")]]
    kb.append([KeyboardButton(text="📊 Mening limitim")])
    if user_id == ADMIN_ID:
        kb.append([KeyboardButton(text="⚙️ Admin Panel")])
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def premium_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💎 Premium oling", callback_data="buy_premium")]
    ])

# --- HANDLERLAR ---

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    db_query("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (message.from_user.id,))
    await message.answer(f"Xush kelibsiz! Bot orqali video generatsiya qilishingiz mumkin.\nSizda 2 ta bepul limit bor.", 
                         reply_markup=get_main_kb(message.from_user.id))

@dp.message(F.text == "📊 Mening limitim")
async def check_limit(message: types.Message):
    user = db_query("SELECT limit_count FROM users WHERE user_id=?", (message.from_user.id,), fetch=True)
    await message.answer(f"Sizning joriy limitingiz: **{user[0][0]} ta video**", parse_mode="Markdown")

@dp.message(F.text == "🎥 Video yaratish")
async def create_video_start(message: types.Message, state: FSMContext):
    user = db_query("SELECT limit_count FROM users WHERE user_id=?", (message.from_user.id,), fetch=True)
    if user[0][0] <= 0:
        return await message.answer("⚠️ Bepul limitlaringiz tugadi! Davom etish uchun Premium sotib oling.", 
                                   reply_markup=premium_kb())
    
    await message.answer("Videoni tasvirlab bering (Ingliz tilida):")
    await state.set_state(UserStates.waiting_for_prompt)

@dp.callback_query(F.data == "buy_premium")
async def show_payment(call: types.CallbackQuery):
    card = db_query("SELECT value FROM settings WHERE key='card'", fetch=True)[0][0]
    text = (f"💎 **Premium Paket (30 ta video)**\n\n"
            f"To'lov uchun karta: `{card}`\n\n"
            f"To'lovni amalga oshirgach, skrinshotni adminga yuboring:\n"
            f"👤 Admin: {ADMIN_USERNAME}\n\n"
            f"Admin to'lovni tekshirib, sizga 30 ta limit qo'shib beradi.")
    await call.message.answer(text, parse_mode="Markdown")
    await call.answer()

# --- ADMIN PANEL MANTIQI ---
@dp.message(F.text == "⚙️ Admin Panel", F.from_user.id == ADMIN_ID)
async def admin_menu(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💎 Premium berish (ID orqali)", callback_data="give_premium")],
        [InlineKeyboardButton(text="💳 Karta raqamini o'zgartirish", callback_data="set_card")],
        [InlineKeyboardButton(text="📊 Foydalanuvchilar soni", callback_data="stats")]
    ])
    await message.answer("🛠 Admin boshqaruv paneli:", reply_markup=kb)

@dp.callback_query(F.data == "give_premium", F.from_user.id == ADMIN_ID)
async def give_premium_start(call: types.CallbackQuery, state: FSMContext):
    await call.message.answer("Premium beriladigan foydalanuvchi ID-sini yuboring:")
    await state.set_state(AdminStates.waiting_for_premium_id)

@dp.message(AdminStates.waiting_for_premium_id, F.from_user.id == ADMIN_ID)
async def process_give_premium(message: types.Message, state: FSMContext):
    try:
        user_id = int(message.text)
        db_query("UPDATE users SET limit_count = 30 WHERE user_id=?", (user_id,))
        await message.answer(f"✅ Foydalanuvchi {user_id} ga 30 ta premium limit berildi!")
        try:
            await bot.send_message(user_id, "🎉 Tabriklaymiz! Admin sizga 30 ta premium limit taqdim etdi. Endi bemalol video yaratishingiz mumkin!")
        except: pass
    except ValueError:
        await message.answer("❌ Xato! Faqat raqamlardan iborat ID yuboring.")
    await state.clear()

@dp.callback_query(F.data == "set_card", F.from_user.id == ADMIN_ID)
async def set_card_step(call: types.CallbackQuery, state: FSMContext):
    await call.message.answer("Yangi karta raqamini kiriting:")
    await state.set_state(AdminStates.waiting_for_card)

@dp.message(AdminStates.waiting_for_card, F.from_user.id == ADMIN_ID)
async def save_card(message: types.Message, state: FSMContext):
    db_query("UPDATE settings SET value=? WHERE key='card'", (message.text,))
    await message.answer(f"✅ Karta saqlandi: {message.text}")
    await state.clear()

@dp.callback_query(F.data == "stats", F.from_user.id == ADMIN_ID)
async def show_stats(call: types.CallbackQuery):
    count = db_query("SELECT COUNT(*) FROM users", fetch=True)[0][0]
    await call.message.answer(f"📊 Jami foydalanuvchilar: {count} ta")

async def main():
    init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
