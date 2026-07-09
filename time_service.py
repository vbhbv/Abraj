from datetime import datetime
from zoneinfo import ZoneInfo
from timezonefinder import TimezoneFinder
from models import BirthDataInput
from utils import resolve_local_time

class BirthDataService:
    def __init__(self):
        self.tf = TimezoneFinder()

    def process_and_convert_to_utc(self, data: BirthDataInput) -> datetime:
        tz_name = self.tf.timezone_at(lng=data.longitude, lat=data.latitude)
        if not tz_name:
            raise ValueError("لم يتم العثور على منطقة زمنية صالحة لهذه الإحداثيات الجغرافية.")
            
        local_aware = resolve_local_time(tz_name, data.year, data.month, data.day, data.hour, data.minute)
        return local_aware.astimezone(ZoneInfo("UTC"))
