import json
import logging
import re
import requests
from typing import Dict, Optional, Any
from datetime import datetime

from models import CodeForcesProfile
from config import DEVELOPMENT_MODE

# Configure logger
logger = logging.getLogger(__name__)

CODEFORCES_API_URL = "https://codeforces.com/api"


def _extract_username(url: str) -> Optional[str]:
    """Extracts CodeForces username from URL or plain text."""
    if not url:
        return None
    url = url.strip()
    # Patterns for CodeForces profile URLs
    patterns = [
        r"https?://codeforces\.com/profile/([^/]+)/?",
        r"codeforces\.com/profile/([^/]+)/?",
        r"^([A-Za-z0-9_\-]+)$",
    ]
    for p in patterns:
        match = re.search(p, url)
        if match:
            return match.group(1)
    return None


def fetch_codeforces_profile(url_or_username: str) -> Optional[CodeForcesProfile]:
    """
    Fetch CodeForces user info using the official API.
    API Endpoint: https://codeforces.com/api/user.info?handles={username}
    """
    username = _extract_username(url_or_username)
    if not username:
        logger.error(f"❌ Could not extract username from: {url_or_username}")
        return None

    api_url = f"{CODEFORCES_API_URL}/user.info"
    params = {"handles": username}

    logging.info(f"🔍 Fetching CodeForces data for '{username}'...")

    try:
        response = requests.get(api_url, params=params, timeout=10)
        if response.status_code != 200:
            logger.error(f"⚠️ CodeForces API returned status {response.status_code}")
            return None
        
        data = response.json()
        if data.get("status") != "OK":
            logger.error(f"❌ CodeForces API error: {data.get('comment')}")
            return None
        
        result = data.get("result", [])
        if not result:
            logger.error("❌ No user data found.")
            return None

        user_info = result[0]

        profile = CodeForcesProfile(
            username=user_info.get("handle"),
            rank=user_info.get("rank"),
            current_rating=user_info.get("rating"),
            max_rating=user_info.get("maxRating"),
            last_online_time_seconds=user_info.get("lastOnlineTimeSeconds"),
            friend_of_count=user_info.get("friendOfCount"),
            title_photo=user_info.get("titlePhoto"),
            max_rank=user_info.get("maxRank"),
        )
        return profile

    except Exception as e:
        logger.error(f"❌ CodeForces API request failed: {e}")
        return None


def fetch_and_display_codeforces_info(url: str) -> Dict[str, Any]:
    """Fetch CodeForces data, print summary, and return structured JSON."""
    profile = fetch_codeforces_profile(url)
    if not profile:
        print("❌ Failed to fetch CodeForces data.")
        return {}

    print("\n📊 CODEFORCES PROFILE SUMMARY")
    print("=" * 60)
    print(f"👤 Handle: {profile.username}")
    print(f"🏆 Rank: {profile.rank} (Max: {profile.max_rank})")
    print(f"📉 Rating: {profile.current_rating} (Max: {profile.max_rating})")
    if profile.last_online_time_seconds:
        last_online = datetime.fromtimestamp(profile.last_online_time_seconds).strftime('%Y-%m-%d %H:%M:%S')
        print(f"📅 Last Online: {last_online}")
    print(f"🤝 Friend of: {profile.friend_of_count} users")
    print("=" * 60)

    return profile.model_dump()


if __name__ == "__main__":
    # Test with a known user, e.g., 'tourist'
    test_user = "tourist"
    fetch_and_display_codeforces_info(test_user)

