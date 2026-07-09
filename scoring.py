from typing import List
from models import AstrologicalFact

class ProfileScores:
    def __init__(self):
        # تعريف الخصائص الأساسية للتقييم
        self.career = 0
        self.leadership = 0
        self.anger = 0
        self.competition = 0

    @property
    def total_score(self):
        # خاصية محسوبة تلقائياً تقوم بجمع جميع النقاط الحالية
        return self.career + self.leadership + self.anger + self.competition

class RulesEngine:
    @staticmethod
    def evaluate(facts: List[AstrologicalFact]) -> ProfileScores:
        # إنشاء كائن جديد لكل عملية تقييم
        scores = ProfileScores()
        
        # تحليل الحقائق وتوزيع النقاط
        for fact in facts:
            if fact.code == "SUN_H10":
                scores.career += 20
                scores.leadership += 15
            elif "MARS" in fact.code and "SQUARE" in fact.code:
                scores.anger += 12
                scores.competition += 18
            elif "ASC_LEO" in fact.code:
                scores.leadership += 10
                
        return scores
        
