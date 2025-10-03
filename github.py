import os
import re
import json
import requests
import time
from pathlib import Path

from typing import Dict, List, Optional, Any
from models import GitHubProfile
from pdf import logger
from prompts.template_manager import TemplateManager
from prompt import DEFAULT_MODEL, MODEL_PARAMETERS
from llm_utils import initialize_llm_provider, extract_json_from_response
from config import DEVELOPMENT_MODE


def _create_cache_filename(api_url: str, params: dict = None) -> str:
    url_parts = api_url.replace("https://api.github.com/", "").replace("/", "_")

    if params:
        clean_params = {}
        for k, v in params.items():
            clean_v = str(v).replace(":", "-").replace(" ", "-").replace("/", "-")
            clean_params[k] = clean_v
        param_str = "_".join([f"{k}_{v}" for k, v in sorted(clean_params.items())])
        filename = f"cache/gh_githubcache_{url_parts}_{param_str}.json"
    else:
        filename = f"cache/gh_githubcache_{url_parts}.json"
    return filename


OPEN_SOURCE_LICENSES = {
    'mit', 'apache-2.0', 'gpl-3.0', 'gpl-2.0', 'bsd-3-clause', 'bsd-2-clause',
    'lgpl-3.0', 'lgpl-2.1', 'mpl-2.0', 'agpl-3.0','isc',
    'cc0-1.0', 'bsl-1.0', 'epl-2.0', 'eupl-1.2', 'artistic-2.0'
}

OPEN_SOURCE_PROGRAMS = {
    'hacktoberfest', 'hacktoberfest-accepted', 'hacktoberfest2024', 'hacktoberfest2023',
    'gssoc', 'gssoc24', 'gssoc-ext', 'gssoc-extd', 'gssoc2024', 'girlscript-summer-of-code',
    'gsoc', 'google-summer-of-code', 'mlh', 'outreachy', 'dwoc', 'kwoc', 'swoc',
    'codepeak', 'cross-winter-of-code', 'winter-of-code', 'summer-of-code',
    'open-source-contest', 'open-source-program', 'first-timers-only',
    'good-first-issue', 'help-wanted', 'beginner-friendly'
}

def _fetch_github_api(api_url, params=None):
    headers = {}
    github_token = os.environ.get("GITHUB_TOKEN")
    if github_token:
        headers["Authorization"] = f"token {github_token}"

    cache_filename = _create_cache_filename(api_url, params)
    if DEVELOPMENT_MODE and os.path.exists(cache_filename):
        print(f"Loading cached GitHub data from {cache_filename}")
        try:
            cached_data = json.loads(Path(cache_filename).read_text(encoding='utf-8'))
            return 200, cached_data
        except Exception as e:
            print(f"Error reading cache file {cache_filename}: {e}")
    
    time.sleep(0.1) 

    response = requests.get(api_url, params, timeout=120, headers=headers)
    status_code = response.status_code
    data = response.json() if response.status_code == 200 else {}

    if DEVELOPMENT_MODE and status_code == 200:
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
            username = match.group(1)
            # Remove query parameters if present (e.g., "?tab=repositories")
            if "?" in username:
                username = username.split("?", 1)[0]
            return username
    return None


def fetch_repo_license(owner: str, repo_name: str) -> Optional[str]:
    try:
        api_url = f"https://api.github.com/repos/{owner}/{repo_name}/license"
        status_code, data = _fetch_github_api(api_url)
        
        if status_code == 200 and data.get('license'):
            license_key = data['license'].get('key', '').lower()
            return license_key
        return None
    except Exception as e:
        print(f"Error fetching license for {owner}/{repo_name}: {e}")
        return None


def is_opensource_license(license_key: str) -> bool:
    if not license_key:
        return False
        
    return license_key.lower() in OPEN_SOURCE_LICENSES


def has_opensource_tags(topics: List[str]) -> bool:
    if not topics:
        return False
    
    topic_set = {topic.lower() for topic in topics}
    return bool(topic_set.intersection(OPEN_SOURCE_PROGRAMS))


def fetch_github_profile(github_url: str) -> Optional[GitHubProfile]:
    try:
        username = extract_github_username(github_url)
        logger.info(f"{username}")
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
            print(f"GitHub API error: {status_code} - {data}")
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


def fetch_repo_contributors(owner: str, repo_name: str) -> List[Dict]:
    try:
        api_url = f"https://api.github.com/repos/{owner}/{repo_name}/contributors"

        status_code, contributors_data = _fetch_github_api(api_url)

        if status_code == 200 and isinstance(contributors_data, list):
            return contributors_data
        else:
            return []

    except Exception as e:
        print(f"Error fetching contributors for {owner}/{repo_name}: {e}")
        return []


def fetch_user_pull_requests(username: str, max_prs: int = 50) -> List[Dict]:
    try:
        # Search for PRs authored by the user
        search_query = f"author:{username} type:pr"
        api_url = "https://api.github.com/search/issues"
        params = {
            "q": search_query,
            "sort": "updated",
            "order": "desc",
            "per_page": min(max_prs, 100)
        }
        
        status_code, data = _fetch_github_api(api_url, params)
        
        if status_code != 200:
            print(f"Failed to fetch PRs for {username}: status {status_code}")
            return []
        
        prs = []
        for item in data.get('items', []):
            try:
                repo_url = item.get('repository_url', '')
                if not repo_url:
                    continue
                
                repo_parts = repo_url.split('/')[-2:]
                if len(repo_parts) != 2:
                    continue
                
                repo_owner, repo_name = repo_parts
                
                if repo_owner.lower() == username.lower():
                    continue
                
                repo_api_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}"
                repo_status, repo_data = _fetch_github_api(repo_api_url)
                
                if repo_status != 200:
                    continue
                
                pr_number = item.get('number')
                pr_api_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/pulls/{pr_number}"
                pr_status, pr_data = _fetch_github_api(pr_api_url)
                
                labels = [label.get('name', '').lower() for label in item.get('labels', [])]
                topics = repo_data.get('topics', [])
                
                opensource_program = None
                program_indicators = set(labels + topics)
                
                for program in OPEN_SOURCE_PROGRAMS:
                    if program in program_indicators:
                        opensource_program = program
                        break
                
                license_key = fetch_repo_license(repo_owner, repo_name)
                
                pr_info = {
                    "name": f"{repo_owner}/{repo_name}",
                    "contribution_type": "pull_request",
                    "project_type": "open_source",
                    "description": item.get('title', ''),
                    "github_url": item.get('html_url', ''),
                    "technologies": [repo_data.get('language')] if repo_data.get('language') else [],
                    "pr_details": {
                        "number": pr_number,
                        "title": item.get('title', ''),
                        "state": item.get('state', ''),
                        "isMerged" : pr_data.get('merged', False) if pr_status == 200 else False,
                        "additions": pr_data.get('additions', 0) if pr_status == 200 else 0,
                        "deletions": pr_data.get('deletions', 0) if pr_status == 200 else 0,
                        "changed_files": pr_data.get('changed_files', 0) if pr_status == 200 else 0,
                        "commits": pr_data.get('commits', 0) if pr_status == 200 else 0,
                        "labels": labels
                    },
                    "opensource_program": {
                        "program_name": opensource_program,
                        "detected": opensource_program is not None
                    } if opensource_program else None,
                    "github_details": {
                        "stars": repo_data.get('stargazers_count', 0),
                        "forks": repo_data.get('forks_count', 0),
                        "language": repo_data.get('language'),
                        "description": repo_data.get('description'),
                        "topics": topics,
                        "license": license_key,
                        "owner": repo_owner,
                        "created_at": repo_data.get('created_at'),
                        "updated_at": repo_data.get('updated_at')
                    }
                }
                
                prs.append(pr_info)
                
            except Exception as e:
                print(f"Error processing PR {item.get('html_url', '')}: {e}")
                continue
        
        print(f"Found {len(prs)} external pull requests for {username}")
        return prs
        
    except Exception as e:
        print(f"Error fetching pull requests for {username}: {e}")
        return []


def determine_project_type(repo: Dict, license_key: str, contributor_count: int, topics: List[str]) -> str:
    stars = repo.get('stargazers_count', 0)
    forks = repo.get('forks_count', 0)
    
    if license_key and is_opensource_license(license_key):
        return "open_source"
    
    if has_opensource_tags(topics):
        return "open_source"
    
    if contributor_count > 1 and (stars > 5 or forks > 2):
        return "open_source"
    
    return "self_project"


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
                topics = repo.get("topics", [])

                contributors_data = fetch_repo_contributors(username, repo_name)
                contributor_count = len(contributors_data)

                user_contributions, total_contributions = fetch_contributions_count(
                    username, contributors_data
                )

                # Fetch repository license
                license_key = fetch_repo_license(username, repo_name)

                # Use enhanced project type determination
                project_type = determine_project_type(repo, license_key, contributor_count, topics)

                # Detect open source program participation
                opensource_program = None
                if has_opensource_tags(topics):
                    for program in OPEN_SOURCE_PROGRAMS:
                        if program in [topic.lower() for topic in topics]:
                            opensource_program = program
                            break

                project = {
                    "name": repo.get("name"),
                    "contribution_type": "owned_repository",
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
                    "opensource_program": {
                        "program_name": opensource_program,
                        "detected": opensource_program is not None
                    } if opensource_program else None,
                    "github_details": {
                        "stars": repo.get("stargazers_count", 0),
                        "forks": repo.get("forks_count", 0),
                        "language": repo.get("language"),
                        "description": repo.get("description"),
                        "created_at": repo.get("created_at"),
                        "updated_at": repo.get("updated_at"),
                        "topics": topics,
                        "license": license_key,
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


def fetch_github_projects_with_prs(github_url: str, max_repos: int = 100, max_prs: int = 50) -> List[Dict]:
    username = extract_github_username(github_url)
    if not username:
        print(f"Could not extract username from: {github_url}")
        return []
    
    owned_repos = fetch_all_github_repos(github_url, max_repos)
    
    pull_requests = fetch_user_pull_requests(username, max_prs)
    
    all_projects = owned_repos + pull_requests
    
    def get_sort_key(project):
        if project.get('contribution_type') == 'pull_request':
            return project.get('github_details', {}).get('stars', 0)
        else:
            return project.get('github_details', {}).get('stars', 0)
    
    all_projects.sort(key=get_sort_key, reverse=True)
    
    owned_open_source = sum(1 for p in owned_repos if p["project_type"] == "open_source")
    owned_self_projects = sum(1 for p in owned_repos if p["project_type"] == "self_project")
    pr_contributions = len(pull_requests)
    
    print(f"Found {len(owned_repos)} owned repositories ({owned_open_source} open source, {owned_self_projects} self projects)")
    print(f"Found {pr_contributions} external pull request contributions")
    print(f"Total projects: {len(all_projects)}")

    return all_projects


def _get_pr_summary(pr_details: Dict) -> Dict:
    if not pr_details:
        return None
    
    return {
        "number": pr_details.get("number"),
        "title": pr_details.get("title", "")[:100],
        "impact": f"+{pr_details.get('additions', 0)}/-{pr_details.get('deletions', 0)} lines",
        "files_changed": pr_details.get("changed_files", 0),
        "commits": pr_details.get("commits", 0)
    }


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
            if (project.get("contribution_type") == "owned_repository" and 
                project.get("author_commit_count", 0) == 0):
                continue

            github_details = project.get("github_details", {})
            project_data = {
                "name": project.get("name"),
                "contribution_type": project.get("contribution_type", "owned_repository"),
                "description": project.get("description", "")[:200],
                "github_url": project.get("github_url"),
                "live_url": project.get("live_url"),
                "technologies": project.get("technologies", [])[:5], 
                "project_type": project.get("project_type", "self_project"),
                "contributor_count": project.get("contributor_count", 1),
                "author_commit_count": project.get("author_commit_count", 0),
                "total_commit_count": project.get("total_commit_count", 0),
                "pr_summary": _get_pr_summary(project.get("pr_details")) if project.get("pr_details") else None,
                "opensource_program": project.get("opensource_program"),
                "github_summary": {
                    "stars": github_details.get("stars", 0),
                    "forks": github_details.get("forks", 0),
                    "language": github_details.get("language"),
                    "license": github_details.get("license"),
                    "topics": github_details.get("topics", [])[:3],  # Limit to 3 topics
                },
            }
            projects_data.append(project_data)

        projects_json = json.dumps(projects_data, indent=2)

        template_manager = TemplateManager()
        prompt = template_manager.render_template(
            "github_project_selection", projects_data=projects_json
        )

        print(
            f"Using LLM to select top 5 projects from {len(projects)} repositories..."
        )

        provider = initialize_llm_provider(DEFAULT_MODEL)

        model_params = MODEL_PARAMETERS.get(
            DEFAULT_MODEL, {"temperature": 0.1, "top_p": 0.9}
        )
        
        model_params.update({
            "timeout": 120,  
            "max_tokens": 4000,  
        })

        system_message = (
            "You are an expert technical recruiter analyzing GitHub repositories to identify the most impressive projects. CRITICAL: You must select exactly 7 UNIQUE projects - no duplicates allowed. Each project must be different from the others Prioritize: 1) External pull requests, "
            "2) Open source program participation, 3) Projects with high commit counts. "
            "Respond only with valid JSON array, no additional text."
        )
        
        chat_params = {
            "model": DEFAULT_MODEL,
            "messages": [
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt},
            ],
            "options": model_params,
        }

        try:
            response = provider.chat(**chat_params)
        except Exception as llm_error:
            print(f"LLM call failed: {llm_error}")
            print("Falling back to algorithmic selection")
            return []

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
                    full_project = project.get("_full_data", project)
                    unique_projects.append(full_project)
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

            print("Falling back to first 7 projects")
            return projects_data[:7]

    except Exception as e:
        print(f"Error using LLM for project selection: {e}")
        print("Falling back to first 7 projects")

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
    logger.info(f"{github_url}")
    github_profile = fetch_github_profile(github_url)
    if not github_profile:
        print("Failed to fetch GitHub profile details.")
        return {}

    print("Fetching all repository details and pull requests...")
    projects = fetch_github_projects_with_prs(github_url)

    if not projects:
        print("No repositories or pull requests found.")

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
