from pydantic import BaseModel
from typing import List, Optional

class ReportRecord(BaseModel):
    value: float
    timestamp: str
    chipId: Optional[str] = "desconhecido"

class ReportStats(BaseModel):
    media: Optional[float] = None
    min: Optional[float] = None
    max: Optional[float] = None
    desvioPadrao: Optional[float] = None
    variancia: Optional[float] = None
    CVOutlier: Optional[float] = None
    CVNoOutlier: Optional[float] = None
    totalRecords: Optional[int] = None
    totalOutliers: Optional[int] = None

class ReportRequest(BaseModel):
    records: List[ReportRecord]
    statistics: Optional[ReportStats] = None

class ExperimentRecord(BaseModel):
    value: float
    timestamp: Optional[str] = None


class ExperimentMetadata(BaseModel):
    nome: str
    objetivo: str
    min: float
    max: float

class ExperimentReportRequest(BaseModel):
    records: List[ExperimentRecord]
    metadata: ExperimentMetadata