import logging
import os
import io
import json
import random
import time
from datetime import datetime
from contextlib import asynccontextmanager
from typing import Dict, Any, List

from fastapi import FastAPI, Request, Response
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode  
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler
)

from chart import CoreAstrologyEngine
from scoring import RulesEngine
from interpreter import AstrologicalInterpreter
from drawer import AstrologyChartDrawer

# 1. إعداد السجلات (Logging)
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# 2. تعريف مراحل المحادثة (Conversation States)
YEAR, MONTH, DAY, KNOWS_TIME, TIME, LOCATION = range(6)

# 3. تهيئة المحركات الأساسية
engine = CoreAstrologyEngine()
interpreter = AstrologicalInterpreter()
drawer = AstrologyChartDrawer()

# التوكن والمتغيرات الخاصة بالـ Webhook
TOKEN = "7523578617:AAHECJgxEx-9FB9GN2lWoyJJHrunbzH-BwU"
WEBHOOK_URL = "https://Abraj-production.up.railway.app/webhook"

# بناء تطبيق التليجرام عالمياً ليتمكن FastAPI من قراءته
telegram_app = Application.builder().token(TOKEN).build()


# =====================================================================
# محرك حفظ واستدعاء بيانات ملفات المستخدمين (تجنب السؤال المتكرر)
# =====================================================================
class UsersDatabaseEngine:
    def __init__(self, file_path: str = "users_db.json"):
        self.file_path = file_path
        self.db = self._load_db()

    def _load_db(self) -> Dict[str, Any]:
        try:
            if os.path.exists(self.file_path):
                with open(self.file_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logger.error(f"Error loading users_db.json: {e}")
            return {}

    def _save_db(self):
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(self.db, f, ensure_ascii=False, indent=4)
        except Exception as e:
            logger.error(f"Error saving users_db.json: {e}")

    def get_user_profile(self, user_id: int) -> Dict[str, Any]:
        """استرجاع بيانات المستخدم إذا كانت موجودة مسبقاً"""
        return self.db.get(str(user_id))

    def save_user_profile(self, user_id: int, profile_data: Dict[str, Any]):
        """حفظ ملف بيانات الولادة الخاص بالمستخدم"""
        self.db[str(user_id)] = profile_data
        self._save_db()

    def delete_user_profile(self, user_id: int):
        """حذف البيانات لتمكين المستخدم من تعديل ميلاده"""
        if str(user_id) in self.db:
            del self.db[str(user_id)]
            self._save_db()

# تهيئة قاعدة بيانات المستخدمين عالمياً
users_db = UsersDatabaseEngine()


# =====================================================================
# محرك تحديد المواقع المحلي الثابت 
# =====================================================================
class LocalGeocodingEngine:
    def __init__(self):
        self.city_db = {
            # العراق
            "بغداد": (33.3152, 44.3661), "الموصل": (36.3400, 43.1300), "البصرة": (30.5081, 47.7835),
            "أربيل": (36.1901, 44.0089), "السليمانية": (35.5560, 45.4330), "النجف": (32.0250, 44.3460),
            "كربلاء": (32.6160, 44.0250), "كركوك": (35.4680, 44.3920), "الحلة": (32.4833, 44.4333),
            "الديوانية": (31.9900, 44.9260), "الناصرية": (31.0500, 46.2600), "العمارة": (31.8400, 47.1500),
            "الكوت": (32.5150, 45.8170), "الرمادي": (33.4166, 43.3000), "تكريت": (34.6000, 43.6800),
            "بعقوبة": (33.7420, 44.6460), "السماوة": (31.3170, 45.2830), "دهوك": (36.8660, 42.9880),
            
            # مصر
            "القاهرة": (30.0444, 31.2357), "الإسكندرية": (31.2001, 29.9187), "الجيزة": (30.0131, 31.2089),
            
            # السعودية ودول الخليج
            "الرياض": (24.7136, 46.6753), "مكة": (21.3891, 39.8579), "جدة": (21.5433, 39.1728),
            "المدينة": (24.4673, 39.6111), "دبي": (25.2048, 55.2708), "أبوظبي": (24.4539, 54.3773),
            "الكويت": (29.3759, 47.9774), "المنامة": (26.2285, 50.5860), "الدوحة": (25.2854, 51.5310),
            "مسقط": (23.5859, 58.4059),
            
            # الشام والبلدان العربية الأخرى
            "دمشق": (33.5138, 36.2765), "حلب": (36.2021, 37.1343), "بيروت": (33.8938, 35.5018),
            "عمان": (31.9454, 35.9284), "صنعاء": (15.3694, 44.1910), "الخرطوم": (15.5007, 32.5599),
            "طرابلس": (32.8872, 13.1913), "تونس": (36.8065, 10.1815), "الجزائر": (36.7525, 3.0420),
            "الرباط": (34.0209, -6.8416), "الدار البيضاء": (33.5731, -7.5898), "نواكشوط": (18.0735, -15.9582)
        }
        self.default_coords = (33.3152, 44.3661) 
        
    def search_city(self, input_text: str) -> tuple:
        clean_name = input_text.strip().replace("ة", "ه").replace("أ", "ا").replace("إ", "ا")
        for city, coords in self.city_db.items():
            clean_city = city.replace("ة", "ه").replace("أ", "ا").replace("إ", "ا")
            if clean_city in clean_name or clean_name in clean_city:
                return city, coords[0], coords[1]
        return "بغداد (افتراضي)", self.default_coords[0], self.default_coords[1]

local_geo = LocalGeocodingEngine()


# =====================================================================
# دالة معالجة الحساب والتحليل المشتركة (تُستدعى للحفظ الجديد أو القديم)
# =====================================================================
async def process_and_send_astrology_report(chat_id: int, user_data: dict, matched_city: str, lat: float, lon: float, update_context_user_data: dict):
    dt_utc = datetime(
        user_data['year'],
        user_data['month'],
        user_data['day'],
        user_data['hour'],
        user_data['minute']
    )
    
    try:
        chart_data = engine.compute_natal_chart(dt_utc, lat, lon)
        facts = [] 
        score_data = RulesEngine.evaluate(facts)
        total_score = score_data.total_score 

        # حفظ النتيجة في جلسة المحادثة المؤقتة لتشغيل الأزرار اللاحقة (التقرير الكامل، الصورة)
        update_context_user_data['last_chart'] = chart_data
        update_context_user_data['last_score'] = total_score
        update_context_user_data['lat'] = lat
        update_context_user_data['lon'] = lon

        summary_msg = interpreter.get_minimal_summary(chart_data)
        score_display = "🚧 قيد الحساب" if total_score == 0 else f"{total_score}"
        summary_msg = summary_msg.replace("SCORE_PLACEHOLDER", score_display)
        
        summary_msg = f"🗺 **المدينة المعتمدة للحساب:** {matched_city}\n\n" + summary_msg

        keyboard = [
            [InlineKeyboardButton("📜 قراءة برجك والتحليل الكامل", callback_data="menu_read_all")],
            [InlineKeyboardButton("🖼 توليد الخريطة الفلكية (صورة)", callback_data="menu_generate_image")],
            [InlineKeyboardButton("🔄 تعديل بيانات ميلادي", callback_data="reset_my_birthdata")],
            [InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="main_home")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await telegram_app.bot.send_message(chat_id=chat_id, text=summary_msg, reply_markup=reply_markup, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Error during calculations: {e}", exc_info=True)
        await telegram_app.bot.send_message(chat_id=chat_id, text="❌ عذراً، حدث خطأ أثناء معالجة البيانات الفلكية داخلياً.")


# =====================================================================
# محرك الخيرة الرقمية 
# =====================================================================
class KhiraEngine:
    def __init__(self, json_path: str = "khira_data.json"):
        self.json_path = json_path
        self.cooldowns = {}
        self.cooldown_duration = 3600  
        self.khira_data = self.load_khira_json()

    def load_khira_json(self) -> Dict[str, List[Dict[str, Any]]]:
        try:
            if os.path.exists(self.json_path):
                with open(self.json_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            return {"good": [], "medium": [], "bad": []}
        except Exception as e:
            logger.error(f"Error loading Khira JSON: {e}")
            return {"good": [], "medium": [], "bad": []}

    def check_cooldown(self, user_id: int) -> int:
        current_time = time.time()
        if user_id in self.cooldowns:
            time_passed = current_time - self.cooldowns[user_id]
            if time_passed < self.cooldown_duration:
                return int((self.cooldown_duration - time_passed) // 60)
        return 0

    def get_random_khira(self, user_id: int) -> Dict[str, Any]:
        categories = ["good", "medium", "bad"]
        weights = [0.50, 0.30, 0.20]
        chosen_category = random.choices(categories, weights=weights, k=1)[0]
        options_list = self.khira_data.get(chosen_category, [])
        if not options_list:
            return {}
        self.cooldowns[user_id] = time.time()
        return random.choice(options_list)

    @staticmethod
    def get_main_keyboard():
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("🔮 طلب خيرة جديدة", callback_data="khira_request")],
            [InlineKeyboardButton("📜 شروط وآداب الخيرة", callback_data="khira_rules")],
            [InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="main_home")]
        ])

khira_engine = KhiraEngine()


# =====================================================================
# تهيئة الـ Webhook و FastAPI
# =====================================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    await telegram_app.initialize()
    await telegram_app.bot.set_webhook(url=WEBHOOK_URL)
    logger.info(f"✅ Webhook successfully set to: {WEBHOOK_URL}")
    await telegram_app.start()
    yield
    await telegram_app.stop()
    await telegram_app.shutdown()

app = FastAPI(lifespan=lifespan)

@app.post("/webhook")
async def webhook_handler(request: Request):
    data = await request.json()
    update = Update.de_json(data, telegram_app.bot)
    await telegram_app.process_update(update)
    return Response(status_code=200)

@app.get("/")
async def root_handler():
    return {"status": "healthy", "bot": "Unified Bot is running via Webhook"}


# =====================================================================
# منطق معالجة القائمة الرئيسية وأمر /start
# =====================================================================
def get_start_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔮 قسم الأبراج والفلك", callback_data="go_astrology")],
        [InlineKeyboardButton("📖 قسم الخيرة الرقمية", callback_data="go_khira")]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    welcome_text = (
        "🔮 **مرحباً بك في البوت الشامل** 🔮\n\n"
        "الرجاء اختيار القسم الذي تود الدخول إليه من الأزرار أدناه:"
    )
    await update.message.reply_text(welcome_text, reply_markup=get_start_keyboard(), parse_mode=ParseMode.MARKDOWN)
    return ConversationHandler.END


async def khira_start_from_menu(query: Update.callback_query, context: ContextTypes.DEFAULT_TYPE):
    welcome_khira = (
        "✨ **خدمة الخيرة والاستخارة الرقمية** ✨\n\n"
        "«فَإِذَا عَزَمْتَ فَتَوَكَّلْ عَلَى اللَّهِ ۚ إِنَّ اللَّهَ يُحِبُّ الْمُتَوَكِّلِينَ»\n\n"
        "يرجى استحضار النية، وقراءة سورة الفاتحة متبوعة بالصلاة على محمد وآل محمد، ثم اضغط على الزر أدناه لبدء الخيرة.\n\n"
        "⚠️ **تنويه إخلاء مسؤولية:**\n"
        "هذه الخدمة برمجية استرشادية رقمية مبنية على التفاؤل بالقرآن الكريم."
    )
    await query.edit_message_text(welcome_khira, reply_markup=khira_engine.get_main_keyboard(), parse_mode=ParseMode.MARKDOWN)


# --- فحص التخزين المسبق عند ضغط زر الأبراج ---
async def astrology_trigger_workflow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer() 
    
    # محاولة جلب بروفايل المستخدم المخزن مسبقاً
    saved_profile = users_db.get_user_profile(user_id)
    
    if saved_profile:
        # إذا وجدنا بيانات مخزنة، نقوم بالحساب فوراً ونتجاوز استمارة الأسئلة
        await query.edit_message_text("✨ تم العثور على بيانات ميلادك المسجلة سابقاً! جاري استخراج خريطتك الحية فوراً...")
        await process_and_send_astrology_report(
            chat_id=user_id,
            user_data=saved_profile,
            matched_city=saved_profile['city'],
            lat=saved_profile['lat'],
            lon=saved_profile['lon'],
            update_context_user_data=context.user_data
        )
        return ConversationHandler.END
    
    # إذا لم توجد بيانات، تبدأ استمارة الأسئلة المعتادة لأول مرة فقط
    await query.edit_message_text(
        "🔮 **نظام التحليل الفلكي الشامل**\n\n"
        "يبدو أنك تستخدم النظام لأول مرة. سنقوم بحفظ بياناتك بعد إدخالها الآن حتى لا تسأل عنها مجدداً.\n\n"
        "ابدأ بإرسال **سنة ميلادك** بالأرقام (مثال: `1998`):"
    )
    return YEAR

async def p_year(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['year'] = int(update.message.text.strip())
    await update.message.reply_text("📆 ممتاز! الآن أرسل **شهر ميلادك** (رقم من 1 إلى 12):")
    return MONTH

async def p_month(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['month'] = int(update.message.text.strip())
    await update.message.reply_text("🗓 رائع! أرسل الآن **يوم ميلادك** برقم من (1 إلى 31):")
    return DAY

async def p_day(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['day'] = int(update.message.text.strip())
    
    keyboard = [
        [InlineKeyboardButton("✅ نعم، أعرفه بدقة", callback_data="knows_true")],
        [InlineKeyboardButton("❌ لا، غير معروف", callback_data="knows_false")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🕒 هل تعرف **وقت ولادتك الدقيق** (الساعة والدقيقة)؟", reply_markup=reply_markup)
    return KNOWS_TIME

async def p_knows_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    if query.data == "knows_true":
        await query.edit_message_text("🕓 أرسل وقت الولادة بتنسيق 24 ساعة (ساعة:دقيقة) مثال: `18:45`:")
        return TIME
    else:
        context.user_data['hour'] = 12
        context.user_data['minute'] = 0
        context.user_data['unknown_time'] = True
        await query.edit_message_text("📍 أرسل **اسم مدينة ميلادك** (مثال: `بغداد` ، `الموصل` ، `القاهرة`):")
        return LOCATION

async def p_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        time_str = update.message.text.strip()
        hour, minute = map(int, time_str.split(':'))
        context.user_data['hour'] = hour
        context.user_data['minute'] = minute
        context.user_data['unknown_time'] = False
    except ValueError:
        await update.message.reply_text("⚠️ تنسيق غير صحيح، يرجى إرساله مثل `14:30`:")
        return TIME

    await update.message.reply_text("📍 أرسل **اسم مدينة ميلادك** (مثال: `بغداد` ، `الموصل` ، `القاهرة`):")
    return LOCATION

async def p_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_input = update.message.text.strip()
    user_id = update.message.from_user.id
    
    matched_city, lat, lon = local_geo.search_city(user_input)

    # هيكلة ملف البيانات لحفظه للمستخدم بشكل دائم
    profile_to_save = {
        "year": context.user_data['year'],
        "month": context.user_data['month'],
        "day": context.user_data['day'],
        "hour": context.user_data['hour'],
        "minute": context.user_data['minute'],
        "city": matched_city,
        "lat": lat,
        "lon": lon
    }
    
    # الحفظ التلقائي الفوري في ملف التخزين المحلي
    users_db.save_user_profile(user_id, profile_to_save)
    logger.info(f"Saved new user profile for ID {user_id}")

    # معالجة وعرض التقرير
    await process_and_send_astrology_report(
        chat_id=user_id,
        user_data=context.user_data,
        matched_city=matched_city,
        lat=lat,
        lon=lon,
        update_context_user_data=context.user_data
    )

    return ConversationHandler.END


# =====================================================================
# معالج ضغطات الأزرار الموحد (مع إضافة خيار تعديل وحذف البيانات)
# =====================================================================
async def handle_menu_clicks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data

    if data == "main_home":
        await query.answer()
        context.user_data.clear()
        welcome_text = (
            "🔮 **مرحباً بك في البوت الشامل** 🔮\n\n"
            "الرجاء اختيار القسم الذي تود الدخول إليه من الأزرار أدناه:"
        )
        await query.edit_message_text(welcome_text, reply_markup=get_start_keyboard(), parse_mode=ParseMode.MARKDOWN)
        return

    elif data == "reset_my_birthdata":
        # حذف البروفايل لتمكينه من إعادة التسجيل مجدداً
        await query.answer("جاري مسح بياناتك السابقة لإعادة تعيينها...")
        users_db.delete_user_profile(user_id)
        context.user_data.clear()
        await query.edit_message_text(
            "🗑 تم مسح بيانات ميلادك السابقة بنجاح.\n"
            "يرجى الضغط على **قسم الأبراج والفلك** مجدداً من القائمة الرئيسية لإدخال البيانات الجديدة.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 العودة للقائمة", callback_data="main_home")]])
        )
        return

    elif data == "go_khira" or data == "khira_back":
        await query.answer()
        await khira_start_from_menu(query, context)
        return

    elif data == "khira_request":
        remaining = khira_engine.check_cooldown(user_id)
        if remaining > 0:
            await query.answer(f"⚠️ انتظر {remaining} دقيقة أو تدبر في نتيجتك الحالية أولاً.", show_alert=True)
            return

        chosen = khira_engine.get_random_khira(user_id)
        if not chosen:
            await query.answer("عذراً، لم يتم العثور على نصوص كافية.", show_alert=True)
            return

        await query.answer("جاري سحب نتيجتك الآن...")
        result_text = (
            f"🔮 **نتيجـة الخيـرة الخاصـة بك**\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📖 **الآية الشريفة الصاعدة:**\n"
            f"**{chosen['verse']}**\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📊 **الحكم والدرجة:**\n"
            f"درجة التيسير: {chosen['stars']}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"💬 **التوجيه والتفسير:**\n"
            f"{chosen['interpretation']}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🤲 **الدعاء المستحب والعمل:**\n"
            f"_{chosen['dua']}_\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"⚠️ *ملاحظة: الخيرة للاسترشاد والتفاؤل، والأمر كله بيد الله تعالى.*"
        )
        back_markup = InlineKeyboardMarkup([[InlineKeyboardButton("↩️ العودة لقائمة الخيرة", callback_data="khira_back")]])
        await query.edit_message_text(result_text, reply_markup=back_markup, parse_mode=ParseMode.MARKDOWN)
        return

    elif data == "khira_rules":
        await query.answer()
        rules_text = (
            "📜 **آداب وشروط عمل الخيرة:**\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "1️⃣ **النية الصادقة:** أن تكون حائراً فعلاً بين أمرين ولم تصل لقرار حاسم بعد الاستشارة والتدبر.\n"
            "2️⃣ **عدم التكرار:** لا تُكرر الخيرة في نفس الأمر إطلاقاً.\n"
            "3️⃣ **الرضا بالنتيجة:** تسليم الأمر لله تعالى والعمل بموجب التوجيه الصاعد بقلب مطمئن."
        )
        back_markup = InlineKeyboardMarkup([[InlineKeyboardButton("↩️ العودة لقائمة الخيرة", callback_data="khira_back")]])
        await query.edit_message_text(rules_text, reply_markup=back_markup, parse_mode=ParseMode.MARKDOWN)
        return

    chart_data = context.user_data.get('last_chart')
    
    astrology_back_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("📜 قراءة برجك والتحليل الكامل", callback_data="menu_read_all")],
        [InlineKeyboardButton("🖼 توليد الخريطة الفلكية (صورة)", callback_data="menu_generate_image")],
        [InlineKeyboardButton("🔄 تعديل بيانات ميلادي", callback_data="reset_my_birthdata")],
        [InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="main_home")]
    ])

    if not chart_data and data.startswith("menu_"):
        # في حال انتهت الجلسة المؤقتة في الـ RAM لكن المستخدم محفوظ في الـ DB
        saved_profile = users_db.get_user_profile(user_id)
        if saved_profile:
            dt_utc = datetime(saved_profile['year'], saved_profile['month'], saved_profile['day'], saved_profile['hour'], saved_profile['minute'])
            chart_data = engine.compute_natal_chart(dt_utc, saved_profile['lat'], saved_profile['lon'])
            context.user_data['last_chart'] = chart_data
        else:
            await query.answer()
            await query.message.reply_text("❌ انتهت صلاحية الجلسة، من فضلك اضغط على قسم الأبراج مجدداً لبدء الحساب تلقائياً.")
            return

    try:
        if data == "menu_read_all":
            await query.answer("جاري تحليل كافة المؤشرات المتقدمة...")
            full_report = interpreter.get_detailed_report(chart_data)
            asc_sign = getattr(chart_data, 'ascendant', 'غير معروف')
            
            complete_analysis = (
                f"🪐 **التقرير الفلكي الشامل والكامل لخريطتك** 🪐\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"• **البرج الصاعد (الطالع):** {asc_sign}\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"{full_report}\n\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"✨ انتهى التقرير النصي الشامل."
            )
            
            if len(complete_analysis) > 4000:
                parts = [complete_analysis[i:i+4000] for i in range(0, len(complete_analysis), 4000)]
                for i, part in enumerate(parts):
                    if i == len(parts) - 1:
                        await query.message.reply_text(part, reply_markup=astrology_back_markup, parse_mode="Markdown")
                    else:
                        await telegram_app.bot.send_message(chat_id=user_id, text=part, parse_mode="Markdown")
            else:
                await query.edit_message_text(complete_analysis, reply_markup=astrology_back_markup, parse_mode="Markdown")

        elif data == "menu_generate_image":
            await query.answer("جاري رسم خريطتك الفلكية الحية...")
            try:
                class FlexibleChartAdapter:
                    def __init__(self, raw_chart):
                        self.ascendant = getattr(raw_chart, 'ascendant', 'Aries')
                        self.ascendant_degree = getattr(raw_chart, 'ascendant_degree', 0.0)
                        self.midheaven_degree = getattr(raw_chart, 'midheaven_degree', 270.0)
                        self.houses = getattr(raw_chart, 'houses', {})
                        self.planets = {}
                        raw_planets = getattr(raw_chart, 'planets', {})
                        for p_name, p_data in raw_planets.items():
                            class PlanetAdapter:
                                def __init__(self, d):
                                    self.longitude = getattr(d, 'longitude', getattr(d, 'abs_degree', getattr(d, 'degree', 0.0)))
                            self.planets[p_name] = PlanetAdapter(p_data)
                        self.aspects = []

                adapted_chart = FlexibleChartAdapter(chart_data)
                img_bytes_data = drawer.generate_chart_png(adapted_chart)
                img_buffer = io.BytesIO(img_bytes_data)
                img_buffer.name = "natal_chart.png"
                
                await telegram_app.bot.send_photo(
                    chat_id=user_id,
                    photo=img_buffer,
                    caption="🪐 **عجلة خريطتك الفلكية الحقيقية (Natal Wheel)**\nتم توليد الرسم البياني بناءً على درجات أجرامك المحفوظة.",
                    reply_markup=astrology_back_markup
                )
            except Exception as draw_err:
                logger.error(f"Error drawing chart: {draw_err}")
                await query.message.reply_text("⚠️ تعذر توليد الصورة حالياً، يرجى مراجعة التقرير النصي.", reply_markup=astrology_back_markup)

    except Exception as exc:
        logger.error(f"Error handling click: {exc}")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("🚫 تم إلغاء العملية الحالية. يمكنك البدء من جديد بإرسال /start")
    return ConversationHandler.END


# =====================================================================
# تسجيل الـ Handlers للـ Conversation والأزرار
# =====================================================================
conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(astrology_trigger_workflow, pattern="^go_astrology$")],
    states={
        YEAR: [MessageHandler(filters.TEXT & ~filters.COMMAND, p_year)],
        MONTH: [MessageHandler(filters.TEXT & ~filters.COMMAND, p_month)],
        DAY: [MessageHandler(filters.TEXT & ~filters.COMMAND, p_day)],
        KNOWS_TIME: [CallbackQueryHandler(p_knows_time)],
        TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, p_time)],
        LOCATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, p_location)],
    },
    fallbacks=[CommandHandler('cancel', cancel)],
    per_message=False
)

telegram_app.add_handler(CommandHandler('start', start))
telegram_app.add_handler(conv_handler)
telegram_app.add_handler(CallbackQueryHandler(handle_menu_clicks, pattern="^(?!(go_astrology)$).*"))
