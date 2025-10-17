import os
import re
import json
import requests
import datetime
import time
from pathlib import Path

from typing import Dict, List, Optional
from models import GitLabProfile
from pdf import logger
from prompts.template_manager import TemplateManager
from prompt import DEFAULT_MODEL, MODEL_PARAMETERS
from llm_utils import initialize_llm_provider, extract_json_from_response
from config import DEVELOPMENT_MODE


def _create_cache_filename(api_url: str, params: dict = None) -> str:
    url_parts = api_url.replace("https://gitlab.com/api/v4/", "").replace("/", "_")
    url_parts = re.sub(r"[^\w\-_.]", "_", url_parts)

    if params:
        param_str = "_".join([f"{k}_{v}" for k, v in sorted(params.items())])
        param_str = re.sub(r"[^\w\-_.]", "_", param_str)
        filename = f"cache/gl_gitlabcache_{url_parts}_{param_str}.json"
    else:
        filename = f"cache/gl_gitlabcache_{url_parts}.json"
    return filename


def _fetch_gitlab_api(api_url, params=None):
    headers = {}
    gitlab_token = os.environ.get("GITLAB_TOKEN")
    if gitlab_token:
        headers["PRIVATE-TOKEN"] = gitlab_token

    cache_filename = _create_cache_filename(api_url, params)
    if DEVELOPMENT_MODE and os.path.exists(cache_filename):
        print(f"Loading cached GitLab data from {cache_filename}")
        try:
            cached_data = json.loads(Path(cache_filename).read_text())
            return 200, cached_data
        except Exception as e:
            print(f"Error reading cache file {cache_filename}: {e}")

    response = requests.get(api_url, params=params, timeout=10, headers=headers)
    status_code = response.status_code

    data = response.json() if response.status_code == 200 else {}

    if DEVELOPMENT_MODE and status_code == 200:
        try:
            os.makedirs("cache", exist_ok=True)
            Path(cache_filename).write_text(
                json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
            )
        except Exception as e:
            logger.error(f"Error caching GitLab data to {cache_filename}: {e}")

    return status_code, data


def extract_gitlab_username(gitlab_url: str) -> Optional[str]:
    if not gitlab_url:
        return None

    gitlab_url = gitlab_url.replace(" ", "")
    gitlab_url = gitlab_url.strip()

    patterns = [
        r"https?://gitlab\.com/([^/]+)",
        r"gitlab\.com/([^/]+)",
        r"@([^/]+)",
        r"^([a-zA-Z0-9_-]+)$",
    ]

    for pattern in patterns:
        match = re.search(pattern, gitlab_url)
        if match:
            username = match.group(1)
            # Remove query parameters if present
            if "?" in username:
                username = username.split("?", 1)[0]
            return username
    return None


def fetch_gitlab_profile(gitlab_url: str) -> Optional[GitLabProfile]:
    try:
        username = extract_gitlab_username(gitlab_url)
        logger.info(f"{username}")
        if not username:
            print(f"Could not extract username from: {gitlab_url}")
            return None

        # GitLab API uses user ID or username, but we'll use username query
        api_url = f"https://gitlab.com/api/v4/users?username={username}"

        status_code, data = _fetch_gitlab_api(api_url)

        if status_code == 200 and data:
            if isinstance(data, list) and len(data) > 0:
                data = data[0]
            profile = GitLabProfile(
                username=username,
                name=data.get("name"),
                bio=data.get("bio"),
                location=data.get("location"),
                avatar_url=data.get("avatar_url"),
                web_url=data.get("web_url"),
                website_url=data.get("website_url"),
                created_at=data.get("created_at"),
            )

            return profile
        elif status_code == 404:
            print(f"GitLab user not found: {username}")
            return None
        else:
            print(f"GitLab API error: {status_code} - {data}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"Error fetching GitLab profile: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error fetching GitLab profile: {e}")
        return None


def fetch_project_contributors(owner: str, project_id: int) -> list[dict]:
    try:
        api_url = (
            f"https://gitlab.com/api/v4/projects/{project_id}/repository/contributors"
        )

        status_code, contributors_data = _fetch_gitlab_api(api_url)

        if status_code == 200:
            return contributors_data
        else:
            return []

    except Exception as e:
        logger.error(f"Error fetching contributors for project {project_id}: {e}")
        return []


def fetch_contributions_count(owner: str, contributors_data):
    user_contributions = 0
    total_contributions = 0

    if not contributors_data:
        return 0, 0

    for contributor in contributors_data:
        if isinstance(contributor, dict):
            contributions = contributor.get("commits", 0)
            total_contributions += contributions

            name = contributor.get("name", "")
            email = contributor.get("email", "")

            normalized_owner = owner.lower()
            if (
                name.lower() == normalized_owner
                or normalized_owner in name.lower()
                or email.lower() == f"{owner}@users.noreply.gitlab.com".lower()
                or email.lower() == f"{owner}@users.noreply.github.com".lower()
            ):
                user_contributions = contributions

    return user_contributions, total_contributions


def fetch_all_gitlab_projects(gitlab_url: str, max_projects: int = 100) -> List[Dict]:
    try:
        username = extract_gitlab_username(gitlab_url)
        if not username:
            print(f"Could not extract username from: {gitlab_url}")
            return []

        # First get user ID since GitLab API often requires IDs
        user_api_url = f"https://gitlab.com/api/v4/users?username={username}"
        status_code, user_data = _fetch_gitlab_api(user_api_url)

        if status_code != 200 or not user_data:
            print(f"Could not fetch user data for {username}")
            return []

        if isinstance(user_data, list) and len(user_data) > 0:
            user_data = user_data[0]  # Take first user from array response
        user_id = user_data.get("id")

        # Fetch user's projects
        api_url = f"https://gitlab.com/api/v4/users/{user_id}/projects"
        params = {
            "order_by": "updated_at",
            "sort": "desc",
            "per_page": min(max_projects, 100),
            "membership": True,  # Include projects where user is a member
        }

        status_code, projects_data = _fetch_gitlab_api(api_url, params=params)

        if status_code == 200:
            projects = []
            for repo in projects_data:
                if repo.get(
                    "forked_from_project"
                ):  # Skip forks unless they have significant activity
                    if repo.get("forks_count", 0) < 5:
                        continue

                repo_id = repo.get("id")

                contributors_data = fetch_project_contributors(username, repo_id)
                contributor_count = len(contributors_data) if contributors_data else 0

                user_contributions, total_contributions = fetch_contributions_count(
                    username, contributors_data
                )

                # If contributors API failed or returned no data, assume owner has commits
                if contributor_count == 0 or (
                    user_contributions == 0 and total_contributions == 0
                ):
                    # Fallback: assume owner has at least 1 commit for their own project
                    user_contributions = 1
                    total_contributions = max(1, total_contributions)

                # Determine project type
                visibility = repo.get("visibility", "private")
                if visibility == "public":
                    project_type = (
                        "open_source" if contributor_count > 1 else "self_project"
                    )
                else:
                    project_type = "self_project"  # Private projects are self projects

                project = {
                    "name": repo.get("name"),
                    "description": repo.get("description"),
                    "gitlab_url": repo.get("web_url"),
                    "live_url": None,
                    "technologies": (
                        [repo.get("language")] if repo.get("language") else []
                    ),
                    "project_type": project_type,
                    "contributor_count": contributor_count,
                    "author_commit_count": user_contributions,
                    "total_commit_count": total_contributions,
                    "gitlab_details": {
                        "stars": repo.get("star_count", 0),
                        "forks": repo.get("forks_count", 0),
                        "language": repo.get("language"),
                        "description": repo.get("description"),
                        "created_at": repo.get("created_at"),
                        "updated_at": repo.get("last_activity_at"),
                        "topics": repo.get("topics", []),
                        "open_issues": repo.get("open_issues_count", 0),
                        "visibility": repo.get("visibility"),
                        "fork": bool(repo.get("forked_from_project")),
                        "archived": repo.get("archived", False),
                        "default_branch": repo.get("default_branch"),
                        "contributors": contributor_count,
                    },
                }
                projects.append(project)

            projects.sort(key=lambda x: x["gitlab_details"]["stars"], reverse=True)

            open_source_count = sum(
                1 for p in projects if p["project_type"] == "open_source"
            )
            self_project_count = sum(
                1 for p in projects if p["project_type"] == "self_project"
            )

            print(f"✅ Found {len(projects)} projects")
            print(
                f"📊 Project classification: {open_source_count} open source, {self_project_count} self projects"
            )
            return projects

        elif status_code == 404:
            print(f"GitLab user not found: {username}")
            return []
        else:
            print(f"GitLab API error: {status_code} - {projects_data}")
            return []

    except requests.exceptions.RequestException as e:
        print(f"Error fetching GitLab projects: {e}")
        return []
    except Exception as e:
        print(f"Unexpected error fetching GitLab projects: {e}")
        return []


def _compact_dict(obj: Dict) -> Dict:
    """Remove keys with None, empty list, or empty dict values (shallow)."""
    return {
        k: v
        for k, v in obj.items()
        if v is not None and not (isinstance(v, (list, dict)) and len(v) == 0)
    }


def generate_profile_json(profile: GitLabProfile) -> Dict:
    if not profile:
        return {}

    profile_data = {
        "username": profile.username,
        "name": profile.name,
        "bio": profile.bio,
        "location": profile.location,
        "public_repos": profile.public_repos,
        "created_at": profile.created_at,
        "avatar_url": profile.avatar_url,
        "profile_url": profile.web_url,
        "website_url": profile.website_url,
    }

    return _compact_dict(profile_data)


def generate_projects_json(projects: List[Dict]) -> List[Dict]:
    if not projects:
        return []

    try:
        projects_data = []
        for project in projects:
            if project.get("author_commit_count") == 0:
                continue

            project_data = _compact_dict(
                {
                    "name": project.get("name"),
                    "description": project.get("description"),
                    "gitlab_url": project.get("gitlab_url"),
                    "live_url": project.get("live_url"),
                    "technologies": project.get("technologies", []),
                    "project_type": project.get("project_type", "self_project"),
                    "contributor_count": project.get("contributor_count", 1),
                    "author_commit_count": project.get("author_commit_count", 0),
                    "total_commit_count": project.get("total_commit_count", 0),
                    "gitlab_details": _compact_dict(project.get("gitlab_details", {})),
                }
            )
            projects_data.append(project_data)

        projects_json = json.dumps(projects_data, indent=2)

        template_manager = TemplateManager()
        prompt = template_manager.render_template(
            "gitlab_project_selection", projects_data=projects_json
        )

        print(f"🤖 Using LLM to select top 7 projects from {len(projects)} projects...")

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
                    "content": "You are an expert technical recruiter analyzing GitLab repositories to identify the most impressive projects. CRITICAL: You must select exactly 7 UNIQUE projects - no duplicates allowed. Each project must be different from the others.",
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
                "gitlab_url": project.get("gitlab_url"),
                "live_url": project.get("live_url"),
                "technologies": project.get("technologies", []),
                "project_type": project.get("project_type", "self_project"),
                "contributor_count": project.get("contributor_count", 1),
                "gitlab_details": project.get("gitlab_details", {}),
            }
            projects_data.append(project_data)

        return projects_data


def fetch_and_display_gitlab_info(gitlab_url: str) -> Dict:
    logger.info(f"{gitlab_url}")
    gitlab_profile = fetch_gitlab_profile(gitlab_url)
    if not gitlab_profile:
        print("\n❌ Failed to fetch GitLab profile details.")
        return {}

    print("🔍 Fetching all project details...")
    projects = fetch_all_gitlab_projects(gitlab_url)

    if not projects:
        print("\n❌ No projects found or failed to fetch project details.")

    profile_json = generate_profile_json(gitlab_profile)
    # Set public_repos count based on discovered projects
    try:
        # This mutates the Pydantic model; safe because we control the instance
        gitlab_profile.public_repos = len(projects)
    except Exception:
        pass

    projects_json = generate_projects_json(projects)

    result = {
        "profile": profile_json,
        "projects": projects_json,
        "total_projects": len(projects_json),
    }

    return result


def main(gitlab_url):
    result = fetch_and_display_gitlab_info(gitlab_url)
    print("\n" + "=" * 60)
    print("JSON DATA OUTPUT")
    print("=" * 60)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print("=" * 60)

    return result


if __name__ == "__main__":
    main("https://gitlab.com/username")
