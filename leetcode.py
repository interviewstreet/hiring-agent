import os
import re
import json
import requests
from pathlib import Path
from typing import Dict, Optional, Any

from models import LeetCodeProfile
from pdf import logger
from config import DEVELOPMENT_MODE

# === CONSTANTS ===
CACHE_DIR = Path("cache")
CACHE_DIR.mkdir(exist_ok=True)
GRAPHQL_URL = "https://leetcode.com/graphql/"
LC_CACHE_PREFIX = "leetcodecache_"


def _extract_username(url: str) -> Optional[str]:
    """Extracts LeetCode username from URL or plain text."""
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


def _create_cache_filename(username: str) -> str:
    """Create cache filename for a given username."""
    return f"cache/{LC_CACHE_PREFIX}{username}.json"


def _fetch_leetcode_api(username: str) -> Dict[str, Any]:
    """Fetch LeetCode profile and contest history using GraphQL."""
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
        response = requests.post(
            GRAPHQL_URL,
            json={"query": query, "variables": {"username": username}},
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
        if response.status_code == 200:
            return response.json()
        logger.error(f"⚠️ LeetCode API returned status {response.status_code}")
        return {}
    except Exception as e:
        logger.error(f"❌ LeetCode API request failed: {e}")
        return {}


def fetch_leetcode_profile(leetcode_url: str) -> Optional[LeetCodeProfile]:
    """Fetch LeetCode profile data and return LeetCodeProfile model."""
    username = _extract_username(leetcode_url)
    if not username:
        print(f"❌ Could not extract username from: {leetcode_url}")
        return None

    cache_filename = _create_cache_filename(username)

    # Load from cache in development mode
    if DEVELOPMENT_MODE and os.path.exists(cache_filename):
        print(f"📦 Loading cached LeetCode data from {cache_filename}")
        try:
            cached_data = json.loads(Path(cache_filename).read_text())
            return LeetCodeProfile(**cached_data)
        except Exception as e:
            logger.error(f"Error reading cache file {cache_filename}: {e}")

    print(f"🔍 Fetching LeetCode data for '{username}' ...")
    data = _fetch_leetcode_api(username)
    user = data.get("data", {}).get("matchedUser")
    if not user:
        print("❌ Failed to fetch or parse LeetCode profile.")
        return None

    contests = data["data"].get("userContestRanking", {}) or {}
    history = data["data"].get("userContestRankingHistory", []) or []

    # Find best contest by highest rating
    best_contest = None
    max_rating = -1
    for c in history:
        if c.get("attended") and isinstance(c.get("rating"), (int, float)):
            if c["rating"] > max_rating:
                max_rating = c["rating"]
                best_contest = c

    # Count active days from submission calendar
    active_days = 0
    try:
        calendar = json.loads(user.get("submissionCalendar", "{}"))
        active_days = sum(1 for v in calendar.values() if int(v) > 0)
    except Exception:
        pass

    profile = LeetCodeProfile(
        username=user.get("username"),
        name=user.get("profile", {}).get("realName"),
        about=user.get("profile", {}).get("aboutMe"),
        solved_by_difficulty=user.get("submitStatsGlobal", {}).get("acSubmissionNum", []),
        contest_rating=contests.get("rating"),
        global_rank=contests.get("globalRanking"),
        top_percentage=contests.get("topPercentage"),
        contests_attended=contests.get("attendedContestsCount"),
        best_contest=(
            {
                "title": best_contest["contest"]["title"],
                "rating": best_contest["rating"],
                "ranking": best_contest["ranking"],
            }
            if best_contest
            else None
        ),
        active_days=active_days,
    )

    # Cache result in dev mode
    if DEVELOPMENT_MODE:
        try:
            os.makedirs("cache", exist_ok=True)
            Path(cache_filename).write_text(
                json.dumps(profile.model_dump(), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            print(f"💾 Cached LeetCode data → {cache_filename}")
        except Exception as e:
            logger.error(f"Error caching LeetCode data: {e}")

    return profile


def generate_profile_json(profile: LeetCodeProfile) -> Dict:
    """Convert LeetCodeProfile model into JSON-friendly structure."""
    if not profile:
        return {}

    profile_json = {
        "username": profile.username,
        "name": profile.name,
        "about": profile.about,
        "solved_by_difficulty": profile.solved_by_difficulty,
        "contest_rating": profile.contest_rating,
        "global_rank": profile.global_rank,
        "top_percentage": profile.top_percentage,
        "contests_attended": profile.contests_attended,
        "best_contest": profile.best_contest,
        "active_days": profile.active_days,
    }
    return profile_json


def fetch_and_display_leetcode_info(leetcode_url: str) -> Dict:
    """Fetch LeetCode data, print summary, and return structured JSON."""
    leetcode_profile = fetch_leetcode_profile(leetcode_url)
    if not leetcode_profile:
        print("❌ Failed to fetch LeetCode data.")
        return {}

    print("\n📘 LEETCODE PROFILE SUMMARY")
    print("=" * 60)
    print(f"👤 Username: {leetcode_profile.username or 'N/A'}")
    print(f"🏆 Contest Rating: {leetcode_profile.contest_rating or 'N/A'}")
    print(f"🌍 Global Rank: {leetcode_profile.global_rank or 'N/A'}")
    print(f"🎯 Contests Attended: {leetcode_profile.contests_attended or 'N/A'}")
    print(f"📅 Active Days: {leetcode_profile.active_days or 'N/A'}")

    if leetcode_profile.solved_by_difficulty:
        print("\n🧩 Problems Solved:")
        for d in leetcode_profile.solved_by_difficulty:
            print(f"   {d.get('difficulty', 'Unknown')}: {d.get('count', 0)}")

    if leetcode_profile.best_contest:
        bc = leetcode_profile.best_contest
        print(
            f"\n⭐ Best Contest: {bc.get('title', 'N/A')} "
            f"(Rating: {bc.get('rating', 'N/A')}, Rank: {bc.get('ranking', 'N/A')})"
        )

    print("=" * 60)

    result = {
        "profile": generate_profile_json(leetcode_profile),
        "solved_by_difficulty": leetcode_profile.solved_by_difficulty,
        "contest_rating": leetcode_profile.contest_rating,
        "global_rank": leetcode_profile.global_rank,
        "top_percentage": leetcode_profile.top_percentage,
        "contests_attended": leetcode_profile.contests_attended,
        "best_contest": leetcode_profile.best_contest,
        "active_days": leetcode_profile.active_days,
    }

    return result


def main(leetcode_url: str):
    result = fetch_and_display_leetcode_info(leetcode_url)
    print("\n" + "=" * 60)
    print("JSON DATA OUTPUT")
    print("=" * 60)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print("=" * 60)
    return result


if __name__ == "__main__":
    main("https://leetcode.com/u/9pranjal/")