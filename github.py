import os
import re
import json
import requests
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
        param_str = "_".join([f"{k}_{v}" for k, v in sorted(params.items())])
        filename = f"cache/gh_githubcache_{url_parts}_{param_str}.json"
    else:
        filename = f"cache/gh_githubcache_{url_parts}.json"
    return filename


def _fetch_github_api(api_url, params=None):
    headers = {}
    github_token = os.environ.get("GITHUB_TOKEN")
    if github_token:
        headers["Authorization"] = f"token {github_token}"

    cache_filename = _create_cache_filename(api_url, params)
    if DEVELOPMENT_MODE and os.path.exists(cache_filename):
        print(f"Loading cached GitHub data from {cache_filename}")
        try:
            cached_data = json.loads(Path(cache_filename).read_text())
            return 200, cached_data
        except Exception as e:
            print(f"Error reading cache file {cache_filename}: {e}")

    response = requests.get(api_url, params, timeout=10, headers=headers)
    status_code = response.status_code
    data = response.json() if response.status_code == 200 else {}

    if DEVELOPMENT_MODE and status_code == 200:
        try:
            os.makedirs("cache", exist_ok=True)
            Path(cache_filename).write_text(
                json.dumps(data, indent=2, ensure_ascii=False)
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


def determine_enhanced_project_type(repo: Dict, contributor_count: int, user_contributions: int, username: str) -> str:
    """
    Enhanced project type determination that better detects open source projects.
    """
    # Check if it's a fork with significant contributions
    if repo.get("fork", False):
        if user_contributions > 10:
            return "open_source"
        elif user_contributions > 0:
            return "fork_contribution"
    
    # Check for multiple contributors (classic open source indicator)
    if contributor_count > 1:
        return "open_source"
    
    # Check for community engagement indicators
    stars = repo.get("stargazers_count", 0)
    forks = repo.get("forks_count", 0)
    topics = repo.get("topics", [])
    
    # If repository has community engagement, it's likely open source
    if stars > 10 or forks > 5 or len(topics) > 0:
        return "open_source"
    
    # Check if it's a well-maintained project with good activity
    if (user_contributions > 20 and 
        repo.get("updated_at") and 
        not repo.get("archived", False)):
        return "open_source"
    
    # Check for popular languages that indicate serious projects
    language = repo.get("language", "")
    serious_languages = ["Python", "JavaScript", "TypeScript", "Java", "C++", "Go", "Rust", "C#"]
    if (language in serious_languages and 
        user_contributions > 5 and 
        stars > 2):
        return "open_source"
    
    return "self_project"


def fetch_repo_contributors(owner: str, repo_name: str) -> List[Dict]:
    """Fetch repository contributors data."""
    try:
        api_url = f"https://api.github.com/repos/{owner}/{repo_name}/contributors"
        status_code, contributors_data = _fetch_github_api(api_url)
        
        if status_code == 200:
            return contributors_data
        else:
            return []

    except Exception as e:
        logger.error(f"Error fetching contributors for {owner}/{repo_name}: {e}")
        return []


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

                project_type = determine_enhanced_project_type(
                    repo, contributor_count, user_contributions, username
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
            print(f"GitHub API error: {status_code} - {data}")
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


def fetch_user_pull_requests(username: str, state: str = "all") -> List[Dict]:
    """
    Fetch all pull requests created by the user with accurate merged status.
    This includes PRs to repositories they don't own (true open source contributions).
    """
    try:
        all_prs = []
        
        # Fetch merged PRs separately for accurate status
        if state in ["all", "merged"]:
            merged_params = {
                "q": f"author:{username} type:pr is:merged",
                "sort": "created",
                "order": "desc",
                "per_page": 100
            }
            status_code, merged_data = _fetch_github_api("https://api.github.com/search/issues", params=merged_params)
            if status_code == 200:
                for item in merged_data.get("items", []):
                    all_prs.append({
                        "title": item.get("title", ""),
                        "url": item.get("html_url", ""),
                        "state": "merged",
                        "created_at": item.get("created_at", ""),
                        "updated_at": item.get("updated_at", ""),
                        "repository": item.get("repository_url", "").replace("https://api.github.com/repos/", ""),
                        "number": item.get("number", 0),
                        "merged": True,
                        "draft": False,
                        "is_own_repo": item.get("repository_url", "").replace("https://api.github.com/repos/", "").startswith(f"{username}/"),
                    })
        
        # Fetch open PRs
        if state in ["all", "open"]:
            open_params = {
                "q": f"author:{username} type:pr is:open",
                "sort": "created",
                "order": "desc",
                "per_page": 100
            }
            status_code, open_data = _fetch_github_api("https://api.github.com/search/issues", params=open_params)
            if status_code == 200:
                for item in open_data.get("items", []):
                    all_prs.append({
                        "title": item.get("title", ""),
                        "url": item.get("html_url", ""),
                        "state": "open",
                        "created_at": item.get("created_at", ""),
                        "updated_at": item.get("updated_at", ""),
                        "repository": item.get("repository_url", "").replace("https://api.github.com/repos/", ""),
                        "number": item.get("number", 0),
                        "merged": False,
                        "draft": item.get("draft", False),
                        "is_own_repo": item.get("repository_url", "").replace("https://api.github.com/repos/", "").startswith(f"{username}/"),
                    })
        
        # Fetch closed (unmerged) PRs
        if state in ["all", "closed"]:
            closed_params = {
                "q": f"author:{username} type:pr is:closed is:unmerged",
                "sort": "created",
                "order": "desc",
                "per_page": 100
            }
            status_code, closed_data = _fetch_github_api("https://api.github.com/search/issues", params=closed_params)
            if status_code == 200:
                for item in closed_data.get("items", []):
                    all_prs.append({
                        "title": item.get("title", ""),
                        "url": item.get("html_url", ""),
                        "state": "closed",
                        "created_at": item.get("created_at", ""),
                        "updated_at": item.get("updated_at", ""),
                        "repository": item.get("repository_url", "").replace("https://api.github.com/repos/", ""),
                        "number": item.get("number", 0),
                        "merged": False,
                        "draft": False,
                        "is_own_repo": item.get("repository_url", "").replace("https://api.github.com/repos/", "").startswith(f"{username}/"),
                    })
        
        print(f"✅ Found {len(all_prs)} pull requests for {username}")
        return all_prs
            
    except Exception as e:
        print(f"❌ Error fetching pull requests: {e}")
        return []


def analyze_open_source_contributions(username: str) -> Dict:
    """
    Analyze open source contributions by fetching PRs and analyzing them.
    """
    try:
        print(f"🔍 Analyzing open source contributions for {username}...")
        
        # Fetch all PRs created by the user
        all_prs = fetch_user_pull_requests(username)
        
        # Categorize PRs
        own_repo_prs = [pr for pr in all_prs if pr.get("is_own_repo", False)]
        external_prs = [pr for pr in all_prs if not pr.get("is_own_repo", False)]
        merged_prs = [pr for pr in all_prs if pr.get("merged", False)]
        
        # Analyze external contributions (true open source)
        external_contributions = []
        for pr in external_prs:
            repo_name = pr.get("repository", "")
            if repo_name:
                repo_api_url = f"https://api.github.com/repos/{repo_name}"
                status_code, repo_data = _fetch_github_api(repo_api_url)
                
                if status_code == 200:
                    contribution = {
                        "repository": repo_name,
                        "repository_stars": repo_data.get("stargazers_count", 0),
                        "repository_forks": repo_data.get("forks_count", 0),
                        "repository_language": repo_data.get("language", ""),
                        "repository_description": repo_data.get("description", ""),
                        "repository_topics": repo_data.get("topics", []),
                        "pr_title": pr.get("title", ""),
                        "pr_url": pr.get("url", ""),
                        "pr_state": pr.get("state", ""),
                        "pr_merged": pr.get("merged", False),
                        "pr_created_at": pr.get("created_at", ""),
                        "pr_labels": pr.get("labels", []),
                        "is_popular_project": repo_data.get("stargazers_count", 0) >= 1000,
                        "is_major_project": repo_data.get("stargazers_count", 0) >= 10000,
                    }
                    external_contributions.append(contribution)
        
        # Calculate metrics
        total_external_prs = len(external_prs)
        merged_external_prs = len([pr for pr in external_prs if pr.get("merged", False)])
        popular_project_contributions = len([
            c for c in external_contributions if c.get("is_popular_project", False)
        ])
        major_project_contributions = len([
            c for c in external_contributions if c.get("is_major_project", False)
        ])
        
        analysis = {
            "total_prs": len(all_prs),
            "own_repo_prs": len(own_repo_prs),
            "external_prs": total_external_prs,
            "merged_prs": len(merged_prs),
            "merged_external_prs": merged_external_prs,
            "popular_project_contributions": popular_project_contributions,
            "major_project_contributions": major_project_contributions,
            "external_contributions": external_contributions,
            "open_source_score": calculate_open_source_score(external_contributions),
            "contribution_quality": assess_contribution_quality(external_contributions)
        }
        
        return analysis
        
    except Exception as e:
        print(f"❌ Error analyzing open source contributions: {e}")
        return {
            "total_prs": 0,
            "own_repo_prs": 0,
            "external_prs": 0,
            "merged_prs": 0,
            "merged_external_prs": 0,
            "popular_project_contributions": 0,
            "major_project_contributions": 0,
            "external_contributions": [],
            "open_source_score": 0,
            "contribution_quality": "No contributions"
        }


def calculate_open_source_score(contributions: List[Dict]) -> int:
    """Calculate open source score based on contributions."""
    if not contributions:
        return 0
    
    score = 0
    
    for contribution in contributions:
        # Base score for any external contribution
        score += 5
        
        # Bonus for merged PRs
        if contribution.get("pr_merged", False):
            score += 10
        
        # Bonus for popular projects (1000+ stars)
        if contribution.get("is_popular_project", False):
            score += 15
        
        # Bonus for major projects (10000+ stars)
        if contribution.get("is_major_project", False):
            score += 25
        
        # Bonus for multiple contributions to same project
        repo_name = contribution.get("repository", "")
        if repo_name:
            same_repo_count = len([c for c in contributions if c.get("repository") == repo_name])
            if same_repo_count > 1:
                score += same_repo_count * 5
    
    return min(score, 100)  # Cap at 100


def assess_contribution_quality(contributions: List[Dict]) -> str:
    """Assess the quality of open source contributions."""
    if not contributions:
        return "No open source contributions"
    
    merged_count = len([c for c in contributions if c.get("pr_merged", False)])
    popular_count = len([c for c in contributions if c.get("is_popular_project", False)])
    major_count = len([c for c in contributions if c.get("is_major_project", False)])
    
    if major_count > 0:
        return "Exceptional - contributions to major projects"
    elif popular_count > 2:
        return "Excellent - multiple contributions to popular projects"
    elif popular_count > 0:
        return "Good - contributions to popular projects"
    elif merged_count > 2:
        return "Good - multiple merged contributions"
    elif merged_count > 0:
        return "Fair - some merged contributions"
    else:
        return "Basic - contributions present but not merged"


def fetch_and_display_github_info(github_url: str) -> Dict:
    logger.info(f"{github_url}")
    github_profile = fetch_github_profile(github_url)
    if not github_profile:
        print("\n❌ Failed to fetch GitHub profile details.")
        return {}

    print("🔍 Fetching all repository details...")
    projects = fetch_all_github_repos(github_url)

    if not projects:
        print("\n❌ No repositories found or failed to fetch repository details.")

    # Get username for PR analysis
    username = extract_github_username(github_url)
    open_source_analysis = {}
    if username:
        print("🔍 Analyzing open source contributions...")
        open_source_analysis = analyze_open_source_contributions(username)

    profile_json = generate_profile_json(github_profile)
    projects_json = generate_projects_json(projects)

    result = {
        "profile": profile_json,
        "projects": projects_json,
        "total_projects": len(projects_json),
        "open_source_analysis": open_source_analysis,
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
