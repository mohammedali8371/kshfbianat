import os
import json
import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from dotenv import load_dotenv

# تحميل المتغيرات البيئية
load_dotenv()

# ========== الإعدادات الأساسية ==========
TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
DEVELOPER_ID = int(os.getenv("DEVELOPER_ID", "0"))

if not TOKEN or not WEBHOOK_URL or DEVELOPER_ID == 0:
    raise ValueError("❌ يرجى تعيين BOT_TOKEN و WEBHOOK_URL و DEVELOPER_ID في متغيرات البيئة")

USER_FILE = "users.json"
logging.basicConfig(level=logging.INFO)

# ========== إدارة المستخدمين ==========
def load_users():
    if os.path.exists(USER_FILE):
        with open(USER_FILE) as f:
            return set(json.load(f))
    return set()

def save_users(users):
    with open(USER_FILE, "w") as f:
        json.dump(list(users), f)

users = load_users()
blocked = set()

# ========== دوال OSINT الأساسية ==========
def phone_lookup(phone):
    """
    بحث عن رقم هاتف باستخدام API مجاني (Veriphone)
    """
    try:
        url = f"https://api.veriphone.io/v2/verify?phone={phone}&key=DEMO&default_country=YE"
        response = requests.get(url, timeout=10)
        data = response.json()
        if data.get("status") == "success":
            return {
                "country": data.get("country_name", "غير معروف"),
                "country_code": data.get("country_code", "غير معروف"),
                "carrier": data.get("carrier", "غير معروف"),
                "valid": "✅ صالح" if data.get("valid") else "❌ غير صالح",
                "number": data.get("phone", phone)
            }
        else:
            return {"error": "لم يتم العثور على معلومات"}
    except Exception as e:
        return {"error": f"خطأ في الاتصال: {e}"}

def username_search(username):
    """
    البحث عن اسم مستخدم عبر منصات التواصل (باستخدام Sherlock API)
    """
    try:
        url = f"https://api.sherlock.project/api/v1/search?username={username}"
        response = requests.get(url, timeout=15)
        data = response.json()
        results = []
        for site, info in data.items():
            if info.get("exists"):
                results.append(f"✅ {site}: {info.get('url')}")
        if results:
            return "\n".join(results[:10])  # عرض أول 10 نتائج
        else:
            return "❌ لم يتم العثور على حسابات بهذا الاسم"
    except Exception as e:
        return f"❌ خطأ في البحث: {e}"

# ========== دوال البوت ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    users.add(uid)
    save_users(users)
    context.user_data.clear()

    keyboard = [
        [InlineKeyboardButton("🇾🇪 معلومات عن اليمن", callback_data="yemen_info")],
        [InlineKeyboardButton("📞 بحث برقم هاتف", callback_data="phone_lookup")],
        [InlineKeyboardButton("🔍 بحث باسم مستخدم", callback_data="username_search")],
        [InlineKeyboardButton("❓ المساعدة", callback_data="help")]
    ]
    if uid == DEVELOPER_ID:
        keyboard.append([InlineKeyboardButton("🔧 لوحة المطور", callback_data="admin_panel")])

    await update.message.reply_text(
        "👋 أهلاً بك في **بوت OSINT اليمن**!\n\n"
        "🇾🇪 اختر خدمة من الأزرار أدناه:\n"
        "• معلومات عن اليمن\n"
        "• بحث برقم هاتف (يدعم +967)\n"
        "• بحث باسم مستخدم (عبر منصات التواصل)\n"
        "• مساعدة",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def yemen_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    info = (
        "🇾🇪 **معلومات عن اليمن**\n\n"
        "• **العاصمة**: صنعاء\n"
        "• **العملة**: ريال يمني\n"
        "• **اللغة**: العربية\n"
        "• **رمز الهاتف الدولي**: +967\n"
        "• **المساحة**: 527,970 كم²\n"
        "• **عدد السكان**: ~30 مليون\n\n"
        "📞 **للتحقق من رقم يمني:**\n"
        "أرسل الرقم بصيغة: `+967XXXXXXXXX`"
    )
    await query.edit_message_text(info, parse_mode="Markdown")

async def phone_lookup_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["mode"] = "phone"
    await query.edit_message_text("📞 أرسل رقم الهاتف بصيغة دولية (مثال: `+967XXXXXXXXX`)")

async def username_search_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["mode"] = "username"
    await query.edit_message_text("🔍 أرسل اسم المستخدم الذي تريد البحث عنه (مثال: `example_user`)")

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != DEVELOPER_ID:
        await update.message.reply_text("⛔ هذا الأمر للمطور فقط.")
        return

    keyboard = [
        [InlineKeyboardButton("📢 إذاعة", callback_data="broadcast")],
        [InlineKeyboardButton("👥 قائمة المستخدمين", callback_data="list_users")],
        [InlineKeyboardButton("🚫 حظر", callback_data="block_user")],
        [InlineKeyboardButton("✅ فك حظر", callback_data="unblock_user")],
        [InlineKeyboardButton("✉️ مراسلة", callback_data="msg_user")],
        [InlineKeyboardButton("🔍 مراقبة", callback_data="toggle_monitor")]
    ]
    await update.message.reply_text("🛠️ لوحة تحكم المطور:", reply_markup=InlineKeyboardMarkup(keyboard))

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = update.effective_user.id
    data = query.data

    if data == "yemen_info":
        await yemen_info(update, context)
    elif data == "phone_lookup":
        await phone_lookup_start(update, context)
    elif data == "username_search":
        await username_search_start(update, context)
    elif data == "help":
        await query.edit_message_text(
            "📖 **طريقة الاستخدام:**\n\n"
            "• **بحث برقم هاتف**: أرسل الرقم بصيغة دولية (مثال: +967XXXXXXXXX)\n"
            "• **بحث باسم مستخدم**: أرسل الاسم (مثال: example_user)\n"
            "• **معلومات اليمن**: تعرض معلومات عامة عن البلد\n\n"
            "🔹 المطور: @xxxpx1"
        )
    elif uid != DEVELOPER_ID:
        await query.edit_message_text("⛔ هذا الزر للمطور فقط.")
    else:
        context.user_data["admin_action"] = data
        await query.edit_message_text(f"📝 اخترت {data}. أرسل التفاصيل.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = update.message.text

    # مراقبة المطور
    if context.bot_data.get("monitor", False) and uid != DEVELOPER_ID:
        try:
            await context.bot.forward_message(
                chat_id=DEVELOPER_ID,
                from_chat_id=update.effective_chat.id,
                message_id=update.message.message_id
            )
        except:
            pass

    # أوامر المطور
    if uid == DEVELOPER_ID and "admin_action" in context.user_data:
        action = context.user_data.pop("admin_action")
        if action == "broadcast":
            for u in users:
                try:
                    await context.bot.send_message(u, f"📢 {text}")
                except:
                    pass
            await update.message.reply_text("✅ تم الإرسال")
        elif action == "block":
            try:
                blocked.add(int(text))
                await update.message.reply_text(f"🚫 تم حظر {text}")
            except:
                await update.message.reply_text("❌ معرف غير صالح")
        elif action == "unblock":
            try:
                blocked.discard(int(text))
                await update.message.reply_text(f"✅ تم فك الحظر عن {text}")
            except:
                await update.message.reply_text("❌ معرف غير صالح")
        elif action == "msg":
            parts = text.split(maxsplit=1)
            if len(parts) == 2:
                try:
                    await context.bot.send_message(int(parts[0]), f"📨 {parts[1]}")
                    await update.message.reply_text("✅ تم الإرسال")
                except Exception as e:
                    await update.message.reply_text(f"❌ فشل: {e}")
            else:
                await update.message.reply_text("❌ الصيغة: المعرف الرسالة")
        return

    # حظر
    if uid in blocked:
        await update.message.reply_text("🚫 أنت محظور.")
        return

    # ===== أوامر OSINT =====
    mode = context.user_data.get("mode")

    if mode == "phone":
        # بحث برقم هاتف
        result = phone_lookup(text)
        if result.get("error"):
            await update.message.reply_text(f"❌ {result['error']}")
        else:
            reply = (
                f"📞 **نتيجة البحث عن الرقم:**\n\n"
                f"• الرقم: {result.get('number')}\n"
                f"• الدولة: {result.get('country')}\n"
                f"• رمز الدولة: {result.get('country_code')}\n"
                f"• مقدم الخدمة: {result.get('carrier')}\n"
                f"• الحالة: {result.get('valid')}"
            )
            await update.message.reply_text(reply, parse_mode="Markdown")
        context.user_data.pop("mode", None)

    elif mode == "username":
        # بحث باسم مستخدم
        await update.message.reply_text("⏳ جاري البحث ...")
        result = username_search(text)
        await update.message.reply_text(f"🔍 **نتائج البحث عن `{text}`:**\n\n{result}", parse_mode="Markdown")
        context.user_data.pop("mode", None)

    else:
        # رسالة عادية
        await update.message.reply_text(
            "👋 استخدم الأزرار لاختيار الخدمة، أو أرسل /start للقائمة الرئيسية."
        )

def main():
    application = Application.builder().token(TOKEN).build()

    # إضافة المعالجات
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("admin", admin_panel))
    application.add_handler(CallbackQueryHandler(callback_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # تشغيل البوت عبر Webhook
    port = int(os.environ.get("PORT", 10000))
    application.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=TOKEN,
        webhook_url=f"{WEBHOOK_URL}/{TOKEN}"
    )

if __name__ == "__main__":
    main()
