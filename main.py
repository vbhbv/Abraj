import logging
import os
import io
import json
import random
import time
from datetime import datetime
from contextlib import asynccontextmanager
from typing import Dict, Any, List

import psycopg2
from psycopg2.extras import RealDictCursor

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

# استيراد المحركات الأساسية من ملفاتك
from chart import CoreAstrologyEngine
from scoring import RulesEngine
from interpreter import AstrologicalInterpreter
from drawer import AstrologyChartDrawer

# 1. إعداد السجلات (Logging)
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# 2. تعريف مراحل المحادثة (Conversation States)
# تمت إضافة مراحل حيازة بيانات الطرف الآخر لحساب التوافق (P2_...)
YEAR, MONTH, DAY, KNOWS_TIME, TIME, LOCATION = range(6)
P2_YEAR, P2_MONTH, P2_DAY, P2_KNOWS_TIME, P2_TIME, P2_LOCATION = range(6, 12)

# 3. تهيئة المحركات الأساسية
engine = CoreAstrologyEngine()
interpreter = AstrologicalInterpreter()
drawer = AstrologyChartDrawer()

# التوكن والمتغيرات الخاصة بالـ Webhook
TOKEN = "7523578617:AAHECJgxEx-9FB9GN2lWoyJJHrunbzH-BwU"
WEBHOOK_URL = "https://Abraj-production.up.railway.app/webhook"

telegram_app = Application.builder().token(TOKEN).build()


# =====================================================================
# محرك حفظ واستدعاء بيانات ملفات المستخدمين (PostgreSQL)
# =====================================================================
class UsersDatabaseEngine:
    def __init__(self):
        self.db_url = os.getenv("DATABASE_URL")
        if not self.db_url:
            raise ValueError("❌ خطأ: لم يتم العثور على متغير البيئة 'DATABASE_URL'!")
        self._init_db()

    def _get_connection(self):
        return psycopg2.connect(self.db_url)

    def _init_db(self):
        conn = None
        try:
            conn = self._get_connection()
            with conn.cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS user_profiles (
                        user_id BIGINT PRIMARY KEY,
                        profile_data TEXT NOT NULL
                    );
                """)
                conn.commit()
                logger.info("✅ PostgreSQL database tables initialized successfully.")
        except Exception as e:
            logger.error(f"Error initializing PostgreSQL Database: {e}")
        finally:
            if conn:
                conn.close()

    def get_user_profile(self, user_id: int) -> Dict[str, Any]:
        conn = None
        try:
            conn = self._get_connection()
            with conn.cursor() as cursor:
                cursor.execute("SELECT profile_data FROM user_profiles WHERE user_id = %s;", (user_id,))
                row = cursor.fetchone()
                if row:
                    return json.loads(row[0])
            return {}
        except Exception as e:
            logger.error(f"Error loading user profile from DB: {e}")
            return {}
        finally:
            if conn:
                conn.close()

    def save_user_profile(self, user_id: int, profile_data: Dict[str, Any]):
        conn = None
        try:
            conn = self._get_connection()
            with conn.cursor() as cursor:
                json_data = json.dumps(profile_data, ensure_ascii=False)
                cursor.execute("""
                    INSERT INTO user_profiles (user_id, profile_data) 
                    VALUES (%s, %s)
                    ON CONFLICT (user_id) 
                    DO UPDATE SET profile_data = EXCLUDED.profile_data;
                """, (user_id, json_data))
                conn.commit()
        except Exception as e:
            logger.error(f"Error saving user profile to DB: {e}")
        finally:
            if conn:
                conn.close()

    def delete_user_profile(self, user_id: int):
        conn = None
        try:
            conn = self._get_connection()
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM user_profiles WHERE user_id = %s;", (user_id,))
                conn.commit()
        except Exception as e:
            logger.error(f"Error deleting user profile from DB: {e}")
        finally:
            if conn:
                conn.close()

users_db = UsersDatabaseEngine()


# =====================================================================
# محرك تحديد المواقع المحلي الثابت 
# =====================================================================
class LocalGeocodingEngine:
    def __init__(self):
        self.city_db = {
            "بغداد": (33.3152, 44.3661), "الموصل": (36.3400, 43.1300), "البصرة": (30.5081, 47.7835),
            "أربيل": (36.1901, 44.0089), "السليمانية": (35.5560, 45.4330), "النجف": (32.0250, 44.3460),
            "كربلاء": (32.6160, 44.0250), "كركوك": (35.4680, 44.3920), "الحلة": (32.4833, 44.4333),
            "الديوانية": (31.9900, 44.9260), "الناصرية": (31.0500, 46.2600), "العمارة": (31.8400, 47.1500),
            "الكوت": (32.5150, 45.8170), "الرمادي": (33.4166, 43.3000), "تكريت": (34.6000, 43.6800),
            "بعقوبة": (33.7420, 44.6460), "السماوة": (31.3170, 45.2830), "دهوك": (36.8660, 42.9880),
            "القاهرة": (30.0444, 31.2357), "الإسكندرية": (31.2001, 29.9187), "الجيزة": (30.0131, 31.2089),
            "الرياض": (24.7136, 46.6753), "مكة": (21.3891, 39.8579), "جدة": (21.5433, 39.1728),
            "المدينة": (24.4673, 39.6111), "دبي": (25.2048, 55.2708), "أبوظبي": (24.4539, 54.3773),
            "الكويت": (29.3759, 47.9774), "المنامة": (26.2285, 50.5860), "الدوحة": (25.2854, 51.5310),
            "مسقط": (23.5859, 58.4059), "دمشق": (33.5138, 36.2765), "حلب": (36.2021, 37.1343), 
            "بيروت": (33.8938, 35.5018), "عمان": (31.9454, 35.9284), "صنعاء": (15.3694, 44.1910)
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
# محرك حساب وتوافق الأبراج المركب (Synastry Engine)
# =====================================================================
class SynastryEngine:
    @staticmethod
    def calculate_compatibility(chart1: Any, chart2: Any) -> Dict[str, Any]:
        """مقارنة موضع الشمس، القمر، والطالع بين خريطتين لحساب التوافق الزوجي والعاطفي"""
        s1 = getattr(chart1.planets.get('Sun'), 'sign', 'Aries').lower()
        s2 = getattr(chart2.planets.get('Sun'), 'sign', 'Aries').lower()
        m1 = getattr(chart1.planets.get('Moon'), 'sign', 'Taurus').lower()
        m2 = getattr(chart2.planets.get('Moon'), 'sign', 'Taurus').lower()
        a1 = getattr(chart1, 'ascendant', 'Gemini').lower()
        a2 = getattr(chart2, 'ascendant', 'Gemini').lower()

        # عناصر الأبراج لتقييم الانسجام الطبيعي
        elements = {
            'fire': ['aries', 'leo', 'sagittarius'],
            'earth': ['taurus', 'virgo', 'capricorn'],
            'air': ['gemini', 'libra', 'aquarius'],
            'water': ['cancer', 'scorpio', 'pisces']
        }

        def get_element(sign):
            for el, signs in elements.items():
                if sign in signs: return el
            return 'fire'

        score = 60 # النسبة الأساسية البادئة
        
        # 1. تناغم الشمس (الهوية والروح)
        if get_element(s1) == get_element(s2): score += 15
        elif (get_element(s1) in ['fire', 'air']) and (get_element(s2) in ['fire', 'air']): score += 10
        elif (get_element(s1) in ['earth', 'water']) and (get_element(s2) in ['earth', 'water']): score += 10
        
        # 2. تناغم القمر (الانسجام العاطفي والنفسي)
        if m1 == m2: score += 15
        elif get_element(m1) == get_element(m2): score += 10
        
        # 3. تناغم الطالع (الكيمياء الظاهرة والتفاهم اليومي)
        if a1 == a2 or get_element(a1) == get_element(a2): score += 10

        total_score = min(score + random.randint(-3, 3), 100)

        # صياغة النص التحليلي بناءً على النتيجة المستخرجة
        if total_score >= 85:
            verdict = "🌟 **توافق استثنائي روحي وعميق**"
            desc = "هذه العلاقة تتمتع بانسجام فلكي نادر جداً. هناك تفاهم تلقائي وكيمياء متبادلة تجعل الأفكار والمشاعر تتدفق بدون مجهود. تتكامل طباعكما وتدعم عواطفكما بعضها البعض بشكل مثالي."
        elif total_score >= 70:
            verdict = "🤝 **توافق قوي ومستقر**"
            desc = "علاقة متوازنة ومبنية على أسس متينة من التفاهم المشترك. نقاط الالتقاء بين خريطتيكما الفلكية تدل على قدرة عالية على تجاوز الخلافات وحل المشكلات بروح الشراكة والدعم."
        elif total_score >= 55:
            verdict = "⚖️ **توافق متوسط يحتاج إلى مرونة**"
            desc = "تجمعكما نقاط جذب واضحة ولكن تظهر بعض الاختلافات الجوهرية في الطباع وطريقة التعبير عن المشاعر. العلاقة ناجحة ومثمرة بشرط تقديم بعض التنازلات المتبادلة وتفهم كل طرف للاختلافات."
        else:
            verdict = "⚡ **علاقة كارمية وتحديات كبرى**"
            desc = "تظهر المقارنة الفلكية وجود زوايا متعارضة تؤدي إلى سوء فهم متكرر أو اختلاف في الأهداف العاطفية. العلاقة ليست مستحيلة ولكنها تتطلب وعياً كبيراً جداً وجهداً مضاعفاً لبنائها والحفاظ عليها."

        return {"score": total_score, "verdict": verdict, "description": desc, "s1": s1, "s2": s2, "m1": m1, "m2": m2, "a1": a1, "a2": a2}


# =====================================================================
# دالة معالجة الحساب والتحليل المشتركة للخريطة الفردية
# =====================================================================
async def process_and_send_astrology_report(chat_id: int, user_data: dict, matched_city: str, lat: float, lon: float, update_context_user_data: dict):
    dt_utc = datetime(user_data['year'], user_data['month'], user_data['day'], user_data['hour'], user_data['minute'])
    try:
        chart_data = engine.compute_natal_chart(dt_utc, lat, lon)
        asc_sign = getattr(chart_data, 'ascendant', 'Aries')
        sun_data = chart_data.planets.get('Sun')
        moon_data = chart_data.planets.get('Moon')
        
        sun_sign = getattr(sun_data, 'sign', 'Gemini') if sun_data else 'Gemini'
        moon_sign = getattr(moon_data, 'sign', 'Leo') if moon_data else 'Leo'
        
        class FactObject:
            def __init__(self, code_string): self.code = code_string

        facts = [FactObject(f"ascendant_{asc_sign.lower()}"), FactObject(f"sun_{sun_sign.lower()}"), FactObject(f"moon_{moon_sign.lower()}")]
        score_data = RulesEngine.evaluate(facts)
        total_score = getattr(score_data, 'total_score', 0) 

        if total_score == 0:
            base_score = 65
            if sun_sign in ['Gemini', 'Libra', 'Aquarius'] and moon_sign in ['Aries', 'Leo', 'Sagittarius']: base_score += 20
            if asc_sign in ['Libra', 'Gemini', 'Aquarius']: base_score += 10
            total_score = min(base_score + random.randint(-5, 5), 100)

        update_context_user_data['last_chart'] = chart_data
        update_context_user_data['last_score'] = total_score
        update_context_user_data['lat'] = lat
        update_context_user_data['lon'] = lon

        summary_msg = interpreter.get_minimal_summary(chart_data)
        summary_msg = summary_msg.replace("SCORE_PLACEHOLDER", f"{total_score}")
        summary_msg = f"🗺 **المدينة المعتمدة للحساب:** {matched_city}\n\n" + summary_msg

        keyboard = [
            [InlineKeyboardButton("📜 قراءة برجك والتحليل الكامل", callback_data="menu_read_all")],
            [InlineKeyboardButton("🖼 توليد الخريطة الفلكية (صورة)", callback_data="menu_generate_image")],
            [InlineKeyboardButton("💞 قياس التوافق مع شريك (Synastry)", callback_data="start_synastry_flow")],
            [InlineKeyboardButton("🔄 تعديل بيانات ميلادي", callback_data="reset_my_birthdata")],
            [InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="main_home")]
        ]
        await telegram_app.bot.send_message(chat_id=chat_id, text=summary_msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error during calculations: {e}", exc_info=True)
        await telegram_app.bot.send_message(chat_id=chat_id, text="❌ عذراً، حدث خطأ أثناء معالجة البيانات الفلكية داخلياً.")


# =====================================================================
# مسار فحص وبدء استمارة التوافق (Synastry Workflow)
# =====================================================================
async def synastry_trigger_workflow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    saved_profile = users_db.get_user_profile(user_id)
    if not saved_profile:
        await query.edit_message_text("⚠️ يجب أن تقوم بحساب خريطتك الشخصية أولاً وتسجيل بيانات ميلادك قبل استخدام ميزة التوافق مع شريك.")
        return ConversationHandler.END

    # تخزين خريطة المستخدم الأول المسجل في الجلسة المؤقتة للمقارنة اللاحقة
    dt_utc1 = datetime(saved_profile['year'], saved_profile['month'], saved_profile['day'], saved_profile['hour'], saved_profile['minute'])
    context.user_data['user_one_chart'] = engine.compute_natal_chart(dt_utc1, saved_profile['lat'], saved_profile['lon'])

    await query.edit_message_text(
        "💞 **قسم قياس التوافق والانسجام الفلكي (Synastry)** 💞\n\n"
        "سنقوم الآن بجمع بيانات الطرف الثاني (الشريك، الحبيب، أو الصديق) لمطابقتها مع خريطتك المسجلة.\n\n"
        "أرسل **سنة ميلاد الطرف الثاني** بالأرقام (مثال: `2000`):"
    )
    return P2_YEAR

async def p2_year(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['p2_year'] = int(update.message.text.strip())
    await update.message.reply_text("📆 ممتاز! الآن أرسل **شهر ميلاد الطرف الثاني** (من 1 إلى 12):")
    return P2_MONTH

async def p2_month(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['p2_month'] = int(update.message.text.strip())
    await update.message.reply_text("🗓 أرسل الآن **يوم ميلاد الطرف الثاني** برقم من (1 إلى 31):")
    return P2_DAY

async def p2_day(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['p2_day'] = int(update.message.text.strip())
    keyboard = [
        [InlineKeyboardButton("✅ نعم، أعرفه بدقة", callback_data="p2_knows_true")],
        [InlineKeyboardButton("❌ لا، غير معروف", callback_data="p2_knows_false")]
    ]
    await update.message.reply_text("🕒 هل تعرف **وقت ولادة الطرف الثاني** بدقة؟", reply_markup=InlineKeyboardMarkup(keyboard))
    return P2_KNOWS_TIME

async def p2_knows_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    if query.data == "p2_knows_true":
        await query.edit_message_text("🕓 أرسل وقت ولادة الطرف الثاني بتنسيق 24 ساعة (ساعة:دقيقة) مثال: `21:15`:")
        return P2_TIME
    else:
        context.user_data['p2_hour'] = 12
        context.user_data['p2_minute'] = 0
        await query.edit_message_text("📍 أرسل **اسم مدينة ميلاد الطرف الثاني** (مثال: `بغداد` ، `القاهرة`):")
        return P2_LOCATION

async def p2_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        time_str = update.message.text.strip()
        hour, minute = map(int, time_str.split(':'))
        context.user_data['p2_hour'] = hour
        context.user_data['p2_minute'] = minute
    except ValueError:
        await update.message.reply_text("⚠️ تنسيق غير صحيح، يرجى إرساله مثل `14:30`:")
        return P2_TIME

    await update.message.reply_text("📍 أرسل **اسم مدينة ميلاد الطرف الثاني** (مثال: `بغداد` ، `القاهرة`):")
    return P2_LOCATION

async def p2_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_input = update.message.text.strip()
    user_id = update.message.from_user.id
    
    matched_city, lat, lon = local_geo.search_city(user_input)
    
    # 1. بناء خريطة الطرف الثاني الفلكية
    dt_utc2 = datetime(
        context.user_data['p2_year'],
        context.user_data['p2_month'],
        context.user_data['p2_day'],
        context.user_data['p2_hour'],
        context.user_data['p2_minute']
    )
    chart2 = engine.compute_natal_chart(dt_utc2, lat, lon)
    chart1 = context.user_data.get('user_one_chart')

    if not chart1:
        saved_profile = users_db.get_user_profile(user_id)
        dt_utc1 = datetime(saved_profile['year'], saved_profile['month'], saved_profile['day'], saved_profile['hour'], saved_profile['minute'])
        chart1 = engine.compute_natal_chart(dt_utc1, saved_profile['lat'], saved_profile['lon'])

    # 2. تشغيل محرك حساب التوافق (Synastry Calculation)
    res = SynastryEngine.calculate_compatibility(chart1, chart2)

    # 3. صياغة وعرض تقرير التوافق الشامل للمستخدم
    report_text = (
        f"💞 **تقرير توافق الأبراج والخرائط الفلكية (Synastry)** 💞\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📊 **نسبة التوافق الإجمالية:** ` {res['score']}% `\n"
        f"الحالة الفلكية: {res['verdict']}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🪐 **مؤشرات المقارنة الحية للطرفين:**\n"
        f"• **برج الشمس:** أنت ({res['s1'].upper()}) ✖️ الطرف الثاني ({res['s2'].upper()})\n"
        f"• **برج القمر:** أنت ({res['m1'].upper()}) ✖️ الطرف الثاني ({res['m2'].upper()})\n"
        f"• **البرج الصاعد:** أنت ({res['a1'].upper()}) ✖️ الطرف الثاني ({res['a2'].upper()})\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💬 **التحليل الفلكي للعلاقة:**\n"
        f"{res['description']}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"✨ *الخريطة المقارنة تعطي مؤشرات التناعم الطبيعي، وتظل الإرادة وحسن التعامل هما أساس استمرار الروابط الحقيقية.*"
    )

    back_markup = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="main_home")]])
    await update.message.reply_text(report_text, reply_markup=back_markup, parse_mode="Markdown")
    return ConversationHandler.END


# =====================================================================
# محرك الخيرة الرقمية الثابت
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
                with open(self.json_path, "r", encoding="utf-8") as f: return json.load(f)
            return {"good": [], "medium": [], "bad": []}
        except Exception as e:
            logger.error(f"Error loading Khira JSON: {e}")
            return {"good": [], "medium": [], "bad": []}

    def check_cooldown(self, user_id: int) -> int:
        current_time = time.time()
        if user_id in self.cooldowns:
            time_passed = current_time - self.cooldowns[user_id]
            if time_passed < self.cooldown_duration: return int((self.cooldown_duration - time_passed) // 60)
        return 0

    def get_random_khira(self, user_id: int) -> Dict[str, Any]:
        categories = ["good", "medium", "bad"]
        weights = [0.50, 0.30, 0.20]
        chosen_category = random.choices(categories, weights=weights, k=1)[0]
        options_list = self.khira_data.get(chosen_category, [])
        if not options_list: return {}
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
    welcome_text = "🔮 **مرحباً بك في البوت الشامل المحدث** 🔮\n\nالرجاء اختيار القسم المخصص من الأزرار أدناه:"
    await update.message.reply_text(welcome_text, reply_markup=get_start_keyboard(), parse_mode=ParseMode.MARKDOWN)
    return ConversationHandler.END

async def khira_start_from_menu(query: Update.callback_query, context: ContextTypes.DEFAULT_TYPE):
    welcome_khira = "✨ **خدمة الخيرة والاستخارة الرقمية** ✨\n\nيرجى استحضار النية وقراءة سورة الفاتحة متبوعة بالصلاة على محمد وآل محمد، ثم اضغط على الزر أدناه لبدء الخيرة."
    await query.edit_message_text(welcome_khira, reply_markup=khira_engine.get_main_keyboard(), parse_mode=ParseMode.MARKDOWN)


# --- فحص التخزين المسبق عند ضغط زر الأبراج الفردية ---
async def astrology_trigger_workflow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer() 
    
    saved_profile = users_db.get_user_profile(user_id)
    if saved_profile:
        await query.edit_message_text("✨ تم العثور على بيانات ميلادك المسجلة سابقاً! جاري استخراج خريطتك الحية فوراً...")
        await process_and_send_astrology_report(
            chat_id=user_id, user_data=saved_profile, matched_city=saved_profile['city'],
            lat=saved_profile['lat'], lon=saved_profile['lon'], update_context_user_data=context.user_data
        )
        return ConversationHandler.END
    
    await query.edit_message_text("🔮 **نظام التحليل الفلكي الشامل**\n\nيبدو أنك تستخدم النظام لأول مرة. ابدأ بإرسال **سنة ميلادك** بالأرقام (مثال: `1998`):")
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
    keyboard = [[InlineKeyboardButton("✅ نعم، أعرفه بدقة", callback_data="knows_true")], [InlineKeyboardButton("❌ لا، غير معروف", callback_data="knows_false")]]
    await update.message.reply_text("🕒 هل تعرف **وقت ولادتك الدقيق**؟", reply_markup=InlineKeyboardMarkup(keyboard))
    return KNOWS_TIME

async def p_knows_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if query.data == "knows_true":
        await query.edit_message_text("🕓 أرسل وقت الولادة بتنسيق 24 ساعة (ساعة:دقيقة) مثال: `18:45`:")
        return TIME
    else:
        context.user_data['hour'], context.user_data['minute'] = 12, 0
        await query.edit_message_text("📍 أرسل **اسم مدينة ميلادك** (مثال: `بغداد`):")
        return LOCATION

async def p_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        time_str = update.message.text.strip()
        hour, minute = map(int, time_str.split(':'))
        context.user_data['hour'], context.user_data['minute'] = hour, minute
    except ValueError:
        await update.message.reply_text("⚠️ تنسيق غير صحيح، يرجى إرساله مثل `14:30`:")
        return TIME
    await update.message.reply_text("📍 أرسل **اسم مدينة ميلادك** (مثال: `بغداد`):")
    return LOCATION

async def p_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_input = update.message.text.strip()
    user_id = update.message.from_user.id
    matched_city, lat, lon = local_geo.search_city(user_input)

    profile_to_save = {
        "year": context.user_data['year'], "month": context.user_data['month'], "day": context.user_data['day'],
        "hour": context.user_data['hour'], "minute": context.user_data['minute'], "city": matched_city, "lat": lat, "lon": lon
    }
    users_db.save_user_profile(user_id, profile_to_save)
    await process_and_send_astrology_report(chat_id=user_id, user_data=context.user_data, matched_city=matched_city, lat=lat, lon=lon, update_context_user_data=context.user_data)
    return ConversationHandler.END


# =====================================================================
# معالج ضغطات الأزرار الموحد المحدث لشاشات التوافق
# =====================================================================
async def handle_menu_clicks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data

    if data == "main_home":
        await query.answer()
        context.user_data.clear()
        await query.edit_message_text("🔮 **مرحباً بك في البوت الشامل** 🔮\n\nالرجاء اختيار القسم الذي تود الدخول إليه من الأزرار أدناه:", reply_markup=get_start_keyboard(), parse_mode=ParseMode.MARKDOWN)
        return

    elif data == "reset_my_birthdata":
        await query.answer()
        users_db.delete_user_profile(user_id)
        context.user_data.clear()
        await query.edit_message_text("🗑 تم مسح بيانات ميلادك السابقة بنجاح من قاعدة البيانات السحابية.\nيرجى الضغط على قس الأبراج مجدداً من القائمة لإدخال بيانات حية جديدة.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 العودة للقائمة", callback_data="main_home")]]))
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
        if not chosen: return
        
        result_text = f"🔮 **نتيجـة الخيـرة الخاصـة بك**\n━━━━━━━━━━━━━━━━━━━━\n\n📖 **الآية الشريفة:**\n**{chosen['verse']}**\n\n📊 **الحكم والدرجة:**\nدرجة التيسير: {chosen['stars']}\n\n💬 **التوجيه والتفسير:**\n{chosen['interpretation']}\n\n🤲 **الدعاء المستحب:**\n_{chosen['dua']}_\n\n━━━━━━━━━━━━━━━━━━━━"
        await query.edit_message_text(result_text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ العودة لقائمة الخيرة", callback_data="khira_back")]]), parse_mode=ParseMode.MARKDOWN)
        return

    elif data == "khira_rules":
        await query.answer()
        rules_text = "📜 **آداب وشروط عمل الخيرة:**\n━━━━━━━━━━━━━━━━━━━━\n1️⃣ **النية الصادقة**\n2️⃣ **عدم التكرار في نفس الأمر**\n3️⃣ **الرضا بالنتيجة وتسليم الأمر لله.**"
        await query.edit_message_text(rules_text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ العودة لقائمة الخيرة", callback_data="khira_back")]]), parse_mode=ParseMode.MARKDOWN)
        return

    chart_data = context.user_data.get('last_chart')
    astrology_back_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("📜 قراءة برجك والتحليل الكامل", callback_data="menu_read_all")],
        [InlineKeyboardButton("🖼 توليد الخريطة الفلكية (صورة)", callback_data="menu_generate_image")],
        [InlineKeyboardButton("💞 قياس التوافق مع شريك (Synastry)", callback_data="start_synastry_flow")],
        [InlineKeyboardButton("🔄 تعديل بيانات ميلادي", callback_data="reset_my_birthdata")],
        [InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="main_home")]
    ])

    if not chart_data and data.startswith("menu_"):
        saved_profile = users_db.get_user_profile(user_id)
        if saved_profile:
            dt_utc = datetime(saved_profile['year'], saved_profile['month'], saved_profile['day'], saved_profile['hour'], saved_profile['minute'])
            chart_data = engine.compute_natal_chart(dt_utc, saved_profile['lat'], saved_profile['lon'])
            context.user_data['last_chart'] = chart_data
        else:
            await query.message.reply_text("❌ انتهت صلاحية الجلسة الآمنة، اضغط على قسم الأبراج مجدداً لبدء الحساب التلقائي.")
            return

    try:
        if data == "menu_read_all":
            await query.answer()
            full_report = interpreter.get_detailed_report(chart_data)
            asc_sign = getattr(chart_data, 'ascendant', 'غير معروف')
            complete_analysis = f"🪐 **التقرير الفلكي الشامل والكامل لخريطتك** 🪐\n━━━━━━━━━━━━━━━━━━━━\n• **البرج الصاعد (الطالع):** {asc_sign}\n━━━━━━━━━━━━━━━━━━━━\n\n{full_report}"
            
            if len(complete_analysis) > 4000:
                parts = [complete_analysis[i:i+4000] for i in range(0, len(complete_analysis), 4000)]
                for i, part in enumerate(parts):
                    if i == len(parts) - 1: await query.message.reply_text(part, reply_markup=astrology_back_markup, parse_mode="Markdown")
                    else: await telegram_app.bot.send_message(chat_id=user_id, text=part, parse_mode="Markdown")
            else:
                await query.edit_message_text(complete_analysis, reply_markup=astrology_back_markup, parse_mode="Markdown")

        elif data == "menu_generate_image":
            await query.answer()
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
                                def __init__(self, d): self.longitude = getattr(d, 'longitude', getattr(d, 'abs_degree', 0.0))
                            self.planets[p_name] = PlanetAdapter(p_data)
                        self.aspects = []

                adapted_chart = FlexibleChartAdapter(chart_data)
                img_bytes_data = drawer.generate_chart_png(adapted_chart)
                img_buffer = io.BytesIO(img_bytes_data)
                img_buffer.name = "natal_chart.png"
                await telegram_app.bot.send_photo(chat_id=user_id, photo=img_buffer, caption="🪐 **عجلة خريطتك الفلكية الحقيقية (Natal Wheel)**", reply_markup=astrology_back_markup)
            except Exception as draw_err:
                logger.error(f"Error drawing chart: {draw_err}")
                await query.message.reply_text("⚠️ تعذر توليد الصورة حالياً، يرجى مراجعة التقرير النصي المعروض.", reply_markup=astrology_back_markup)
    except Exception as exc:
        logger.error(f"Error handling click: {exc}")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("🚫 تم إلغاء العملية الحالية بنجاح. ارسل /start للبدء مجدداً.")
    return ConversationHandler.END


# =====================================================================
# تسجيل الـ Handlers للـ Conversation المزدوج (فردي + توافق)
# =====================================================================
conv_handler = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(astrology_trigger_workflow, pattern="^go_astrology$"),
        CallbackQueryHandler(synastry_trigger_workflow, pattern="^start_synastry_flow$")
    ],
    states={
        # مراحل خريطة المستخدم الأساسي
        YEAR: [MessageHandler(filters.TEXT & ~filters.COMMAND, p_year)],
        MONTH: [MessageHandler(filters.TEXT & ~filters.COMMAND, p_month)],
        DAY: [MessageHandler(filters.TEXT & ~filters.COMMAND, p_day)],
        KNOWS_TIME: [CallbackQueryHandler(p_knows_time)],
        TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, p_time)],
        LOCATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, p_location)],
        
        # مراحل خريطة الطرف الثاني (التوافق والـ Synastry)
        P2_YEAR: [MessageHandler(filters.TEXT & ~filters.COMMAND, p2_year)],
        P2_MONTH: [MessageHandler(filters.TEXT & ~filters.COMMAND, p2_month)],
        P2_DAY: [MessageHandler(filters.TEXT & ~filters.COMMAND, p2_day)],
        P2_KNOWS_TIME: [CallbackQueryHandler(p2_knows_time)],
        P2_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, p2_time)],
        P2_LOCATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, p2_location)],
    },
    fallbacks=[CommandHandler('cancel', cancel)],
    per_message=False
)

telegram_app.add_handler(CommandHandler('start', start))
telegram_app.add_handler(conv_handler)
telegram_app.add_handler(CallbackQueryHandler(handle_menu_clicks, pattern="^(?!(go_astrology|start_synastry_flow)$).*"))
