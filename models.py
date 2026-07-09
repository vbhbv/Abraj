from pydantic import BaseModel, Field
from typing import List, Dict, Optional

class CalculationSystem(BaseModel):
    house_system: str = "Placidus"
    zodiac: str = "Tropical"
    ayanamsa: Optional[str] = None

class ChartMetadata(BaseModel):
    schema_version: str = "1.0"
    engine_version: str = "1.0.0"
    calculation_system: CalculationSystem = Field(default_factory=CalculationSystem)

class BirthDataInput(BaseModel):
    year: int = Field(..., ge=1800, le=2100)
    month: int = Field(..., ge=1, le=12)
    day: int = Field(..., ge=1, le=31)
    hour: int = Field(..., ge=0, le=23)
    minute: int = Field(..., ge=0, le=59)
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)

class PlanetData(BaseModel):
    name: str
    longitude: float
    sign: str
    degree: float
    house: int
    retrograde: bool
    speed: float

class AspectData(BaseModel):
    planet1: str
    planet2: str
    type: str
    orb: float
    applying: bool

class ChartResult(BaseModel):
    metadata: ChartMetadata = Field(default_factory=ChartMetadata)
    ascendant: str
    midheaven: str
    planets: Dict[str, PlanetData]
    aspects: List[AspectData]
    houses: Dict[int, float]

class AstrologicalFact(BaseModel):
    code: str
    strength: float
    category: str

class ProfileScores(BaseModel):
    career: int = 0
    leadership: int = 0
    anger: int = 0
    competition: int = 0
    emotion: int = 0
