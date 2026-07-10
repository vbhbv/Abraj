import json
import logging
from typing import Dict, List, Any

# إعداد السجلات لمراقبة الأداء في الاستضافة (مثل Railway)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AstrologySynthesisEngine:
    def __init__(self, json_path: str = "interpretations.json"):
        self.json_path = json_path
        self.interpretations = self.load_interpretations()
        
        # أدوات ربط ديناميكية لكسر الجمود النصي
        self.connectors = [
            " يتكامل هذا التموقع بعمق مع وجوده في ",
            "، الأمر الذي ينعكس بشكل مباشر على شؤون ",
            "، مما يمنح طاقة هذا الكوكب تجسيداً عملياً داخل ",
            " ليصبح مسرحاً رئيسياً لـ "
        ]

    def load_interpretations(self) -> Dict[str, Any]:
        """تحميل ملف الـ JSON المصلح والتأكد من سلامته برمجياً"""
        try:
            with open(self.json_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading JSON file: {e}")
            return {}

    def calculate_element_balance(self, birth_data: Dict[str, str]) -> str:
        """
        1. نظام الموازين والعناصر: يحسب طغيان الطاقات النفسية (ترابي، مائي، ناري، هوائي)
        """
        elements = {"نارية": 0, "ترابية": 0, "هوائية": 0, "مائية": 0}
        
        element_mapping = {
            "Aries": "نارية", "Leo": "نارية", "Sagittarius": "نارية",
            "Taurus": "ترابية", "Virgo": "ترابية", "Capricorn": "ترابية",
            "Gemini": "هوائية", "Libra": "هوائية", "Aquarius": "هوائية",
            "Cancer": "مائية", "Scorpio": "مائية", "Pisces": "مائية"
        }
        
        # فحص الكواكب الشخصية الرئيسية لإعطاء وزن للعناصر
        for planet in ["Sun", "Moon", "Mercury", "Venus", "Mars"]:
            sign = birth_data.get(planet)
            if sign in element_mapping:
                elements[element_mapping[sign]] += 1
                
        # تحديد العنصر المهيمن
        dominant_element = max(elements, key=elements.get)
        
        balance_reports = {
            "نارية": "🔥 تفوح خريطتك بطاقة نارية دافقة، مما يمنحك روحاً مبادرة، حماساً اشتعالياً، ورغبة مستمرة في قيادة واقعك وتحدي الركود.",
            "ترابية": "🪵 تهيمن العناصر الترابية على بنيتك الفلكية، مما يجعلك شخصاً شديد الواقعية، يبحث عن الأمان الملموس، ويتقن الصبر وبناء الاستقرار طويل الأمد.",
            "هوائية": "💨 طغيان الطابع الهوائي يمنحك عقلاً حاداً، وفضولاً معرفياً لا يهدأ، حيث تتنفس عبر الأفكار، التواصل، والتحليل المستمر للمحيط.",
            "مائية": "💧 الغلبة هنا للعنصر المائي؛ أنت تسبح في عالم من الحدس، المشاعر العميقة، والامتصاص النفسي لطاقات الآخرين، مما يمنحك بصيرة شفائية استثنائية."
        }
        return balance_reports.get(dominant_element, "")

    def detect_psychological_conflicts(self, birth_data: Dict[str, str]) -> List[str]:
        """
        2. خوارزمية رصد التناقضات: تفحص التضاد بين الكواكب الشخصية (الشمس والقمر كمثال)
        """
        conflicts = []
        sun = birth_data.get("Sun")
        moon = birth_data.get("Moon")
        
        # مثال لتناقض الظهور والانطواء (الأسد ضد العذراء أو السرطان)
        if sun == "Leo" and moon in ["Virgo", "Cancer", "Scorpio"]:
            conflicts.append(
                "🔄 **تناقض الهوية الداخلي:** تختبر صراعاً صامتاً بين شمسك في الأسد التي تعشق التقدير والظهور، وبين قمرك الباطني الذي يميل للتحفظ، الخصوصية، والتحليل خلف الكواليس."
            )
        # مثال لتناقض الاندفاع والتردد (الحمل ضد الميزان)
        if sun == "Aries" and moon == "Libra":
            conflicts.append(
                "🔄 **محور المواجهة والسلام:** روحك ممزقة بين رغبة شمسك في الحسم والمواجهة الشجاعة المباشرة، وبين حاجة قمرك في الميزان للمداراة، الدبلوماسية، والحفاظ على السلم مع الآخرين بأي ثمن."
            )
        return conflicts

    def synthesize_astrology_report(self, birth_data: Dict[str, str]) -> List[str]:
        """
        3. المحرك التركيبي الرئيسي: يدمج البروج والبيوت ديناميكياً ويقسم التقرير تلقائياً لتفادي حظر تليجرام
        """
        messages_to_send = []
        
        # الجزء الأول: المقدمة والموازين والتناقضات
        header = "🔮 **التحليل الفلكي التركيبي للمحترفين** 🔮\n\n"
        header += self.calculate_element_balance(birth_data) + "\n\n"
        
        conflicts = self.detect_psychological_conflicts(birth_data)
        if conflicts:
            header += "⚠️ **رادار البصيرة الفلكية (التناقضات المكتشفة):**\n" + "\n".join(conflicts) + "\n\n"
            
        header += "📌 **التشريح التفصيلي للمواضع الفلكية:**\n"
        current_chunk = header
        
        # دمج الكواكب والبيوت ديناميكياً من الـ JSON
        for planet, sign in birth_data.items():
            if planet in ["house_1", "house_2"]: # تجنب مفاتيح البيوت المجردة إن وجدت في المدخلات
                continue
                
            house = birth_data.get(f"{planet}_house") # نفترض أن المدخلات تحتوي على الكوكب وبيته مثل: 'Sun_house': '10'
            
            sign_text = self.interpretations.get(planet, {}).get(sign, "")
            house_text = self.interpretations.get(planet, {}).get(house, "")
            
            if sign_text and house_text:
                # صياغة تركيبية ممتازة باستخدام أداة ربط
                combined_analysis = f"🪐 **{planet} في {sign} داخل البيت {house}:**\n{sign_text}{self.connectors[1]}{house}\n↳ *العمق الاستراتيجي:* {house_text}\n\n"
                
                # التحقق من سعة الرسالة (تليجرام يسمح بـ 4096 حرفاً، نأخذ 3500 كأمان)
                if len(current_chunk) + len(combined_analysis) > 3500:
                    messages_to_send.append(current_chunk)
                    current_chunk = combined_analysis
                else:
                    current_chunk += combined_analysis
                    
        if current_chunk:
            messages_to_send.append(current_chunk)
            
        return messages_to_send

# ==========================================
# مثال تشغيلي لمحاكاة البوت عند ضغط زر المحترفين
# ==========================================
if __name__ == "__main__":
    # محاكاة لبيانات مستخدم تم حساب خريطته (الشمس في الأسد في البيت 10، القمر في العذراء في البيت 4... الخ)
    user_birth_chart = {
        "Sun": "Leo", "Sun_house": "10",
        "Moon": "Virgo", "Moon_house": "4",
        "Mercury": "Gemini", "Mercury_house": "11",
        "Venus": "Taurus", "Venus_house": "2",
        "Mars": "Aries", "Mars_house": "1",
        "Jupiter": "Capricorn", "Jupiter_house": "3"
    }
    
    # تشغيل المحرك
    engine = AstrologySynthesisEngine()
    report_chunks = engine.synthesize_astrology_report(user_birth_chart)
    
    # طباعة النتيجة لرؤية كيف سيبدو التقرير ذكياً ومتدفقاً ومقسماً في التليجرام
    for index, chunk in enumerate(report_chunks, start=1):
        print(f"--- الرسالة رقم {index} ---")
        print(chunk)
              
