import json
from pathlib import Path
from urllib.parse import urlparse

JOBS_FILE = Path(__file__).with_name("saved_jobs.json")


def load_jobs():
    if not JOBS_FILE.exists():
        return []

    try:
        with JOBS_FILE.open("r", encoding="utf-8") as file:
            return json.load(file)
    except (json.JSONDecodeError, OSError):
        print("Could not read saved_jobs.json.")
        return []


def save_jobs(jobs):
    with JOBS_FILE.open("w", encoding="utf-8") as file:
        json.dump(jobs, file, indent=4, ensure_ascii=False)


def add_job():
    print("\n--- Save a LinkedIn Job ---")

    title = input("Job title: ").strip()
    company = input("Company name: ").strip()
    location = input("Location (default Remote): ").strip() or "Remote"
    url = input("LinkedIn job URL: ").strip()

    if not title or not company:
        print("Job title and company name are required.")
        return

    parsed_url = urlparse(url)

    if (
        parsed_url.scheme != "https"
        or parsed_url.hostname not in ("linkedin.com", "www.linkedin.com")
        or not parsed_url.path.startswith("/jobs/")
    ):
        print("Please enter a valid HTTPS LinkedIn Jobs link.")
        return

    jobs = load_jobs()

    if any(job["url"] == url for job in jobs):
        print("This job link is already saved.")
        return

    job = {
        "title": title,
        "company": company,
        "location": location,
        "url": url,
        "status": "Saved",
        "source": "LinkedIn",
    }

    jobs.append(job)
    save_jobs(jobs)

    print("\nJob saved successfully!")


def show_jobs():
    jobs = load_jobs()

    if not jobs:
        print("\nNo saved jobs yet.")
        return

    print(f"\n--- Saved Jobs: {len(jobs)} ---")

    for number, job in enumerate(jobs, start=1):
        print(f"\n{number}. {job['title']}")
        print(f"   Company: {job['company']}")
        print(f"   Location: {job['location']}")
        print(f"   Status: {job['status']}")
        print(f"   Link: {job['url']}")


def main():
    while True:
        print("\n===== JARVIS JOB TRACKER =====")
        print("1. Save a LinkedIn job")
        print("2. View saved jobs")
        print("3. Exit")

        choice = input("Choose an option: ").strip()

        if choice == "1":
            add_job()
        elif choice == "2":
            show_jobs()
        elif choice == "3":
            print("Job tracker closed.")
            break
        else:
            print("Invalid choice. Enter 1, 2, or 3.")


if __name__ == "__main__":
    main()
