from typing import Dict, List, Optional
import pdb
from models import JSONResume


def transform_parsed_data(parsed_data: Dict) -> Dict:
    try:
        if isinstance(parsed_data, dict):
            if "basics" in parsed_data and len(parsed_data) > 1:
                transformed = {
                    "basics": transform_basics(parsed_data.get("basics", {})),
                    "work": transform_work_experience(
                        parsed_data.get(
                            "work_experience",
                            parsed_data.get("work", parsed_data.get("experience", [])),
                        )
                    ),
                    "volunteer": transform_organizations(
                        parsed_data.get("organizations", [])
                    ),
                    "education": transform_education(parsed_data.get("education", [])),
                    "awards": transform_achievements(
                        parsed_data.get(
                            "achievements",
                            parsed_data.get(
                                "awards", parsed_data.get("honors_and_awards", [])
                            ),
                        )
                    ),
                    "certificates": parsed_data.get("certificates", []),
                    "publications": parsed_data.get("publications", []),
                    "skills": transform_skills_comprehensive(parsed_data),
                    "languages": parsed_data.get("languages", []),
                    "interests": parsed_data.get("interests", []),
                    "references": parsed_data.get("references", []),
                    "projects": transform_projects_comprehensive(parsed_data),
                    "meta": parsed_data.get("meta", {}),
                }
            else:
                if "basics" in parsed_data:
                    basics_data = parsed_data.get("basics", parsed_data)
                    transformed = {"basics": transform_basics(basics_data)}
                elif (
                    "work" in parsed_data
                    or "work_experience" in parsed_data
                    or "experience" in parsed_data
                ):
                    work_data = parsed_data.get(
                        "work",
                        parsed_data.get(
                            "work_experience", parsed_data.get("experience", [])
                        ),
                    )
                    transformed = {"work": transform_work_experience(work_data)}
                elif "education" in parsed_data:
                    transformed = {
                        "education": transform_education(
                            parsed_data.get("education", [])
                        )
                    }
                elif (
                    "skills" in parsed_data
                    or "librariesFrameworks" in parsed_data
                    or "toolsPlatforms" in parsed_data
                    or "databases" in parsed_data
                ):
                    transformed = {
                        "skills": transform_skills_comprehensive(parsed_data)
                    }
                elif "projects" in parsed_data or "projectsOpenSource" in parsed_data:
                    transformed = {
                        "projects": transform_projects_comprehensive(parsed_data)
                    }
                elif (
                    "awards" in parsed_data
                    or "achievements" in parsed_data
                    or "honors_and_awards" in parsed_data
                ):
                    awards_data = parsed_data.get(
                        "awards",
                        parsed_data.get(
                            "achievements", parsed_data.get("honors_and_awards", [])
                        ),
                    )
                    transformed = {"awards": transform_achievements(awards_data)}
                else:
                    transformed = parsed_data

            return transformed
        else:
            return parsed_data

    except Exception as e:
        print(f"Error transforming parsed data: {e}")
        return parsed_data


def extract_domain_from_url(url: str) -> str:
    try:
        if "://" in url:
            url = url.split("://")[1]
        domain = url.split("/")[0]
        if domain.startswith("www."):
            domain = domain[4:]
        return domain
    except Exception:
        return ""


def get_network_name(domain: str) -> str:
    domain_mapping = {
        "github.com": "GitHub",
        "linkedin.com": "LinkedIn",
        "leetcode.com": "LeetCode",
        "stackoverflow.com": "Stack Overflow",
        "hackerrank.com": "HackerRank",
        "behance.net": "Behance",
        "dev.to": "DEV Community",
        "twitter.com": "X",
        "x.com": "X",
    }
    return domain_mapping.get(domain, "")


def transform_basics(basics_data: Dict) -> Dict:
    if not isinstance(basics_data, dict):
        return basics_data

    profiles = basics_data.get("profiles", [])

    transformed_profiles = []
    if isinstance(profiles, list):
        for i, profile in enumerate(profiles):
            if isinstance(profile, dict):
                transformed_profile = profile.copy()
                url = transformed_profile.get("url", "")
                network = transformed_profile.get("network")

                if url and network is None:
                    domain = extract_domain_from_url(url)
                    network_name = get_network_name(domain)

                    if network_name:
                        transformed_profile["network"] = network_name
                        username = extract_username_from_url(url, domain)
                        if username:
                            transformed_profile["username"] = username
                transformed_profiles.append(transformed_profile)

    basics_data["profiles"] = transformed_profiles
    return basics_data


def extract_username_from_url(url: str, domain: str) -> str:
    try:
        path = url.split(domain)[1] if domain in url else ""
        if not path:
            return ""
        path = path.lstrip("/")

        parts = [part for part in path.split("/") if part]

        if parts:
            if domain == "linkedin.com":
                return parts[1]
            elif domain == "stackoverflow.com":
                return parts[2]
            else:
                return parts[0]
        return ""
    except Exception:
        return ""


def transform_work_experience(work_list: List) -> List[Dict]:
    transformed = []
    for item in work_list:
        if isinstance(item, dict):
            description = item.get("description", "")
            if isinstance(description, list):
                description = " ".join(description)

            # Try to parse from 'startDate' if it contains a date range
            start_date_input = item.get("startDate", "")
            if start_date_input and any(
                month in start_date_input
                for month in [
                    "Jan",
                    "Feb",
                    "Mar",
                    "Apr",
                    "May",
                    "Jun",
                    "Jul",
                    "Aug",
                    "Sep",
                    "Oct",
                    "Nov",
                    "Dec",
                ]
            ):
                start_date, end_date = parse_date_range(start_date_input)
            else:
                # Use existing startDate and endDate values
                start_date = item.get("startDate")
                end_date = item.get("endDate")

            transformed.append(
                {
                    "name": item.get("name", ""),
                    "position": item.get(
                        "position", item.get("type", item.get("title", ""))
                    ),
                    "url": item.get("url", None),
                    "startDate": start_date,
                    "endDate": end_date,
                    "summary": item.get("summary", description),
                    "highlights": item.get("highlights", []),
                }
            )
    return transformed


def transform_organizations(org_list: List) -> List[Dict]:
    transformed = []
    for item in org_list:
        if isinstance(item, dict):
            transformed.append(
                {
                    "organization": item.get("name", ""),
                    "position": item.get("role", ""),
                    "url": item.get("url", None),
                    "startDate": None,
                    "endDate": "Present",
                    "summary": None,
                    "highlights": [],
                }
            )
    return transformed


def transform_education(edu_list: List) -> List[Dict]:
    transformed = []
    for item in edu_list:
        if isinstance(item, dict):
            if "degree" in item:
                score = item.get("gpa", item.get("percentage", None))
                if score is not None:
                    score = str(score)

                start_date, end_date = parse_date_range(item.get("years", ""))
                transformed.append(
                    {
                        "institution": item.get("institution", ""),
                        "url": item.get("url", None),
                        "area": (
                            item.get("degree", "").split(", ")[-1]
                            if "," in item.get("degree", "")
                            else None
                        ),
                        "studyType": (
                            item.get("degree", "").split(", ")[0]
                            if "," in item.get("degree", "")
                            else item.get("degree", "")
                        ),
                        "startDate": start_date,
                        "endDate": end_date,
                        "score": score,
                        "courses": [],
                    }
                )
            else:
                transformed.append(item)
    return transformed


def transform_achievements(achievements_list: List) -> List[Dict]:
    transformed = []
    for item in achievements_list:
        if isinstance(item, dict):
            title = item.get("title", item.get("name", ""))
            awarder = item.get("awarder", item.get("organization", ""))
            summary = item.get("summary", item.get("description", None))

            transformed.append(
                {
                    "title": title,
                    "date": f"{item.get('year', '')}-01" if item.get("year") else None,
                    "awarder": awarder,
                    "summary": summary,
                }
            )
    return transformed


def transform_skills(skills_list: List) -> List[Dict]:
    transformed = []
    for item in skills_list:
        if isinstance(item, dict):
            if "category" in item:
                transformed.append(
                    {
                        "name": item.get("category", ""),
                        "level": None,
                        "keywords": item.get("keywords", []),
                    }
                )
            else:
                transformed.append(item)
    return transformed


def transform_projects(projects_list: List) -> List[Dict]:
    transformed = []
    for item in projects_list:
        if isinstance(item, dict):
            skills = []
            project_name = item.get("name", "")
            if "|" in project_name:
                name_parts = project_name.split("|")
                if len(name_parts) > 1:
                    skills_part = name_parts[1].strip()
                    skills = [skill.strip() for skill in skills_part.split(",")]
                    item["name"] = name_parts[0].strip()

            technologies = item.get("technologies", [])
            if isinstance(technologies, str):
                technologies = [tech.strip() for tech in technologies.split(",")]

            if not skills and technologies:
                skills = technologies

            transformed.append(
                {
                    "name": item.get("name", ""),
                    "startDate": None,
                    "endDate": None,
                    "description": item.get("description", ""),
                    "highlights": [item.get("type", "")] if item.get("type") else [],
                    "url": item.get("url", None),
                    "technologies": technologies,
                    "skills": skills,
                }
            )
    return transformed


def transform_skills_comprehensive(parsed_data: Dict) -> List[Dict]:
    skills = []

    if "skills" in parsed_data and isinstance(parsed_data["skills"], list):
        if parsed_data["skills"] and isinstance(parsed_data["skills"][0], str):
            skills.append(
                {
                    "name": "Programming Languages",
                    "level": None,
                    "keywords": parsed_data["skills"],
                }
            )
        else:
            skills.extend(transform_skills(parsed_data["skills"]))

    skill_categories = {
        "librariesFrameworks": "Libraries/Frameworks",
        "toolsPlatforms": "Tools/Platforms",
        "databases": "Databases",
    }

    for field, category_name in skill_categories.items():
        if field in parsed_data and isinstance(parsed_data[field], list):
            skills.append(
                {"name": category_name, "level": None, "keywords": parsed_data[field]}
            )

    return skills


def transform_projects_comprehensive(parsed_data: Dict) -> List[Dict]:
    projects = []

    if "projects" in parsed_data:
        projects.extend(transform_projects(parsed_data["projects"]))

    if "projectsOpenSource" in parsed_data:
        for item in parsed_data["projectsOpenSource"]:
            if isinstance(item, dict):
                skills = []
                project_name = item.get("name", "")
                if "|" in project_name:
                    name_parts = project_name.split("|")
                    if len(name_parts) > 1:
                        skills_part = name_parts[1].strip()
                        skills = [skill.strip() for skill in skills_part.split(",")]
                        item["name"] = name_parts[0].strip()

                projects.append(
                    {
                        "name": item.get("name", ""),
                        "startDate": None,
                        "endDate": None,
                        "description": item.get("summary", ""),
                        "highlights": [],
                        "url": item.get("url", None),
                        "technologies": item.get("technologies", []),
                        "skills": skills,
                    }
                )

    return projects


def parse_date_range(date_range: str) -> tuple:
    """
    Parse date range and return both start and end dates.
    For format like "Jan-Mar 2021", returns ("Jan 2021", "Mar 2021")
    """
    if not date_range:
        return None, None

    # Handle "onwards" case
    if "onwards" in date_range:
        # Extract the start date from "onwards" format
        start_part = date_range.replace("onwards", "").strip()
        if start_part:
            return start_part, "Present"
        return None, "Present"

    # Handle format like "Jan-Mar 2021"
    if " " in date_range and any(
        month in date_range
        for month in [
            "Jan",
            "Feb",
            "Mar",
            "Apr",
            "May",
            "Jun",
            "Jul",
            "Aug",
            "Sep",
            "Oct",
            "Nov",
            "Dec",
        ]
    ):
        parts = date_range.split(" ")
        if len(parts) >= 2:
            year = parts[-1]
            month_map = {
                "Jan": "Jan",
                "Feb": "Feb",
                "Mar": "Mar",
                "Apr": "Apr",
                "May": "May",
                "Jun": "Jun",
                "Jul": "Jul",
                "Aug": "Aug",
                "Sep": "Sep",
                "Oct": "Oct",
                "Nov": "Nov",
                "Dec": "Dec",
            }

            # Check if it's a range like "Jan-Mar 2021"
            if "-" in parts[0] and len(parts[0].split("-")) == 2:
                start_month, end_month = parts[0].split("-")
                start_date = f"{month_map.get(start_month, start_month)} {year}"
                end_date = f"{month_map.get(end_month, end_month)} {year}"
                return start_date, end_date
            else:
                # Single month format like "Jan 2021"
                month = month_map.get(parts[0], parts[0])
                start_date = f"{month} {year}"
                return start_date, None

    # Handle year range like "2020-2021"
    if "-" in date_range and len(date_range.split("-")) == 2:
        start_year, end_year = date_range.split("-")
        start_date = f"{start_year}-01"
        end_date = f"{end_year}-12"
        return start_date, end_date

    return None, None


def fetch_profile(profiles, network_names, prefix):
    """Helper function to extract profile information for a given network."""
    for network in network_names:
        profile = next(
            (p for p in profiles if p.network and p.network.lower() == network.lower()),
            None,
        )
        if profile:
            return profile


def transform_evaluation_response(
    file_name=None, resume_data=None, github_data=None, evaluation=None
):
    """
    Transform the three inputs (resume_data, github_data, evaluation) into the most important columns as a CSV row.

    Args:
        resume_data: JSONResume object containing parsed resume data
        github_data: dict containing GitHub profile data
        evaluation: EvaluationData object containing evaluation results

    Returns:
        dict: Dictionary with the most important columns for CSV output
    """
    csv_row = {}

    csv_row["file_name"] = file_name

    # Extract basic information from resume_data
    if resume_data and hasattr(resume_data, "basics") and resume_data.basics:
        basics = resume_data.basics
        csv_row["name"] = basics.name if basics.name else ""
        csv_row["email"] = basics.email if basics.email else ""
        csv_row["phone"] = basics.phone if basics.phone else ""
        csv_row["location"] = (
            f"{basics.location.city}, {basics.location.region}"
            if basics.location
            else ""
        )
        csv_row["summary"] = basics.summary if basics.summary else ""

        # Extract all profile information
        if basics.profiles:
            # Extract profiles for each platform
            github_profile = fetch_profile(basics.profiles, ["github"], "github")
            linkedin_profile = fetch_profile(basics.profiles, ["linkedin"], "linkedin")
            twitter_profile = fetch_profile(
                basics.profiles, ["twitter", "x"], "twitter"
            )
            dev_profile = fetch_profile(
                basics.profiles, ["dev community", "dev"], "dev"
            )
            behance_profile = fetch_profile(basics.profiles, ["behance"], "behance")

            # Add GitHub profile columns
            if github_profile:
                csv_row["github_url"] = github_profile.url
                csv_row["github_username"] = (
                    github_profile.username if github_profile.username else ""
                )
            else:
                csv_row["github_url"] = ""
                csv_row["github_username"] = ""

            # Add LinkedIn profile columns
            if linkedin_profile:
                csv_row["linkedin_url"] = linkedin_profile.url
                csv_row["linkedin_username"] = (
                    linkedin_profile.username if linkedin_profile.username else ""
                )
            else:
                csv_row["linkedin_url"] = ""
                csv_row["linkedin_username"] = ""

            # Add Twitter/X profile columns
            if twitter_profile:
                csv_row["twitter_url"] = twitter_profile.url
                csv_row["twitter_username"] = (
                    twitter_profile.username if twitter_profile.username else ""
                )
            else:
                csv_row["twitter_url"] = ""
                csv_row["twitter_username"] = ""

            # Add DEV Community profile columns
            if dev_profile:
                csv_row["dev_url"] = dev_profile.url
                csv_row["dev_username"] = (
                    dev_profile.username if dev_profile.username else ""
                )
            else:
                csv_row["dev_url"] = ""
                csv_row["dev_username"] = ""

            # Add Behance profile columns
            if behance_profile:
                csv_row["behance_url"] = behance_profile.url
                csv_row["behance_username"] = (
                    behance_profile.username if behance_profile.username else ""
                )
            else:
                csv_row["behance_url"] = ""
                csv_row["behance_username"] = ""
        else:
            # Initialize empty profile columns
            for prefix in ["github", "linkedin", "twitter", "dev", "behance"]:
                csv_row[f"{prefix}_url"] = ""
                csv_row[f"{prefix}_username"] = ""

    # Extract work experience summary
    if resume_data and hasattr(resume_data, "work") and resume_data.work:
        work_experience = resume_data.work
        csv_row["total_work_experience"] = len(work_experience)

        # Get most recent position
        if work_experience:
            latest_work = work_experience[0]  # Assuming sorted by date
            csv_row["current_position"] = (
                latest_work.position if latest_work.position else ""
            )
            csv_row["current_company"] = latest_work.name if latest_work.name else ""
        else:
            csv_row["current_position"] = ""
            csv_row["current_company"] = ""
    else:
        csv_row["total_work_experience"] = 0
        csv_row["current_position"] = ""
        csv_row["current_company"] = ""

    # Extract education summary
    if resume_data and hasattr(resume_data, "education") and resume_data.education:
        education = resume_data.education
        csv_row["total_education"] = len(education)

        # Get highest education level
        if education:
            highest_edu = education[0]  # Assuming sorted by date
            csv_row["highest_degree"] = (
                highest_edu.studyType if highest_edu.studyType else ""
            )
            csv_row["institution"] = (
                highest_edu.institution if highest_edu.institution else ""
            )
        else:
            csv_row["highest_degree"] = ""
            csv_row["institution"] = ""
    else:
        csv_row["total_education"] = 0
        csv_row["highest_degree"] = ""
        csv_row["institution"] = ""

    # Extract skills summary
    if resume_data and hasattr(resume_data, "skills") and resume_data.skills:
        skills = resume_data.skills
        all_skills = []
        for skill_category in skills:
            if skill_category.keywords:
                all_skills.extend(skill_category.keywords)
        csv_row["total_skills"] = len(all_skills)
        csv_row["skills_list"] = ", ".join(all_skills[:10])  # Top 10 skills
    else:
        csv_row["total_skills"] = 0
        csv_row["skills_list"] = ""

    # Extract projects summary
    if resume_data and hasattr(resume_data, "projects") and resume_data.projects:
        projects = resume_data.projects
        csv_row["total_projects"] = len(projects)
    else:
        csv_row["total_projects"] = 0

    # Extract GitHub data
    if github_data:
        csv_row["github_repos"] = github_data.get("public_repos", 0)
        csv_row["github_followers"] = github_data.get("followers", 0)
        csv_row["github_following"] = github_data.get("following", 0)
        csv_row["github_created_at"] = github_data.get("created_at", "")
        csv_row["github_bio"] = github_data.get("bio", "")
    else:
        csv_row["github_repos"] = 0
        csv_row["github_followers"] = 0
        csv_row["github_following"] = 0
        csv_row["github_created_at"] = ""
        csv_row["github_bio"] = ""

    # Extract evaluation scores
    if evaluation and hasattr(evaluation, "scores"):
        scores = evaluation.scores

        csv_row["open_source_score"] = scores.open_source.score
        csv_row["open_source_max"] = scores.open_source.max

        csv_row["self_projects_score"] = scores.self_projects.score
        csv_row["self_projects_max"] = scores.self_projects.max

        csv_row["production_score"] = scores.production.score
        csv_row["production_max"] = scores.production.max

        csv_row["technical_skills_score"] = scores.technical_skills.score
        csv_row["technical_skills_max"] = scores.technical_skills.max

        total_score = (
            scores.open_source.score
            + scores.self_projects.score
            + scores.production.score
            + scores.technical_skills.score
        )
        total_max = (
            scores.open_source.max
            + scores.self_projects.max
            + scores.production.max
            + scores.technical_skills.max
        )

        csv_row["total_score"] = total_score
        csv_row["total_max"] = total_max
    else:
        csv_row["open_source_score"] = "N/A"
        csv_row["open_source_max"] = "N/A"
        csv_row["self_projects_score"] = "N/A"
        csv_row["self_projects_max"] = "N/A"
        csv_row["production_score"] = "N/A"
        csv_row["production_max"] = "N/A"
        csv_row["technical_skills_score"] = "N/A"
        csv_row["technical_skills_max"] = "N/A"
        csv_row["total_score"] = "N/A"
        csv_row["total_max"] = "N/A"

    # Extract bonus points and deductions
    if evaluation and hasattr(evaluation, "bonus_points"):
        csv_row["bonus_points"] = evaluation.bonus_points.total
        csv_row["bonus_breakdown"] = evaluation.bonus_points.breakdown
    else:
        csv_row["bonus_points"] = 0
        csv_row["bonus_breakdown"] = ""

    if evaluation and hasattr(evaluation, "deductions"):
        csv_row["deductions"] = evaluation.deductions.total
        csv_row["deduction_reasons"] = evaluation.deductions.reasons
    else:
        csv_row["deductions"] = 0
        csv_row["deduction_reasons"] = ""

    # Extract key strengths and areas for improvement
    if evaluation and hasattr(evaluation, "key_strengths"):
        csv_row["key_strengths"] = "; ".join(evaluation.key_strengths)
    else:
        csv_row["key_strengths"] = ""

    if evaluation and hasattr(evaluation, "areas_for_improvement"):
        csv_row["areas_for_improvement"] = "; ".join(evaluation.areas_for_improvement)
    else:
        csv_row["areas_for_improvement"] = ""

    return csv_row


def convert_json_resume_to_text(resume_data: JSONResume) -> str:
    text_parts = []

    if resume_data.basics:
        basics = resume_data.basics
        text_parts.append("=== BASIC INFORMATION ===")
        text_parts.append(f"Name: {basics.name or 'Not provided'}")
        text_parts.append(f"Email: {basics.email or 'Not provided'}")
        text_parts.append(f"Phone: {basics.phone or 'Not provided'}")
        text_parts.append(f"Website: {basics.url or 'Not provided'}")

        if basics.summary:
            text_parts.append(f"Summary: {basics.summary}")

        if basics.location:
            loc = basics.location
            location_parts = []
            if loc.address:
                location_parts.append(loc.address)
            if loc.city:
                location_parts.append(loc.city)
            if loc.region:
                location_parts.append(loc.region)
            if loc.postalCode:
                location_parts.append(loc.postalCode)
            if loc.countryCode:
                location_parts.append(loc.countryCode)

            if location_parts:
                text_parts.append(f"Location: {', '.join(location_parts)}")

        if basics.profiles:
            text_parts.append("Profiles:")
            for profile in basics.profiles:
                text_parts.append(
                    f"  - {profile.network}: {profile.username} ({profile.url})"
                )

    if resume_data.work:
        text_parts.append("\n=== WORK EXPERIENCE ===")
        for i, work in enumerate(resume_data.work, 1):
            text_parts.append(f"{i}. {work.position} at {work.name}")
            text_parts.append(f"   Period: {work.startDate} - {work.endDate}")
            if work.url:
                text_parts.append(f"   Website: {work.url}")
            if work.summary:
                text_parts.append(f"   Description: {work.summary}")
            if work.highlights:
                text_parts.append("   Key Achievements:")
                for highlight in work.highlights:
                    text_parts.append(f"     • {highlight}")

    if resume_data.education:
        text_parts.append("\n=== EDUCATION ===")
        for i, edu in enumerate(resume_data.education, 1):
            text_parts.append(f"{i}. {edu.studyType} in {edu.area}")
            text_parts.append(f"   Institution: {edu.institution}")
            text_parts.append(f"   Period: {edu.startDate} - {edu.endDate}")
            if edu.score:
                text_parts.append(f"   Score: {edu.score}")
            if edu.url:
                text_parts.append(f"   Website: {edu.url}")
            if edu.courses:
                text_parts.append(f"   Courses: {', '.join(edu.courses)}")

    if resume_data.skills:
        text_parts.append("\n=== SKILLS ===")
        for skill in resume_data.skills:
            text_parts.append(f"• {skill.name}")
            if skill.level:
                text_parts.append(f"  Level: {skill.level}")
            if skill.keywords:
                text_parts.append(f"  Keywords: {', '.join(skill.keywords)}")

    if resume_data.projects:
        text_parts.append("\n=== PROJECTS ===")
        for i, project in enumerate(resume_data.projects, 1):
            text_parts.append(f"{i}. {project.name}")
            if project.startDate and project.endDate:
                text_parts.append(f"   Period: {project.startDate} - {project.endDate}")
            if project.description:
                text_parts.append(f"   Description: {project.description}")
            if project.url:
                text_parts.append(f"   URL: {project.url}")
            if project.highlights:
                text_parts.append("   Highlights:")
                for highlight in project.highlights:
                    text_parts.append(f"     • {highlight}")

    if resume_data.awards:
        text_parts.append("\n=== AWARDS ===")
        for award in resume_data.awards:
            text_parts.append(f"• {award.title} - {award.awarder} ({award.date})")
            if award.summary:
                text_parts.append(f"  {award.summary}")

    if resume_data.certificates:
        text_parts.append("\n=== CERTIFICATES ===")
        for cert in resume_data.certificates:
            text_parts.append(f"• {cert.name} - {cert.issuer} ({cert.date})")
            if cert.url:
                text_parts.append(f"  URL: {cert.url}")

    if resume_data.publications:
        text_parts.append("\n=== PUBLICATIONS ===")
        for pub in resume_data.publications:
            text_parts.append(f"• {pub.name} - {pub.publisher} ({pub.releaseDate})")
            if pub.url:
                text_parts.append(f"  URL: {pub.url}")
            if pub.summary:
                text_parts.append(f"  {pub.summary}")

    if resume_data.languages:
        text_parts.append("\n=== LANGUAGES ===")
        for lang in resume_data.languages:
            text_parts.append(f"• {lang.language} - {lang.fluency}")

    if resume_data.interests:
        text_parts.append("\n=== INTERESTS ===")
        for interest in resume_data.interests:
            text_parts.append(f"• {interest.name}")
            if interest.keywords:
                text_parts.append(f"  Keywords: {', '.join(interest.keywords)}")

    if resume_data.references:
        text_parts.append("\n=== REFERENCES ===")
        for ref in resume_data.references:
            text_parts.append(f"• {ref.name}")
            if ref.reference:
                text_parts.append(f"  {ref.reference}")

    if resume_data.volunteer:
        text_parts.append("\n=== VOLUNTEER EXPERIENCE ===")
        for volunteer in resume_data.volunteer:
            text_parts.append(f"• {volunteer.position} at {volunteer.organization}")
            text_parts.append(f"  Period: {volunteer.startDate} - {volunteer.endDate}")
            if volunteer.url:
                text_parts.append(f"  Website: {volunteer.url}")
            if volunteer.summary:
                text_parts.append(f"  Description: {volunteer.summary}")
            if volunteer.highlights:
                text_parts.append("  Highlights:")
                for highlight in volunteer.highlights:
                    text_parts.append(f"    • {highlight}")

    return "\n".join(text_parts)


def convert_github_data_to_text(github_data: dict) -> str:
    github_text = "\n\n=== GITHUB DATA ===\n"

    if "profile" in github_data:
        profile = github_data["profile"]
        github_text += f"GitHub Profile:\n"
        github_text += f"- Username: {profile.get('username', 'N/A')}\n"
        github_text += f"- Name: {profile.get('name', 'N/A')}\n"
        github_text += f"- Bio: {profile.get('bio', 'N/A')}\n"
        github_text += f"- Public Repositories: {profile.get('public_repos', 'N/A')}\n"
        github_text += f"- Followers: {profile.get('followers', 'N/A')}\n"
        github_text += f"- Following: {profile.get('following', 'N/A')}\n"
        github_text += f"- Account Created: {profile.get('created_at', 'N/A')}\n"
        github_text += f"- Last Updated: {profile.get('updated_at', 'N/A')}\n"

    if "projects" in github_data:
        projects = github_data["projects"]
        github_text += f"\nGitHub Projects ({len(projects)} total):\n"
        for i, project in enumerate(projects[:10], 1):
            github_text += f"{i}. {project.get('name', 'N/A')}\n"
            github_text += f"   Description: {project.get('description', 'N/A')}\n"
            github_text += f"   URL: {project.get('github_url', 'N/A')}\n"
            if "github_details" in project:
                details = project["github_details"]
                github_text += f"   Stars: {details.get('stars', 'N/A')}\n"
                github_text += f"   Forks: {details.get('forks', 'N/A')}\n"
                github_text += f"   Language: {details.get('language', 'N/A')}\n"
            github_text += "\n"

    if "open_source_analysis" in github_data:
        analysis = github_data["open_source_analysis"]
        github_text += f"\n=== OPEN SOURCE CONTRIBUTIONS ANALYSIS ===\n"
        github_text += f"Total Pull Requests: {analysis.get('total_prs', 0)}\n"
        github_text += f"External PRs (to other repos): {analysis.get('external_prs', 0)}\n"
        github_text += f"Merged External PRs: {analysis.get('merged_external_prs', 0)}\n"
        github_text += f"Popular Project Contributions: {analysis.get('popular_project_contributions', 0)}\n"
        github_text += f"Major Project Contributions: {analysis.get('major_project_contributions', 0)}\n"
        github_text += f"Open Source Score: {analysis.get('open_source_score', 0)}/100\n"
        github_text += f"Contribution Quality: {analysis.get('contribution_quality', 'N/A')}\n"
        
        # Add detailed external contributions
        external_contributions = analysis.get('external_contributions', [])
        if external_contributions:
            github_text += f"\nExternal Contributions Details:\n"
            for i, contrib in enumerate(external_contributions[:5], 1):
                github_text += f"{i}. Repository: {contrib.get('repository', 'N/A')}\n"
                github_text += f"   Stars: {contrib.get('repository_stars', 'N/A')}\n"
                github_text += f"   PR Title: {contrib.get('pr_title', 'N/A')}\n"
                github_text += f"   PR State: {contrib.get('pr_state', 'N/A')}\n"
                github_text += f"   Merged: {contrib.get('pr_merged', False)}\n"
                github_text += f"   Popular Project: {contrib.get('is_popular_project', False)}\n"
                github_text += f"   Major Project: {contrib.get('is_major_project', False)}\n"
                github_text += "\n"

    return github_text


def convert_blog_data_to_text(blog_data: dict) -> str:
    blog_text = "\n\n=== BLOG DATA ===\n"
    blog_text += f"Total Blogs Found: {blog_data.get('total_blogs', 'N/A')}\n"
    blog_text += f"Blog Score: {blog_data.get('blog_score', 'N/A')}/10.0\n"
    blog_text += f"Blog Details: {blog_data.get('blog_details', 'N/A')}\n"

    if "blogs" in blog_data:
        blog_text += "\nBlog URLs Found:\n"
        for i, blog in enumerate(blog_data["blogs"][:5], 1):
            blog_text += f"{i}. {blog.get('url', 'N/A')}\n"
            blog_text += f"   Score: {blog.get('score', 'N/A')}/10.0\n"
            blog_text += f"   Details: {blog.get('details', 'N/A')}\n"
            blog_text += "\n"

    return blog_text
