import logging
import os
import io
import json
from datetime import datetime
from contextlib import asynccontextmanager
from typing import Dict, Any, List

from fastapi import FastAPI, Request, Response
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode  # التصحيح هنا: استيراد مود البارس الصحيح مباشرة
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
# محرك التحليل الفلكي التركيبي الذكي (النقلة التقنية للمحترفين)
# =====================================================================
class AstrologySynthesisEngine:
    def __init__(self, json_path: str = "interpretations.json"):
        self.json_path = json_path
        self.interpretations = self.load_interpretations()
        self.connectors = [
            " يتكامل this التموقع بعمق مع وجوده في ",
            "، الأمر الذي ينعكس بشكل مباشر على شؤون ",
            "، مما يمنح طاقة هذا الكوكب تجسيداً عملياً داخل ",
            " ليصبح مسرحاً رئيسياً لـ "
        ]

    def load_interpretations(self) -> Dict[str, Any]:
        try:
            with open(self.json_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading JSON file: {e}")
            return {}

    def calculate_element_balance(self, birth_data: Dict[str, str]) -> str:
        elements = {"نارية": 0, "ترابية": 0, "هوائية": 0, "مائية": 0}
        element_mapping = {
            "Aries": "نارية", "Leo": "نارية", "Sagittarius": "نارية",
            "Taurus": "ترابية", "Virgo": "ترابية", "Capricorn": "ترابية",
            "Gemini": "هوائية", "Libra": "هوائية", "Aquarius": "هوائية",
            "Cancer": "مائية", "Scorpio": "مائية", "Pisces": "مائية"
        }
        
        for planet in ["Sun", "Moon", "Mercury", "Venus", "Mars"]:
            sign = birth_data.get(planet)
            if sign in element_mapping:
                elements[element_mapping[sign]] += 1
                
        dominant_element = max(elements, key=elements.get)
        balance_reports = {
            "نارية": "🔥 تفوح خريطتك بطاقة نارية دافقة، مما يمنحك روحاً مبادرة، حماساً اشتعالياً، ورغبة مستمرة في قيادة واقعك وتحدي الركود.",
            "ترابية": "🪵 تهيمن العناصر الترابية على بنيتك الفلكية، مما يجعلك شخصاً شديد الواقعية، يبحث عن الأمان الملموس، ويتقن الصبر وبناء الاستقرار طويل الأمد.",
            "هوائية": "💨 طغيان الطابع الهوائي يمنحك عقلاً حاداً، وفضولاً معرفياً لا يهدأ، حيث تتنفس عبر الأفكار، التواصل، والتحليل المستمر للمحيط.",
            "مائية": "💧 الغلبة هنا للعنصر المائي؛ أنت تسبح في عالم من الحدس، المشاعر العميقة، والامتصاص النفسي لطاقات الآخرين، مما يمنحك بصيرة شفائية استثنائية."
        }
        return balance_reports.get(dominant_element, "")

    def detect_psychological_conflicts(self, birth_data: Dict[str, str]) -> List[str]:
        conflicts = []
        sun = birth_data.get("Sun")
        moon = birth_data.get("Moon")
        
        if sun == "Leo" and moon in ["Virgo", "Cancer", "Scorpio"]:
            conflicts.append(
                "🔄 **تناقض الهوية الداخلي:** تختبر صراعاً صامتاً بين شمسك في الأسد التي تعشق التقدير والظهور، وبين قمرك الباطني الذي يميل للتحفظ، الخصوصية، والتحليل خلف الكواليس."
            )
        if sun == "Aries" and moon == "Libra":
            conflicts.append(
                "🔄 **محور المواجهة والسلام:** روحك ممزقة بين رغبة شمسك في الحسم والمواجهة الشجاعة المباشرة، وبين حاجة قمرك في الميزان للمداراة، الدبلوماسية، والحفاظ على السلم مع الآخرين بأي ثمن."
            )
        return conflicts

    def synthesize_astrology_report(self, birth_data: Dict[str, str]) -> List[str]:
        messages_to_send = []
        header = "🔮 **التحليل الفلكي التركيبي للمحترفين** 🔮\n\n"
        header += self.calculate_element_balance(birth_data) + "\n\n"
        
        conflicts = self.detect_psychological_conflicts(birth_data)
        if conflicts:
            header += "⚠️ **رادار البصيرة الفلكية (التناقضات المكتشفة):**\n" + "\n".join(conflicts) + "\n\n"
            
        header += "📌 **التشريح التفصيلي للمواضع الفلكية:**\n"
        current_chunk = header
        
        for planet, sign in birth_data.items():
            if planet in ["house_1", "house_2"] or "_house" in planet:
                continue
                
            house = birth_data.get(f"{planet}_house", "1")
            sign_text = self.interpretations.get(planet, {}).get(sign, "")
            house_text = self.interpretations.get(planet, {}).get(str(house), "")
            
            if sign_text and house_text:
                combined_analysis = f"🪐 **{planet} في {sign} داخل البيت {house}:**\n{sign_text}{self.connectors[1]}{house}\n↳ *العمق الاستراتيجي:* {house_text}\n\n"
                
                if len(current_chunk) + len(combined_analysis) > 3500:
                    messages_to_send.append(current_chunk)
                    current_chunk = combined_analysis
                else:
                    current_chunk += combined_analysis
                    
        if current_chunk:
            messages_to_send.append(current_chunk)
            
        return messages_to_send


# كائن وسيط مرن لتخطي قيود Pydantic وتوحيد أسماء الحقول لملف الرسم
class FlexibleChartAdapter:
    def __init__(self, raw_chart: Any):
        self.ascendant = getattr(raw_chart, 'ascendant', 'Aries')
        self.ascendant_degree = getattr(raw_chart, 'ascendant_degree', 0.0)
        self.midheaven_degree = getattr(raw_chart, 'midheaven_degree', 270.0)
        self.houses = getattr(raw_chart, 'houses', {})
        
        # نسخ وتكييف الكواكب
        self.planets = {}
        raw_planets = getattr(raw_chart, 'planets', {})
        for p_name, p_data in raw_planets.items():
            class PlanetAdapter:
                def __init__(self, data):
                    self.longitude = getattr(data, 'longitude', getattr(data, 'abs_degree', getattr(data, 'degree', 0.0)))
            self.planets[p_name] = PlanetAdapter(p_data)
            
        # نسخ وتكييف الاتصالات (Aspects)
        self.aspects = []
        raw_aspects = getattr(raw_chart, 'aspects', [])
        for aspect in raw_aspects:
            class AspectAdapter:
                def __init__(self, asp):
                    self.p1 = getattr(asp, 'p1', getattr(asp, 'planet1', getattr(asp, 'p1_name', None)))
                    self.p2 = getattr(asp, 'p2', getattr(asp, 'planet2', getattr(asp, 'p2_name', None)))
                    self.type = getattr(asp, 'type', getattr(asp, 'aspect_type', 'Conjunction'))
                    self.orb = getattr(asp, 'orb', 0.0)
            
            adapted_asp = AspectAdapter(aspect)
            if adapted_asp.p1 and adapted_asp.p2:
                self.aspects.append(adapted_asp)

# 4. إدارة دورة حياة FastAPI والتليجرام (Lifespan)
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
    return {"status": "healthy", "bot": "Astrology Bot is running via Webhook"}

# --- منطق المحادثة الفلكية والمراحل ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "🔮 **مرحباً بك في نظام التحليل الفلكي الشامل**\n\n"
        "سنقوم بإعداد خريطتك الشخصية العميقة واستخراج ملامحك الفلكية بدقة.\n"
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
        await query.edit_message_text("📍 أرسل الإحداثيات الجغرافية لمكان ميلادك بتنسيق (خط العرض,خط الطول) مثال: `36.34,43.13`:")
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

    await update.message.reply_text("📍 أرسل الإحداثيات الجغرافية لمكان ميلادك بتنسيق (خط العرض,خط الطول) مثال: `36.34,43.13`:")
    return LOCATION

async def p_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        loc_str = update.message.text.strip()
        lat, lon = map(float, loc_str.split(','))
    except ValueError:
        await update.message.reply_text("⚠️ التنسيق خاطئ، يرجى الإرسال هكذا `36.34,43.13`:")
        return LOCATION

    dt_utc = datetime(
        context.user_data['year'],
        context.user_data['month'],
        context.user_data['day'],
        context.user_data['hour'],
        context.user_data['minute']
    )
    
    await update.message.reply_text("⏳ جاري استخراج البيانات وحساب المواقع الفلكية من المصادر الرسمية...")

    try:
        # 1. حساب الخريطة الأساسية من محرك السويس إيفيمريس
        chart_data = engine.compute_natal_chart(dt_utc, lat, lon)
        
        # 2. استخراج وفحص النقاط من محرك القواعد
        facts = [] 
        score_data = RulesEngine.evaluate(facts)
        total_score = score_data.total_score 

        # حفظ البيانات والسكور منفصلين داخل جلسة المستخدم الحالية
        context.user_data['last_chart'] = chart_data
        context.user_data['last_score'] = total_score

        # 3. توليد الرسم بصيغة بايتات PNG حقيقية مباشرة عبر Pillow لمنع مشاكل العرض تماماً
        try:
            adapted_chart = FlexibleChartAdapter(chart_data)
            img_bytes_data = drawer.generate_chart_png(adapted_chart)
            
            img_buffer = io.BytesIO(img_bytes_data)
            img_buffer.name = "natal_chart.png"
            
            await update.message.reply_photo(
                photo=img_buffer,
                caption="🪐 **عجلة خريطتك الفلكية الحقيقية (Natal Wheel)**\nتم رسمها هندسياً بدقة بالغة اعتماداً على درجات أجرامك وأوتادك الحقيقية لحظة ميلادك."
            )
        except Exception as draw_err:
            logger.error(f"Error during chart drawing: {draw_err}", exc_info=True)
            await update.message.reply_text("⚠️ تم حساب بياناتك بنجاح ولكن تعذر توليد الصورة، جاري إرسال التقرير النصي...")

        # 4. حل مشكلة دالة التفسير النصي للمستخدم
        summary_msg = interpreter.get_minimal_summary(chart_data)
        score_display = "🚧 قيد الحساب" if total_score == 0 else f"{total_score}"
        summary_msg = summary_msg.replace("SCORE_PLACEHOLDER", score_display)
        
        # 5. بناء مصفوفة الأزرار الجذابة التشويقية
        keyboard = [
            [InlineKeyboardButton("🧠 شخصيتك الحقيقية", callback_data="menu_personal"), InlineKeyboardButton("❤️ الحب والزواج", callback_data="menu_love")],
            [InlineKeyboardButton("💼 المهنة المناسبة", callback_data="menu_career"), InlineKeyboardButton("💰 المال والثروة", callback_data="menu_money")],
            [InlineKeyboardButton("🌟 نقاط القوة والضعف", callback_data="menu_features"), InlineKeyboardButton("🔮 التوقعات", callback_data="menu_predict")],
            [InlineKeyboardButton("🪐 الخريطة الكاملة (للمحترفين)", callback_data="menu_full_chart")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(summary_msg, reply_markup=reply_markup, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Error during calculations: {e}", exc_info=True)
        await update.message.reply_text("❌ عذراً، حدث خطأ أثناء معالجة البيانات الفلكية داخلياً.")

    return ConversationHandler.END

async def handle_menu_clicks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    chart_data = context.user_data.get('last_chart')
    if not chart_data:
        await query.answer()
        await query.message.reply_text("❌ انتهت صلاحية الجلسة، من فضلك أعد حساب الخريطة باستخدام الأمر /start")
        return

    # زر العودة إلى القائمة الرئيسية
    if query.data == "menu_back":
        await query.answer()
        summary_msg = interpreter.get_minimal_summary(chart_data)
        total_score = context.user_data.get('last_score', 0)
        score_display = "🚧 قيد الحساب" if total_score == 0 else f"{total_score}"
        summary_msg = summary_msg.replace("SCORE_PLACEHOLDER", score_display)
            
        keyboard = [
            [InlineKeyboardButton("🧠 شخصيتك الحقيقية", callback_data="menu_personal"), InlineKeyboardButton("❤️ الحب والزواج", callback_data="menu_love")],
            [InlineKeyboardButton("💼 المهنة المناسبة", callback_data="menu_career"), InlineKeyboardButton("💰 المال والثروة", callback_data="menu_money")],
            [InlineKeyboardButton("🌟 نقاط القوة والضعف", callback_data="menu_features"), InlineKeyboardButton("🔮 التوقعات", callback_data="menu_predict")],
            [InlineKeyboardButton("🪐 الخريطة الكاملة (للمحترفين)", callback_data="menu_full_chart")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(summary_msg, reply_markup=reply_markup, parse_mode="Markdown")
        return

    back_markup = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ العودة للقائمة الرئيسية", callback_data="menu_back")]])

    # استخراج التقرير الشامل لتفكيكه وتصفيته بحسب كواكب كل قسم معني
    full_report = interpreter.get_detailed_report(chart_data)
    
    def extract_planets_info(report_text, target_planets):
        sections = report_text.split("---")
        extracted = []
        for section in sections:
            if any(planet in section for planet in target_planets):
                extracted.append(section.strip())
        if extracted:
            return "\n\n---\n\n".join(extracted)
        return "⚠️ تفاصيل هذا القسم مدمجة في تقرير خريطتك الكاملة."

    try:
        # 1. زر الشخصية الحقيقية (يسحب الشمس والقمر والطالع)
        if query.data == "menu_personal":
            await query.answer()
            asc_sign = getattr(chart_data, 'ascendant', 'غير معروف')
            planets_data = extract_planets_info(full_report, ["الشمس", "القمر"])
            report = (
                f"🧠 **تحليل شخصيتك الحقيقية والفريدة**\n\n"
                f"• **البرج الصاعد (الطالع):** {asc_sign}\n\n"
                f"**المواقع والمؤشرات النفسية لجوهر شخصيتك الحالية:**\n\n"
                f"{planets_data}"
            )
            await query.edit_message_text(report, reply_markup=back_markup, parse_mode="Markdown")

        # 2. زر الحب والزواج (يسحب الزهرة ونبتون والبيت 7)
        elif query.data == "menu_love":
            await query.answer()
            planets_data = extract_planets_info(full_report, ["الزهرة", "البيت 7", "نبتون"])
            report = (
                "❤️ **تحليل العلاقات، الحب والشراكات العاطفية**\n\n"
                "إليك الجوانب الفلكية الحاكمة لطاقتك العاطفية والارتباط في خريطتك:\n\n"
                f"{planets_data}"
            )
            await query.edit_message_text(report, reply_markup=back_markup, parse_mode="Markdown")

        # 3. زر المهنة المناسبة (يسحب المريخ وعطارد والبيت 6 أو 11)
        elif query.data == "menu_career":
            await query.answer()
            planets_data = extract_planets_info(full_report, ["المريخ", "عطارد", "البيت 6", "البيت 11"])
            report = (
                "💼 **المسار المهني، بيئة العمل والإنتاجية الاحترافية**\n\n"
                "الكواكب المسؤولة عن مجالات نجاحك، وتعاملك مع المسؤوليات والزملاء:\n\n"
                f"{planets_data}"
            )
            await query.edit_message_text(report, reply_markup=back_markup, parse_mode="Markdown")

        # 4. زر المال والثروة (يسحب زحل والمشتري والبيت 2)
        elif query.data == "menu_money":
            await query.answer()
            planets_data = extract_planets_info(full_report, ["زحل", "المشتري", "البيت 2"])
            report = (
                "💰 **التحليل المالي، إدارة الثروة وفرص الوفرة**\n\n"
                "مواقع الكواكب والبيوت الحاكمة لوضعك المالي ومجهودك الشخصي لإحراز المكتسبات:\n\n"
                f"{planets_data}"
            )
            await query.edit_message_text(report, reply_markup=back_markup, parse_mode="Markdown")

        # 5. زر نقاط القوة والضعف (يسحب تشيرون وليليث وعطارد)
        elif query.data == "menu_features":
            await query.answer()
            planets_data = extract_planets_info(full_report, ["تشيرون", "ليليث", "عطارد"])
            report = (
                "🌟 **تحليل نقاط القوة، التحديات والمخاوف النفسية الباطنية**\n\n"
                "يكشف التوزيع الفلكي عن مواضع قوتك العقلية وجراحك الكرمية العميقة:\n\n"
                f"{planets_data}"
            )
            await query.edit_message_text(report, reply_markup=back_markup, parse_mode="Markdown")

        # 6. زر التوقعات (يسحب أورانوس وبلوتو والعقد الفلكية)
        elif query.data == "menu_predict":
            await query.answer()
            planets_data = extract_planets_info(full_report, ["أورانوس", "بلوتو", "العقدة الشمالية", "العقدة الجنوبية"])
            report = (
                "🔮 **مؤشرات التغيير، التوقعات والتحولات الكرمية**\n\n"
                "تأثير أجرام التحول الجذري ومسارات التطور الروحي في خريطتك الحالية:\n\n"
                f"{planets_data}"
            )
            await query.edit_message_text(report, reply_markup=back_markup, parse_mode="Markdown")

        # 7. زر الخريطة الكاملة للمحترفين (تفعيل الخوارزمية التركيبية المقسمة)
        elif query.data == "menu_full_chart":
            await query.answer("جاري استخلاص وقراءة موازين الخريطة الفلكية لوضع المحترفين...")
            
            raw_planets = getattr(chart_data, 'planets', {})
            birth_map_data = {}
            for p_name, p_data in raw_planets.items():
                birth_map_data[p_name] = getattr(p_data, 'sign', 'Aries')
                birth_map_data[f"{p_name}_house"] = str(getattr(p_data, 'house', '1'))
            
            synthesis_engine = AstrologySynthesisEngine()
            chunks = synthesis_engine.synthesize_astrology_report(birth_map_data)
            
            user_id = query.from_user.id
            
            for i, chunk in enumerate(chunks):
                if i == 0:
                    await query.edit_message_text(chunk, parse_mode=ParseMode.MARKDOWN)
                else:
                    await telegram_app.bot.send_message(chat_id=user_id, text=chunk, parse_mode=ParseMode.MARKDOWN)
                    
            await telegram_app.bot.send_message(
                chat_id=user_id,
                text="✨ **انتهى تقرير المحترفين الشامل.** يمكنك الآن العودة للقائمة الرئيسية:",
                reply_markup=back_markup
            )
            
    except Exception as exc:
        logger.error(f"Error handling menu click {query.data}: {exc}", exc_info=True)
        await query.message.reply_text("⚠️ عذراً، جاري تحديث الفلترة الفلكية، يمكنك مراجعة التقرير الشامل مباشرة.")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("🚫 تم إلغاء العملية. يمكنك البدء من جديد بإرسال /start")
    return ConversationHandler.END

# 5. تسجيل ومعالجة الـ Handlers
conv_handler = ConversationHandler(
    entry_points=[CommandHandler('start', start)],
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

telegram_app.add_handler(conv_handler)
telegram_app.add_handler(CallbackQueryHandler(handle_menu_clicks, pattern="^menu_"))
