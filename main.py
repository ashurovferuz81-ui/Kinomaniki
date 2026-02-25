import sqlite3
import asyncio
import aiohttp
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

# --- SOZLAMALAR ---
BOT_TOKEN = '8509571152:AAFw5GXdZRyuiqTOzm3znlQCa_S4JQXcnvU'
VIDEO_API_KEY = '6b9295b31afbd00d31fe20a4cb9b6969' 
ADMIN_ID = 5775388579 
ADMIN_USERNAME = "@Sardorbeko008"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# --- MA'LUMOTLAR BAZASI ---
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

# --- HOLATLAR (STATES) ---
class AdminStates(StatesGroup):
    waiting_for_card = State()
    waiting_for_premium_id = State()

class UserStates(StatesGroup):
    waiting_for_prompt = State()

# --- KLAVIATURA ---
def get_main_kb(user_id):
    kb = [
        [KeyboardButton(text="🎥 Video yaratish")],
        [KeyboardButton(text="📊 Mening limitim")]
    ]
    if user_id == ADMIN_ID:
        kb.append([KeyboardButton(text="⚙️ Admin Panel")])
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

# --- BOT FUNKSIYALARI ---

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    db_query("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (message.from_user.id,))
    await message.answer(f"👋 Salom! Men Kling AI Video Generatorman.\nSizda 2 ta bepul video yaratish imkoniyati bor.", 
                         reply_markup=get_main_kb(message.from_user.id))

@dp.message(F.text == "📊 Mening limitim")
async def check_limit(message: types.Message):
    user = db_query("SELECT limit_count FROM users WHERE user_id=?", (message.from_user.id,), fetch=True)
    await message.answer(f"💎 Sizning qolgan limitingiz: **{user[0][0]} ta video**", parse_mode="Markdown")

@dp.message(F.text == "🎥 Video yaratish")
async def create_video_start(message: types.Message, state: FSMContext):
    user = db_query("SELECT limit_count FROM users WHERE user_id=?", (message.from_user.id,), fetch=True)
    if user[0][0] <= 0:
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="💎 Premium oling", callback_data="buy_premium")]])
        return await message.answer(f"⚠️ Limit tugadi! Premium paket oling.", reply_markup=kb)
    
    await message.answer("📝 Video uchun Ingliz tilida so'rov (prompt) yuboring:")
    await state.set_state(UserStates.waiting_for_prompt)

@dp.callback_query(F.data == "buy_premium")
async def show_payment(call: types.CallbackQuery):
    card = db_query("SELECT value FROM settings WHERE key='card'", fetch=True)[0][0]
    text = (f"💳 Karta: `{card}`\n\nSkrinshotni adminga yuboring: {ADMIN_USERNAME}\n"
            f"Paket: 30 ta video.")
    await call.message.answer(text, parse_mode="Markdown")
    await call.answer()

# --- KLING AI BILAN ISHLASH ---
@dp.message(UserStates.waiting_for_prompt)
async def process_video(message: types.Message, state: FSMContext):
    prompt = message.text
    status = await message.answer("🚀 Kling AI video generatsiya qilmoqda... Iltimos, 1-2 daqiqa kuting. ⏳")
    
    # Kling AI API sozlamalari (fal.ai orqali)
    url = "https://fal.run/fal-ai/kling-video/v1.5/standard/text-to-video"
    headers = {
        "Authorization": f"Key {VIDEO_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "prompt": prompt,
        "aspect_ratio": "16:9"
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    # Fal.ai natijani 'video' va 'url' ichida qaytaradi
                    video_url = data.get("video", {}).get("url")
                    
                    if video_url:
                        db_query("UPDATE users SET limit_count = limit_count - 1 WHERE user_id=?", (message.from_user.id,))
                        await bot.send_video(message.chat.id, video=video_url, caption=f"✅ Video tayyor!\nPrompt: {prompt}")
                        await status.delete()
                    else:
                        await status.edit_text("❌ API video tayyorladi, lekin manzilni bera olmadi.")
                else:
                    error_info = await response.text()
                    await status.edit_text(f"❌ API xatosi: {response.status}\nHisobingizda mablag' borligini tekshiring.")
                    print(f"Log: {error_info}")
    except Exception as e:
        await status.edit_text(f"⚠️ Xatolik yuz berdi: {str(e)}")
    
    await state.clear()

# --- ADMIN PANEL ---
@dp.message(F.text == "⚙️ Admin Panel", F.from_user.id == ADMIN_ID)
async def admin_menu(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💎 Premium berish", callback_data="give_premium")],
        [InlineKeyboardButton(text="💳 Karta o'zgartirish", callback_data="set_card")]
    ])
    await message.answer("🛠 Admin Paneli:", reply_markup=kb)

@dp.callback_query(F.data == "give_premium", F.from_user.id == ADMIN_ID)
async def give_premium_start(call: types.CallbackQuery, state: FSMContext):
    await call.message.answer("Foydalanuvchi ID raqamini yuboring:")
    await state.set_state(AdminStates.waiting_for_premium_id)

@dp.message(AdminStates.waiting_for_premium_id, F.from_user.id == ADMIN_ID)
async def process_give_premium(message: types.Message, state: FSMContext):
    try:
        uid = int(message.text)
        db_query("UPDATE users SET limit_count = 30 WHERE user_id=?", (uid,))
        await message.answer(f"✅ {uid} ga 30 ta limit berildi!")
        await bot.send_message(uid, "🎉 Premium paket faollashdi! 30 ta video yaratishingiz mumkin.")
    except:
        await message.answer("❌ Xato ID!")
    await state.clear()

@dp.callback_query(F.data == "set_card", F.from_user.id == ADMIN_ID)
async def set_card_step(call: types.CallbackQuery, state: FSMContext):
    await call.message.answer("Yangi karta raqamini yozing:")
    await state.set_state(AdminStates.waiting_for_card)

@dp.message(AdminStates.waiting_for_card, F.from_user.id == ADMIN_ID)
async def save_card(message: types.Message, state: FSMContext):
    db_query("UPDATE settings SET value=? WHERE key='card'", (message.text,))
    await message.answer(f"✅ Karta yangilandi: {message.text}")
    await state.clear()

async def main():
    init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
