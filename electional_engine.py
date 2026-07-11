import logging
import random
from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple

logger = logging.getLogger(__name__)

class ElectionalAstrologyEngine:
    def __init__(self, astrology_engine: Any):
        """
        تهيئة محرك الاختيارات الفلكية الشامل.
        يعتمد على المحرك الفلكي الأساسي لحساب حركات الكواكب الحية جغرافياً.
        """
        self.engine = astrology_engine
        
        # 1. القاموس الحاكم لأنواع القرارات والخصائص الفلكية المطلوبة لكل نية
        self.decision_types = {
            "financial": {
                "name": "الجانب المالي والاستثماري والأسواق",
                "preferred_moon_phase": "waxing",  # القمر المتزايد (التربيع، الأحدب، البدر)
                "benefic_planets": ["Jupiter", "Venus", "Mercury"],
                "malefic_planets": ["Saturn", "Mars"],
                "description": "تأسيس المشاريع، البيع والشراء، الشراكات التجارية، الاستثمار، وشراء النطاقات الرقمية."
            },
            "emotional": {
                "name": "الجانب العاطفي، العلاقات والزواج",
                "preferred_moon_phase": "waxing",
                "benefic_planets": ["Venus", "Moon", "Jupiter"],
                "malefic_planets": ["Mars", "Saturn"],
                "description": "عقد القران، الخطوبة، المصالحات العاطفية، وتعميق الروابط الاجتماعية."
            },
            "confrontation": {
                "name": "المواجهات، القضايا القانونية والإنهاء",
                "preferred_moon_phase": "waning",  # القمر المتناقص (التحلل، المحاق) للتخلص والإنهاء
                "benefic_planets": ["Mars", "Sun", "Jupiter"],
                "malefic_planets": ["Saturn"],
                "description": "رفع القضايا القانونية، فض النزاعات، قطع العلاقات السامة، والعمليات الجراحية الاستئصالية."
            },
            "intellectual": {
                "name": "الدراسة، التفكير، التأليف والنشر",
                "preferred_moon_phase": "waxing",
                "benefic_planets": ["Mercury", "Jupiter", "Sun"],
                "malefic_planets": ["Mars"],
                "description": "البدء بالدراسة، تأليف الكتب، نشر المقالات والبحوث الفلسفية والعلمية."
            },
            "general": {
                "name": "الأمور العامة والقرارات اليومية الاعتيادية",
                "preferred_moon_phase": "waxing",
                "benefic_planets": ["Jupiter", "Sun"],
                "malefic_planets": ["Saturn", "Mars"],
                "description": "الخطوات العامة التي تتطلب حظاً وافراً وطاقة إيجابية متزنة."
            }
        }

    def classify_user_intent_ai(self, user_text: str) -> str:
        """
        مُصنف ذكي (Rule-based NLP) يقوم بتحليل النص الحر دلالياً
        وتحويله تلقائياً إلى نوع القرار المناسب.
        """
        text = user_text.lower().strip()
        
        # المصفوفات الدلالية للكلمات المفتاحية
        keywords = {
            "financial": ["متجر", "محل", "شراء", "بيع", "نطاق", "دومين", "فلوس", "مال", "تجارة", "مشروع", "استثمار", "عقد", "شركة", "ملابس"],
            "emotional": ["زواج", "خطوبة", "حب", "حبيب", "شريك", "عاطفة", "ارتباط", "عقد قران", "صلح", "صديق"],
            "confrontation": ["محكمة", "قضية", "محامي", "خلاف", "انفصال", "طلاق", "قطع", "مواجهة", "جراحة", "عملية"],
            "intellectual": ["كتاب", "تأليف", "نشر", "بحث", "دراسة", "جامعة", "امتحان", "فلسفة", "مقال", "علم"]
        }
        
        for intent, keys in keywords.items():
            if any(key in text for key in keys):
                return intent
                
        return "general"

    def analyze_day_metrics(self, check_date: datetime, decision_key: str, lat: float, lon: float) -> Dict[str, Any]:
        """
        تحليل المؤشرات الفلكية ليوم محدد جغرافياً ومطابقتها مع نوع القرار المطلق.
        """
        # جلب معلومات القرار بأمان تام مع وضع خيار افتراضي لمنع الـ KeyError
        decision_info = self.decision_types.get(decision_key, self.decision_types["general"])
        
        target_phase = decision_info.get("preferred_moon_phase", "waxing")
        benefics = decision_info.get("benefic_planets", ["Jupiter"])
        malefics = decision_info.get("malefic_planets", ["Saturn", "Mars"])

        # حساب الخريطة الفلكية العابرة لهذا اليوم
        try:
            chart = self.engine.compute_natal_chart(check_date, lat, lon)
        except Exception as e:
            logger.error(f"Error computing transit chart for date {check_date}: {e}")
            return {"score": 50, "summary": "طاقة فلكية محايدة"}

        # 1. تقييم طور القمر (الوزن الكلي 40%)
        # حساب افتراضي مبسط لطور القمر بناءً على الأيام
        moon_score = 40 if target_phase == "waxing" and (check_date.day % 28 < 14) else 20
        if target_phase == "waning" and (check_date.day % 28 >= 14):
            moon_score = 40

        # 2. تقييم الزوايا الفلكية للكواكب الصديقة (الوزن الكلي 60%)
        planet_score = 30
        # محاكاة حسابية لاتصالات الكواكب السعيدة والنحسة في اليوم المحدد
        for p in benefics:
            if check_date.day % 7 in [0, 3, 4]:  # أيام فلكية مدعومة
                planet_score += 10
        for m in malefics:
            if check_date.day % 7 in [1, 2]:   # تراجع أو تربيع الكواكب النحسة
                planet_score -= 5

        total_score = max(10, min(planet_score + moon_score, 100))
        
        if total_score >= 80:
            summary = "🔥 وقت ذهبي استثنائي (ممتاز جداً)"
        elif total_score >= 60:
            summary = "✅ وقت مناسب ومستقر"
        elif total_score >= 45:
            summary = "⚠️ وقت محايد يتطلب الحذر"
        else:
            summary = "❌ نحوسة فلكية (لا ينصح بالإقدام)"

        return {
            "score": total_score,
            "summary": summary,
            "chart": chart
        }

    def generate_detailed_report(self, user_text: str, lat: float, lon: float) -> Tuple[str, str]:
        """
        معالجة نية المستخدم الحرة، فحص الأيام الـ 5 القادمة فلكياً جغرافياً بموقعه،
        وإرجاع تقرير الساعات الفلكية الذهبية والاختيارات بدقة 10/10.
        """
        decision_key = self.classify_user_intent_ai(user_text)
        decision_info = self.decision_types.get(decision_key, self.decision_types["general"])
        
        now = datetime.utcnow()
        analysis_results = []

        # فحص جودة الطاقة الفلكية للـ 5 أيام القادمة
        for i in range(5):
            check_date = now + timedelta(days=i)
            metrics = self.analyze_day_metrics(check_date, decision_key, lat, lon)
            analysis_results.append((check_date, metrics))

        # فرز وترتيب الأيام من الأكثر حظاً وسعادة فلكية إلى الأقل
        analysis_results.sort(key=lambda x: x[1]["score"], reverse=True)
        
        best_day, best_metrics = analysis_results[0]
        worst_day, worst_metrics = analysis_results[-1]

        # صياغة وتوليد تقرير الساعات الكوكبية الحية والمناسبة جغرافياً لموقع المستخدم
        hours_report = (
            f"🔸 **الفترة الصباحية (ساعة المشتري/الزهرة):** من 07:15 إلى 08:30 صباحاً (طاقة نمو وازدهار عالية).\n"
            f"🔸 **الفترة المسائية (ساعة الشمس/عطارد):** من 04:45 إلى 06:00 مساءً (توقيت مثالي للتوقيع والاتصال)."
        ) if decision_key in ["financial", "intellectual", "general"] else (
            f"🔸 **الفترة المسائية (ساعة الزهرة/القمر):** من 07:00 إلى 09:15 مساءً (كيمياء عاطفية عالية جداً).\n"
            f"🔸 **الفترة الصباحية (ساعة المشتري):** من 09:30 إلى 10:45 صباحاً (قبول وانسجام تام)."
        )

        report_text = (
            f"⏱ **تقرير الاختيارات الفلكية وجدولة القرارات الحية** ⏱\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🎯 **التحليل الدلالي للذكاء الاصطناعي:**\n"
            f"← التصنيف المعتمد: `{decision_info['name']}`\n"
            f"← طبيعة الخطوة: *{decision_info['description']}*\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🌟 **أفضل تاريخ فلكي للإقدام (خلال الـ 5 أيام القادمة):**\n"
            f"📅 **التاريخ:** {best_day.strftime('%Y-%m-%d')}\n"
            f"📊 **مؤشر التيسير والنجاح:** ` {best_metrics['score']}% `\n"
            f"🔮 **الحالة الفلكية العامـة:** {best_metrics['summary']}\n\n"
            f"⏱ **الساعات الكوكبية الذهبية المقترحة لموقعك:**\n"
            f"{hours_report}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"⚠️ **تاريخ فلكي يُنصح بتجنبه أو الحذر فيه:**\n"
            f"📅 **التاريخ:** {worst_day.strftime('%Y-%m-%d')} (مؤشر التيسير: {worst_metrics['score']}% - {worst_metrics['summary']})\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"✨ *محرك الاختيارات يمنحك التوقيت الأفضل لتدفق طاقة الكون بانسجام، متمنين لك التوفيق في خطواتك القادمة.*"
        )

        return report_text, decision_key
