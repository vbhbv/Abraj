from datetime import datetime
from zoneinfo import ZoneInfo

def is_between_arc(start: float, end: float, longitude: float) -> bool:
    """تحقق ما إذا كان خط طول الكوكب يقع ضمن قوس دائري محدد برمجياً ومعالجة الالتفاف 360"""
    if start <= end:
        return start <= longitude < end
    else:
        return longitude >= start or longitude < end

def resolve_local_time(tz_name: str, y: int, m: int, d: int, h: int, mn: int) -> datetime:
    """بناء وقت واعٍ بالمنطقة الزمنية مع معالجة التوقيت الصيفي بشكل آمن تلقائياً"""
    tz = ZoneInfo(tz_name)
    local_naive = datetime(y, m, d, h, mn)
    
    # ربط المنطقة الزمنية مباشرة؛ بايثون سيتكفل بحل التناقضات الصيفية/الشتوية تلقائياً
    return local_naive.replace(tzinfo=tz)
