"""
Codeforces API Integration

Fetches competitive programming data from Codeforces public API:
- User profile (rating, rank, solved count)
- Cheating detection via SKIPPED verdict analysis
"""

import logging
import requests
from typing import Dict, Optional, List, Tuple

logger = logging.getLogger(__name__)

CODEFORCES_API_BASE = "https://codeforces.com/api"

# Cheating thresholds
SKIPPED_PER_CONTEST_THRESHOLD = 4  # 4+ SKIPPED in one contest = cheated
CHEATED_CONTESTS_THRESHOLD = 2  # 2+ contests cheated = nuclear (entire CP section 0)
TOTAL_SKIPPED_THRESHOLD = 6  # 6+ SKIPPED across all contests = also nuclear


def _extract_handle_from_url(url: str) -> Optional[str]:
    """Extract Codeforces handle from a profile URL.

    Handles formats like:
      - https://codeforces.com/profile/tourist
      - https://www.codeforces.com/profile/tourist
      - codeforces.com/profile/tourist
      - Just the handle itself (e.g. 'tourist')
    """
    if not url:
        return None

    url = url.strip().rstrip("/")

    # If it looks like a URL with /profile/
    if "/profile/" in url:
        parts = url.split("/profile/")
        if len(parts) == 2 and parts[1]:
            return parts[1].strip("/")

    # If it's a codeforces URL without /profile/ (e.g. codeforces.com/tourist)
    if "codeforces.com" in url:
        parts = url.rstrip("/").split("/")
        if parts:
            return parts[-1]

    # If it's just a handle (no slashes, no dots)
    if "/" not in url and "." not in url:
        return url

    return None


def fetch_codeforces_profile(handle: str) -> Optional[Dict]:
    """Fetch user profile info from Codeforces API.

    Returns:
        Dict with keys: handle, rating, max_rating, rank, max_rank, solved_count
        or None on failure.
    """
    try:
        # Fetch user info
        resp = requests.get(
            f"{CODEFORCES_API_BASE}/user.info",
            params={"handles": handle},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()

        if data.get("status") != "OK" or not data.get("result"):
            logger.warning(f"Codeforces API returned non-OK for handle '{handle}'")
            return None

        user = data["result"][0]

        profile = {
            "handle": user.get("handle", handle),
            "rating": user.get("rating", 0),
            "max_rating": user.get("maxRating", 0),
            "rank": user.get("rank", "unrated"),
            "max_rank": user.get("maxRank", "unrated"),
        }

        # Fetch solved count from user.status (count unique accepted problems)
        solved_count = _fetch_solved_count(handle)
        profile["solved_count"] = solved_count

        return profile

    except requests.RequestException as e:
        logger.error(f"Failed to fetch Codeforces profile for '{handle}': {e}")
        return None
    except (KeyError, IndexError, ValueError) as e:
        logger.error(f"Failed to parse Codeforces profile for '{handle}': {e}")
        return None


def _fetch_solved_count(handle: str) -> int:
    """Count unique problems solved (ACCEPTED verdicts) by a user."""
    try:
        resp = requests.get(
            f"{CODEFORCES_API_BASE}/user.status",
            params={"handle": handle},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()

        if data.get("status") != "OK":
            return 0

        solved = set()
        for submission in data.get("result", []):
            if submission.get("verdict") == "OK":
                problem = submission.get("problem", {})
                contest_id = problem.get("contestId", "")
                index = problem.get("index", "")
                if contest_id and index:
                    solved.add(f"{contest_id}-{index}")

        return len(solved)

    except Exception as e:
        logger.error(f"Failed to fetch solved count for '{handle}': {e}")
        return 0


def detect_cheating(handle: str) -> Dict:
    """Analyze user submissions for cheating patterns.

    Detects SKIPPED verdicts per contest. A SKIPPED verdict on Codeforces
    typically indicates the system detected plagiarism/cheating.

    Returns:
        Dict with keys:
        - is_cheater: bool
        - is_serial_cheater: bool (2+ contests or 6+ total SKIPPED)
        - cheated_contests: int (number of contests with 4+ SKIPPED)
        - total_skipped: int
        - details: str
    """
    result = {
        "is_cheater": False,
        "is_serial_cheater": False,
        "cheated_contests": 0,
        "total_skipped": 0,
        "details": "No cheating detected",
    }

    try:
        resp = requests.get(
            f"{CODEFORCES_API_BASE}/user.status",
            params={"handle": handle},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()

        if data.get("status") != "OK":
            return result

        # Group SKIPPED verdicts by contest
        skipped_by_contest: Dict[int, int] = {}
        for submission in data.get("result", []):
            if submission.get("verdict") == "SKIPPED":
                contest_id = submission.get("contestId")
                if contest_id:
                    skipped_by_contest[contest_id] = (
                        skipped_by_contest.get(contest_id, 0) + 1
                    )

        total_skipped = sum(skipped_by_contest.values())
        cheated_contests = sum(
            1
            for count in skipped_by_contest.values()
            if count >= SKIPPED_PER_CONTEST_THRESHOLD
        )

        result["total_skipped"] = total_skipped
        result["cheated_contests"] = cheated_contests

        if cheated_contests >= 1:
            result["is_cheater"] = True
            result["details"] = (
                f"Detected {cheated_contests} contest(s) with "
                f"{SKIPPED_PER_CONTEST_THRESHOLD}+ SKIPPED submissions "
                f"(total SKIPPED: {total_skipped})"
            )

        # Nuclear: 2+ cheated contests or 6+ total SKIPPED
        if (
            cheated_contests >= CHEATED_CONTESTS_THRESHOLD
            or total_skipped >= TOTAL_SKIPPED_THRESHOLD
        ):
            result["is_serial_cheater"] = True
            result["details"] = (
                f"SERIAL CHEATING: {cheated_contests} cheated contest(s), "
                f"{total_skipped} total SKIPPED submissions. "
                f"Entire competitive programming section zeroed."
            )

    except Exception as e:
        logger.error(f"Failed to run cheating detection for '{handle}': {e}")
        result["details"] = f"Cheating detection failed: {e}"

    return result


def fetch_codeforces_data(url_or_handle: str) -> Optional[Dict]:
    """Orchestrate Codeforces data fetching: profile + cheating detection.

    Args:
        url_or_handle: Codeforces profile URL or raw handle.

    Returns:
        Dict with keys: profile, cheating, or None if handle extraction fails.
    """
    handle = _extract_handle_from_url(url_or_handle)
    if not handle:
        logger.warning(f"Could not extract Codeforces handle from: {url_or_handle}")
        return None

    logger.info(f"Fetching Codeforces data for handle: {handle}")

    profile = fetch_codeforces_profile(handle)
    if not profile:
        return None

    cheating = detect_cheating(handle)

    return {
        "profile": profile,
        "cheating": cheating,
    }
