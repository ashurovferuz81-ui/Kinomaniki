import asyncio
import sqlite3
import random
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# --- SOZLAMALAR ---
TOKEN = "8509571152:AAFw5GXdZRyuiqTOzm3znlQCa_S4JQXcnvU"
ADMIN_ID = 5775388579
ADMIN_USERNAME = "@Sardorbeko008"

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

class GenState(StatesGroup):
    waiting_for_prompt = State()

# --- BAZA FUNKSIYALARI ---
def update_db(query, params=()):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute(query, params)
    conn.commit()
    conn.close()

def get_db(query, params=()):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute(query, params)
    res = cursor.fetchone()
    conn.close()
    return res

# --- KLAVIATURA ---
def main_menu(uid):
    kb = [[KeyboardButton(text="🎨 Rasm chizish")], [KeyboardButton(text="📊 Limitim")]]
    if uid == ADMIN_ID:
        kb.append([KeyboardButton(text="⚙️ Admin Panel")])
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

# --- HANDLERLAR ---
@dp.message(Command("start"))
async def start(message: types.Message):
    conn = sqlite3.connect("users.db")
    conn.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, limit_count INTEGER DEFAULT 2)")
    conn.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
    conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('card', '8600000000000000')")
    conn.commit()
    conn.close()
    
    update_db("INSERT OR IGNORE INTO users (id) VALUES (?)", (message.from_user.id,))
    await message.answer("Xush kelibsiz! Men AI rasm chizuvchi botman. 🎨", reply_markup=main_menu(message.from_user.id))

@dp.message(F.text == "📊 Limitim")
async def my_limit(message: types.Message):
    user = get_db("SELECT limit_count FROM users WHERE id=?", (message.from_user.id,))
    await message.answer(f"Sizning qolgan limitingiz: {user[0]} ta rasm.")

@dp.message(F.text == "🎨 Rasm chizish")
async def draw_request(message: types.Message, state: FSMContext):
    user = get_db("SELECT limit_count FROM users WHERE id=?", (message.from_user.id,))
    if user[0] <= 0:
        card = get_db("SELECT value FROM settings WHERE key='card'")[0]
        btn = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="💎 Premium olish", callback_data="buy")]])
        return await message.answer(f"Limitingiz tugadi. ❌\n\nTo'lov uchun karta: `{card}`\nSkrinshotni {ADMIN_USERNAME} ga tashlang.", reply_markup=btn, parse_mode="Markdown")
    
    await message.answer("📝 Rasm tavsifini yozing (Ingliz tilida):")
    await state.set_state(GenState.waiting_for_prompt)

@dp.message(GenState.waiting_for_prompt)
async def generate_image(message: types.Message, state: FSMContext):
    prompt = message.text
    # Admin tugmalarini yozib yuborsa to'xtatish
    if prompt in ["🎨 Rasm chizish", "📊 Limitim", "⚙️ Admin Panel"]:
        await state.clear()
        return

    wait = await message.answer("Chizyapman, iltimos kuting... ⏳")
    
    # Tasodifiy son qo'shish (har safar har xil rasm chiqishi uchun)
    seed = random.randint(1, 999999)
    # Pollinations API-ga promptni to'g'ri yuborish
    img_url = f"https://pollinations.ai/p/{prompt.replace(' ', '%20')}?width=1024&height=1024&seed={seed}&model=flux"

    try:
        await bot.send_photo(message.chat.id, photo=img_url, caption=f"✅ Natija: {prompt}\nLimit: -1")
        update_db("UPDATE users SET limit_count = limit_count - 1 WHERE id=?", (message.from_user.id,))
        await wait.delete()
    except Exception as e:
        await wait.edit_text(f"❌ Xatolik yuz berdi. Boshqa so'z yozib ko'ring.")
    
    await state.clear()

@dp.callback_query(F.data == "buy")
async def buy_alert(call: types.CallbackQuery):
    await call.answer("To'lovdan so'ng adminga skrinshot yuboring!", show_alert=True)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
