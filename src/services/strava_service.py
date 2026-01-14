"""
Strava Activity Parser Service
Extracts activity data from Strava links (short links and full URLs)
"""

import requests
from bs4 import BeautifulSoup
import re
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


def parse_strava(url: str) -> Dict[str, Any]:
    """
    ดึงข้อมูล Activity จาก Strava Link
    รองรับทั้ง short link (strava.app.link) และ full link (strava.com/activities/xxx)
    
    Args:
        url: Strava activity URL
        
    Returns:
        Dictionary with activity data or error information
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
    }

    try:
        session = requests.Session()
        response = session.get(url, headers=headers, allow_redirects=True, timeout=10)
        
        if response.status_code != 200:
            logger.warning(f"Strava request failed with status {response.status_code} for URL: {url}")
            return {
                "success": False, 
                "error": f"HTTP {response.status_code}",
                "hint": "Please enter distance manually"
            }

        html = response.text
        soup = BeautifulSoup(html, 'html.parser')
        
        data = {
            "success": True,
            "distance_km": 0.0,
            "moving_time": None,
            "activity_name": None,
            "elevation_gain": None
        }

        # 1. Activity Name
        if soup.title:
            title_text = soup.title.string if soup.title.string else ""
            data["activity_name"] = title_text.replace('| Strava', '').strip() or None

        # 2. Distance (meters -> km)
        dist_match = re.search(r'"distance"\s*:\s*([\d.]+)', html)
        if dist_match:
            data["distance_km"] = round(float(dist_match.group(1)) / 1000, 2)

        # 3. Moving Time
        for key in ['moving_time', 'elapsed_time']:
            time_match = re.search(f'"{key}"\\s*:\\s*(\\d+)', html)
            if time_match:
                seconds = int(time_match.group(1))
                if seconds > 0:
                    h, rem = divmod(seconds, 3600)
                    m, s = divmod(rem, 60)
                    data["moving_time"] = f"{h:02d}:{m:02d}:{s:02d}"
                    break
        
        # 3b. Fallback - Text patterns (1h 20m, 50m 30s)
        if not data["moving_time"]:
            text = soup.get_text(" ", strip=True)
            hm = re.search(r'(\d+)h\s+(\d+)m', text)
            ms = re.search(r'(\d+)m\s+(\d+)s', text)
            if hm:
                secs = int(hm.group(1)) * 3600 + int(hm.group(2)) * 60
                h, rem = divmod(secs, 3600)
                m, s = divmod(rem, 60)
                data["moving_time"] = f"{h:02d}:{m:02d}:{s:02d}"
            elif ms:
                secs = int(ms.group(1)) * 60 + int(ms.group(2))
                m, s = divmod(secs, 60)
                data["moving_time"] = f"00:{m:02d}:{s:02d}"

        # 4. Elevation
        elev_match = re.search(r'"elevation_gain"\s*:\s*([\d.]+)', html)
        if elev_match:
            data["elevation_gain"] = f"{int(float(elev_match.group(1)))} m"

        # Validate - must have distance
        if data["distance_km"] <= 0:
            logger.info(f"Could not extract distance from Strava URL: {url}")
            return {
                "success": False, 
                "error": "Could not extract distance",
                "hint": "Please enter distance manually"
            }

        logger.info(f"Successfully parsed Strava activity: {data['activity_name']} - {data['distance_km']} km")
        return data

    except requests.Timeout:
        logger.warning(f"Timeout while fetching Strava URL: {url}")
        return {
            "success": False, 
            "error": "Request timeout",
            "hint": "Please try again or enter distance manually"
        }
    except requests.RequestException as e:
        logger.error(f"Request error for Strava URL {url}: {str(e)}")
        return {
            "success": False, 
            "error": f"Network error: {str(e)}",
            "hint": "Please check the URL or enter distance manually"
        }
    except Exception as e:
        logger.error(f"Unexpected error parsing Strava URL {url}: {str(e)}")
        return {
            "success": False, 
            "error": str(e),
            "hint": "Please enter distance manually"
        }
