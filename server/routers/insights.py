from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Any
from datetime import datetime
from ..dependencies import get_db_manager
from src.data.db_manager import DBManager

router = APIRouter(prefix="/insights", tags=["insights"])

class InsightItem(BaseModel):
    type: str # duplicate_found, untagged_files, album_suggestion, low_quality_tags
    title: str
    message: str
    action_url: str
    action_label: str
    priority: str # high, medium, low
    count: int
    tag: Optional[str] = None
    query_json: Optional[str] = None

class InsightsResponse(BaseModel):
    insights: List[InsightItem]
    generated_at: datetime

@router.get("", response_model=InsightsResponse)
async def get_insights(db: DBManager = Depends(get_db_manager)):
    """
    Analyzes the library and returns actionable suggestions.
    """
    try:
        insights_data = db.get_insights()
        return {
            "insights": insights_data,
            "generated_at": datetime.now()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate insights: {str(e)}")
