"""
Strava API Endpoints
Parse Strava activity links to extract distance and other data
"""

from fastapi import APIRouter, Depends, HTTPException
from src.api.dependencies import get_current_user
from src.schemas.strava_schema import StravaParseRequest, StravaParseResponse
from src.services.strava_service import parse_strava
from src.models.user import User
import re

router = APIRouter()


def is_valid_strava_url(url: str) -> bool:
    """
    Validate that the URL is a Strava activity link
    """
    strava_patterns = [
        r'^https?://(www\.)?strava\.com/activities/\d+',
        r'^https?://strava\.app\.link/\w+',
    ]
    return any(re.match(pattern, url) for pattern in strava_patterns)


@router.post("/parse", response_model=StravaParseResponse)
async def parse_strava_activity(
    req: StravaParseRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Parse Strava activity URL to extract distance and activity data
    
    **Supported URL formats:**
    - Short link: `https://strava.app.link/i1I3oE8wmZb`
    - Full URL: `https://www.strava.com/activities/16830167117`
    
    **Returns:**
    - `distance_km`: Distance in kilometers
    - `moving_time`: Moving time in HH:MM:SS format
    - `activity_name`: Activity title
    - `elevation_gain`: Elevation gain in meters
    
    **Note:** Requires authentication. If parsing fails, user should enter distance manually.
    """
    url = req.url.strip()
    
    # Validate URL format
    if not is_valid_strava_url(url):
        return StravaParseResponse(
            success=False,
            error="Invalid Strava URL format",
            hint="Please provide a valid Strava activity link"
        )
    
    # Parse the Strava activity
    result = parse_strava(url)
    
    return StravaParseResponse(**result)
