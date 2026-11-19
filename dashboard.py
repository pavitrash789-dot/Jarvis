import json
import shutil
from pathlib import Path
from datetime import datetime

from flask import Flask, render_template_string, request, redirect, url_for

app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent
JOBS_FILE = BASE_DIR / "saved_jobs.json"
BACKUP_FILE = BASE_DIR / "saved_jobs.backup.json"

STATUSES = [
    "Found",
    "Interested",
    "Applied",
    "Interview",
    "Assessment",
    "Offer",
    "Rejected",
    "Withdrawn",
]


def load_jobs():
    if not JOBS_FILE.exists():
        return []

    try:
        with JOBS_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)
        return data if isinstance(data, list) else []
    except (OSError, json.JSONDecodeError):
        return []


def save_jobs(jobs):
    # Keep a backup of the previous file before updating it.
    if JOBS_FILE.exists():
        shutil.copy2(JOBS_FILE, BACKUP_FILE)

    temp_file = JOBS_FILE.with_suffix(".tmp")
    with temp_file.open("w", encoding="utf-8") as file:
        json.dump(jobs, file, indent=4, ensure_ascii=False)
    temp_file.replace(JOBS_FILE)


PAGE = """
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>JARVIS | Job Dashboard</title>
<style>
:root {
    color-scheme: dark;
    --bg: #0b1020;
    --panel: #141c30;
    --line: #293650;
    --text: #eef3ff;
    --muted: #9caac4;
    --accent: #7c9cff;
}
* { box-sizing: border-box; }
body {
    margin: 0;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    background: var(--bg);
    color: var(--text);
}
header {
    padding: 28px 5%;
    border-bottom: 1px solid var(--line);
    background: #10182b;
}
header h1 { margin: 0 0 7px; letter-spacing: 1px; }
header p, .muted { color: var(--muted); }
main { max-width: 1450px; margin: auto; padding: 26px 5%; }
.stats {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 14px;
    margin-bottom: 24px;
}
.stat, .panel, .job {
    background: var(--panel);
    border: 1px solid var(--line);
    border-radius: 14px;
}
.stat { padding: 19px; }
.stat strong { display: block; font-size: 28px; margin-top: 8px; }
.filters {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 12px;
    padding: 18px;
    margin-bottom: 22px;
}
input, select, button, .link {
    font: inherit;
    border-radius: 8px;
    padding: 10px 12px;
}
input, select {
    color: var(--text);
    background: #0c1425;
    border: 1px solid var(--line);
    min-width: 0;
    width: 100%;
}
button {
    border: 0;
    color: #081126;
    background: var(--accent);
    cursor: pointer;
    font-weight: 650;
}
.jobs {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(min(100%, 390px), 1fr));
    gap: 15px;
}
.job { padding: 20px; min-width: 0; }
.job h3 { margin: 0 0 8px; line-height: 1.4; }
.job p { line-height: 1.5; overflow-wrap: anywhere; }
.pill {
    display: inline-block;
    padding: 5px 9px;
    border-radius: 20px;
    background: #253455;
    color: #d8e2ff;
    font-size: 12px;
}
.row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    margin-top: 16px;
}
.row form { display: flex; gap: 8px; min-width: 0; }
.row select { max-width: 160px; }
a { color: #a9beff; }
.empty { padding: 35px; text-align: center; color: var(--muted); }
@media (max-width: 520px) {
    .row { align-items: stretch; flex-direction: column; }
    .row form { flex-direction: column; }
    .row select { max-width: none; }
}
</style>
</head>
<body>
<header>
    <h1>◈ JARVIS</h1>
    <div>Career Intelligence · Job Application Dashboard</div>
    <p>Discover opportunities. Track progress. Stay in control.</p>
</header>
<main>
    <section class="stats">
        <div class="stat">Saved jobs<strong>{{ total }}</strong></div>
        <div class="stat">Interested<strong>{{ counts["Interested"] }}</strong></div>
        <div class="stat">Applied<strong>{{ counts["Applied"] }}</strong></div>
        <div class="stat">Interviews<strong>{{ counts["Interview"] }}</strong></div>
        <div class="stat">Offers<strong>{{ counts["Offer"] }}</strong></div>
    </section>

    <form class="panel filters" method="get">
        <input name="q" placeholder="Search title, company, skills..."
               value="{{ query }}">
        <select name="status">
            <option value="">All statuses</option>
            {% for item in statuses %}
            <option value="{{ item }}" {% if status == item %}selected{% endif %}>
                {{ item }}
            </option>
            {% endfor %}
        </select>
        <select name="source">
            <option value="">All sources</option>
            {% for item in sources %}
            <option value="{{ item }}" {% if selected_source == item %}selected{% endif %}>
                {{ item }}
            </option>
            {% endfor %}
        </select>
        <button type="submit">Filter jobs</button>
    </form>

    {% if jobs %}
    <section class="jobs">
        {% for job in jobs %}
        <article class="job">
            <h3>{{ job.get("title") or "Untitled role" }}</h3>
            <p class="muted">
                {{ job.get("company") or "Company not disclosed" }}
                · {{ job.get("location") or "Location not specified" }}
            </p>
            <p>
                <span class="pill">{{ job.get("source") or "Unknown source" }}</span>
                <span class="pill">{{ job.get("category") or "Uncategorized" }}</span>
            </p>
            <p><strong>Salary:</strong>
                {{ job.get("salary") or "Not disclosed" }}
            </p>
             <p><strong>India eligibility:</strong>
                {{ job.get("eligibility") or "Unverified" }}
            </p>
            <p><strong>Match score:</strong>
                {% if job.get("score") is not none %}
                    {{ job.get("score") }}/100
                {% else %}
                    Not scored
                {% endif %}
            </p>
            <div class="row">
                {% if job.get("apply_url") or job.get("url") %}
                <a href="{{ job.get('apply_url') or job.get('url') }}"
                   target="_blank" rel="noopener noreferrer">View job ↗</a>
                {% else %}
                <span class="muted">No job link</span>
                {% endif %}
                <form method="post" action="{{ url_for('update_status') }}">
                    <input type="hidden" name="url"
                           value="{{ job.get('url') or job.get('apply_url') }}">
                    <select name="status" aria-label="Application status">
                        {% for item in statuses %}
                        <option value="{{ item }}"
                            {% if job.get("status", "Found") == item %}
                            selected{% endif %}>
                            {{ item }}
                        </option>
                        {% endfor %}
                    </select>
                    <button type="submit">Save</button>
                </form>
            </div>
        </article>
        {% endfor %}
    </section>
    {% else %}
    <div class="panel empty">
        No jobs match these filters. Try a different search.
    </div>
    {% endif %}
</main>
</body>
</html>
"""


@app.get("/")
def index():
    all_jobs = load_jobs()
    query = request.args.get("q", "").strip().lower()
    status = request.args.get("status", "").strip()
    source = request.args.get("source", "").strip()

    counts = {
        item: sum(
            1 for job in all_jobs
            if job.get("status", "Found") == item
        )
        for item in STATUSES
    }

    jobs = []
    for job in all_jobs:
        searchable = " ".join(
            str(job.get(key) or "")
            for key in ("title", "company", "location", "description",
                        "category", "matched_skills")
        ).lower()

        if query and query not in searchable:
            continue
        if status and job.get("status", "Found") != status:
            continue
        if source and job.get("source", "") != source:
            continue

        jobs.append(job)

    jobs.sort(
        key=lambda job: float(job.get("score") or 0),
        reverse=True,
    )

    sources = sorted({
        job.get("source", "Unknown source") for job in all_jobs
    })

    return render_template_string(
        PAGE,
        jobs=jobs,
        total=len(all_jobs),
        counts=counts,
        statuses=STATUSES,
        sources=sources,
        query=request.args.get("q", ""),
        status=status,
        selected_source=source,
    )


@app.post("/update-status")
def update_status():
    url = request.form.get("url", "")
    status = request.form.get("status", "")

    if status not in STATUSES:
        return "Invalid application status", 400

    jobs = load_jobs()
    for job in jobs:
        job_url = job.get("url") or job.get("apply_url")
        if job_url == url and url:
            job["status"] = status
            job["status_updated_at"] = datetime.now().isoformat(
                timespec="seconds"
            )
            save_jobs(jobs)
            break

    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
