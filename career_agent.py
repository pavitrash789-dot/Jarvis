# ============================================================
# JARVIS AI CAREER AGENT
# Stage 1: Career Profile and Job Matching
# ============================================================

import json
from pathlib import Path

from salary_utils import parse_salary

PROFILE_FILE = Path(__file__).with_name("career_profile.json")


CAREER_PROFILE = {
    "education": "B.Com Graduate",
    "specialization": [
        "Finance",
        "Economics"
    ],
    "experience_years": 1,

    "skills": [
        # Accounting and Finance
        "Tally Prime",
        "Bookkeeping",
        "Journal Entries",
        "Ledger Posting",
        "Bank Reconciliation",
        "Accounts Payable",
        "Accounts Receivable",
        "Financial Analysis",
        "Payroll Basics",

        # Microsoft Excel and Reporting
        "Microsoft Excel",
        "PivotTables",
        "VLOOKUP",
        "SUMIF",
        "Conditional Formatting",
        "Data Cleaning",
        "Dashboards",
        "MIS Reporting",

        # SQL and Data Analysis
        "MySQL",
        "SQL",
        "Database Queries",
        "Data Analysis",
        "Data Visualization",
        "Data Reporting",
        "Data Interpretation",
        "Business Intelligence",
        "Power BI",

        # Programming and Full-Stack Development
        "Python",
        "HTML",
        "CSS",
        "JavaScript",
        "Full-Stack Development",
        "Frontend Development",
        "Backend Development",
        "Web Development",
        "REST APIs",
        "Git",
        "GitHub",

        # Tools and Frameworks You Are Learning or Exploring
        "Flask",
        "Node.js",
        "React",
        "VS Code",
        "Supabase",

        # Business and Process Skills
        "Business Analysis",
        "Process Management",
        "Problem Solving",
        "Process Improvement"
    ],

    "learning_skills": [
        "Full-Stack Web Development",
        "Python Programming",
        "MySQL and SQL",
        "Data Analysis",
        "Power BI",
        "API Integration",
        "Database Design",
        "AI Application Development"
    ],

    "preferred_roles": [
        # Accounting and Finance
        "Accountant",
        "Junior Accountant",
        "Accounts Executive",
        "Bookkeeper",
        "Accounts Payable Executive",
        "Accounts Receivable Executive",
        "Payroll Specialist",

        # Data and Business Analysis
        "Data Analyst",
        "Junior Data Analyst",
        "MIS Executive",
        "Reporting Analyst",
        "Business Analyst",
        "Junior Business Analyst",
        "Financial Analyst",
        "SQL Analyst",

        # Software and Web Development
        "Python Developer",
        "Junior Python Developer",
        "Full Stack Developer",
        "Junior Full Stack Developer",
        "Web Developer",
        "Frontend Developer",
        "Backend Developer",
        "Software Developer",
        "Automation Developer"
    ],

    "preferred_locations": [
        "Remote",
        "Work From Home",
        "Kota",
        "Jaipur"
    ],

    "minimum_salary_lpa": 6,
    "target_salary_lpa": 10
}



def save_career_profile():
    """Save the career profile to a local JSON file."""

    with open(PROFILE_FILE, "w", encoding="utf-8") as file:
        json.dump(CAREER_PROFILE, file, indent=4)

    print(f"Career profile saved to: {PROFILE_FILE.name}")


def load_career_profile():
    """Load the saved profile, or create it if missing."""

    if not PROFILE_FILE.exists():
        save_career_profile()

    with open(PROFILE_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def show_career_profile():
    """Display the current career profile."""

    profile = load_career_profile()

    print("\n========== JARVIS CAREER PROFILE ==========")
    print("Education:", profile["education"])
    print("Experience:", profile["experience_years"], "year(s)")

    print("\nSkills:")
    for skill in profile["skills"]:
        print("-", skill)

    print("\nPreferred roles:")
    for role in profile["preferred_roles"]:
        print("-", role)

    print("\nPreferred locations:")
    for location in profile["preferred_locations"]:
        print("-", location)

    print(
        "\nSalary target:",
        f"₹{profile['minimum_salary_lpa']}-"
        f"₹{profile['target_salary_lpa']} LPA"
    )

    print("===========================================\n")

def classify_job_category(job):
    """Classify a job into one of three career paths."""

    title = job.get("title", "").lower()
    description = job.get("description", "").lower()
    text = title + " " + description

    categories = {
        "Accounting & Finance": [
            "accountant", "accounting", "bookkeeper",
            "payroll", "accounts payable",
            "accounts receivable", "finance",
            "financial analyst", "tax"
        ],
        "Data & Business Analysis": [
            "data analyst", "sql analyst",
            "business analyst", "mis executive",
            "reporting analyst", "power bi",
            "business intelligence"
        ],
        "Software & Full-Stack Development": [
            "developer", "software engineer",
            "web developer", "full stack",
            "frontend", "backend", "programmer",
            "python", "automation developer"
        ]
    }

    # Check the job title first.
    for category, keywords in categories.items():
        if any(keyword in title for keyword in keywords):
            return category

    # If the title is unclear, check the description.
    for category, keywords in categories.items():
        if any(keyword in text for keyword in keywords):
            return category

    return "Other"


def match_job(job, profile=None):
    """Score a job against your profile."""

    if profile is None:
        profile = load_career_profile()

    title = job.get("title", "").lower()
    description = job.get("description", "").lower()
    location = job.get("location", "").lower()

    score = 0
    reasons = []

    # Preferred role match
    matched_roles = [
        role for role in profile["preferred_roles"]
        if role.lower() in title
    ]

    if matched_roles:
        score += 30
        reasons.append("Matches preferred role")

    # Relevant skills
    matched_skills = [
        skill for skill in profile["skills"]
        if skill.lower() in description
    ]

    score += min(40, len(matched_skills) * 5)

    if matched_skills:
        reasons.append(
            f"{len(matched_skills)} matching skills"
        )

    # Preferred location
    matched_locations = [
        item for item in profile["preferred_locations"]
        if item.lower() in location
    ]

    if matched_locations:
        score += 20
        reasons.append("Matches preferred location")


    # Salary check: compare only verified INR salary values in LPA.
    salary = job.get("salary_lpa")
    salary_text = job.get("salary", "")

    if salary is None and salary_text:
        parsed_salary = parse_salary(salary_text)

        if parsed_salary["salary_currency"] == "INR":
            salary = parsed_salary["salary_lpa"]

    if salary is not None:
        try:
            salary = float(salary)

            if salary >= profile["minimum_salary_lpa"]:
                score += 10
                reasons.append("Meets minimum salary target")
            else:
                reasons.append("Below minimum salary target")
        except (TypeError, ValueError):
            reasons.append("Salary needs verification")
    elif salary_text:
        reasons.append("Salary disclosed but needs verification")
    else:
        reasons.append("Salary not disclosed")


    return {
        "title": job.get("title", "Unknown"),
        "url": job.get("url") or job.get("apply_url", ""),
        "company": job.get("company", "Unknown"),
        "location": job.get("location", "Unknown"),
        "score": min(score, 100),
        "category": classify_job_category(job),
        "matched_skills": matched_skills,
        "reasons": reasons,
        "apply_url": job.get("apply_url", "")
    }


def rank_jobs(jobs):
    """Balance the three career paths and rank matching jobs."""

    profile = load_career_profile()

    categories = [
        "Accounting & Finance",
        "Data & Business Analysis",
        "Software & Full-Stack Development"
    ]

    grouped = {category: [] for category in categories}
    other_jobs = []

    for job in jobs:
        result = match_job(job, profile)
        category = result["category"]

        if category in grouped:
            grouped[category].append(result)
        else:
            other_jobs.append(result)

    # Highest scoring jobs first within each career path.
    for category in categories:
        grouped[category].sort(
            key=lambda item: item["score"],
            reverse=True
        )

    # Alternate career paths to avoid favoring just one.
    ranked = []
    max_count = max(
        (len(items) for items in grouped.values()),
        default=0
    )

    for index in range(max_count):
        for category in categories:
            if index < len(grouped[category]):
                ranked.append(grouped[category][index])

    other_jobs.sort(
        key=lambda item: item["score"],
        reverse=True
    )

    ranked.extend(other_jobs)
    return ranked


def show_job_matches(jobs):
    """Display ranked jobs in the terminal."""

    ranked = rank_jobs(jobs)

    print("\n========== JARVIS JOB MATCHES ==========")

    for number, job in enumerate(ranked, start=1):
        print(f"\n{number}. {job['title']}")
        print("Company:", job["company"])
        print("Career path:", job["category"])
        print("Location:", job["location"])
        print("Match score:", f"{job['score']}/100")

        if job["matched_skills"]:
            print(
                "Matching skills:",
                ", ".join(job["matched_skills"])
            )

        print("Reasons:", ", ".join(job["reasons"]))

        if job["apply_url"]:
            print("Application link:", job["apply_url"])

    print("\n========================================")



if __name__ == "__main__":
    save_career_profile()
    show_career_profile()

    sample_jobs = [
        {
            "title": "Junior Accountant",
            "company": "Example Finance Ltd",
            "location": "Jaipur",
            "description": (
                "Tally Prime, bookkeeping, Excel, "
                "bank reconciliation and accounts payable."
            ),
            "salary_lpa": 7
        },
        {
            "title": "Junior Data Analyst",
            "company": "Example Analytics Ltd",
            "location": "Remote",
            "description": (
                "MySQL, SQL, Power BI, Excel and "
                "data visualization."
            ),
            "salary_lpa": 8
        },
        {
            "title": "Junior Full Stack Developer",
            "company": "Example Software Ltd",
            "location": "Jaipur",
            "description": (
                "Python, JavaScript, HTML, CSS, "
                "React and REST APIs."
            ),
            "salary_lpa": 9
        }
    ]

    show_job_matches(sample_jobs)
