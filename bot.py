import os
import json
import logging
import requests
import http.server
import socketserver
import threading
import telegram
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

# ========== الإعدادات الثابتة ==========
BOT_TOKEN = "8503124202:AAGI9rPf3P-5pr5VGzwLhofgda1PXCJtqX4"
DEVELOPER_ID = 7958260008  # رقم حسابك
# =====================================

USER_FILE = "users.json"
logging.basicConfig(level=logging.INFO)

print(f"📦 إصدار python-telegram-bot: {telegram.__version__}")

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

# ========== دوال OSINT ==========
def phone_lookup(phone):
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
    try:
        url = f"https://api.sherlock.project/api/v1/search?username={username}"
        response = requests.get(url, timeout=15)
        data = response.json()
        results = []
        for site, info in data.items():
            if info.get("exists"):
                results.append(f"✅ {site}: {info.get('url')}")
        if results:
            return "\n".join(results[:10])
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

    welcome_message = (
        "👋 **أهلاً بك في بوت OSINT اليمن!**\n\n"
        "🇾🇪 هذا البوت يساعدك في جمع المعلومات من المصادر المفتوحة.\n\n"
        "📌 **اختر الخدمة من الأزرار أدناه:**\n"
        "• 🇾🇪 معلومات عن اليمن\n"
        "• 📞 بحث برقم هاتف (يدعم +967)\n"
        "• 🔍 بحث باسم مستخدم (عبر منصات التواصل)\n"
        "• ❓ المساعدة والاستخدام\n\n"
        "🔹 **المطور**: @xxxpx1"
    )

    await update.message.reply_text(
        welcome_message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def yemen_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    info = (
        "🇾🇪 **معلومات عن الجمهورية اليمنية**\n\n"
        "• **العاصمة**: صنعاء\n"
        "• **العملة**: ريال يمني\n"
        "• **اللغة الرسمية**: العربية\n"
        "• **رمز الهاتف الدولي**: +967\n"
        "• **المساحة**: 527,970 كم²\n"
        "• **عدد السكان**: ~30 مليون نسمة\n\n"
        "📞 **للتحقق من رقم يمني:**\n"
        "أرسل الرقم بصيغة: `+967XXXXXXXXX`"
    )
    await query.edit_message_text(info, parse_mode="Markdown")

async def phone_lookup_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["mode"] = "phone"
    await query.edit_message_text(
        "📞 **أرسل رقم الهاتف بصيغة دولية**\n"
        "مثال: `+967XXXXXXXXX`\n\n"
        "🔹 **ملاحظة**: البحث يعتمد على قواعد البيانات العامة."
    )

async def username_search_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["mode"] = "username"
    await query.edit_message_text(
        "🔍 **أرسل اسم المستخدم الذي تريد البحث عنه**\n"
        "مثال: `example_user`\n\n"
        "🔹 سيتم البحث في أكثر من 100 منصة تواصل اجتماعي."
    )

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != DEVELOPER_ID:
        if update.callback_query:
            await update.callback_query.answer("⛔ هذا الزر للمطور فقط.", show_alert=True)
        else:
            await update.message.reply_text("⛔ هذا الأمر للمطور فقط.")
        return

    keyboard = [
        [InlineKeyboardButton("📢 إذاعة", callback_data="broadcast")],
        [InlineKeyboardButton("👥 قائمة المستخدمين", callback_data="list_users")],
        [InlineKeyboardButton("🚫 حظر مستخدم", callback_data="block_user")],
        [InlineKeyboardButton("✅ فك حظر", callback_data="unblock_user")],
        [InlineKeyboardButton("✉️ مراسلة فردية", callback_data="msg_user")],
        [InlineKeyboardButton("🔍 مراقبة الرسائل", callback_data="toggle_monitor")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            "🛠️ **لوحة تحكم المطور**\nاختر الإجراء المناسب:",
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            "🛠️ **لوحة تحكم المطور**\nاختر الإجراء المناسب:",
            reply_markup=reply_markup
        )

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
            "1️⃣ اختر الخدمة من الأزرار الرئيسية.\n"
            "2️⃣ اتبع التعليمات التي تظهر.\n"
            "3️⃣ انتظر النتيجة (قد تستغرق بضع ثوانٍ).\n\n"
            "🔹 **البحث برقم هاتف**: أدخل الرقم بصيغة دولية.\n"
            "🔹 **البحث باسم مستخدم**: أدخل اسم المستخدم فقط.\n"
            "🔹 **معلومات اليمن**: تعرض معلومات عامة عن البلد.\n\n"
            "📌 **ملاحظة**: جميع المعلومات مستخلصة من المصادر المفتوحة."
        )
    elif data == "admin_panel":
        await admin_panel(update, context)
    elif uid != DEVELOPER_ID:
        await query.edit_message_text("⛔ هذا الزر للمطور فقط.")
    else:
        context.user_data["admin_action"] = data
        if data == "broadcast":
            await query.edit_message_text("📢 أرسل الآن رسالة الإذاعة (نص فقط).")
        elif data == "list_users":
            await query.edit_message_text(f"👥 عدد المستخدمين المسجلين: {len(users)}")
        elif data == "block_user":
            await query.edit_message_text("🚫 أرسل معرف المستخدم (ID) لحظره.")
        elif data == "unblock_user":
            await query.edit_message_text("✅ أرسل معرف المستخدم (ID) لفك الحظر.")
        elif data == "msg_user":
            await query.edit_message_text("✉️ أرسل المعرف ثم الرسالة مفصولة بمسافة:\nمثال: `123456789 مرحبا`")
        elif data == "toggle_monitor":
            current = context.bot_data.get("monitor", False)
            context.bot_data["monitor"] = not current
            status = "مفعلة" if not current else "معطلة"
            await query.edit_message_text(f"🔍 حالة مراقبة الرسائل: {status}")

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
            await update.message.reply_text("✅ تم إرسال الإذاعة لجميع المستخدمين.")
        elif action == "block_user":
            try:
                blocked.add(int(text))
                await update.message.reply_text(f"🚫 تم حظر المستخدم `{text}`.")
            except:
                await update.message.reply_text("❌ معرف غير صالح.")
        elif action == "unblock_user":
            try:
                blocked.discard(int(text))
                await update.message.reply_text(f"✅ تم فك الحظر عن المستخدم `{text}`.")
            except:
                await update.message.reply_text("❌ معرف غير صالح.")
        elif action == "msg_user":
            parts = text.split(maxsplit=1)
            if len(parts) == 2:
                try:
                    await context.bot.send_message(int(parts[0]), f"📨 {parts[1]}")
                    await update.message.reply_text("✅ تم إرسال الرسالة.")
                except Exception as e:
                    await update.message.reply_text(f"❌ فشل الإرسال: {e}")
            else:
                await update.message.reply_text("❌ الصيغة: `المعرف الرسالة`")
        return

    # حظر
    if uid in blocked:
        await update.message.reply_text("🚫 أنت محظور من استخدام هذا البوت.")
        return

    # أوامر OSINT
    mode = context.user_data.get("mode")
    if mode == "phone":
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
        await update.message.reply_text("⏳ جاري البحث ...")
        result = username_search(text)
        await update.message.reply_text(f"🔍 **نتائج البحث عن `{text}`:**\n\n{result}", parse_mode="Markdown")
        context.user_data.pop("mode", None)

    else:
        await update.message.reply_text(
            "👋 استخدم الأزرار لاختيار الخدمة.\n"
            "أو أرسل `/start` لإعادة ظهور الأزرار."
        )

# ========== تشغيل البوت ==========
def run_bot():
    try:
        application = Application.builder().token(BOT_TOKEN).build()
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("admin", admin_panel))
        application.add_handler(CallbackQueryHandler(callback_handler))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        print("✅ البوت جاهز للتشغيل (OSINT YEMEN V2)")
        application.run_polling()
    except Exception as e:
        print(f"❌ فشل تشغيل البوت: {e}")
        import traceback
        traceback.print_exc()

# ========== خادم ويب بسيط ==========
class HealthCheckHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running!")

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    with socketserver.TCPServer(("0.0.0.0", port), HealthCheckHandler) as httpd:
        print(f"✅ خادم الويب يعمل على المنفذ {port}")
        httpd.serve_forever()

# ========== نقطة الدخول ==========
if __name__ == "__main__":
    print("🚀 بدء تشغيل البوت...")
    web_thread = threading.Thread(target=run_web_server, daemon=True)
    web_thread.start()
    run_bot()
