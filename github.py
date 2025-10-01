import os
import re
import json
import requests
import time
from pathlib import Path
import logging


from typing import Dict, List, Optional, Any
from models import GitHubProfile
from prompts.template_manager import TemplateManager
from prompt import DEFAULT_MODEL, MODEL_PARAMETERS
from llm_utils import initialize_llm_provider, extract_json_from_response
from config import DEVELOPMENT_MODE

logger = logging.getLogger(__name__)

def _create_cache_filename(api_url: str, params: dict = None) -> str:
    url_parts = api_url.replace("https://api.github.com/", "").replace("/", "_")

    if params:
        param_str = "_".join([f"{k}_{v}" for k, v in sorted(params.items())])
        filename = f"cache/gh_githubcache_{url_parts}_{param_str}.json"
    else:
        filename = f"cache/gh_githubcache_{url_parts}.json"
    return filename

def _check_rate_limit(response):
    """Check GitHub API rate limit headers and wait if necessary."""
    if response.headers.get('X-RateLimit-Remaining'):
        remaining = int(response.headers.get('X-RateLimit-Remaining', 0))
        reset_time = int(response.headers.get('X-RateLimit-Reset', 0))
        
        if remaining < 5:  # Conservative threshold
            wait_time = max(reset_time - int(time.time()), 0) + 1
            print(f"⚠️ GitHub rate limit low ({remaining} remaining). Waiting {wait_time}s...")
            time.sleep(wait_time)
            return True
    return False


def _fetch_github_api_with_retry(api_url, params=None, max_retries=3):
    """Fetch GitHub API with retry logic and proper error handling."""
    headers = {}
    github_token = os.environ.get("GITHUB_TOKEN")
    if github_token:
        headers["Authorization"] = f"token {github_token}"
    
    for attempt in range(max_retries):
        try:
            # Check cache first (existing logic)
            cache_filename = _create_cache_filename(api_url, params)
            if DEVELOPMENT_MODE and os.path.exists(cache_filename):
                print(f"Loading cached GitHub data from {cache_filename}")
                try:
                    cache_content = Path(cache_filename).read_text(encoding='utf-8')
                    if cache_content.strip():  # Check if not empty
                        cached_data = json.loads(cache_content)
                        return 200, cached_data
                    else:
                        print(f"⚠️ Cache file {cache_filename} is empty, re-fetching...")
                except json.JSONDecodeError as e:
                    print(f"⚠️ Corrupted cache file {cache_filename}: {e}. Re-fetching...")
                except Exception as e:
                    print(f"⚠️ Error reading cache file {cache_filename}: {e}. Re-fetching...")
            # Make the API request
            response = requests.get(api_url, params=params, timeout=10, headers=headers)
            status_code = response.status_code
            
            # Handle rate limiting
            if status_code == 403:
                if 'rate limit' in response.text.lower():
                    reset_time = int(response.headers.get('X-RateLimit-Reset', time.time() + 60))
                    wait_time = max(reset_time - int(time.time()), 0) + 1
                    print(f"⚠️ Rate limit exceeded. Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                    continue  # Retry after waiting
            
            # Check rate limit for successful requests
            if status_code == 200:
                _check_rate_limit(response)
                data = response.json()
                
                # Cache successful responses (existing logic)
                if DEVELOPMENT_MODE:
                    try:
                        os.makedirs("cache", exist_ok=True)
                        Path(cache_filename).write_text(
                            json.dumps(data, indent=2, ensure_ascii=False),
                            encoding='utf-8'
                        )
                        print(f"Cached GitHub data to {cache_filename}")
                    except Exception as e:
                        print(f"Error caching GitHub data to {cache_filename}: {e}")
                
                return status_code, data
            
            # For other status codes, return immediately (don't retry 404s)
            if status_code == 404:
                return status_code, {}
            
            # For server errors, retry with backoff
            if status_code >= 500:
                wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                print(f"Server error ({status_code}). Retrying in {wait_time}s...")
                time.sleep(wait_time)
                continue
            
            # For other errors, return the response
            return status_code, {}
            
        except requests.exceptions.Timeout as e:
            wait_time = 2 ** attempt  # Exponential backoff
            print(f"Request timeout (attempt {attempt + 1}/{max_retries}). Retrying in {wait_time}s...")
            if attempt < max_retries - 1:
                time.sleep(wait_time)
            else:
                print(f"Failed after {max_retries} attempts: {e}")
                return 0, {}
                
        except requests.exceptions.ConnectionError as e:
            wait_time = 2 ** attempt
            print(f"Connection error (attempt {attempt + 1}/{max_retries}). Retrying in {wait_time}s...")
            if attempt < max_retries - 1:
                time.sleep(wait_time)
            else:
                print(f"Failed after {max_retries} attempts: {e}")
                return 0, {}
                
        except requests.exceptions.RequestException as e:
            print(f"Request error: {e}")
            return 0, {}
    
    print(f"Failed to fetch {api_url} after {max_retries} attempts")
    return 0, {}

def _fetch_github_api(api_url, params=None):
    """Wrapper for backward compatibility."""
    return _fetch_github_api_with_retry(api_url, params)

def extract_github_username(github_url: str) -> Optional[str]:
    if not github_url:
        return None

    github_url = github_url.replace(" ", "")
    github_url = github_url.strip()

    patterns = [
        r"https?://github\.com/([^/]+)",
        r"github\.com/([^/]+)",
        r"@([^/]+)",
        r"^([a-zA-Z0-9-]+)$",
    ]

    for pattern in patterns:
        match = re.search(pattern, github_url)
        if match:
            return match.group(1)

    return None


def fetch_github_profile(github_url: str) -> Optional[GitHubProfile]:
    try:
        username = extract_github_username(github_url)
        if not username:
            print(f"Could not extract username from: {github_url}")
            return None

        api_url = f"https://api.github.com/users/{username}"

        status_code, data = _fetch_github_api(api_url)

        if status_code == 200:
            profile = GitHubProfile(
                username=username,
                name=data.get("name"),
                bio=data.get("bio"),
                location=data.get("location"),
                company=data.get("company"),
                public_repos=data.get("public_repos"),
                followers=data.get("followers"),
                following=data.get("following"),
                created_at=data.get("created_at"),
                updated_at=data.get("updated_at"),
                avatar_url=data.get("avatar_url"),
                blog=data.get("blog"),
                twitter_username=data.get("twitter_username"),
                hireable=data.get("hireable"),
            )

            return profile
        elif status_code == 404:
            print(f"GitHub user not found: {username}")
            return None
        else:
            print(f"GitHub API error: {status_code}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"Error fetching GitHub profile: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error fetching GitHub profile: {e}")
        return None


def fetch_contributions_count(owner: str, contributors_data):
    user_contributions = 0
    total_contributions = 0

    for contributor in contributors_data:
        if isinstance(contributor, dict):
            contributions = contributor.get("contributions", 0)
            total_contributions += contributions

            if contributor.get("login", "").lower() == owner.lower():
                user_contributions = contributions

    return user_contributions, total_contributions


def fetch_repo_contributors(owner: str, repo_name: str) -> int:
    try:
        api_url = f"https://api.github.com/repos/{owner}/{repo_name}/contributors"

        status_code, contributors_data = _fetch_github_api(api_url)

        # return contributors_data

        if status_code == 200:
            return contributors_data
        else:
            return []

    except Exception as e:
        logger.error(f"Error fetching contributors for {owner}/{repo_name}: {e}")
        return 1


def fetch_all_github_repos(github_url: str, max_repos: int = 100) -> List[Dict]:
    try:
        username = extract_github_username(github_url)
        if not username:
            print(f"Could not extract username from: {github_url}")
            return []

        api_url = f"https://api.github.com/users/{username}/repos"

        params = {"sort": "updated", "per_page": min(max_repos, 100), "type": "all"}

        status_code, repos_data = _fetch_github_api(api_url, params=params)

        if status_code == 200:
            projects = []
            for repo in repos_data:
                if repo.get("fork") and repo.get("forks_count", 0) < 5:
                    continue

                repo_name = repo.get("name")

                contributors_data = fetch_repo_contributors(username, repo_name)
                contributor_count = len(contributors_data)

                user_contributions, total_contributions = fetch_contributions_count(
                    username, contributors_data
                )

                project_type = (
                    "open_source" if contributor_count > 1 else "self_project"
                )

                project = {
                    "name": repo.get("name"),
                    "description": repo.get("description"),
                    "github_url": repo.get("html_url"),
                    "live_url": repo.get("homepage") if repo.get("homepage") else None,
                    "technologies": (
                        [repo.get("language")] if repo.get("language") else []
                    ),
                    "project_type": project_type,
                    "contributor_count": contributor_count,
                    "author_commit_count": user_contributions,
                    "total_commit_count": total_contributions,
                    "github_details": {
                        "stars": repo.get("stargazers_count", 0),
                        "forks": repo.get("forks_count", 0),
                        "language": repo.get("language"),
                        "description": repo.get("description"),
                        "created_at": repo.get("created_at"),
                        "updated_at": repo.get("updated_at"),
                        "topics": repo.get("topics", []),
                        "open_issues": repo.get("open_issues_count", 0),
                        "size": repo.get("size", 0),
                        "fork": repo.get("fork", False),
                        "archived": repo.get("archived", False),
                        "default_branch": repo.get("default_branch"),
                        "contributors": contributor_count,
                    },
                }
                projects.append(project)

            projects.sort(key=lambda x: x["github_details"]["stars"], reverse=True)

            open_source_count = sum(
                1 for p in projects if p["project_type"] == "open_source"
            )
            self_project_count = sum(
                1 for p in projects if p["project_type"] == "self_project"
            )

            print(f"✅ Found {len(projects)} repositories")
            print(
                f"📊 Project classification: {open_source_count} open source, {self_project_count} self projects"
            )
            return projects

        elif status_code == 404:
            print(f"GitHub user not found: {username}")
            return []
        else:
            print(f"GitHub API error: {status_code}")
            return []

    except requests.exceptions.RequestException as e:
        print(f"Error fetching GitHub repositories: {e}")
        return []
    except Exception as e:
        print(f"Unexpected error fetching GitHub repositories: {e}")
        return []


def generate_profile_json(profile: GitHubProfile) -> Dict:
    if not profile:
        return {}

    profile_data = {
        "username": profile.username,
        "name": profile.name,
        "bio": profile.bio,
        "location": profile.location,
        "company": profile.company,
        "public_repos": profile.public_repos,
        "followers": profile.followers,
        "following": profile.following,
        "created_at": profile.created_at,
        "updated_at": profile.updated_at,
        "avatar_url": profile.avatar_url,
        "blog": profile.blog,
        "twitter_username": profile.twitter_username,
        "hireable": profile.hireable,
    }

    return profile_data


def generate_projects_json(projects: List[Dict]) -> List[Dict]:
    if not projects:
        return []

    try:
        projects_data = []
        for project in projects:

            if project.get("author_commit_count") == 0:
                continue

            project_data = {
                "name": project.get("name"),
                "description": project.get("description"),
                "github_url": project.get("github_url"),
                "live_url": project.get("live_url"),
                "technologies": project.get("technologies", []),
                "project_type": project.get("project_type", "self_project"),
                "contributor_count": project.get("contributor_count", 1),
                "author_commit_count": project.get("author_commit_count", 0),
                "total_commit_count": project.get("total_commit_count", 0),
                "github_details": project.get("github_details", {}),
            }
            projects_data.append(project_data)

        projects_json = json.dumps(projects_data, indent=2)

        template_manager = TemplateManager()
        prompt = template_manager.render_template(
            "github_project_selection", projects_data=projects_json
        )

        print(
            f"🤖 Using LLM to select top 5 projects from {len(projects)} repositories..."
        )

        # Initialize the LLM provider
        provider = initialize_llm_provider(DEFAULT_MODEL)

        # Get model parameters
        model_params = MODEL_PARAMETERS.get(
            DEFAULT_MODEL, {"temperature": 0.1, "top_p": 0.9}
        )

        # Prepare chat parameters
        chat_params = {
            "model": DEFAULT_MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": "You are an expert technical recruiter analyzing GitHub repositories to identify the most impressive projects. CRITICAL: You must select exactly 7 UNIQUE projects - no duplicates allowed. Each project must be different from the others.",
                },
                {"role": "user", "content": prompt},
            ],
            "options": model_params,
        }

        # Call the LLM provider
        response = provider.chat(**chat_params)

        response_text = response["message"]["content"]

        try:
            response_text = response_text.strip()
            response_text = extract_json_from_response(response_text)

            selected_projects = json.loads(response_text)

            unique_projects = []
            seen_names = set()

            for project in selected_projects:
                project_name = project.get("name", "")
                if project_name and project_name not in seen_names:
                    unique_projects.append(project)
                    seen_names.add(project_name)

            if len(unique_projects) < 7:
                print(
                    f"⚠️ LLM selected {len(selected_projects)} projects but {len(unique_projects)} are unique"
                )

                for project in projects_data:
                    if len(unique_projects) >= 7:
                        break
                    project_name = project.get("name", "")
                    if project_name and project_name not in seen_names:
                        unique_projects.append(project)
                        seen_names.add(project_name)

            project_names = ", ".join(
                [proj.get("name", "N/A") for proj in unique_projects]
            )
            print(
                f"✅ LLM selected {len(unique_projects)} unique top projects: {project_names}"
            )
            return unique_projects

        except json.JSONDecodeError as e:
            print(f"ERROR: Error parsing LLM response: {e}")
            print(f"ERROR: Raw response: {response_text}")

            print("🔄 Falling back to first 7 projects")
            return projects_data[:7]

    except Exception as e:
        print(f"Error using LLM for project selection: {e}")
        print("🔄 Falling back to first 7 projects")

        projects_data = []
        for project in projects[:7]:
            project_data = {
                "name": project.get("name"),
                "description": project.get("description"),
                "github_url": project.get("github_url"),
                "live_url": project.get("live_url"),
                "technologies": project.get("technologies", []),
                "project_type": project.get("project_type", "self_project"),
                "contributor_count": project.get("contributor_count", 1),
                "github_details": project.get("github_details", {}),
            }
            projects_data.append(project_data)

        return projects_data


def fetch_and_display_github_info(github_url: str) -> Dict:
    github_profile = fetch_github_profile(github_url)
    if not github_profile:
        print("\n❌ Failed to fetch GitHub profile details.")
        return {}

    print("🔍 Fetching all repository details...")
    projects = fetch_all_github_repos(github_url)

    if not projects:
        print("\n❌ No repositories found or failed to fetch repository details.")

    profile_json = generate_profile_json(github_profile)
    projects_json = generate_projects_json(projects)

    result = {
        "profile": profile_json,
        "projects": projects_json,
        "total_projects": len(projects_json),
    }

    return result


def main(github_url):
    result = fetch_and_display_github_info(github_url)
    print("\n" + "=" * 60)
    print("JSON DATA OUTPUT")
    print("=" * 60)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print("=" * 60)

    return result


if __name__ == "__main__":
    main("https://github.com/PavitKaur05")
