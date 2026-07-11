import logging
import os
import io
import json
import random
import time
import asyncio
import hashlib
import re
from datetime import datetime
from contextlib import asynccontextmanager
from typing import Dict, Any, List, Tuple, Optional

import asyncpg
import pytz
from cachetools import TTLCache

try:
    from timezonefinder import TimezoneFinder
    tf_engine = TimezoneFinder()
except ImportError:
    tf_engine = None

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
    ConversationHandler,
    AIORateLimiter
)

# =====================================================================
# 1. إدارة الـ Imports والمحركات الفلكية والـ Fallbacks الآمنة
# =====================================================================
try:
    from chart import CoreAstrologyEngine
    from interpreter import AstrologicalInterpreter
    from drawer import AstrologyChartDrawer
    from electional_engine import ElectionalAstrologyEngine
except ImportError:
    class CoreAstrologyEngine:
        def compute_natal_chart(self, dt, lat, lon): 
            return type('MockChart', (object,), {'ascendant': 'Aries', 'planets': {}, 'houses': {}, 'aspects': []})()
    class AstrologicalInterpreter:
        def get_minimal_summary(self, c): return "SCORE_PLACEHOLDER \n*تحليل مبدئي خفيف*"
        def get_detailed_report(self, c): return "تقرير تفصيلي احترافي كاملاً من المحرك الخاص\\."
    class AstrologyChartDrawer:
        def generate_chart_png(self, c): return b""
    class ElectionalAstrologyEngine:
        def __init__(self, astrology_engine): pass
        def generate_detailed_report(self, t, lat, lon): return "تقرير الاختيارات الحقيقي المتكامل", None

try:
    from transit_engine import TransitEngine
    from synastry_engine import SynastryEngine
except ImportError:
    class TransitEngine:
        @staticmethod
        def generate_daily_forecast(chart_data) -> str:
            return "🪐 *تقرير العبور الفلكي الحي لهذا اليوم*:\n━━━━━━━━━━━━━━━━━━━━\nحركة القمر الحالية تدعم ترتيب أوراقك المالية والمهنية بنجاح\\."
    class SynastryEngine:
        @staticmethod
        def calculate_compatibility(c1, c2) -> dict:
            return {"score": 88, "verdict": "توافق فلكي ممتاز", "description": "تكامل رائع بين الشمس والقمر والزهرة في الخريطتين المقارنتين\\."}

try:
    from horoscope_daily import HoroscopeDailyEngine
except ImportError:
    class HoroscopeDailyEngine:
        @staticmethod
        def get_daily_forecast(sun_sign: str) -> str:
            return f"🌟 *توقعات برجك الشمسي لهذا اليوم*:\n━━━━━━━━━━━━━━━━━━━━\nالأجواء إيجابية وداعمة لخطواتك الجديدة\\."

# إعداد الـ Logging الهيكلي للإنتاج والـ Metrics
logging.basicConfig(format='%(asctime)s - [User: %(processName)s] - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# مقاييس الأداء الداخلية للمراقبة والـ Metrics
METRICS = {
    "cache_hits": 0,
    "cache_misses": 0,
    "total_calculations": 0,
    "total_drawings": 0,
    "calculation_timeouts": 0,
    "db_retries": 0
}

# مراحل الـ Conversation
YEAR, MONTH, DAY, KNOWS_TIME, TIME, LOCATION = range(6)
P2_YEAR, P2_MONTH, P2_DAY, P2_KNOWS_TIME, P2_TIME, P2_LOCATION = range(6, 12)
ELECTIONAL_QUERY = 12  

engine = CoreAstrologyEngine()
interpreter = AstrologicalInterpreter()
drawer = AstrologyChartDrawer()
electional_engine = ElectionalAstrologyEngine(astrology_engine=engine)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEBHOOK_URL = "https://Abraj-production.up.railway.app/webhook"

telegram_app = Application.builder().token(TOKEN).updater(None).rate_limiter(AIORateLimiter()).build()

# =====================================================================
# 2. إدارة الـ Cache الموحد والـ الثابت لمنع الـ Race Condition
# =====================================================================
CHART_CACHE = TTLCache(maxsize=1500, ttl=7200)

# قاموس أقفال برمجية ثابت ومؤمن، يتم تصفية القفل المنتهي منه عبر الـ Garbage Collector الدوري
_fixed_key_locks: Dict[str, asyncio.Lock] = {}

def get_per_key_lock(cache_key: str) -> asyncio.Lock:
    if cache_key not in _fixed_key_locks:
        _fixed_key_locks[cache_key] = asyncio.Lock()
    return _fixed_key_locks[cache_key]

def generate_blake2_key(user_id: int, profile_dict: dict, prefix: str = "natal") -> str:
    profile_json = json.dumps(profile_dict, sort_keys=True, ensure_ascii=False)
    profile_hash = hashlib.blake2b(profile_json.encode('utf-8'), digest_size=16).hexdigest()
    return f"{prefix}_{user_id}_{profile_hash}"

def invalidate_user_old_cache(user_id: int, prefix: str = "natal"):
    for key in list(CHART_CACHE.keys()):
        if key.startswith(f"{prefix}_{user_id}_"):
            del CHART_CACHE[key]

def escape_markdown_v2(text: str) -> str:
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return re.sub(r'([%s])' % re.escape(escape_chars), r'\\\1', text)

# =====================================================================
# 3. مسبح الخيوط المتكيف (Dynamic Thread Pool Executor)
# =====================================================================
from concurrent.futures import ThreadPoolExecutor

# ضبط ديناميكي ممتد ليتناسب مع نوى المعالج المتاحة في الاستضافة بشكل آمن
computed_max_workers = min(32, (os.cpu_count() or 2) * 2)
chart_executor = ThreadPoolExecutor(max_workers=computed_max_workers, thread_name_prefix="AstrologyChart")
drawing_executor = ThreadPoolExecutor(max_workers=max(2, os.cpu_count() or 2), thread_name_prefix="ChartDrawing")

async def compute_chart_safe(engine, dt_utc, lat, lon, user_id: int) -> Any:
    loop = asyncio.get_running_loop()
    start_time = time.perf_counter()
    try:
        chart = await asyncio.wait_for(
            loop.run_in_executor(chart_executor, engine.compute_natal_chart, dt_utc, lat, lon),
            timeout=10.0
        )
        elapsed = time.perf_counter() - start_time
        METRICS["total_calculations"] += 1
        logger.info(f"⚡ [METRIC] Chart calc for User={user_id} done in {elapsed:.4f}s")
        return chart
    except asyncio.TimeoutError:
        METRICS["calculation_timeouts"] += 1
        logger.error(f"🚨 [Timeout] CoreAstrologyEngine hung up for User={user_id}")
        raise

async def draw_chart_safe(drawer, adapted_chart, user_id: int) -> bytes:
    loop = asyncio.get_running_loop()
    start_time = time.perf_counter()
    try:
        img_bytes = await asyncio.wait_for(
            loop.run_in_executor(drawing_executor, drawer.generate_chart_png, adapted_chart),
            timeout=15.0
        )
        elapsed = time.perf_counter() - start_time
        METRICS["total_drawings"] += 1
        logger.info(f"🎨 [METRIC] Image drawing for User={user_id} done in {elapsed:.4f}s")
        return img_bytes
    except asyncio.TimeoutError:
        logger.error(f"🚨 [Timeout] AstrologyChartDrawer rendering timed out for User={user_id}")
        raise

# =====================================================================
# 4. محرك الـ PostgreSQL المطور بأعمدة مهيكلة (Structured Schema)
# =====================================================================
class AsyncUsersDatabase:
    def __init__(self):
        self.db_url = os.getenv("DATABASE_URL")
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self):
        if not self.db_url:
            raise ValueError("❌ DATABASE_URL missing!")
        try:
            self.pool = await asyncpg.create_pool(
                self.db_url, min_size=2, max_size=15,
                max_queries=50000, max_inactive_connection_lifetime=300
            )
            async with self.pool.acquire() as conn:
                # التحول بالكامل لأعمدة منفصلة صلبة وسريعة بدلاً من الـ JSONB المستهلك للمعالج
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS user_profiles (
                        user_id BIGINT PRIMARY KEY,
                        birth_year INT NOT NULL,
                        birth_month INT NOT NULL,
                        birth_day INT NOT NULL,
                        birth_hour INT NOT NULL,
                        birth_minute INT NOT NULL,
                        lat DECIMAL(9,6) NOT NULL,
                        lon DECIMAL(9,6) NOT NULL,
                        city VARCHAR(100) NOT NULL,
                        timezone VARCHAR(50) NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                await conn.execute("CREATE INDEX IF NOT EXISTS idx_user_profiles_search ON user_profiles(user_id);")
            logger.info("✅ Async PostgreSQL Pool initialized with fast Structured Columns Schema.")
        except Exception as e:
            logger.critical(f"Database connection pool initiation failed: {e}", exc_info=True)
            raise e

    async def get_user_profile(self, user_id: int) -> Dict[str, Any]:
        if not self.pool: return {}
        async def _get():
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow("""
                    SELECT birth_year, birth_month, birth_day, birth_hour, birth_minute, lat, lon, city, timezone
                    FROM user_profiles WHERE user_id = $1;
                """, user_id)
                if row:
                    return {
                        "year": row["birth_year"], "month": row["birth_month"], "day": row["birth_day"],
                        "hour": row["birth_hour"], "minute": row["birth_minute"],
                        "lat": float(row["lat"]), "lon": float(row["lon"]),
                        "city": row["city"], "timezone": row["timezone"]
                    }
            return {}
        return await self.execute_with_retry(_get)

    async def save_user_profile(self, user_id: int, p: Dict[str, Any]):
        if not self.pool: return
        async def _save():
            async with self.pool.acquire() as conn:
                # دمج تحديث last_active مع عملية الإدخال أو التعديل المباشر لمنع الـ Writes الزائدة
                await conn.execute("""
                    INSERT INTO user_profiles (
                        user_id, birth_year, birth_month, birth_day, birth_hour, birth_minute, lat, lon, city, timezone, last_active
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, CURRENT_TIMESTAMP)
                    ON CONFLICT (user_id) 
                    DO UPDATE SET 
                        birth_year = EXCLUDED.birth_year, birth_month = EXCLUDED.birth_month, birth_day = EXCLUDED.birth_day,
                        birth_hour = EXCLUDED.birth_hour, birth_minute = EXCLUDED.birth_minute, lat = EXCLUDED.lat,
                        lon = EXCLUDED.lon, city = EXCLUDED.city, timezone = EXCLUDED.timezone, last_active = CURRENT_TIMESTAMP;
                """, user_id, p["year"], p["month"], p["day"], p["hour"], p["minute"], p["lat"], p["lon"], p["city"], p["timezone"])
        await self.execute_with_retry(_save)

    async def update_active_heartbeat(self, user_id: int):
        """تحديث دوري منفصل عند العمليات الأساسية الكبرى وليس مع كل استدعاء لقراءة الكاش"""
        if not self.pool: return
        async def _heartbeat():
            async with self.pool.acquire() as conn:
                await conn.execute("UPDATE user_profiles SET last_active = CURRENT_TIMESTAMP WHERE user_id = $1;", user_id)
        try:
            await self.execute_with_retry(_heartbeat)
        except Exception:
            pass

    async def delete_user_profile(self, user_id: int):
        if not self.pool: return
        async def _delete():
            async with self.pool.acquire() as conn:
                await conn.execute("DELETE FROM user_profiles WHERE user_id = $1;", user_id)
        await self.execute_with_retry(_delete)

    async def execute_with_retry(self, func, retries: int = 3, initial_delay: float = 0.5):
        delay = initial_delay
        for attempt in range(1, retries + 1):
            try:
                return await func()
            except (asyncpg.PostgresConnectionError, asyncpg.InterfaceError) as db_err:
                METRICS["db_retries"] += 1
                if attempt == retries:
                    logger.critical(f"🚨 [DB Fail] Master database failure after {retries} retries: {db_err}")
                    raise
                logger.warning(f"⚠️ [DB Retry] Disturbance caught. Attempt {attempt}/{retries}. Waiting {delay}s...")
                await asyncio.sleep(delay)
                delay *= 2

async_db = AsyncUsersDatabase()

# =====================================================================
# 5. محرك الجغرافيا الموسع وتحديد المنطقة الزمنية لمرة واحدة (Timezone Caching)
# =====================================================================
class EnhancedGeocodingEngine:
    def __init__(self):
        self.city_db = {
            "baghdad": (33.3152, 44.3661), "بغداد": (33.3152, 44.3661),
            "mosul": (36.3400, 43.1300), "الموصل": (36.3400, 43.1300),
            "basra": (30.5081, 47.7835), "البصرة": (30.5081, 47.7835),
            "erbil": (36.1901, 44.0089), "اربيل": (36.1901, 44.0089), "أربيل": (36.1901, 44.0089),
            "sulaymaniyah": (35.5560, 45.4330), "السليمانية": (35.5560, 45.4330),
            "najaf": (32.0250, 44.3460), "النجف": (32.0250, 44.3460),
            "karbala": (32.6160, 44.0250), "كربلاء": (32.6160, 44.0250),
            "kirkuk": (35.4681, 44.3922), "كركوك": (35.4681, 44.3922),
            "dahuk": (36.8601, 42.9904), "دهوك": (36.8601, 42.9904),
            "hilla": (32.4833, 44.4333), "الحلة": (32.4833, 44.4333), "بابل": (32.4833, 44.4333),
            "nasiriyah": (31.0500, 46.2500), "الناصرية": (31.0500, 46.2500), "ذي قار": (31.0500, 46.2500),
            "tikrit": (34.6000, 43.6800), "تكريت": (34.6000, 43.6800), "صلاح الدين": (34.6000, 43.6800),
            "ramadi": (33.4167, 43.3000), "الرمادي": (33.4167, 43.3000), "الانبار": (33.4167, 43.3000),
            "fallujah": (33.3500, 43.7833), "الفلوجة": (33.3500, 43.7833),
            "samawah": (31.3167, 45.2833), "السماوة": (31.3167, 45.2833), "المثنى": (31.3167, 45.2833),
            "kut": (32.5036, 45.8236), "الكوت": (32.5036, 45.8236), "واسط": (32.5036, 45.8236),
            "baqubah": (33.7422, 44.6442), "بعقوبة": (33.7422, 44.6442), "ديالى": (33.7422, 44.6442),
            "amarah": (31.8439, 47.1511), "العمارة": (31.8439, 47.1511), "ميسان": (31.8439, 47.1511),
            "diwaniyah": (31.9922, 44.9211), "الديوانية": (31.9922, 44.9211), "القادسية": (31.9922, 44.9211),
            "cairo": (30.0444, 31.2357), "القاهرة": (30.0444, 31.2357),
            "riyadh": (24.7136, 46.6753), "الرياض": (24.7136, 46.6753)
        }
        self.default_coords = (33.3152, 44.3661) 

    def clean_text(self, text: str) -> str:
        return text.strip().lower().replace("ة", "ه").replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")

    def search_city(self, input_text: str) -> tuple:
        clean_input = self.clean_text(input_text)
        for city_key, coords in self.city_db.items():
            if city_key in clean_input or clean_input in city_key:
                tz_resolved = "UTC"
                if tf_engine:
                    tz_found = tf_engine.timezone_at(lng=coords[1], lat=coords[0])
                    if tz_found: tz_resolved = tz_found
                return city_key.capitalize(), coords[0], coords[1], tz_resolved
        
        return "Baghdad (Default)", self.default_coords[0], self.default_coords[1], "Asia/Baghdad"

local_geo = EnhancedGeocodingEngine()

def convert_local_time_to_utc(user_data: dict, lat: float, lon: float) -> datetime:
    naive_dt = datetime(user_data['year'], user_data['month'], user_data['day'], user_data['hour'], user_data['minute'])
    timezone_str = user_data.get("timezone", "UTC")
    try:
        local_tz = pytz.timezone(timezone_str)
        local_dt = local_tz.localize(naive_dt, is_dst=None)
        return local_dt.astimezone(pytz.utc).replace(tzinfo=None)
    except Exception as e:
        logger.error(f"Timezone conversion via cached string failed: {e}")
        return naive_dt

async def get_or_compute_user_chart(user_id: int, user_profile: dict, engine) -> Optional[Any]:
    cache_key = generate_blake2_key(user_id, user_profile, "natal")
    
    # فحص الكاش السريع الأولي
    cached_data = CHART_CACHE.get(cache_key)
    if cached_data:
        METRICS["cache_hits"] += 1
        return cached_data
        
    # جلب القفل الخاص بهذا المفتاح لمنع الـ Stampede كلياً وسد ثغرات السباق
    key_lock = get_per_key_lock(cache_key)
    async with key_lock:
        # التحقق المزدوج (Double Check)
        cached_data = CHART_CACHE.get(cache_key)
        if cached_data:
            METRICS["cache_hits"] += 1
            return cached_data
            
        METRICS["cache_misses"] += 1
        lat = user_profile.get('lat', 33.3152)
        lon = user_profile.get('lon', 44.3661)
        dt_utc = convert_local_time_to_utc(user_profile, lat, lon)
        
        chart_data = await compute_chart_safe(engine, dt_utc, lat, lon, user_id)
        if chart_data:
            CHART_CACHE[cache_key] = chart_data
        return chart_data

async def process_and_send_astrology_report(chat_id: int, user_data: dict, matched_city: str):
    try:
        chart_data = await get_or_compute_user_chart(chat_id, user_data, engine)
        if chart_data is None:
            await telegram_app.bot.send_message(chat_id=chat_id, text="❌ خطأ حرج: فشل محرك الفلك في معالجة خريطتك\\.", parse_mode=ParseMode.MARKDOWN_V2)
            return

        total_score = 75
        summary_msg = interpreter.get_minimal_summary(chart_data)
        summary_msg = summary_msg.replace("SCORE_PLACEHOLDER", f"{total_score}")
        
        header = f"🗺 *المدينة والمنطقة الزمنية المسجلة:* {escape_markdown_v2(matched_city)}\n\n"
        final_msg = header + summary_msg

        keyboard = [
            [InlineKeyboardButton("✨ الأبراج وحظك اليوم", callback_data="menu_horoscope_daily")],
            [InlineKeyboardButton("📜 قراءة برجك والتحليل الكامل", callback_data="menu_read_all")],
            [InlineKeyboardButton("📅 التوقعات الحية اليومية (Transits)", callback_data="menu_daily_forecast")],
            [InlineKeyboardButton("⏱ تحديد اليوم والساعة الأنسب لقراراتك", callback_data="start_electional_flow")],
            [InlineKeyboardButton("🖼 توليد الخريطة الفلكية (صورة)", callback_data="menu_generate_image")],
            [InlineKeyboardButton("💞 قياس التوافق مع شريك (Synastry)", callback_data="start_synastry_flow")],
            [InlineKeyboardButton("🔄 تعديل بيانات ميلادي", callback_data="reset_my_birthdata")],
            [InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="main_home")]
        ]
        await telegram_app.bot.send_message(chat_id=chat_id, text=final_msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN_V2)
        # تحديث النشاط بشكل منفصل للحفاظ على أداء معالجة الذاكرة لقاعدة البيانات
        asyncio.create_task(async_db.update_active_heartbeat(chat_id))
    except Exception as e:
        logger.error(f"Error executing report dispatch for user={chat_id}: {e}", exc_info=True)
        await telegram_app.bot.send_message(chat_id=chat_id, text="❌ عذراً، حدث خطأ داخلي أثناء معالجة بياناتك\\.", parse_mode=ParseMode.MARKDOWN_V2)

# =====================================================================
# 6. مسارات الـ Conversations (المواليد، التوافق، الاختيارات)
# =====================================================================
async def synastry_trigger_workflow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    saved_profile = await async_db.get_user_profile(user_id)
    if not saved_profile:
        await query.edit_message_text("⚠️ يجب أن تقوم بحساب خريطتك الشخصية أولاً وتسجيل بيانات ميلادك قبل استخدام ميزة التوافق\\.", parse_mode=ParseMode.MARKDOWN_V2)
        return ConversationHandler.END

    await query.edit_message_text(
        "💞 *قسم قياس التوافق والانسجام الفلكي \\(Synastry\\)* 💞\n\n"
        "أرسل *سنة ميلاد الطرف الثاني* بالأرقام \\(مثال: `2000`\\):", parse_mode=ParseMode.MARKDOWN_V2
    )
    return P2_YEAR

async def p2_year(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        val = int(update.message.text.strip())
        if not (1900 <= val <= datetime.now().year + 1): raise ValueError()
        context.user_data['p2_year'] = val
    except ValueError:
        await update.message.reply_text("⚠️ سنة غير صالحة\\. يرجى إدخال سنة ميلاد حقيقية بالأرقام:", parse_mode=ParseMode.MARKDOWN_V2)
        return P2_YEAR
    await update.message.reply_text("季度 ممتاز\\! الآن أرسل *شهر ميلاد الطرف الثاني* \\(من 1 إلى 12\\):", parse_mode=ParseMode.MARKDOWN_V2)
    return P2_MONTH

async def p2_month(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        val = int(update.message.text.strip())
        if not (1 <= val <= 12): raise ValueError()
        context.user_data['p2_month'] = val
    except ValueError:
        await update.message.reply_text("⚠️ شهر غير صالح\\. يرجى إدخال رقم من 1 إلى 12:", parse_mode=ParseMode.MARKDOWN_V2)
        return P2_MONTH
    await update.message.reply_text("🗓 أرسل الآن *يوم ميلاد الطرف الثاني* برقم من \\(1 إلى 31\\):", parse_mode=ParseMode.MARKDOWN_V2)
    return P2_DAY

async def p2_day(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        val = int(update.message.text.strip())
        if not (1 <= val <= 31): raise ValueError()
        context.user_data['p2_day'] = val
    except ValueError:
        await update.message.reply_text("⚠️ يوم غير صالح\\. يرجى إدخال رقم اليوم من 1 إلى 31:", parse_mode=ParseMode.MARKDOWN_V2)
        return P2_DAY
    keyboard = [[InlineKeyboardButton("✅ نعم، أعرفه بدقة", callback_data="p2_knows_true")], [InlineKeyboardButton("❌ لا، غير معروف", callback_data="p2_knows_false")]]
    await update.message.reply_text("🕒 هل تعرف *وقت ولادة الطرف الثاني* بدقة؟", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN_V2)
    return P2_KNOWS_TIME

async def p2_knows_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if query.data == "p2_knows_true":
        await query.edit_message_text("🕓 أرسل وقت ولادة الطرف الثاني بتنسيق 24 ساعة \\(ساعة:دقيقة\\) مثال: `21:15`:", parse_mode=ParseMode.MARKDOWN_V2)
        return P2_TIME
    else:
        context.user_data['p2_hour'], context.user_data['p2_minute'] = 12, 0
        await query.edit_message_text("📍 أرسل *اسم مدينة ميلاد الطرف الثاني* باللغة العربية أو الإنجليزية:", parse_mode=ParseMode.MARKDOWN_V2)
        return P2_LOCATION

async def p2_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        time_str = update.message.text.strip()
        hour, minute = map(int, time_str.split(':'))
        if not (0 <= hour <= 23 and 0 <= minute <= 59): raise ValueError()
        context.user_data['p2_hour'], context.user_data['p2_minute'] = hour, minute
    except ValueError:
        await update.message.reply_text("⚠️ تنسيق غير صحيح، يرجى إرساله مجدداً مثل `14:30`:", parse_mode=ParseMode.MARKDOWN_V2)
        return P2_TIME
    await update.message.reply_text("📍 أرسل *اسم مدينة ميلاد الطرف الثاني* باللغة العربية أو الإنجليزية:", parse_mode=ParseMode.MARKDOWN_V2)
    return P2_LOCATION

async def p2_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_input = update.message.text.strip()
    user_id = update.message.from_user.id
    
    matched_city, lat, lon, tz_resolved = local_geo.search_city(user_input)
    
    p2_data = {
        'year': context.user_data['p2_year'], 'month': context.user_data['p2_month'], 'day': context.user_data['p2_day'],
        'hour': context.user_data['p2_hour'], 'minute': context.user_data['p2_minute'], 'timezone': tz_resolved
    }
    
    saved_profile = await async_db.get_user_profile(user_id)
    chart1 = await get_or_compute_user_chart(user_id, saved_profile, engine)
    
    dt_utc2 = convert_local_time_to_utc(p2_data, lat, lon)
    chart2 = await compute_chart_safe(engine, dt_utc2, lat, lon, user_id)

    res = SynastryEngine.calculate_compatibility(chart1, chart2)

    report_text = (
        f"💞 *تقرير توافق الأبراج والخرائط الفلكية \\(Synastry\\)* 💞\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📊 *نسبة التوافق الإجمالية:* ` {res['score']}% `\n"
        f"الحالة الفلكية: {escape_markdown_v2(res['verdict'])}\n\n"
        f"💬 *التحليل الفلكي والمقارن للعلاقة:*\n"
        f"{res['description']}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )

    back_markup = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="main_home")]])
    await update.message.reply_text(report_text, reply_markup=back_markup, parse_mode=ParseMode.MARKDOWN_V2)
    return ConversationHandler.END

async def electional_trigger_workflow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    saved_profile = await async_db.get_user_profile(user_id)
    if not saved_profile:
        await query.edit_message_text("⚠️ يجب أن تقوم بحساب خريطتك الفردية الشخصية أولاً قبل استخدام محرك الاختيارات\\.", parse_mode=ParseMode.MARKDOWN_V2)
        return ConversationHandler.END

    await query.edit_message_text(
        "🔮 *محرك الاختيارات الفلكية وجدولة القرارات الحية* 🔮\n\n"
        "اكتب الآن بأسلوبك ونصك الحر القرار أو الخطوة التي تنوي الإقدام عليها ليتسنى قياس زوايا الفلك لبلدك جغرافياً\\.", parse_mode=ParseMode.MARKDOWN_V2
    )
    return ELECTIONAL_QUERY

async def handle_electional_query_analysis(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_text = update.message.text.strip()
    user_id = update.message.from_user.id
    
    saved_profile = await async_db.get_user_profile(user_id)
    lat = saved_profile.get("lat", 33.3152) 
    lon = saved_profile.get("lon", 44.3661)
    
    report_text, _ = electional_engine.generate_detailed_report(user_text, lat, lon)
    
    back_markup = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="main_home")]])
    await update.message.reply_text(escape_markdown_v2(report_text), reply_markup=back_markup, parse_mode=ParseMode.MARKDOWN_V2)
    return ConversationHandler.END

# =====================================================================
# 7. محرك الخيرة الرقمية مع ميكانيكية الـ Dynamic BLAKE2b Seed
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
        except Exception:
            return {"good": [], "medium": [], "bad": []}

    def check_cooldown(self, user_id: int) -> int:
        current_time = time.time()
        if user_id in self.cooldowns:
            time_passed = current_time - self.cooldowns[user_id]
            if time_passed < self.cooldown_duration: return int((self.cooldown_duration - time_passed) // 60)
        return 0

    def get_seeded_khira(self, user_id: int, user_profile: dict) -> Dict[str, Any]:
        today_str = datetime.now().strftime("%Y-%m-%d")
        birth_str = f"{user_profile.get('year', 1990)}-{user_profile.get('month', 1)}-{user_profile.get('day', 1)}"
        seed_source = f"{user_id}_{birth_str}_{today_str}"
        
        hash_digest = hashlib.blake2b(seed_source.encode('utf-8'), digest_size=8).hexdigest()
        seed_int = int(hash_digest, 16)
        
        state = random.getstate()
        random.seed(seed_int)
        
        categories = ["good", "medium", "bad"]
        weights = [0.50, 0.30, 0.20]
        chosen_category = random.choices(categories, weights=weights, k=1)[0]
        options_list = self.khira_data.get(chosen_category, [])
        
        if not options_list:
            random.setstate(state)
            return {"verse": "يرجى التوكل على الله والعمل بالخير.", "stars": "⭐⭐⭐⭐", "interpretation": "الأبواب ميسرة ومباركة.", "dua": "اللهم صل على محمد وآل محمد"}
            
        chosen_item = random.choice(options_list)
        random.setstate(state) 
        self.cooldowns[user_id] = time.time()
        return chosen_item

    @staticmethod
    def get_main_keyboard():
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("🔮 طلب خيرة اليوم", callback_data="khira_request")],
            [InlineKeyboardButton("📜 شروط وآداب الخيرة", callback_data="khira_rules")],
            [InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="main_home")]
        ])

khira_engine = KhiraEngine()

# =====================================================================
# 8. إدارة الـ Lifespan، تنظيف الأقفال الخاملة لـ FastAPI
# =====================================================================
async def cache_and_locks_garbage_collector(interval: int = 300):
    """تنظيف الكاش منتهى الصلاحية وإزالة الأقفال الخاملة لمنع تسريب الذاكرة وتراكمها صامتاً"""
    while True:
        try:
            await asyncio.sleep(interval)
            CHART_CACHE.expire()
            
            # تطهير القواميس البرمجية للأقفال التي لم تعد قيد الانتظار لحل ثغرات الـ Race Conditions
            initial_count = len(_fixed_key_locks)
            for k in list(_fixed_key_locks.keys()):
                lock = _fixed_key_locks[k]
                if not lock.locked():
                    _fixed_key_locks.pop(k, None)
                    
            logger.info(f"🧹 [GC] Cache size: {len(CHART_CACHE)} | Cleared Locks: {initial_count - len(_fixed_key_locks)}")
            logger.info(f"📊 [METRICS LOG] Hits={METRICS['cache_hits']} Misses={METRICS['cache_misses']} Timeouts={METRICS['calculation_timeouts']}")
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"⚠️ Error during database cache gc loop: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    await async_db.connect()
    gc_task = asyncio.create_task(cache_and_locks_garbage_collector())
    
    await telegram_app.initialize()
    await telegram_app.bot.set_webhook(url=WEBHOOK_URL)
    logger.info(f"✅ Webhook applied securely to production: {WEBHOOK_URL}")
    await telegram_app.start()
    yield
    logger.info("🛑 Initiating graceful shutdown sequence...")
    gc_task.cancel()
    await asyncio.gather(gc_task, return_exceptions=True)
    
    chart_executor.shutdown(wait=True)
    drawing_executor.shutdown(wait=True)
    logger.info("✅ Tailored Variable ThreadPoolExecutors terminated.")
    
    if async_db.pool:
        await async_db.pool.close()
    await telegram_app.stop()
    await telegram_app.shutdown()
    logger.info("🏁 Core engines offline. Shutdown complete.")

app = FastAPI(lifespan=lifespan)

@app.post("/webhook")
async def webhook_handler(request: Request):
    try:
        data = await request.json()
        update = Update.de_json(data, telegram_app.bot)
        await telegram_app.update_queue.put(update)
    except Exception as e:
        logger.error(f"Error processing update via Queue: {e}", exc_info=True)
    return Response(status_code=200)

@app.get("/metrics")
async def export_internal_metrics():
    """تصدير المقاييس والعدادات للتمكين من ربطها مستقبلاً بـ Prometheus و Grafana"""
    return {
        "status": "healthy",
        "cache_capacity_used": len(CHART_CACHE),
        "active_locks_tracked": len(_fixed_key_locks),
        **METRICS
    }

# =====================================================================
# 9. إدارة لوحات الأزرار والـ Handlers الفرعية والقائمة الرئيسية
# =====================================================================
def get_start_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔮 قسم الأبراج والفلك", callback_data="go_astrology")],
        [InlineKeyboardButton("📖 قسم الخيرة الرقمية", callback_data="go_khira")]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    welcome_text = "🔮 *مرحباً بك في البوت الفلكي الشامل عالي الاعتمادية للإنتاج* 🔮\n\nالرجاء اختيار القسم من الأزرار أدناه:"
    await update.message.reply_text(welcome_text, reply_markup=get_start_keyboard(), parse_mode=ParseMode.MARKDOWN_V2)
    return ConversationHandler.END

async def khira_start_from_menu(query: Any, context: ContextTypes.DEFAULT_TYPE):
    welcome_khira = "✨ *خدمة الخيرة والاستخارة الرقمية المحصنة بالبصمة الحسابية الموحدة* ✨\n\nيرجى استحضار النية وقراءة سورة الفاتحة، ثم اضغط على الزر أدناه لبدء الخيرة\\."
    await query.edit_message_text(welcome_khira, reply_markup=khira_engine.get_main_keyboard(), parse_mode=ParseMode.MARKDOWN_V2)

async def astrology_trigger_workflow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer() 
    
    saved_profile = await async_db.get_user_profile(user_id)
    if saved_profile:
        await query.edit_message_text("✨ تم العثور على بيانات ميلادك المسجلة سابقاً\\! جاري الاستخراج فوراً\\.\\.\\.", parse_mode=ParseMode.MARKDOWN_V2)
        context.user_data.update(saved_profile)
        await process_and_send_astrology_report(chat_id=user_id, user_data=saved_profile, matched_city=saved_profile.get('city', 'Baghdad'))
        return ConversationHandler.END
    
    await query.edit_message_text("🔮 *نظام التحليل الفلكي الشامل*\n\nابدأ بإرسال *سنة ميلادك* بالأرقام \\(مثال: `1998`\\):", parse_mode=ParseMode.MARKDOWN_V2)
    return YEAR

async def p_year(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        val = int(update.message.text.strip())
        if not (1900 <= val <= datetime.now().year + 1): raise ValueError()
        context.user_data['year'] = val
    except ValueError:
        await update.message.reply_text("⚠️ سنة غير صالحة\\. أرسل سنة حقيقية بالأرقام:", parse_mode=ParseMode.MARKDOWN_V2)
        return YEAR
    await update.message.reply_text("📆 ممتاز\\! الآن أرسل *شهر ميلادك* \\(رقم من 1 إلى 12\\):", parse_mode=ParseMode.MARKDOWN_V2)
    return MONTH

async def p_month(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        val = int(update.message.text.strip())
        if not (1 <= val <= 12): raise ValueError()
        context.user_data['month'] = val
    except ValueError:
        await update.message.reply_text("⚠️ شهر غير صالح\\. يرجى إدخال رقم شهر حقيقي بين 1 و 12:", parse_mode=ParseMode.MARKDOWN_V2)
        return MONTH
    await update.message.reply_text("🗓 رائع\\! أرسل الآن *يوم ميلادك* برقم من \\(1 إلى 31\\):", parse_mode=ParseMode.MARKDOWN_V2)
    return DAY

async def p_day(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        val = int(update.message.text.strip())
        if not (1 <= val <= 31): raise ValueError()
        context.user_data['day'] = val
    except ValueError:
        await update.message.reply_text("⚠️ يوم غير صالح\\. يرجى إدخال رقم اليوم بشكل صحيح:", parse_mode=ParseMode.MARKDOWN_V2)
        return DAY
    keyboard = [[InlineKeyboardButton("✅ نعم، أعرفه بدقة", callback_data="knows_true")], [InlineKeyboardButton("❌ لا، غير معروف", callback_data="knows_false")]]
    await update.message.reply_text("🕒 هل تعرف *وقت ولادتك الدقيق*؟", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN_V2)
    return KNOWS_TIME

async def p_knows_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if query.data == "knows_true":
        await query.edit_message_text("🕓 أرسل وقت الولادة بتنسيق 24 ساعة \\(ساعة:دقيقة\\) مثال: `18:45`:", parse_mode=ParseMode.MARKDOWN_V2)
        return TIME
    else:
        context.user_data['hour'], context.user_data['minute'] = 12, 0
        await query.edit_message_text("📍 أرسل *اسم مدينة ميلادك* باللغة العربية أو الإنجليزية:", parse_mode=ParseMode.MARKDOWN_V2)
        return LOCATION

async def p_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        time_str = update.message.text.strip()
        hour, minute = map(int, time_str.split(':'))
        if not (0 <= hour <= 23 and 0 <= minute <= 59): raise ValueError()
        context.user_data['hour'], context.user_data['minute'] = hour, minute
    except ValueError:
        await update.message.reply_text("⚠️ تنسيق أو وقت خاطئ، يرجى إرساله مثل `14:30`:", parse_mode=ParseMode.MARKDOWN_V2)
        return TIME
    await update.message.reply_text("📍 أرسل *اسم مدينة ميلادك* باللغة العربية أو الإنجليزية:", parse_mode=ParseMode.MARKDOWN_V2)
    return LOCATION

async def p_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_input = update.message.text.strip()
    user_id = update.message.from_user.id
    matched_city, lat, lon, tz_resolved = local_geo.search_city(user_input)

    profile_to_save = {
        "year": context.user_data['year'], "month": context.user_data['month'], "day": context.user_data['day'],
        "hour": context.user_data['hour'], "minute": context.user_data['minute'], 
        "city": matched_city, "lat": lat, "lon": lon, "timezone": tz_resolved
    }
    context.user_data.update(profile_to_save)
    await async_db.save_user_profile(user_id, profile_to_save)
    await process_and_send_astrology_report(chat_id=user_id, user_data=profile_to_save, matched_city=matched_city)
    return ConversationHandler.END

async def handle_menu_clicks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data

    if data == "main_home":
        await query.answer()
        context.user_data.clear()
        await query.edit_message_text("🔮 *مرحباً بك في البوت الشامل المحدث* 🔮\n\nالرجاء اختيار القسم من الأزرار أدناه:", reply_markup=get_start_keyboard(), parse_mode=ParseMode.MARKDOWN_V2)
        return

    elif data == "reset_my_birthdata":
        await query.answer()
        await async_db.delete_user_profile(user_id)
        invalidate_user_old_cache(user_id, "natal")
        context.user_data.clear()
        await query.edit_message_text("🗑 تم مسح بيانات ميلادك السابقة بنجاح من قاعدة البيانات\\.\nيرجى إعادة إرسال /start لتسجيل بياناتك الحية من جديد\\.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 العودة للقائمة", callback_data="main_home")]]), parse_mode=ParseMode.MARKDOWN_V2)
        return

    elif data in ["go_khira", "khira_back"]:
        await query.answer()
        await khira_start_from_menu(query, context)
        return

    elif data == "khira_request":
        saved_profile = await async_db.get_user_profile(user_id)
        if not saved_profile:
            await query.answer("⚠️ يرجى تعبئة ملفك الشخصي الفلكي أولاً من القائمة لتفعيل الخيرة الديناميكية.", show_alert=True)
            return

        remaining = khira_engine.check_cooldown(user_id)
        if remaining > 0:
            await query.answer(f"⚠️ انتظر {remaining} دقيقة أو تدبر في نتيجتك الحالية أولاً.", show_alert=True)
            return
            
        chosen = khira_engine.get_seeded_khira(user_id, saved_profile)
        result_text = f"🔮 *نتيجـة الخيـرة الخاصـة بك لهذا اليوم*\n━━━━━━━━━━━━━━━━━━━━\n\n📖 *الآية الشريفة:*\n__{escape_markdown_v2(chosen.get('verse', ''))}__\n\n📊 *الحكم والدرجة:*\nدرجة التيسير: {escape_markdown_v2(chosen.get('stars', ''))}\n\n💬 *التوجيه والتفسير:*\n{escape_markdown_v2(chosen.get('interpretation', ''))}\n\n🤲 *الدعاء المستحب:*\n_{escape_markdown_v2(chosen.get('dua', ''))}_\n\n━━━━━━━━━━━━━━━━━━━━"
        await query.edit_message_text(result_text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ العودة لقائمة الخيرة", callback_data="khira_back")]]), parse_mode=ParseMode.MARKDOWN_V2)
        return

    elif data == "khira_rules":
        await query.answer()
        rules_text = "📜 *آداب وشروط عمل الخيرة:*\n━━━━━━━━━━━━━━━━━━━━\n1️⃣ *النية الصادقة والوضوء*\n2️⃣ *عدم التكرار في نفس الأمر في ذات اليوم*\n3️⃣ *الرضا بالنتيجة وتسليم الأمر لله\\.*"
        await query.edit_message_text(rules_text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ العودة لقائمة الخيرة", callback_data="khira_back")]]), parse_mode=ParseMode.MARKDOWN_V2)
        return

    saved_profile = await async_db.get_user_profile(user_id)
    if not saved_profile:
        await query.message.reply_text("❌ لم يتم العثور على بيانات، اضغط على /start لبدء الحساب مجدداً\\.", parse_mode=ParseMode.MARKDOWN_V2)
        return

    chart_data = await get_or_compute_user_chart(user_id, saved_profile, engine)
    astrology_back_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("✨ الأبراج وحظك اليوم", callback_data="menu_horoscope_daily")],
        [InlineKeyboardButton("📜 قراءة برجك والتحليل الكامل", callback_data="menu_read_all")],
        [InlineKeyboardButton("📅 التوقعات الحية اليومية (Transits)", callback_data="menu_daily_forecast")],
        [InlineKeyboardButton("⏱ تحديد اليوم والساعة الأنسب لقراراتك", callback_data="start_electional_flow")],
        [InlineKeyboardButton("🖼 توليد الخريطة الفلكية (صورة)", callback_data="menu_generate_image")],
        [InlineKeyboardButton("💞 قياس التوافق مع شريك (Synastry)", callback_data="start_synastry_flow")],
        [InlineKeyboardButton("🔄 تعديل بيانات ميلادي", callback_data="reset_my_birthdata")],
        [InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="main_home")]
    ])

    try:
        if data == "menu_horoscope_daily":
            await query.answer()
            sun_sign = "Aries"
            if hasattr(chart_data, 'planets') and chart_data.planets and chart_data.planets.get('Sun'):
                sun_sign = getattr(chart_data.planets.get('Sun'), 'sign', 'Aries')
            horoscope_report = HoroscopeDailyEngine.get_daily_forecast(sun_sign)
            await query.edit_message_text(escape_markdown_v2(horoscope_report), reply_markup=astrology_back_markup, parse_mode=ParseMode.MARKDOWN_V2)

        elif data == "menu_daily_forecast":
            await query.answer()
            forecast_report = TransitEngine.generate_daily_forecast(chart_data)
            await query.edit_message_text(escape_markdown_v2(forecast_report), reply_markup=astrology_back_markup, parse_mode=ParseMode.MARKDOWN_V2)

        elif data == "menu_read_all":
            await query.answer()
            full_report = interpreter.get_detailed_report(chart_data)
            asc_sign = getattr(chart_data, 'ascendant', 'Aries')
            complete_analysis = f"🪐 *التقرير الفلكي الشامل والكامل لخريطتك* 🪐\n━━━━━━━━━━━━━━━━━━━━\n• *البرج الصاعد \\(الطالع\\):* {escape_markdown_v2(asc_sign)}\n━━━━━━━━━━━━━━━━━━━━\n\n{full_report}"
            
            if len(complete_analysis) > 4000:
                parts = [complete_analysis[i:i+4000] for i in range(0, len(complete_analysis), 4000)]
                for i, part in enumerate(parts):
                    if i == len(parts) - 1: await query.message.reply_text(part, reply_markup=astrology_back_markup, parse_mode=ParseMode.MARKDOWN_V2)
                    else: await telegram_app.bot.send_message(chat_id=user_id, text=part, parse_mode=ParseMode.MARKDOWN_V2)
            else:
                await query.edit_message_text(complete_analysis, reply_markup=astrology_back_markup, parse_mode=ParseMode.MARKDOWN_V2)

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
                        self.aspects = getattr(raw_chart, 'aspects', [])

                adapted_chart = FlexibleChartAdapter(chart_data)
                img_bytes_data = await draw_chart_safe(drawer, adapted_chart, user_id)
                
                if not img_bytes_data:
                    await query.message.reply_text("⚠️ المحرك لم يقم بتوليد مخرجات رسومية صالحة حالياً\\.", reply_markup=astrology_back_markup, parse_mode=ParseMode.MARKDOWN_V2)
                    return

                img_buffer = io.BytesIO(img_bytes_data)
                img_buffer.name = "natal_chart.png"
                await telegram_app.bot.send_photo(chat_id=user_id, photo=img_buffer, caption="🪐 *عجلة خريطتك الفلكية الاحترافية كاملة الدلالات \\(Natal Wheel\\)*", reply_markup=astrology_back_markup)
            except Exception as draw_err:
                logger.error(f"Error drawing chart for user={user_id}: {draw_err}")
                await query.message.reply_text("⚠️ تعذر توليد الصورة حالياً، يرجى مراجعة التقرير النصي المعروض\\.", reply_markup=astrology_back_markup, parse_mode=ParseMode.MARKDOWN_V2)
    except Exception as exc:
        logger.error(f"Error handling menu click for user={user_id}: {exc}")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("🚫 تم إلغاء العملية الحالية بنجاح\\. ارسل /start للبدء مجدداً\\.", parse_mode=ParseMode.MARKDOWN_V2)
    return ConversationHandler.END

# =====================================================================
# 10. ربط الـ Handlers وبناء الـ Conversation بالكامل
# =====================================================================
conv_handler = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(astrology_trigger_workflow, pattern="^go_astrology$"),
        CallbackQueryHandler(synastry_trigger_workflow, pattern="^start_synastry_flow$"),
        CallbackQueryHandler(electional_trigger_workflow, pattern="^start_electional_flow$")
    ],
    states={
        YEAR: [MessageHandler(filters.TEXT & ~filters.COMMAND, p_year)],
        MONTH: [MessageHandler(filters.TEXT & ~filters.COMMAND, p_month)],
        DAY: [MessageHandler(filters.TEXT & ~filters.COMMAND, p_day)],
        KNOWS_TIME: [CallbackQueryHandler(p_knows_time)],
        TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, p_time)],
        LOCATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, p_location)],
        
        P2_YEAR: [MessageHandler(filters.TEXT & ~filters.COMMAND, p2_year)],
        P2_MONTH: [MessageHandler(filters.TEXT & ~filters.COMMAND, p2_month)],
        P2_DAY: [MessageHandler(filters.TEXT & ~filters.COMMAND, p2_day)],
        P2_KNOWS_TIME: [CallbackQueryHandler(p2_knows_time)],
        P2_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, p2_time)],
        P2_LOCATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, p2_location)],
        
        ELECTIONAL_QUERY: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_electional_query_analysis)]
    },
    fallbacks=[CommandHandler('cancel', cancel)],
    per_message=False,
    allow_reentry=True
)

telegram_app.add_handler(CommandHandler('start', start))
telegram_app.add_handler(conv_handler)
telegram_app.add_handler(CallbackQueryHandler(handle_menu_clicks, pattern="^(?!(go_astrology|start_synastry_flow|start_electional_flow)$).*"))
