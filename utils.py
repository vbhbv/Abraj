from datetime import datetime
from zoneinfo import ZoneInfo, AmbiguousTimeError, NonExistentTimeError

def is_between_arc(start: float, end: float, longitude: float) -> bool:
    """تحقق ما إذا كان خط طول الكوكب يقع ضمن قوس دائري محدد برمجياً ومعالجة الالتفاف 360"""
    if start <= end:
        return start <= longitude < end
    else:
        return longitude >= start or longitude < end

def resolve_local_time(tz_name: str, y: int, m: int, d: int, h: int, mn: int) -> datetime:
    """بناء وقت واعٍ بالمنطقة الزمنية مع معالجة الساعات الملتبسة أو المفقودة أثناء قفزة التوقيت الصيفي"""
    tz = ZoneInfo(tz_name)
    local_naive = datetime(y, m, d, h, mn)
    
    try:
        return local_naive.replace(tzinfo=tz)
    except AmbiguousTimeError:
        return local_naive.replace(tzinfo=tz).astimezone(tz)
    except NonExistentTimeError:
        raise ValueError("وقت الميلاد المدخل يقع ضمن ساعة قفزة التوقيت الصيفي (ساعة غير موجودة جغرافياً).")
