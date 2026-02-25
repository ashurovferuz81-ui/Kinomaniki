import asyncio
import sqlite3
import random
import aiohttp
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# --- ASOSIY SOZLAMALAR ---
TOKEN = "8509571152:AAFw5GXdZRyuiqTOzm3znlQCa_S4JQXcnvU"
# Siz yuborgan API kalitni shu yerga o'rnatdim
POLLINATIONS_API_KEY = "Sk_1GPzbkNH2oMLcTB4BUORtGLhX1qqUQWb"
ADMIN_ID = 5775388579
ADMIN_USERNAME = "@Sardorbeko008"

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

class GenState(StatesGroup):
    waiting_for_prompt = State()

# --- MA'LUMOTLAR BAZASI ---
def init_db():
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, limit_count INTEGER DEFAULT 2)")
    cursor.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('card', '8600000000000000')")
    conn.commit()
    conn.close()

def db_action(query, params=()):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute(query, params)
    res = cursor.fetchone() if "SELECT" in query else None
    conn.commit()
    conn.close()
    return res

# --- MENYU ---
def main_menu(uid):
    buttons = [[KeyboardButton(text="🎨 Rasm chizish")], [KeyboardButton(text="📊 Limitim")]]
    if uid == ADMIN_ID:
        buttons.append([KeyboardButton(text="⚙️ Admin Panel")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

# --- BOT FUNKSIYALARI ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    init_db()
    db_action("INSERT OR IGNORE INTO users (id) VALUES (?)", (message.from_user.id,))
    await message.answer(
        "Xush kelibsiz! Men professional AI rasm generatoriman. 🎨\n"
        "Xohlagan narsangizni yozing, men uni rasmga aylantiraman.",
        reply_markup=main_menu(message.from_user.id)
    )

@dp.message(F.text == "📊 Limitim")
async def check_limit(message: types.Message):
    user = db_action("SELECT limit_count FROM users WHERE id=?", (message.from_user.id,))
    await message.answer(f"Sizda {user[0]} ta bepul rasm yaratish imkoniyati qoldi.")

@dp.message(F.text == "🎨 Rasm chizish")
async def start_gen(message: types.Message, state: FSMContext):
    user = db_action("SELECT limit_count FROM users WHERE id=?", (message.from_user.id,))
    if user and user[0] <= 0:
        card = db_action("SELECT value FROM settings WHERE key='card'")[0]
        btn = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="💎 Premium limit olish", callback_data="buy")]])
        return await message.answer(f"Limitingiz tugadi! ❌\n\nLimitni to'ldirish uchun adminga murojaat qiling.\nKarta: `{card}`", reply_markup=btn, parse_mode="Markdown")
    
    await message.answer("📝 Rasm tavsifini yozing (Inglizcha, masalan: 'A golden dragon in the sky'):")
    await state.set_state(GenState.waiting_for_prompt)

@dp.message(GenState.waiting_for_prompt)
async def process_generation(message: types.Message, state: FSMContext):
    prompt = message.text
    if prompt in ["🎨 Rasm chizish", "📊 Limitim"]:
        await state.clear()
        return

    wait = await message.answer("AI o'ylamoqda va chizmoqda... ⏳")
    
    # Rasm generatsiyasi (Pollinations API orqali)
    seed = random.randint(1, 1000000)
    # Flux modelini ishlatamiz, bu eng yuqori sifat beradi
    img_url = f"https://pollinations.ai/p/{prompt.replace(' ', '%20')}?width=1024&height=1024&seed={seed}&model=flux&nologo=true"
    
    # API keyni headers orqali yuboramiz (agar kerak bo'lsa)
    headers = {"Authorization": f"Bearer {POLLINATIONS_API_KEY}"}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(img_url, headers=headers) as resp:
                if resp.status == 200:
                    await bot.send_photo(
                        message.chat.id, 
                        photo=img_url, 
                        caption=f"✅ Tayyor!\nPrompt: {prompt}\nLimit: -1"
                    )
                    db_action("UPDATE users SET limit_count = limit_count - 1 WHERE id=?", (message.from_user.id,))
                    await wait.delete()
                else:
                    await wait.edit_text("❌ Hozirda serverda yuklama ko'p. Birozdan so'ng urinib ko'ring.")
    except Exception:
        await wait.edit_text("❌ Rasm yaratishda xatolik yuz berdi.")
    
    await state.clear()

@dp.callback_query(F.data == "buy")
async def buy_callback(call: types.CallbackQuery):
    await call.answer("To'lov qilib, adminga skrinshot yuboring!", show_alert=True)

async def main():
    init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
