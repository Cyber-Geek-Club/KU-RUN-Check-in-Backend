from pydantic import BaseModel, Field
from typing import Optional


class StravaParseRequest(BaseModel):
    """Request schema for parsing Strava activity URL"""
    url: str = Field(..., description="Strava activity URL (short link or full URL)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://strava.app.link/i1I3oE8wmZb"
            }
        }


class StravaParseResponse(BaseModel):
    """Response schema for Strava activity parsing"""
    success: bool = Field(..., description="Whether parsing was successful")
    distance_km: Optional[float] = Field(None, description="Distance in kilometers")
    moving_time: Optional[str] = Field(None, description="Moving time in HH:MM:SS format")
    activity_name: Optional[str] = Field(None, description="Activity name/title")
    elevation_gain: Optional[str] = Field(None, description="Elevation gain (e.g., '15 m')")
    error: Optional[str] = Field(None, description="Error message if parsing failed")
    hint: Optional[str] = Field(None, description="Hint for user if parsing failed")
    
    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "success": True,
                    "distance_km": 1.1,
                    "moving_time": "00:08:30",
                    "activity_name": "Morning Run",
                    "elevation_gain": "15 m"
                },
                {
                    "success": False,
                    "error": "Could not extract distance",
                    "hint": "Please enter distance manually"
                }
            ]
        }
