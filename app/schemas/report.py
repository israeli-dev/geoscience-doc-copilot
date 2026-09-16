from typing import List, Optional
from pydantic import BaseModel, Field

class GeoscienceReportRequest(BaseModel):
    report_text: str = Field(..., description="Raw text from geological/petroleum survey document")

class FormationDetail(BaseModel):
    formation_name: str = Field(..., description="Name of rock/geological formation")
    depth_meters: Optional[float] = Field(None, description="Depth recorded in meters")
    lithology: str = Field(..., description="Rock type (e.g., Sandstone, Shale, Limestone)")

class GeoscienceReportAnalysis(BaseModel):
    field_location: str = Field(..., description="Geographic or basin location")
    primary_minerals: List[str] = Field(..., description="Key minerals or hydrocarbon indicators identified")
    formations: List[FormationDetail] = Field(..., description="Extracted structural formations")
    commercial_viability_score: int = Field(..., description="Objective viability rating from 0 to 100", ge=0, le=100)
    summary: str = Field(..., description="2-sentence executive summary of geological potential")