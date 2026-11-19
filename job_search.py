import json
import re
import time
from pathlib import Path
from datetime import datetime

import requests

from career_agent import rank_jobs
from salary_utils import parse_salary


API_URL = "https://remotive.com/api/remote-jobs"
JOBS_FILE = Path(__file__).with_name("saved_jobs.json")

# Search across all three career paths.
ROLE_KEYWORDS = [
    "accountant",
    "accounting",
    "bookkeeper",
    "payroll",
    "finance",
    "financial analyst",
    "accounts payable",
    "accounts receivable",
    "data analyst",
    "business analyst",
    "mis analyst",
    "sql",
    "power bi",
    "reporting analyst",
    "python",
    "software developer",
    "web developer",
    "full stack",
    "frontend",
    "backend",
    "automation developer",
]

INDIA_ALLOWED = [
    "india",
    "worldwide",
    "anywhere",
    "global",
    "all countries",
]


def load_saved_jobs():
    if not JOBS_FILE.exists():
        return []

    try:
        with JOBS_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)
            return data if isinstance(data, list) else []
    except (OSError, json.JSONDecodeError):
        print("Could not read saved_jobs.json.")
        return []


def save_jobs(jobs):
    with JOBS_FILE.open("w", encoding="utf-8") as file:
        json.dump(jobs, file, indent=4, ensure_ascii=False)


def accepts_india(location):
    location = (location or "").strip().lower()

    # Keep unspecified eligibility, but flag it for verification.
    if not location:
        return True

    return any(place in location for place in INDIA_ALLOWED)




def relevant_to_profile(job):
    """Match jobs across accounting, data, and software career paths."""

    title = (job.get("title") or "").lower()

    accounting_roles = [
        "accountant", "accounting", "bookkeeper", "payroll",
        "finance", "financial analyst", "accounts payable",
        "accounts receivable", "accounts executive",
        "finance associate", "tax analyst", "audit associate",
        "auditor", "accounting associate", "billing specialist",
        "financial reporting", "treasury analyst",        "accounts assistant",
        "junior accountant",
        "accounting clerk",
        "bookkeeping assistant",
        "accounts payable specialist",
        "accounts receivable specialist",
        "finance operations",
        "financial operations",
        "financial reporting analyst",
        "payroll specialist",
        "reconciliation analyst",
        "billing analyst",
    ]

    data_roles = [
        "data analyst", "business analyst", "mis analyst",
        "sql analyst", "reporting analyst", "bi analyst",
        "business intelligence", "power bi", "data associate",
        "analytics analyst", "operations analyst",
        "research analyst", "data reporting",        "junior data analyst",
        "data operations analyst",
        "business operations analyst",
        "reporting specialist",
        "power bi developer",
        "sql developer",
    ]

    software_roles = [
        "software developer", "software engineer",
        "junior software", "web developer", "full stack",
        "frontend developer", "front-end developer",
        "backend developer", "back-end developer",
        "python developer", "automation developer",
        "programmer", "application developer",
        "react developer", "node.js developer",
        "flask developer", "qa automation",        "full stack product engineer",
        "full-stack engineer",
        "junior developer",
        "associate software engineer",
        "graduate software engineer",
        "software engineer i",
        "web application developer",
    ]

    target_roles = accounting_roles + data_roles + software_roles

    if not any(role in title for role in target_roles):
        return False

    senior_terms = [
        "senior ", "staff ", "principal ", "director ",
        "head of ", "vice president", " vp ",
        "engineering manager", "team lead",
    ]

    if any(term in title for term in senior_terms):
        return False
        # Reject unrelated and unsuitable job titles.
    excluded_terms = [
        "copywriter",
        "content writer",
        "sales contractor",
        "sales representative",
        "shopify developer",
        "working student",
        "werkstudent",
        "internship",
        "senior",
        "lead ",
        "principal",
        "director",
        "head of",
        "manager",
        "architect",
    ]

    if any(term in title for term in excluded_terms):
        return False
    return True




def fetch_remote_jobs():
    print("\nSearching Remotive for remote jobs...")

    try:
        response = requests.get(
            API_URL,
            timeout=30,
            headers={"User-Agent": "JARVIS-Career-Agent/1.0"},
        )
        response.raise_for_status()
        data = response.json()

    except (requests.RequestException, ValueError) as error:
        print("Job search failed:", error)
        return []

    listings = data.get("jobs", [])
    results = []

    for item in listings:
        title = item.get("title", "").strip()
        company = item.get("company_name", "").strip()
        url = item.get("url", "").strip()
        eligible_location = item.get(
            "candidate_required_location", ""
        ).strip()

        if not title or not url:
            continue


        if not relevant_to_profile(item):
            continue

        if not accepts_india(eligible_location):
            continue

        # Avoid clearly senior roles for now.
        title_lower = title.lower()

        senior_terms = [
            "senior ",
            "staff ",
            "principal ",
            "director ",
            "head of ",
            "lead developer",
            "engineering manager",
        ]

        if any(term in title_lower for term in senior_terms):
            continue


        location = "Remote"
        if eligible_location:
            location += " — " + eligible_location
        else:
            location += " — eligibility to verify"

        
        salary_text = item.get("salary", "") or ""
        salary_info = parse_salary(salary_text)

        results.append({
            "title": title,
            "company": company or "Not disclosed",
            "location": location,
            "description": re.sub(
                r"<[^>]+>", " ", item.get("description", "")
            ),
            "salary": salary_text,
            "salary_lpa": salary_info["salary_lpa"],
            "salary_period": salary_info["salary_period"],
            "salary_currency": salary_info["salary_currency"],
            "salary_note": salary_info["salary_note"],
            "apply_url": url,
            "url": url,
            "source": "Remotive",
            "status": "Found",
            "category": item.get("category", ""),
            "job_type": item.get("job_type", ""),
            "publication_date": item.get("publication_date", ""),
        })


    print("Relevant remote listings found:", len(results))
    return results


def fetch_arbeitnow_jobs():
    """Fetch relevant remote jobs from Arbeitnow."""
    print("\nSearching Arbeitnow for remote jobs...")

    try:
        response = requests.get(
            "https://www.arbeitnow.com/api/job-board-api",
            timeout=30,
            headers={"User-Agent": "JARVIS-Career-Agent/1.0"},
        )
        response.raise_for_status()
        listings = response.json().get("data", [])

    except (requests.RequestException, ValueError) as error:
        print("Arbeitnow search failed:", error)
        return []

    results = []

    for item in listings:
        title = (item.get("title") or "").strip()
        url = (item.get("url") or "").strip()
        location = (item.get("location") or "").strip()

        if not title or not url:
            continue

        if not relevant_to_profile(item):
            continue


        salary_info = parse_salary("")
        location_lower = location.lower()

        india_eligible = any(
            place in location_lower for place in INDIA_ALLOWED
        )


        if india_eligible:
            remote_location = "Remote — " + location
            eligibility = "India eligible"
        elif location:
            remote_location = (
                "Remote — " + location
                + " (India eligibility to verify)"
            )
            eligibility = "Unverified"
        else:
            remote_location = "Remote — India eligibility to verify"
            eligibility = "Unverified"


        results.append({
            "title": title,
            "company": item.get("company_name") or "Not disclosed",
            "location": remote_location,
            "eligibility": eligibility,
            "description": re.sub(
                r"<[^>]+>", " ", item.get("description") or ""
            ),
            "salary": "",
            "salary_lpa": salary_info["salary_lpa"],
            "salary_period": salary_info["salary_period"],
            "salary_currency": salary_info["salary_currency"],
            "salary_note": salary_info["salary_note"],
            "apply_url": url,
            "url": url,
            "source": "Arbeitnow",
            "status": "Found",
            "category": ", ".join(item.get("tags") or []),
            "job_type": ", ".join(item.get("job_types") or []),
            "publication_date": str(item.get("created_at") or ""),
        })

    print("Relevant Arbeitnow listings found:", len(results))
    return results

def search_and_save():
    new_jobs = fetch_remote_jobs()
    new_jobs.extend(fetch_arbeitnow_jobs())

    if not new_jobs:
        print("No matching jobs found in this search.")
        return

    saved_jobs = load_saved_jobs()
    existing_urls = {job.get("url") for job in saved_jobs}

    added = 0

    for job in new_jobs:
        if job["url"] not in existing_urls:
            saved_jobs.append(job)
            existing_urls.add(job["url"])
            added += 1

    save_jobs(saved_jobs)

    print("New jobs saved:", added)
    print("Total saved jobs:", len(saved_jobs))

    # Daily discovery target
    DAILY_TARGET = 50

    print("\n======= DAILY DISCOVERY REPORT =======")
    print(f"Target: {DAILY_TARGET} new jobs")
    print(f"New jobs discovered: {added}")
    print(f"Remaining to target: {max(0, DAILY_TARGET - added)}")
    print(f"Total jobs in database: {len(saved_jobs)}")
    print("======================================")    

    # Use your existing career-agent scoring.
    ranked = rank_jobs(saved_jobs)

    # Save scores and matched skills for the dashboard.
    ranked_by_url = {
        job.get("url"): job
        for job in ranked
        if job.get("url")
    }

    for saved_job in saved_jobs:
        ranked_job = ranked_by_url.get(saved_job.get("url"))
        if ranked_job:
            saved_job["score"] = ranked_job.get("score")
            saved_job["matched_skills"] = ranked_job.get("matched_skills", [])
            saved_job["reasons"] = ranked_job.get("reasons", [])

    save_jobs(saved_jobs)



    print("\n======= TOP JARVIS JOB MATCHES =======")
    for number, job in enumerate(ranked[:20], start=1):
        print(f"\n{number}. {job['title']}")
        print("Company:", job["company"])
        print("Category:", job["category"])
        print("Location:", job["location"])
        print("Match score:", str(job["score"]) + "/100")
        print(
            "Matched skills:",
            ", ".join(job["matched_skills"]) or "None detected"
        )
        print("Reasons:", ", ".join(job["reasons"]))
        print("Apply link:", job["apply_url"])

    print("\nJob search complete.")


if __name__ == "__main__":
    print("\nJARVIS Daily Job Discovery")
    print("Daily target: 50 new relevant jobs")
    search_and_save()
