import os
import re
import json
import requests
from pathlib import Path
from typing import Dict, Any, Optional

from pdf import logger
from config import DEVELOPMENT_MODE

# === Constants ===
CACHE_DIR = Path("cache")
CACHE_DIR.mkdir(exist_ok=True)
GRAPHQL_URL = "https://leetcode.com/graphql/"
LC_CACHE_PREFIX = "leetcodecache_"


def _extract_username(url: str) -> Optional[str]:
    """Extracts LeetCode username from profile URL."""
    if not url:
        return None
    url = url.strip()
    patterns = [
        r"https?://leetcode\.com/u/([^/]+)/?",
        r"https?://leetcode\.com/profile/([^/]+)/?",
        r"leetcode\.com/u/([^/]+)/?",
        r"leetcode\.com/profile/([^/]+)/?",
        r"^([A-Za-z0-9_\-]+)$",
    ]
    for p in patterns:
        match = re.search(p, url)
        if match:
            return match.group(1)
    return None


def _cache_path(username: str) -> Path:
    return CACHE_DIR / f"{LC_CACHE_PREFIX}{username}.json"


def _fetch_from_api(username: str) -> Dict[str, Any]:
    """Fetch profile data using LeetCode GraphQL."""
    query = """
    query getUserProfile($username: String!) {
      matchedUser(username: $username) {
        username
        profile { realName aboutMe userAvatar }
        submitStatsGlobal { acSubmissionNum { difficulty count } }
        submissionCalendar
      }
      userContestRanking(username: $username) {
        rating globalRanking topPercentage attendedContestsCount
      }
      userContestRankingHistory(username: $username) {
        contest { title startTime }
        rating ranking attended
      }
    }"""
    try:
        res = requests.post(
            GRAPHQL_URL,
            json={"query": query, "variables": {"username": username}},
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
        if res.status_code == 200:
            return res.json()
        logger.error(f"⚠️ LeetCode API error: {res.status_code}")
        return {}
    except Exception as e:
        logger.error(f"❌ Request failed: {e}")
        return {}


def fetch_leetcode_profile(url: str) -> Optional[Dict[str, Any]]:
    """Fetch and cache user profile data."""
    username = _extract_username(url)
    if not username:
        print(f"❌ Could not extract username from: {url}")
        return None

    cache_file = _cache_path(username)
    if DEVELOPMENT_MODE and cache_file.exists():
        print(f"📦 Loaded cached data → {cache_file}")
        return json.loads(cache_file.read_text())

    print(f"🔍 Fetching LeetCode data for {username}...")
    data = _fetch_from_api(username)
    user = data.get("data", {}).get("matchedUser")
    if not user:
        print("❌ Failed to fetch or parse profile.")
        return None

    contests = data["data"].get("userContestRanking", {}) or {}
    history = data["data"].get("userContestRankingHistory", []) or []

    # Identify best contest by highest rating
    best_contest = None
    max_rating = -1
    for c in history:
        if c.get("attended") and isinstance(c.get("rating"), (int, float)):
            if c["rating"] > max_rating:
                max_rating = c["rating"]
                best_contest = c

    # Count active days
    active_days = 0
    try:
        cal = json.loads(user.get("submissionCalendar", "{}"))
        active_days = sum(1 for v in cal.values() if int(v) > 0)
    except Exception:
        pass

    profile = {
        "username": user.get("username"),
        "name": user.get("profile", {}).get("realName"),
        "about": user.get("profile", {}).get("aboutMe"),
        "solved_by_difficulty": user.get("submitStatsGlobal", {}).get("acSubmissionNum", []),
        "contest_rating": contests.get("rating"),
        "global_rank": contests.get("globalRanking"),
        "top_percentage": contests.get("topPercentage"),
        "contests_attended": contests.get("attendedContestsCount"),
        "best_contest": {
            "title": best_contest["contest"]["title"],
            "rating": best_contest["rating"],
            "ranking": best_contest["ranking"],
        } if best_contest else None,
        "active_days": active_days,
    }

    if DEVELOPMENT_MODE:
        cache_file.write_text(json.dumps(profile, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"💾 Cached LeetCode data → {cache_file}")

    return profile


def display_leetcode_info(url: str) -> Dict[str, Any]:
    """Minimal CLI summary."""
    profile = fetch_leetcode_profile(url)
    if not profile:
        print("❌ No LeetCode data found.")
        return {}

    print("\n📊 LeetCode Summary")
    print("----------------------------")
    print(f"👤 {profile.get('name')} ({profile.get('username')})")
    print(f"🏆 Rating: {profile.get('contest_rating')} | 🧩 Solved: {profile['solved_by_difficulty'][0]['count']}")
    print(f"📅 Active Days: {profile.get('active_days')} | 🌍 Rank: {profile.get('global_rank')}")
    if profile.get("best_contest"):
        bc = profile["best_contest"]
        print(f"⭐ Best Contest: {bc['title']} (Rank {bc['ranking']})")
    print("----------------------------")
    return profile


if __name__ == "__main__":
    display_leetcode_info("https://leetcode.com/u/9pranjal/")