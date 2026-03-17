from pydantic import BaseModel, Field
from typing import List, Optional, Union, Literal


class InsightThresholds(BaseModel):
    min: float
    max: float
    criticalMax: float


class InsightStatistics(BaseModel):
    mean: float
    max: float
    min: float
    stdDev: Optional[float] = None
    lastValue: float
    outliers: List[float] = []
    sampling: List[float] = [] 


class GeneralInsightRequest(BaseModel):
    mode: Literal['general']
    text: str
    statistics: InsightStatistics

class ExperimentInsightRequest(BaseModel):
    mode: Literal['experiment']
    text: str
    culture: str
    stage: str
    thresholds: InsightThresholds
    equipment: List[str]
    statistics: InsightStatistics


InsightRequest = Union[GeneralInsightRequest, ExperimentInsightRequest]