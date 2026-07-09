from fastapi import FastAPI, HTTPException
import os
from models import BirthDataInput, ChartResult, ProfileScores
from chart import CoreAstrologyEngine
from time_service import BirthDataService
from facts_engine import FactsEngine
from scoring import RulesEngine

app = FastAPI(
    title="Professional Astrology Engine API",
    description="Enterprise Architecture with Facts Engine Layer",
    version="1.0.0"
)

# تهيئة المحركات تلقائياً من مجلد الجذر
engine = CoreAstrologyEngine()
time_service = BirthDataService()

@app.get("/")
def health_check():
    # جلب المتغيرات من لوحة تحكم الاستضافة للتأكد من قراءتها واختبار الحالة
    db_url = os.getenv("DATABASE_URL")
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    
    return {
        "status": "online",
        "engine": "Swiss Ephemeris Core",
        "database_configured": True if db_url else False,
        "telegram_bot_configured": True if bot_token else False
    }

@app.post("/api/v1/chart", response_model=ChartResult, tags=["V1 Core"])
def calculate_chart(birth_data: BirthDataInput):
    try:
        dt_utc = time_service.process_and_convert_to_utc(birth_data)
        return engine.compute_natal_chart(dt_utc, birth_data.latitude, birth_data.longitude)
    except ValueError as ve:
        raise HTTPException(status_code=422, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Calculation Error: {str(e)}")

@app.post("/api/v1/facts", tags=["V1 Core"])
def get_facts(chart: ChartResult):
    return FactsEngine.extract_facts(chart)

@app.post("/api/v1/scoring", response_model=ProfileScores, tags=["V1 Core"])
def get_scoring(chart: ChartResult):
    facts = FactsEngine.extract_facts(chart)
    return RulesEngine.evaluate(facts)

if __name__ == "__main__":
    import uvicorn
    # جلب المنفذ ديناميكياً من السيرفر (Railway يعين المنفذ تلقائياً عبر متغير PORT)
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
