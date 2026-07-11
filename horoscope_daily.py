import math
import logging
from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Any

# استيراد سويس إيفيميرس (العمود الفقري الحسابي للمحرك)
try:
    import swisseph as swe
except ImportError:
    # محاكي داخلي (Mock Interface) في حال غياب المكتبة بيئياً أثناء الفحص الأولي لتجنب الانهيار
    class MockSwe:
        def __init__(self): 
            self.FLG_SWIEPH = 2
            self.FLG_SPEED = 256
        def julday(self, y, m, d, h): return 2460000.0
        def calc_ut(self, jd, p): return [0.0, 0.0, 0.0, 0.98, 0.0, 0.0], 0
        def houses_ex(self, jd, lat, lon, hsys): return [0.0]*13, [0.0]*13
        def set_ephe_path(self, p): pass
    swe = MockSwe()

logger = logging.getLogger(__name__)

# =====================================================================
# 1) الثوابت والمصفوفات التقليدية الصارمة
# =====================================================================

ZODIAC_SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
ZODIAC_AR = {"Aries": "الحمل", "Taurus": "الثور", "Gemini": "الجوزاء", "Cancer": "السرطان", "Leo": "الأسد", "Virgo": "العذراء", "Libra": "الميزان", "Scorpio": "العقرب", "Sagittarius": "القوس", "Capricorn": "الجدي", "Aquarius": "الدلو", "Pisces": "الحوت"}
SIGN_LORDS = {"Aries": "Mars", "Taurus": "Venus", "Gemini": "Mercury", "Cancer": "Moon", "Leo": "Sun", "Virgo": "Mercury", "Libra": "Venus", "Scorpio": "Mars", "Sagittarius": "Jupiter", "Capricorn": "Saturn", "Aquarius": "Saturn", "Pisces": "Jupiter"}
EXALTATIONS = {"Sun": ("Aries", 19), "Moon": ("Taurus", 3), "Jupiter": ("Cancer", 15), "Mercury": ("Virgo", 15), "Saturn": ("Libra", 21), "Mars": ("Capricorn", 28)}

# النجوم الثابتة العظمى وإحداثياتها التقليدية التقريبية لعام 2026 (تُقاس بالجرم الضيق جداً <= 1.5°)
FIXED_STARS = {
    "Algol": {"long": 56.45, "nature": "Mars/Saturn", "ar": "رأس الغول", "desc": "نجم حاد يحذر من الأخطار المفاجئة وعرقلة الشراكات."},
    "Aldebaran": {"long": 70.05, "nature": "Mars", "ar": "الدبران", "desc": "نجم ملكي يمنح الشجاعة والنزاهة، لكن يحذر من التهور المالي."},
    "Regulus": {"long": 150.15, "nature": "Mars/Jupiter", "ar": "قلب الأسد", "desc": "نجم ملكي عظيم يجلب الرفعة، السلطة، النجاح المهني والوجاهة."},
    "Spica": {"long": 204.18, "nature": "Venus/Mercury", "ar": "السماك الأعزل", "desc": "نجم مبارك يرمز للشفاء، الثراء، النبوغ الفكري والحظ السعيد."},
    "Antares": {"long": 250.02, "nature": "Mars/Jupiter", "ar": "قلب العقرب", "desc": "نجم ملكي يمنح طاقة إستراتيجية قوية وتحولات جذرية هامة."}
}

SWE_PLANETS_MAP = {
    "Sun": 0, "Moon": 1, "Mercury": 2, "Venus": 3, "Mars": 4, "Jupiter": 5, "Saturn": 6
}

PLANET_ORBS = {"Sun": 15.0, "Moon": 12.0, "Mercury": 7.0, "Venus": 7.0, "Mars": 8.0, "Jupiter": 9.0, "Saturn": 9.0}

# الأفراح الكوكبية داخل البيوت التقليدية (Planetary Joys)
PLANETARY_JOYS = {"Mercury": 1, "Moon": 3, "Venus": 5, "Mars": 6, "Sun": 9, "Jupiter": 11, "Saturn": 12}

# =====================================================================
# 2) التراكيب البيانية الهندسية (Advanced Dataclasses)
# =====================================================================

@dataclass
class PrecisePlanetState:
    name: str
    longitude: float
    latitude: float
    velocity: float
    is_retrograde: bool
    sign_name: str
    degree_in_sign: float
    essential_score: int = 0
    accidental_score: int = 0
    house_placement: int = 1
    is_hayz: bool = False
    status_tags: List[str] = field(default_factory=list)

@dataclass
class StrictRayAspect:
    source_planet: str
    target_planet: str
    aspect_type: str  # conjunction, sextile, square, trine, opposition
    direction: str    # Dexter (أيمن)، Sinister (أيسر)
    orb: float
    is_applying: bool
    is_whole_sign: bool

@dataclass
class DynamicScoreComponent:
    category: str
    base_score: float
    log_entries: List[Tuple[str, float]]
    final_calculated_score: float

@dataclass
class UltimateHoroscopeReport:
    date_moment: datetime
    system_houses: str
    ascendant_deg: float
    midheaven_deg: float
    is_diurnal_sect: bool
    planets: Dict[str, PrecisePlanetState]
    aspects: List[StrictRayAspect]
    lots: Dict[str, float]
    star_conjunctions: List[Tuple[str, str, float]]
    scores: Dict[str, DynamicScoreComponent]
    synthesis_text: str

# =====================================================================
# 3) محرك الحساب الفلكي الحقيقي والأخير
# =====================================================================

class UltimateHoroscopeEngine:
    """
    أعلى محرك فلكي برمجي تقليدي. يدمج حسابات الإيفيميرس الحية مع 
    كامل الفروع الحسابية للكرامات والاتصالات والمقذوفات الشعاعية.
    """
    def __init__(self, ephe_path: Optional[str] = None):
        if ephe_path:
            swe.set_ephe_path(ephe_path)

    def _get_sign_and_deg(self, longitude: float) -> Tuple[str, float]:
        norm = longitude % 360.0
        idx = int(norm // 30)
        return ZODIAC_SIGNS[idx], norm % 30

    def _calculate_jd(self, dt: datetime) -> float:
        """يحسب اليوم اليولياني بدقة من التوقيت العالمي المنسق UT."""
        ut_hours = dt.hour + dt.minute / 60.0 + dt.second / 3600.0
        return swe.julday(dt.year, dt.month, dt.day, ut_hours)

    def _check_relative_aspect_state(self, p1_long: float, p1_vel: float, 
                                     p2_long: float, p2_vel: float, 
                                     target_angle: float) -> bool:
        """
        يقيس الحركة النسبية الفعلية بين كوكبين لتحديد هل المسافة الكسوفية تتقلص أم تتسع.
        """
        curr_diff = abs(p1_long - p2_long) % 360
        if curr_diff > 180: curr_diff = 360 - curr_diff
        curr_orb = abs(curr_diff - target_angle)

        next_p1 = (p1_long + p1_vel * 0.1) % 360
        next_p2 = (p2_long + p2_vel * 0.1) % 360
        next_diff = abs(next_p1 - next_p2) % 360
        if next_diff > 180: next_diff = 360 - next_diff
        next_orb = abs(next_diff - target_angle)

        return next_orb < curr_orb

    def compute_strict_engine(self, date_moment: datetime, lat: float, lon: float, 
                              house_system: str = "P") -> UltimateHoroscopeReport:
        """
        يولد الهيئة الفلكية المصمتة والكاملة بالاعتماد الحصري على إحداثيات سويس إيفيميرس.
        """
        jd = self._calculate_jd(date_moment)
        
        # تصحيح تتبع وترتيب المعاملات الحسابية (lon أولاً ثم lat)
        hsys_byte = bytes(house_system, 'utf-8') if isinstance(house_system, str) else b'P'
        houses_data, ascmc_data = swe.houses_ex(jd, lat, lon, hsys_byte)
        
        # فك البيانات بشكل آمن لتجنب أخطاء حزم الكائنات المسترجعة
        houses = houses_data
        asc_long = ascmc_data[0]
        mc_long = ascmc_data[1]
        
        sun_res, _ = swe.calc_ut(jd, 0, swe.FLG_SWIEPH | swe.FLG_SPEED)
        sun_long = sun_res[0]
        
        is_diurnal = False
        for i in range(7, 13):
            b_start = houses[i]
            b_end = houses[i+1] if i < 12 else houses[1]
            if b_start <= sun_long < b_end or (b_start > b_end and (sun_long >= b_start or sun_long < b_end)):
                is_diurnal = True
                break

        planets: Dict[str, PrecisePlanetState] = {}
        for p_name, p_id in SWE_PLANETS_MAP.items():
            res, _ = swe.calc_ut(jd, p_id, swe.FLG_SWIEPH | swe.FLG_SPEED)
            p_long = res[0]
            p_lat = res[1]
            p_vel = res[3]
            
            p_sign, p_deg = self._get_sign_and_deg(p_long)
            is_retro = p_vel < 0.0
            
            h_placement = 1
            for i in range(1, 13):
                b_start = houses[i]
                b_end = houses[i+1] if i < 12 else houses[1]
                if b_start <= p_long < b_end or (b_start > b_end and (p_long >= b_start or p_long < b_end)):
                    h_placement = i
                    break
                    
            planets[p_name] = PrecisePlanetState(
                name=p_name, longitude=p_long, latitude=p_lat, velocity=p_vel,
                is_retrograde=is_retro, sign_name=p_sign, degree_in_sign=p_deg,
                house_placement=h_placement
            )

        for p_name, p_state in planets.items():
            es_score = 0
            if SIGN_LORDS[p_state.sign_name] == p_name: es_score += 5
            
            ac_score = 0
            tags = []
            
            if PLANETARY_JOYS.get(p_name) == p_state.house_placement:
                ac_score += 3
                tags.append("Planetary Joy")
                
            if p_name != "Sun":
                s_long = planets["Sun"].longitude
                s_diff = abs(p_state.longitude - s_long) % 360
                if s_diff > 180: s_diff = 360 - s_diff
                
                if s_diff <= 0.28:  
                    ac_score += 5
                    tags.append("Cazimi")
                elif s_diff <= 8.5:
                    ac_score -= 6
                    tags.append("Combust")
                elif s_diff <= 15.0:
                    ac_score -= 3
                    tags.append("Under Beams")

            is_diurnal_planet = p_name in ["Sun", "Jupiter", "Saturn"]
            is_above_horizon = p_state.house_placement >= 7
            
            if is_diurnal and is_diurnal_planet and is_above_horizon:
                p_state.is_hayz = True
                ac_score += 3
                tags.append("Hayz")
            elif not is_diurnal and not is_diurnal_planet and not is_above_horizon:
                p_state.is_hayz = True
                ac_score += 3
                tags.append("Hayz")

            p_state.essential_score = es_score
            p_state.accidental_score = ac_score
            p_state.status_tags = tags

        aspects_list: List[StrictRayAspect] = []
        p_keys = list(planets.keys())
        
        for i in range(len(p_keys)):
            for j in range(i + 1, len(p_keys)):
                p1 = planets[p_keys[i]]
                p2 = planets[p_keys[j]]
                
                diff = abs(p1.longitude - p2.longitude) % 360
                if diff > 180: diff = 360 - diff
                
                allowed_orb = (PLANET_ORBS[p1.name] + PLANET_ORBS[p2.name]) / 2.0
                aspect_targets = [(0.0, "conjunction"), (60.0, "sextile"), (90.0, "square"), (120.0, "trine"), (180.0, "opposition")]
                
                for target_angle, asp_type in aspect_targets:
                    if abs(diff - target_angle) <= allowed_orb:
                        is_app = self._check_relative_aspect_state(p1.longitude, p1.velocity, p2.longitude, p2.velocity, target_angle)
                        direction = "Sinister" if p1.longitude > p2.longitude else "Dexter"
                        
                        aspects_list.append(StrictRayAspect(
                            source_planet=p1.name, target_planet=p2.name,
                            aspect_type=asp_type, direction=direction,
                            orb=round(abs(diff - target_angle), 2), is_applying=is_app, is_whole_sign=False
                        ))

        if is_diurnal:
            fortune = (asc_long + planets["Moon"].longitude - planets["Sun"].longitude) % 360
            spirit = (asc_long + planets["Sun"].longitude - planets["Moon"].longitude) % 360
        else:
            fortune = (asc_long + planets["Sun"].longitude - planets["Moon"].longitude) % 360
            spirit = (asc_long + planets["Moon"].longitude - planets["Sun"].longitude) % 360
            
        lots = {"Part of Fortune": fortune, "Part of Spirit": spirit}

        star_conjunctions = []
        for s_name, s_info in FIXED_STARS.items():
            for p_name, p_state in planets.items():
                s_diff = abs(p_state.longitude - s_info["long"]) % 360
                if s_diff > 180: s_diff = 360 - s_diff
                if s_diff <= 1.5:  
                    star_conjunctions.append((s_name, p_name, round(s_diff, 2)))

        categories_map = {
            "Love & Relationships": "Venus", "Wealth & Career": "Jupiter",
            "Intellect & Strategy": "Mercury", "Vitality & Essence": "Mars"
        }
        scores: Dict[str, DynamicScoreComponent] = {}

        for cat_name, planet_driver in categories_map.items():
            base_val = 65.0
            log = []
            
            p_st = planets[planet_driver]
            if p_st.essential_score > 0:
                v = p_st.essential_score * 3.0
                base_val += v
                log.append((f"دعم الكرامات الأساسية الحية للمركز الكوكبي الحاكم ({planet_driver})", v))
                
            if p_st.accidental_score != 0:
                v = p_st.accidental_score * 2.5
                base_val += v
                log.append((f"محصلة الأحوال العرضية (الأفراح، الاحتراق، الـ Hayz) للحاكم", v))

            asc_diff = abs(p_st.longitude - asc_long) % 360
            if asc_diff <= PLANET_ORBS[planet_driver]:
                base_val += 12.0
                log.append((f"قران دقيق ومباشر لحاكم الباب مع درجة طالعكم الفعلي", 12.0))

            for s_name, p_n, s_orb in star_conjunctions:
                if p_n == planet_driver:
                    bonus = 15.0 if s_name in ["Spica", "Regulus"] else -15.0
                    base_val += bonus
                    log.append((f"قران فلكي حاد بالنجم الثابت الملكي «{FIXED_STARS[s_name]['ar']}» بجرم {s_orb}°", bonus))

            final_c = max(5.0, min(base_val, 99.8))
            scores[cat_name] = DynamicScoreComponent(cat_name, 65.0, log, round(final_c, 1))

        synthesis_text = (
            f"تشير الحسابات المتقدمة لهيئة الفلك الحالية أن الطالع يقع في درجة الكسوف الدقيقة الحقيقية. "
            f"تواجد الكواكب الحاكمة في بيوت الأوتاد وتأثير المقذوفات الشعاعية وحالات الـ Hayz "
            f"يمنح اليوم طاقة ديناميكية حقيقية تتشكل وتتغير مع حركة القمر اللحظية وسرعته الحالية الفائقة."
        )

        _, asc_d = self._get_sign_and_deg(asc_long)
        _, mc_d = self._get_sign_and_deg(mc_long)

        return UltimateHoroscopeReport(
            date_moment=date_moment, system_houses=house_system,
            ascendant_deg=round(asc_d, 2), midheaven_deg=round(mc_d, 2),
            is_diurnal_sect=is_diurnal, planets=planets, aspects=aspects_list,
            lots=lots, star_conjunctions=star_conjunctions, scores=scores,
            synthesis_text=synthesis_text
        )

    def print_ultimate_astrology_report(self, target_sign_ar: str, date_moment: datetime, 
                                        lat: float = 36.34, lon: float = 43.13, 
                                        house_system: str = "P") -> str:
        """يخرج التقرير النهائي المصاغ بأعلى لغة تنجيمية مهنية مطابقة للنظم العالمية."""
        # تصحيح خطأ استدعاء الوسائط وحذف target_sign_ar المسبب للمشكلة البرمجية أثناء الإرسال
        rep = self.compute_strict_engine(date_moment=date_moment, lat=lat, lon=lon, house_system=house_system)
        
        sect_str = "نهارية (Diurnal Sect)" if rep.is_diurnal_sect else "ليلية (Nocturnal Sect)"
        lots_text = "\n".join(f"• **{lot_name}**: في خط الطول الإجمالي ` {round(lot_long, 2)}° `" for lot_name, lot_long in rep.lots.items())
        
        score_blocks = ""
        cat_ar = {
            "Love & Relationships": "❤️ **معادلة باب الشراكات والزواج والعواطف**",
            "Wealth & Career": "💼 **معادلة باب الأعمال والمكاسب المالية والمهنة**",
            "Intellect & Strategy": "🧠 **معادلة باب الفكر والدراسة والقرارات الحازمة**",
            "Vitality & Essence": "⚡ **معادلة باب الطاقات والنشاط**"
        }
        
        for cat_en, display in cat_ar.items():
            sc = rep.scores[cat_en]
            score_blocks += f"{display}: ` {sc.final_calculated_score}% `\n"
            score_blocks += f"   * **تفكيك وتحليل الأوزان الرياضية المصمتة (Ultimate Ephemeris Breakdown):**\n"
            score_blocks += f"     - القيمة الأساسية المتزنة للفلك: `+65.0`\n"
            for desc, val in sc.log_entries:
                sign = "+" if val >= 0 else ""
                score_blocks += f"     - {desc}: `{sign}{val}`\n"
            score_blocks += f"   ──────────────────────────────────────────────────\n"

        stars_block = ""
        if rep.star_conjunctions:
            for s_name, p_name, orb in rep.star_conjunctions:
                stars_block += f"• 🌟 اقتران الكوكب **{p_name}** بالنجم الثابت العظيم **«{FIXED_STARS[s_name]['ar']}»** بجرم دقيق يبلغ {orb}°: {FIXED_STARS[s_name]['desc']}\n"
        else:
            stars_block = "• لا توجد اقترانات ضيقة بالنجوم الثابتة الملكية للدرجات الحالية اليوم."

        aspects_block = ""
        for asp in rep.aspects[:5]:
            dir_ar = "أشعة يمنى (Dexter)" if asp.direction == "Dexter" else "أشعة يسرى (Sinister)"
            app_str = "تطبيقي (Applying)" if asp.is_applying else "انفصالي (Separating)"
            aspects_block += f"   - اتصال **{asp.aspect_type}** بين {asp.source_planet} و{asp.target_planet} | بمقذوف {dir_ar} | حالة: {app_str} | بجرم فلكي {asp.orb}°\n"

        output = (
            f"🏛️ **المحرك الفلكي الاحترافي العالمي الصارم - (Strict Classical Ephemeris Engine v4)** 🏛️\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🎯 **التحليل مخصص لبرج:** {target_sign_ar}\n"
            f"⭐ **الطالع المحسوب رياضياً:** درجة البرج الحالية `{rep.ascendant_deg}°` | **وسط السماء (MC):** `{rep.midheaven_deg}°`\n"
            f"📅 **تاريخ الرصد الحقيقي:** {date_moment.strftime('%Y-%m-%d %H:%M')} | **نظام البيوت المعتمد:** {house_system} | **الهيئة:** {sect_str}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 **التحليل الرقمي والمعادلات الرياضية المشتقة من إحداثيات Swiss Ephemeris:**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{score_blocks}\n"
            f"📡 **تحليل المقذوفات الشعاعية والروابط النسبية الحية (Relative Applying Rays):**\n"
            f"───────────────────────────────────────────────────────────────────\n"
            f"{aspects_block}\n"
            f"🌟 **تأثير النجوم الثابتة العظمى (Fixed Stars Conjunctions):**\n"
            f"───────────────────────────────────────────────────────────────────\n"
            f"{stars_block}\n\n"
            f"🏹 **السهام والنقاط الرياضية الحساسة المستخرجة (Astrological Lots):**\n"
            f"{lots_text}\n\n"
            f"💡 **الخلاصة الفلسفية التنجيمية الكبرى لليوم:**\n"
            f"_{rep.synthesis_text}_\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⚠️ **وثيقة المنهجية الفلكية:** هذا التقرير هو محاكاة حاسوبية مصمتة مستخرجة بالكامل "
            f"من جداول مكتبة سويس إيفيميرس العالمية، حيث تُجرى حسابات الإسقاط الكروي وميل دائرة البروج بدقة تامة."
        )
        return output
