# -*- coding: utf-8 -*-
"""
محرك الاختيارات التنجيمية الاحترافي - نسخة تقنية موسّعة (Engine v2)
=====================================================================
يعتمد بالكامل على قواعد التنجيم التقليدي الكلاسيكي (Traditional / Classical
Astrology) وحسابات فلكية-رياضية صريحة. لا يوجد أي استدعاء لنموذج ذكاء
اصطناعي أو توليد نصي احتمالي في أي جزء من هذا الملف - كل نتيجة قابلة
لإعادة الاشتقاق يدوياً من الجداول والمعادلات المذكورة أدناه.

أهم الإضافات التقنية مقارنة بالنسخة السابقة:
    1) الكرامات الأساسية الخمس كاملة (Domicile / Exaltation / Triplicity /
       Term / Face) بدل بيت وشرف فقط، مع جدول الحدود المصرية (Egyptian
       Terms) وجدول الوجوه الكلداني (Chالداني Faces) الكاملين.
    2) الكرامات العرضية (Accidental Dignity): زاوية البيت، السرعة/البطء،
       الاتجاه المباشر/التراجعي/التوقف (Station)، الاحتراق التام مقابل
       الكازيمي (Cazimi) مقابل "تحت الأشعة" (Under the Beams)، والحصار
       بين نحسين (Besiegement).
    3) رصد القِران المتبادل (Mutual Reception) بين الكواكب الحاكمة.
    4) حساب الشروق والغروب الفلكي الحقيقي لأي إحداثيات جغرافية عبر معادلة
       الشروق/الغروب القياسية (Sunrise Equation)، ثم اشتقاق الساعات
       العربية غير المتساوية (Unequal/Planetary Hours) منها بدل افتراض
       شروق ثابت الساعة 6:00.
    5) منازل القمر الثماني والعشرون (منازل القمر العربية التقليدية) كطبقة
       معلوماتية إضافية على موضع القمر.
    6) نظام تقييم مرجّح (Weighted Scoring) قابل للتهيئة بالكامل، يُرجع
       تفصيلاً بنيوياً (breakdown) وليس نصاً فقط، لتسهيل التدقيق والاختبار.

تنويه منهجي: هذا الملف "تنجيم تقليدي" حاسوبي بحت (قواعد ثابتة + رياضيات)،
وليس تنبؤاً علمياً مثبتاً. تم توسيعه تقنياً بناءً على طلب صريح، ولا يمثل
تأييداً لصحة الادعاءات التنبؤية.
"""

import logging
import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# =====================================================================
# 1) الثوابت الفلكية والتنجيمية الأساسية
# =====================================================================

ZODIAC_SIGNS: List[str] = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]

ZODIAC_SIGNS_AR: Dict[str, str] = {
    "Aries": "الحمل", "Taurus": "الثور", "Gemini": "الجوزاء", "Cancer": "السرطان",
    "Leo": "الأسد", "Virgo": "العذراء", "Libra": "الميزان", "Scorpio": "العقرب",
    "Sagittarius": "القوس", "Capricorn": "الجدي", "Aquarius": "الدلو", "Pisces": "الحوت",
}

CHALDEAN_ORDER: List[str] = ["Saturn", "Jupiter", "Mars", "Sun", "Venus", "Mercury", "Moon"]

# ترتيب الأيام حسب توقيت بايثون: الإثنين=0 ... الأحد=6
WEEKDAY_TO_PLANET: Dict[int, str] = {
    0: "Moon", 1: "Mars", 2: "Mercury", 3: "Jupiter", 4: "Venus", 5: "Saturn", 6: "Sun",
}

# --- الكرامات الأساسية: البيت والشرف والوبال والهبوط ---
DOMICILE: Dict[str, List[str]] = {
    "Sun": ["Leo"], "Moon": ["Cancer"],
    "Mercury": ["Gemini", "Virgo"], "Venus": ["Taurus", "Libra"],
    "Mars": ["Aries", "Scorpio"], "Jupiter": ["Sagittarius", "Pisces"],
    "Saturn": ["Capricorn", "Aquarius"],
}
EXALTATION: Dict[str, Tuple[str, float]] = {
    # (البرج، الدرجة المثلى للشرف - Exact Exaltation Degree)
    "Sun": ("Aries", 19.0), "Moon": ("Taurus", 3.0), "Mercury": ("Virgo", 15.0),
    "Venus": ("Pisces", 27.0), "Mars": ("Capricorn", 28.0),
    "Jupiter": ("Cancer", 15.0), "Saturn": ("Libra", 21.0),
}
DETRIMENT: Dict[str, List[str]] = {
    "Sun": ["Aquarius"], "Moon": ["Capricorn"],
    "Mercury": ["Sagittarius", "Pisces"], "Venus": ["Scorpio", "Aries"],
    "Mars": ["Libra", "Taurus"], "Jupiter": ["Gemini", "Virgo"],
    "Saturn": ["Cancer", "Leo"],
}
FALL: Dict[str, str] = {
    "Sun": "Libra", "Moon": "Scorpio", "Mercury": "Pisces", "Venus": "Virgo",
    "Mars": "Cancer", "Jupiter": "Capricorn", "Saturn": "Aries",
}

# --- الثلاثيات (Triplicity Rulers) حسب نظام دوروثيوس/بطليموس التقليدي ---
# (حاكم نهاري، حاكم ليلي، حاكم مُشارك)
TRIPLICITY: Dict[str, Dict[str, Optional[str]]] = {
    "fire":  {"signs": ["Aries", "Leo", "Sagittarius"], "day": "Sun", "night": "Jupiter", "participating": "Saturn"},
    "earth": {"signs": ["Taurus", "Virgo", "Capricorn"], "day": "Venus", "night": "Moon", "participating": "Mars"},
    "air":   {"signs": ["Gemini", "Libra", "Aquarius"], "day": "Saturn", "night": "Mercury", "participating": "Jupiter"},
    "water": {"signs": ["Cancer", "Scorpio", "Pisces"], "day": "Venus", "night": "Mars", "participating": "Moon"},
}

# --- الحدود المصرية (Egyptian Terms/Bounds): (نهاية الدرجة، الكوكب الحاكم) ---
EGYPTIAN_TERMS: Dict[str, List[Tuple[float, str]]] = {
    "Aries":       [(6, "Jupiter"), (12, "Venus"), (20, "Mercury"), (25, "Mars"), (30, "Saturn")],
    "Taurus":      [(8, "Venus"), (14, "Mercury"), (22, "Jupiter"), (27, "Saturn"), (30, "Mars")],
    "Gemini":      [(6, "Mercury"), (12, "Jupiter"), (17, "Venus"), (24, "Mars"), (30, "Saturn")],
    "Cancer":      [(7, "Mars"), (13, "Venus"), (19, "Mercury"), (26, "Jupiter"), (30, "Saturn")],
    "Leo":         [(6, "Jupiter"), (11, "Venus"), (18, "Saturn"), (24, "Mercury"), (30, "Mars")],
    "Virgo":       [(7, "Mercury"), (17, "Venus"), (21, "Jupiter"), (28, "Mars"), (30, "Saturn")],
    "Libra":       [(6, "Saturn"), (14, "Mercury"), (21, "Jupiter"), (28, "Venus"), (30, "Mars")],
    "Scorpio":     [(7, "Mars"), (11, "Venus"), (19, "Mercury"), (24, "Jupiter"), (30, "Saturn")],
    "Sagittarius": [(12, "Jupiter"), (17, "Venus"), (21, "Mercury"), (26, "Saturn"), (30, "Mars")],
    "Capricorn":   [(7, "Mercury"), (14, "Jupiter"), (22, "Venus"), (26, "Saturn"), (30, "Mars")],
    "Aquarius":    [(7, "Mercury"), (13, "Venus"), (20, "Jupiter"), (25, "Mars"), (30, "Saturn")],
    "Pisces":      [(12, "Venus"), (16, "Jupiter"), (19, "Mercury"), (28, "Mars"), (30, "Saturn")],
}

# --- الوجوه/الديكانات الكلدانية (Chaldean Faces): 36 وجهاً بدورة سبع كواكب ---
_FACE_CYCLE = ["Mars", "Sun", "Venus", "Mercury", "Moon", "Saturn", "Jupiter"]

# --- منازل القمر الثماني والعشرون (كل منزلة = 360/28 درجة تبدأ من 0° الحمل) ---
LUNAR_MANSIONS_AR: List[str] = [
    "الشرطين", "البطين", "الثريا", "الدبران", "الهقعة", "الهنعة", "الذراع",
    "النثرة", "الطرف", "الجبهة", "الزبرة", "الصرفة", "العواء", "السماك",
    "الغفر", "الزبانى", "الإكليل", "القلب", "الشولة", "النعائم", "البلدة",
    "سعد الذابح", "سعد بلع", "سعد السعود", "سعد الأخبية",
    "الفرغ المقدم", "الفرغ المؤخر", "بطن الحوت",
]
_MANSION_WIDTH = 360.0 / 28.0

# --- زوايا الاتصالات ونصف قطر التأثير (Orb) لكل كوكب ---
ASPECT_ANGLES: Dict[str, float] = {
    "conjunction": 0.0, "sextile": 60.0, "square": 90.0, "trine": 120.0, "opposition": 180.0,
}
PLANET_ORB: Dict[str, float] = {
    "Sun": 15.0, "Moon": 12.0, "Mercury": 7.0, "Venus": 7.0,
    "Mars": 8.0, "Jupiter": 9.0, "Saturn": 9.0,
}

CAZIMI_ORB = 17.0 / 60.0        # 17 دقيقة قوسية = اتحاد كلي (تقوية استثنائية)
COMBUSTION_ORB = 8.5            # احتراق تام (إضعاف شديد)
UNDER_THE_BEAMS_ORB = 15.0      # تحت الأشعة (إضعاف أخف)

# =====================================================================
# 2) دوال رياضية/فلكية مساعدة عامة
# =====================================================================

def normalize_degrees(deg: float) -> float:
    """تطبيع أي زاوية لتقع ضمن المجال [0, 360)."""
    d = deg % 360.0
    return d + 360.0 if d < 0 else d


def angular_separation(a: float, b: float) -> float:
    """أقصر مسافة زاوية بين نقطتين على الدائرة (0 إلى 180 درجة)."""
    diff = abs(normalize_degrees(a) - normalize_degrees(b)) % 360.0
    return min(diff, 360.0 - diff)


def sign_of(longitude: float) -> str:
    return ZODIAC_SIGNS[int(normalize_degrees(longitude) // 30)]


def degree_in_sign(longitude: float) -> float:
    return normalize_degrees(longitude) % 30.0


def get_triplicity_element(sign: str) -> str:
    for element, data in TRIPLICITY.items():
        if sign in data["signs"]:
            return element
    return "fire"


def get_term_ruler(sign: str, degree: float) -> Optional[str]:
    table = EGYPTIAN_TERMS.get(sign, [])
    for end_deg, planet in table:
        if degree < end_deg:
            return planet
    return table[-1][1] if table else None


def get_face_ruler(longitude: float) -> str:
    """الوجه/الديكان: كل 10 درجات من بداية الحمل (0-359) ضمن دورة كلدانية مستمرة."""
    decan_index = int(normalize_degrees(longitude) // 10)  # 0..35
    return _FACE_CYCLE[decan_index % 7]


def get_lunar_mansion(moon_longitude: float) -> Dict[str, Any]:
    idx = int(normalize_degrees(moon_longitude) // _MANSION_WIDTH)
    idx = min(idx, 27)
    start = idx * _MANSION_WIDTH
    return {
        "index": idx + 1,
        "name_ar": LUNAR_MANSIONS_AR[idx],
        "range_start_deg": round(start, 2),
        "range_end_deg": round(start + _MANSION_WIDTH, 2),
    }


# =====================================================================
# 3) حساب الشروق/الغروب الحقيقي والساعات الكوكبية غير المتساوية
# =====================================================================

def compute_sunrise_sunset_utc(date: datetime, lat: float, lon: float,
                                zenith_deg: float = 90.833) -> Optional[Dict[str, float]]:
    """
    معادلة الشروق/الغروب القياسية (Sunrise Equation - NOAA/Almanac form).
    ترجع الشروق والغروب بالساعات العشرية بتوقيت UTC. تُرجع None في حال
    عدم شروق/غروب الشمس فعلياً (المناطق القطبية في فصول معينة).
    """
    n = date.timetuple().tm_yday
    lng_hour = lon / 15.0
    results: Dict[str, float] = {}

    for event, base_hour in (("sunrise", 6.0), ("sunset", 18.0)):
        t = n + ((base_hour - lng_hour) / 24.0)
        M = (0.9856 * t) - 3.289
        M_rad = math.radians(M)
        L = (M + (1.916 * math.sin(M_rad)) + (0.020 * math.sin(2 * M_rad)) + 282.634) % 360.0
        L_rad = math.radians(L)

        RA = math.degrees(math.atan(0.91764 * math.tan(L_rad))) % 360.0
        L_quadrant = math.floor(L / 90.0) * 90.0
        RA_quadrant = math.floor(RA / 90.0) * 90.0
        RA = (RA + (L_quadrant - RA_quadrant)) / 15.0

        sin_dec = 0.39782 * math.sin(L_rad)
        cos_dec = math.cos(math.asin(sin_dec))

        cos_H_num = math.cos(math.radians(zenith_deg)) - (sin_dec * math.sin(math.radians(lat)))
        cos_H_den = cos_dec * math.cos(math.radians(lat))
        if cos_H_den == 0:
            return None
        cos_H = cos_H_num / cos_H_den
        if cos_H > 1.0 or cos_H < -1.0:
            return None  # لا شروق أو لا غروب في هذا اليوم/الموقع

        H = (360.0 - math.degrees(math.acos(cos_H))) if event == "sunrise" else math.degrees(math.acos(cos_H))
        H /= 15.0

        T = H + RA - (0.06571 * t) - 6.622
        UT = (T - lng_hour) % 24.0
        results[event] = UT

    return results


def compute_planetary_hours(date: datetime, lat: float, lon: float) -> Optional[List[Dict[str, Any]]]:
    """
    يبني جدول الساعات الكوكبية الاثنتي عشرة النهارية والاثنتي عشرة الليلية
    (24 ساعة غير متساوية الطول) بدءاً من الشروق الحقيقي وانتهاءً بالشروق التالي،
    باستخدام كوكب حاكم اليوم كنقطة انطلاق ودورة كلدانية هابطة.
    """
    today_times = compute_sunrise_sunset_utc(date, lat, lon)
    tomorrow_times = compute_sunrise_sunset_utc(date + timedelta(days=1), lat, lon)
    if not today_times or not tomorrow_times:
        return None

    day_start = date.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(hours=today_times["sunrise"])
    day_end = date.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(hours=today_times["sunset"])
    next_sunrise = (date + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0) \
        + timedelta(hours=tomorrow_times["sunrise"])

    day_length = (day_end - day_start).total_seconds()
    night_length = (next_sunrise - day_end).total_seconds()
    if day_length <= 0 or night_length <= 0:
        return None

    day_hour_len = day_length / 12.0
    night_hour_len = night_length / 12.0

    start_planet = WEEKDAY_TO_PLANET[date.weekday()]
    start_index = CHALDEAN_ORDER.index(start_planet)

    hours: List[Dict[str, Any]] = []
    for i in range(12):
        planet = CHALDEAN_ORDER[(start_index + i) % 7]
        h_start = day_start + timedelta(seconds=day_hour_len * i)
        h_end = h_start + timedelta(seconds=day_hour_len)
        hours.append({"index": i + 1, "period": "day", "planet": planet, "start": h_start, "end": h_end})

    for i in range(12):
        planet = CHALDEAN_ORDER[(start_index + 12 + i) % 7]
        h_start = day_end + timedelta(seconds=night_hour_len * i)
        h_end = h_start + timedelta(seconds=night_hour_len)
        hours.append({"index": i + 13, "period": "night", "planet": planet, "start": h_start, "end": h_end})

    return hours


def is_daytime_chart(moment: datetime, sun_longitude: float, ascendant: Optional[float],
                      sunrise_utc: Optional[float] = None, sunset_utc: Optional[float] = None) -> bool:
    """
    تقدير كون اللحظة نهارية أم ليلية. الأدق فلكياً هو مقارنة وقت اللحظة
    بالشروق/الغروب الحقيقيين إن توفرا، وإلا نستخدم موضع الشمس نسبة للطالع
    كبديل تقريبي (الشمس فوق الأفق إذا كانت بين الطالع والغارب في نصف الدائرة العلوي).
    """
    if sunrise_utc is not None and sunset_utc is not None:
        hour = moment.hour + moment.minute / 60.0
        return sunrise_utc <= hour < sunset_utc
    if ascendant is not None:
        # النصف السماوي العلوي تقريبياً: من الطالع إلى الغارب عكس اتجاه الأبراج
        diff = normalize_degrees(ascendant - sun_longitude)
        return diff < 180.0
    # افتراض احتياطي محافظ إن غابت كل البيانات
    return 6 <= moment.hour < 18


# =====================================================================
# 4) هياكل بيانات التقييم (Dataclasses)
# =====================================================================

@dataclass
class EssentialDignity:
    planet: str
    sign: str
    domicile: bool = False
    exaltation: bool = False
    triplicity: bool = False
    term: bool = False
    face: bool = False
    detriment: bool = False
    fall: bool = False
    peregrine: bool = False   # لا يملك أي كرامة أساسية إطلاقاً (أضعف حالة)
    score: int = 0
    notes: List[str] = field(default_factory=list)


@dataclass
class AccidentalDignity:
    planet: str
    house: Optional[int]
    angular: bool = False
    succedent: bool = False
    cadent: bool = False
    retrograde: bool = False
    stationary: bool = False
    cazimi: bool = False
    combust: bool = False
    under_beams: bool = False
    besieged_by_malefics: bool = False
    score: int = 0
    notes: List[str] = field(default_factory=list)


@dataclass
class PlanetEvaluation:
    planet: str
    essential: EssentialDignity
    accidental: AccidentalDignity

    @property
    def total_score(self) -> int:
        return self.essential.score + self.accidental.score


# =====================================================================
# 5) محرك الاختيارات التنجيمية
# =====================================================================

class ElectionalAstrologyEngine:

    # أوزان قابلة للتهيئة - تُمكّن ضبط حساسية النموذج دون تعديل المنطق
    WEIGHTS = {
        "domicile": 20, "exaltation": 15, "triplicity": 8, "term": 4, "face": 2,
        "detriment": -15, "fall": -20, "peregrine": -5,
        "angular_house": 8, "cadent_house": -6,
        "retrograde": -25, "stationary_retrograde": -35, "stationary_direct": 10,
        "cazimi": 25, "combust": -20, "under_beams": -10, "besieged": -18,
        "mutual_reception": 12,
        "moon_favorable_sign": 10, "moon_waning_penalty": -15,
        "moon_void_of_course": -30, "moon_critical_degree": -20,
        "aspect_trine_sextile": 10, "aspect_square_opposition": -15,
        "eclipse_period": -40,
        "base_score": 60.0,
    }

    ANGULAR_HOUSES = {1, 4, 7, 10}
    CADENT_HOUSES = {3, 6, 9, 12}

    def __init__(self, astrology_engine: Any):
        """محرك الاختيارات يعتمد على محرك حسابات فلكية خارجي (self.engine) لتوليد
        خرائط العبور (Transit Charts) اللحظية لأي تاريخ ووقت وإحداثيات."""
        self.engine = astrology_engine

        self.decision_rules: Dict[str, Dict[str, Any]] = {
            "financial": {
                "name": "الجانب المالي والاستثماري",
                "ruling_planets": ["Jupiter", "Venus", "Mercury"],
                "preferred_houses": [2, 8, 10, 11],
                "moon_signs": ["Taurus", "Virgo", "Capricorn", "Cancer"],
                "allow_waning": False,
                "critical_planets": ["Mercury", "Jupiter"],
                "description": "تأسيس المشاريع، توقيع العقود التجارية، الاستثمار، وشراء النطاقات والمتاجر.",
            },
            "emotional": {
                "name": "الجانب العاطفي والعلاقات",
                "ruling_planets": ["Venus", "Moon"],
                "preferred_houses": [5, 7, 11],
                "moon_signs": ["Taurus", "Cancer", "Libra", "Pisces"],
                "allow_waning": False,
                "critical_planets": ["Venus", "Moon"],
                "description": "عقد القران، الخطوبة، الزواج، المصالحات، وتعميق الروابط الاجتماعية.",
            },
            "confrontation": {
                "name": "المواجهات والقضايا والإنهاء",
                "ruling_planets": ["Mars", "Saturn"],
                "preferred_houses": [6, 8, 12],
                "moon_signs": ["Aries", "Scorpio", "Capricorn"],
                "allow_waning": True,
                "critical_planets": ["Mars"],
                "description": "رفع الدعاوى القضائية، إنهاء العلاقات السامة، والعمليات الجراحية والاستئصال.",
            },
            "intellectual": {
                "name": "الجانب الفكري والتأليف والنشر",
                "ruling_planets": ["Mercury", "Jupiter"],
                "preferred_houses": [3, 9],
                "moon_signs": ["Gemini", "Libra", "Aquarius", "Virgo"],
                "allow_waning": False,
                "critical_planets": ["Mercury"],
                "description": "بدء الدراسات والأبحاث، تأليف الكتب، وإطلاق المنصات الفكرية والأرشيفية.",
            },
            "general": {
                "name": "الأمور اليومية العامة",
                "ruling_planets": ["Sun", "Jupiter"],
                "preferred_houses": [1, 5, 9],
                "moon_signs": ZODIAC_SIGNS,
                "allow_waning": False,
                "critical_planets": ["Sun"],
                "description": "الخطوات الاعتيادية والشراء الشخصي الاستهلاكي الذي يتطلب تيسيراً بركة عامة.",
            },
        }

        # مصنّف نية قائم على قواعد كلمات مفتاحية صريحة (Rule-Based، بلا أي ذكاء اصطناعي)
        self._intent_keywords: Dict[str, List[str]] = {
            "financial": ["متجر", "محل", "شراء", "بيع", "نطاق", "دومين", "فلوس", "مال", "تجارة", "مشروع", "استثمار", "عقد", "شركة", "نشاط"],
            "emotional": ["زواج", "خطوبة", "حب", "حبيب", "شريك", "عاطفة", "ارتباط", "عقد قران", "صلح", "صديق"],
            "confrontation": ["محكمة", "قضية", "محامي", "خلاف", "انفصال", "طلاق", "قطع", "مواجهة", "جراحة", "عملية"],
            "intellectual": ["كتاب", "تأليف", "نشر", "بحث", "دراسة", "جامعة", "امتحان", "فلسفة", "مقال", "علم", "أرشيف"],
        }

    # -----------------------------------------------------------------
    # تصنيف النية (قائم على قواعد صريحة - Rule-Based Classifier)
    # -----------------------------------------------------------------
    def classify_user_intent(self, user_text: str) -> str:
        text = (user_text or "").lower().strip()
        
        # حماية إضافية ذكية للمشتريات التقنية والشخصية البسيطة لكي لا تُصنف كاستثمار تجاري ضخم
        if any(tech in text for tech in ["ايفون", "آيفون", "جوال", "هاتف", "تلفون", "كمبيوتر", "لابتوب"]):
            return "general"
            
        for intent, keys in self._intent_keywords.items():
            if any(key in text for key in keys):
                return intent
        return "general"

    # للتوافق الرجعي مع الاستدعاءات القديمة لنفس الاسم السابق
    classify_user_intent_ai = classify_user_intent

    # -----------------------------------------------------------------
    # الكرامة الأساسية الكاملة (5 كرامات)
    # -----------------------------------------------------------------
    def calculate_essential_dignity(self, planet: str, longitude: float, is_day: bool) -> EssentialDignity:
        sign = sign_of(longitude)
        deg_in_sign = degree_in_sign(longitude)
        result = EssentialDignity(planet=planet, sign=sign)

        if planet not in DOMICILE:
            return result  # كواكب خارج نطاق النظام السباعي التقليدي (لا كرامة تقليدية لها)

        if sign in DOMICILE[planet]:
            result.domicile = True
            result.score += self.WEIGHTS["domicile"]
            result.notes.append(f"{planet} في بيته الأصلي ({ZODIAC_SIGNS_AR.get(sign, sign)}).")

        exalt_sign, exalt_deg = EXALTATION.get(planet, (None, None))
        if exalt_sign and sign == exalt_sign:
            result.exaltation = True
            result.score += self.WEIGHTS["exaltation"]
            proximity = 1.0 - (abs(deg_in_sign - exalt_deg) / 30.0)
            result.notes.append(
                f"{planet} في شرفه ({ZODIAC_SIGNS_AR.get(sign, sign)}) بقرب {proximity * 100:.0f}٪ من درجة الشرف المثلى."
            )

        element = get_triplicity_element(sign)
        trip = TRIPLICITY[element]
        trip_ruler = trip["day"] if is_day else trip["night"]
        if planet == trip_ruler or planet == trip.get("participating"):
            result.triplicity = True
            result.score += self.WEIGHTS["triplicity"]
            result.notes.append(f"{planet} حاكم ثلاثية {element} ({'نهاراً' if is_day else 'ليلاً'}).")

        term_ruler = get_term_ruler(sign, deg_in_sign)
        if planet == term_ruler:
            result.term = True
            result.score += self.WEIGHTS["term"]
            result.notes.append(f"{planet} حاكم الحد (الحدود المصرية) عند {deg_in_sign:.1f}° {ZODIAC_SIGNS_AR.get(sign, sign)}.")

        face_ruler = get_face_ruler(longitude)
        if planet == face_ruler:
            result.face = True
            result.score += self.WEIGHTS["face"]
            result.notes.append(f"{planet} حاكم الوجه (الديكان) الحالي.")

        if sign in DETRIMENT.get(planet, []):
            result.detriment = True
            result.score += self.WEIGHTS["detriment"]
            result.notes.append(f"{planet} في وباله ({ZODIAC_SIGNS_AR.get(sign, sign)}) - ضعف بنيوي.")

        if sign == FALL.get(planet):
            result.fall = True
            result.score += self.WEIGHTS["fall"]
            result.notes.append(f"{planet} في هبوطه ({ZODIAC_SIGNS_AR.get(sign, sign)}) - أضعف حالاته.")

        if not any([result.domicile, result.exaltation, result.triplicity, result.term, result.face]):
            result.peregrine = True
            result.score += self.WEIGHTS["peregrine"]
            result.notes.append(f"{planet} غريب/هائم (Peregrine) - لا يملك أي كرامة أساسية في موضعه الحالي.")

        return result

    # -----------------------------------------------------------------
    # الكرامة العرضية (زاوية البيت، السرعة، الاحتراق/الكازيمي، الحصار)
    # -----------------------------------------------------------------
    def calculate_accidental_dignity(self, planet: str, planet_data: Dict[str, Any],
                                      sun_longitude: float, all_planets: Dict[str, Any],
                                      house: Optional[int]) -> AccidentalDignity:
        result = AccidentalDignity(planet=planet, house=house)
        longitude = planet_data.get("longitude", 0.0)

        if house is not None:
            if house in self.ANGULAR_HOUSES:
                result.angular = True
                result.score += self.WEIGHTS["angular_house"]
                result.notes.append(f"{planet} في بيت وتدي (بيت {house}) - قوة عرضية ودفع فوري للأحداث.")
            elif house in self.CADENT_HOUSES:
                result.cadent = True
                result.score += self.WEIGHTS["cadent_house"]
                result.notes.append(f"{planet} في بيت ساقط (بيت {house}) - ضعف في الفاعلية والأثر.")

        is_retrograde = bool(planet_data.get("retrograde", False))
        is_stationary = bool(planet_data.get("stationary", False))
        if planet != "Sun":
            if is_stationary and is_retrograde:
                result.stationary = True
                result.retrograde = True
                result.score += self.WEIGHTS["stationary_retrograde"]
                result.notes.append(f"{planet} في محطة توقف قبيل التراجع - أشد حالات التعطل حدة.")
            elif is_stationary:
                result.stationary = True
                result.score += self.WEIGHTS["stationary_direct"]
                result.notes.append(f"{planet} في محطة توقف قبيل الاستقامة - نقطة تحول إيجابية.")
            elif is_retrograde:
                result.retrograde = True
                result.score += self.WEIGHTS["retrograde"]
                result.notes.append(f"{planet} متراجع - تأخير أو عودة لملفات من الماضي.")

        if planet != "Sun":
            sep = angular_separation(longitude, sun_longitude)
            if sep <= CAZIMI_ORB:
                result.cazimi = True
                result.score += self.WEIGHTS["cazimi"]
                result.notes.append(f"{planet} في قلب الشمس (كازيمي) - تقوية استثنائية عظمى ونادرة.")
            elif sep <= COMBUSTION_ORB:
                result.combust = True
                result.score += self.WEIGHTS["combust"]
                result.notes.append(f"{planet} محترق تماماً بسبب قربه من الشمس - إضعاف وتعطيل لفاعليته.")
            elif sep <= UNDER_THE_BEAMS_ORB:
                result.under_beams = True
                result.score += self.WEIGHTS["under_beams"]
                result.notes.append(f"{planet} تحت أشعة الشمس - ضعف بنيوي أخف.")

        mars_data = all_planets.get("Mars")
        saturn_data = all_planets.get("Saturn")
        if planet not in ("Mars", "Saturn") and mars_data and saturn_data:
            mars_long = mars_data.get("longitude", 0.0) if isinstance(mars_data, dict) else getattr(mars_data, "longitude", 0.0)
            sat_long = saturn_data.get("longitude", 0.0) if isinstance(saturn_data, dict) else getattr(saturn_data, "longitude", 0.0)
            d_mars = angular_separation(longitude, mars_long)
            d_sat = angular_separation(longitude, sat_long)
            same_side_check = (normalize_degrees(mars_long - longitude) < 180) != (normalize_degrees(sat_long - longitude) < 180)
            if d_mars <= 8.0 and d_sat <= 8.0 and same_side_check:
                result.besieged_by_malefics = True
                result.score += self.WEIGHTS["besieged"]
                result.notes.append(f"{planet} محاصر بين النحسين (المريخ وزحل) - ضغوط وعراقيل مزدوجة.")

        return result

    # -----------------------------------------------------------------
    # القِران المتبادل (Mutual Reception)
    # -----------------------------------------------------------------
    def detect_mutual_receptions(self, planets: Dict[str, Any]) -> List[Tuple[str, str, str]]:
        """يرصد كل زوج كواكب يقع كل منهما في بيت أو شرف الآخر (تعاون بنيوي قوي)."""
        receptions: List[Tuple[str, str, str]] = []
        names = [p for p in planets.keys() if p in DOMICILE]
        for i, p1 in enumerate(names):
            for p2 in names[i + 1:]:
                d1 = planets[p1]
                d2 = planets[p2]
                l1 = d1.get("longitude", 0.0) if isinstance(d1, dict) else getattr(d1, "longitude", 0.0)
                l2 = d2.get("longitude", 0.0) if isinstance(d2, dict) else getattr(d2, "longitude", 0.0)
                s1, s2 = sign_of(l1), sign_of(l2)

                p1_in_p2_domicile = s1 in DOMICILE.get(p2, [])
                p2_in_p1_domicile = s2 in DOMICILE.get(p1, [])
                p1_in_p2_exalt = EXALTATION.get(p2, (None, None))[0] == s1
                p2_in_p1_exalt = EXALTATION.get(p1, (None, None))[0] == s2

                if (p1_in_p2_domicile and p2_in_p1_domicile):
                    receptions.append((p1, p2, "domicile"))
                elif (p1_in_p2_exalt and p2_in_p1_exalt):
                    receptions.append((p1, p2, "exaltation"))
                elif (p1_in_p2_domicile and p2_in_p1_exalt) or (p2_in_p1_domicile and p1_in_p2_exalt):
                    receptions.append((p1, p2, "mixed"))

        return receptions

    # -----------------------------------------------------------------
    # الساعة الكوكبية الحقيقية (بالشروق/الغروب الفعليين)
    # -----------------------------------------------------------------
    def calculate_best_planetary_hour(self, target_date: datetime, ruling_planets: List[str],
                                       lat: float, lon: float) -> str:
        hours = compute_planetary_hours(target_date, lat, lon)
        if not hours:
            return "⏳ تعذّر حساب الساعات الكوكبية الدقيقة لهذا الموقع/التاريخ."

        for h in hours:
            if h["planet"] in ruling_planets and h["period"] == "day":
                return (f"⏳ الساعة النهارية رقم {h['index']} - ساعة {h['planet']} "
                        f"(من {h['start'].strftime('%H:%M')} إلى {h['end'].strftime('%H:%M')} بتوقيت غرينتش)")

        for h in hours:
            if h["planet"] in ruling_planets:
                return (f"⏳ الساعة الليلية رقم {h['index'] - 12} - ساعة {h['planet']} "
                        f"(من {h['start'].strftime('%H:%M')} إلى {h['end'].strftime('%H:%M')} بتوقيت غرينتش)")

        first = hours[0]
        return (f"⏳ ساعة {first['planet']} (تبدأ من {first['start'].strftime('%H:%M')} بتوقيت غرينتش)")

    # -----------------------------------------------------------------
    # التقييم الفلكي الشامل (النواة التحليلية)
    # -----------------------------------------------------------------
    def evaluate_astrological_fitness(self, chart: Any, rules: Dict[str, Any],
                                       moment: Optional[datetime] = None,
                                       lat: Optional[float] = None,
                                       lon: Optional[float] = None) -> Tuple[float, List[str], Dict[str, Any]]:
        score = self.WEIGHTS["base_score"]
        reasons: List[str] = []
        breakdown: Dict[str, Any] = {"planets": {}, "mutual_receptions": [], "lunar_mansion": None}

        if hasattr(chart, "__dict__") and not isinstance(chart, dict):
            planets = getattr(chart, "planets", {})
            aspects = getattr(chart, "aspects", [])
            is_eclipse_period = getattr(chart, "is_eclipse_period", False)
            houses = getattr(chart, "houses", {})
            ascendant = getattr(chart, "ascendant", None)
        elif isinstance(chart, dict):
            planets = chart.get("planets", {})
            aspects = chart.get("aspects", [])
            is_eclipse_period = chart.get("is_eclipse_period", False)
            houses = chart.get("houses", {})
            ascendant = chart.get("ascendant")
        else:
            planets, aspects, is_eclipse_period, houses, ascendant = {}, [], False, {}, None

        def get_planet_data(name: str) -> Dict[str, Any]:
            p = planets.get(name) if isinstance(planets, dict) else getattr(planets, name, None)
            if p is None:
                return {}
            if isinstance(p, dict):
                return p
            return {
                "longitude": getattr(p, "longitude", 0.0),
                "retrograde": getattr(p, "retrograde", False),
                "stationary": getattr(p, "stationary", False),
                "house": getattr(p, "house", None),
                "sign": getattr(p, "sign", ""),
                "degree": getattr(p, "degree", 0.0),
                "is_waning": getattr(p, "is_waning", False),
                "is_void_of_course": getattr(p, "is_void_of_course", False),
            }

        planets_normalized = {name: get_planet_data(name) for name in
                               ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn"]
                               if get_planet_data(name)}

        sun_data = planets_normalized.get("Sun", {})
        sun_long = sun_data.get("longitude", 0.0)

        sun_times = compute_sunrise_sunset_utc(moment, lat, lon) if (moment and lat is not None and lon is not None) else None
        day_flag = is_daytime_chart(
            moment or datetime.utcnow(), sun_long, ascendant,
            sunrise_utc=sun_times.get("sunrise") if sun_times else None,
            sunset_utc=sun_times.get("sunset") if sun_times else None,
        )

        # --- تقييم الكواكب الحاكمة الحرجة (كرامة أساسية + عرضية) ---
        for p_name in rules["critical_planets"]:
            p_data = planets_normalized.get(p_name)
            if not p_data:
                continue

            essential = self.calculate_essential_dignity(p_name, p_data.get("longitude", 0.0), day_flag)
            house = p_data.get("house")
            accidental = self.calculate_accidental_dignity(p_name, p_data, sun_long, planets_normalized, house)

            evaluation = PlanetEvaluation(planet=p_name, essential=essential, accidental=accidental)
            score += evaluation.total_score
            reasons.extend(essential.notes)
            reasons.extend(accidental.notes)
            breakdown["planets"][p_name] = {
                "essential_score": essential.score,
                "accidental_score": accidental.score,
                "sign": essential.sign,
                "peregrine": essential.peregrine,
            }

        # --- القِران المتبادل بين الكواكب الحاكمة للمسعى ---
        receptions = self.detect_mutual_receptions(
            {k: v for k, v in planets_normalized.items() if k in rules["ruling_planets"]}
        )
        if receptions:
            score += self.WEIGHTS["mutual_reception"] * len(receptions)
            for p1, p2, kind in receptions:
                reasons.append(f"🤝 قِران متبادل ({kind}) بين {p1} و{p2} - تعاون بنيوي يقوّي احتمالية النجاح.")
        breakdown["mutual_receptions"] = receptions

        # --- تحليل القمر التفصيلي ---
        moon_data = planets_normalized.get("Moon")
        if moon_data:
            moon_long = moon_data.get("longitude", 0.0)
            moon_sign = sign_of(moon_long)
            moon_deg = degree_in_sign(moon_long)
            moon_is_waning = moon_data.get("is_waning", False)

            mansion = get_lunar_mansion(moon_long)
            breakdown["lunar_mansion"] = mansion
            reasons.append(
                f"🌙 القمر في منزلة ({mansion['name_ar']}) [المنزلة رقم {mansion['index']}]."
            )

            if moon_sign in rules["moon_signs"]:
                score += self.WEIGHTS["moon_favorable_sign"]
                reasons.append(f"🌙 القمر في برج داعم ومناسب لطبيعة مسعاك وهو برج ({ZODIAC_SIGNS_AR.get(moon_sign, moon_sign)}).")

            if moon_is_waning and not rules["allow_waning"]:
                score += self.WEIGHTS["moon_waning_penalty"]
                reasons.append("🌙 نور القمر يتناقص، وهو ما يعيق خطوات التأسيس والنمو المستدام.")

            if moon_data.get("is_void_of_course", False):
                score += self.WEIGHTS["moon_void_of_course"]
                reasons.append("🚨 القمر خالي المسار (Void of Course)! طاقة الركود مرتفعة وتجنب البدء بالخطوة الآن.")

            if moon_deg >= 29.0:
                score += self.WEIGHTS["moon_critical_degree"]
                reasons.append("⚠️ القمر في الدرجة الأخيرة الحرجة (29°+) من البرج - طاقة متقلبة وغير مستقرة.")

        # --- الاتصالات الحية بين الكواكب الحاكمة وبقية الفلك ---
        rulers = rules["ruling_planets"]
        for asp in aspects:
            p1 = asp.get("planet1") if isinstance(asp, dict) else getattr(asp, "planet1", None)
            p2 = asp.get("planet2") if isinstance(asp, dict) else getattr(asp, "planet2", None)
            a_type = asp.get("type") if isinstance(asp, dict) else getattr(asp, "type", None)
            if p1 in rulers or p2 in rulers:
                if a_type in ("trine", "sextile"):
                    score += self.WEIGHTS["aspect_trine_sextile"]
                elif a_type in ("square", "opposition"):
                    score += self.WEIGHTS["aspect_square_opposition"]
                    reasons.append(f"⚡ اتصال تربيع أو مقابلة نحس بين {p1} و{p2} يهدد سلاسة وسهولة المسعى.")

        if is_eclipse_period:
            score += self.WEIGHTS["eclipse_period"]
            reasons.append("🌑 النافذة الزمنية تقع تحت ظلال عاصفة الكسوف/الخسوف، ويُنصح بالتأجيل.")

        final_score = max(5.0, min(score, 100.0))
        breakdown["final_score"] = round(final_score, 2)
        breakdown["is_day_chart"] = day_flag
        return final_score, reasons, breakdown

    # -----------------------------------------------------------------
    # التقرير الشامل النهائي (تم تعديل الكليشة لتصبح سهلة ومبسطة كلياً)
    # -----------------------------------------------------------------
    def generate_detailed_report(self, user_text: str, lat: float, lon: float,
                                  scan_days: int = 30) -> Tuple[str, str]:
        decision_key = self.classify_user_intent(user_text)
        rules = self.decision_rules.get(decision_key, self.decision_rules["general"])

        start_date = datetime.utcnow()
        all_days_evaluated: List[Dict[str, Any]] = []

        for day_offset in range(scan_days):
            current_check = start_date + timedelta(days=day_offset)
            try:
                chart = self.engine.compute_natal_chart(current_check, lat, lon)
                score, reasons, breakdown = self.evaluate_astrological_fitness(
                    chart, rules, moment=current_check, lat=lat, lon=lon
                )
                all_days_evaluated.append({
                    "date": current_check, "score": score, "reasons": reasons, "breakdown": breakdown,
                })
            except Exception as e:
                logger.error("Error evaluating day %s: %s", day_offset, e)
                continue

        if not all_days_evaluated:
            return "❌ عذراً، هناك خلل في معالجة خريطة السماء اللحظية (Transit).", decision_key

        all_days_evaluated.sort(key=lambda x: x["score"], reverse=True)
        best_option = all_days_evaluated[0]
        worst_option = all_days_evaluated[-1]

        best_hour_text = self.calculate_best_planetary_hour(
            best_option["date"], rules["ruling_planets"], lat, lon
        )
        reasons_bulleted = "\n".join(f"• {r}" for r in best_option["reasons"][:6]) if best_option["reasons"] \
            else "• اتصالات الكواكب والكرامات الفلكية مستقرة ومتزنة ومائلة للسعود والبركة."

        mansion = best_option["breakdown"].get("lunar_mansion") or {}
        mansion_line = f"🌙 **منزلة القمر الحالية:** {mansion.get('name_ar', 'غير محددة')} (المنزلة رقم {mansion.get('index', '-')})" if mansion else ""
        
        receptions = best_option["breakdown"].get("mutual_receptions") or []
        reception_line = f"🤝 **قِرانات التعاون المرصودة:** {len(receptions)} (كواكب تدعم بعضها تنجيمياً)" if receptions else "🤝 **قِرانات التعاون المرصودة:** لا يوجد قِران تبادلي حالي"

        chart_type_line = "☀️ خريطة نهارية (Diurnal)" if best_option["breakdown"].get("is_day_chart") else "🌙 خريطة ليلية (Nocturnal)"

        # الصياغة الكليشية المحدثة والمبسطة لتلائم جميع القراء بسلاسة واحترافية
        report_text = (
            f"🪐 **تقرير الاختيارات الفلكية الشامل وتحليل العبور الهندسي** 🪐\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🎯 **تحليل خطوتك الحالية:**\n"
            f"← التصنيف الدلالي المكتشف: **{rules['name']}**\n"
            f"← طبيعة النوافذ والخطوات: *{rules['description']}*\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🌟 **أفضل توقيت فلكي للإقدام (خلال مسح الـ {scan_days} يوماً القادمة):**\n"
            f"📅 **اليوم المقترح والمختار:** {best_option['date'].strftime('%Y-%m-%d')} (توقيت غرينتش)\n"
            f"📊 **معدل التيسير والنجاح الرياضي:** ` {best_option['score']:.1f}% `\n\n"
            f"🧭 **الحالة الفلكية اللحظية الكلية:**\n"
            f"• فئة الأفق: {chart_type_line}\n"
            f"• {mansion_line}\n"
            f"• {reception_line}\n\n"
            f"🔭 **المسوغات والشهادات الفلكية التقليدية (أسباب الاختيار):**\n"
            f"{reasons_bulleted}\n\n"
            f"⏱ **الساعة الكوكبية الذهبية الموصى بها في ذلك اليوم:**\n"
            f"{best_hour_text}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🛑 **فترة الحذر الأعلى نحوسة واحتراقاً (تجنب البدء أو التوقيع فيها):**\n"
            f"📅 **التاريخ المحذر منه:** {worst_option['date'].strftime('%Y-%m-%d')} (مؤشر التيسير والنجاح: {worst_option['score']:.1f}%)\n"
            f"❌ **سبب النحوسة:** هبوط أو تراجع حاد لكواكب النية، أو وقوعها تحت أشعة الاحتراق المباشرة للشمس أو ظلال الكسوف.\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⚠️ **ملاحظة منهجية:** جميع الحسابات المعروضة مستخرجة من معادلات التنجيم التقليدي الكلاسيكي "
            f"(الكرامات الخمس، الحدود المصرية، الوجوه الكلدانية، والساعات الكوكبية المستندة للشروق والغروب الفعليين) "
            f"بشكل حاسوبي بحت دون تدخل احتمالي. هذه الحسابات تهدف لتحديد الفترات الرمزية الأكثر توازناً، "
            f"ولا تمثل حقائق علمية قطعية أو جزماً بحتمية الأحداث الحياتية الغيبية."
        )

        return report_text, decision_key
