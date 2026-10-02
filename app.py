"""
FutureReady AI - Backend (Flask)
A career readiness platform for students with AI-powered skill-gap analysis,
personalized roadmaps, interview coaching, and progress tracking.
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import pandas as pd
import json
import os
import uuid
import datetime
import random

app = Flask(__name__, static_folder="static", template_folder="templates")
CORS(app, origins="*")

# ─────────────────────────────────────────────
# Data Loading
# ─────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "future_ready_dataset.csv")
DB_FILE   = os.path.join(BASE_DIR, "students_db.json")

def load_career_data():
    df = pd.read_csv(DATA_FILE)
    df["required_skills"]      = df["required_skills"].apply(lambda x: [s.strip() for s in x.split(",")])
    df["core_topics"]          = df["core_topics"].apply(lambda x: [s.strip() for s in x.split(",")])
    df["recommended_projects"] = df["recommended_projects"].apply(lambda x: [s.strip() for s in x.split(",")])
    return df

# In-memory DB (Render free plan has no persistent disk)
# Falls back to file if running locally
IN_MEMORY_DB = {}

def load_db():
    # Try file first (local), fall back to in-memory (Render)
    try:
        if os.path.exists(DB_FILE):
            with open(DB_FILE, "r") as f:
                return json.load(f)
    except Exception:
        pass
    return dict(IN_MEMORY_DB)

def save_db(data):
    global IN_MEMORY_DB
    IN_MEMORY_DB = dict(data)
    # Also try to write to file (works locally, silently fails on Render)
    try:
        with open(DB_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass

CAREER_DF = load_career_data()

# ─────────────────────────────────────────────
# Helper: normalize skill strings
# ─────────────────────────────────────────────
def normalize(skill):
    return skill.strip().lower()

def parse_skills(raw):
    """Accept comma-separated string or list."""
    if isinstance(raw, list):
        return [normalize(s) for s in raw if s.strip()]
    if isinstance(raw, str):
        return [normalize(s) for s in raw.split(",") if s.strip()]
    return []

# ─────────────────────────────────────────────
# AI Logic: Skill-Gap Analysis
# ─────────────────────────────────────────────
def compute_skill_gap(student_skills_raw, career_role):
    row = CAREER_DF[CAREER_DF["career_role"].str.lower() == career_role.strip().lower()]
    if row.empty:
        return None

    row = row.iloc[0]
    required   = [normalize(s) for s in row["required_skills"]]
    student    = parse_skills(student_skills_raw)
    matched    = [s for s in required if s in student]
    missing    = [s for s in required if s not in student]
    extra      = [s for s in student  if s not in required]
    match_pct  = round(len(matched) / len(required) * 100, 1) if required else 0

    return {
        "career_role":        row["career_role"],
        "required_skills":    row["required_skills"],
        "current_skills":     student,
        "matched_skills":     matched,
        "missing_skills":     missing,
        "extra_skills":       extra,
        "match_percentage":   match_pct,
        "avg_salary":         int(row["avg_salary"]),
        "demand_level":       row["demand_level"],
        "description":        row["description"],
        "core_topics":        row["core_topics"],
        "recommended_projects": row["recommended_projects"],
    }

# ─────────────────────────────────────────────
# AI Logic: Personalized Roadmap Generator
# ─────────────────────────────────────────────
ROADMAP_TEMPLATES = {
    "Python Developer": [
        ("Learn Python fundamentals", "study",    "Core Python: syntax, loops, functions, OOP"),
        ("Practice OOP & modules",    "study",    "Classes, inheritance, packages, virtual envs"),
        ("Learn SQL & databases",     "study",    "MySQL/SQLite basics, CRUD queries"),
        ("Master Pandas & NumPy",     "study",    "DataFrames, array operations, data wrangling"),
        ("Learn Flask/Django",        "study",    "Routing, templates, REST API design"),
        ("Build a CLI tool",          "project",  "Command-line app using argparse"),
        ("Build a REST API",          "project",  "CRUD API with Flask + SQLite"),
        ("Write unit tests",          "study",    "unittest / pytest basics"),
        ("Practice DSA",              "practice", "LeetCode: arrays, strings, hashmaps"),
        ("Apply for internship",      "milestone","Polish resume & submit 5 applications"),
    ],
    "Data Analyst": [
        ("Learn Python basics",        "study",    "Variables, loops, functions, file I/O"),
        ("Master SQL",                 "study",    "SELECT, JOINs, GROUP BY, subqueries"),
        ("Learn Pandas",               "study",    "DataFrames, merging, pivot tables"),
        ("Learn data visualization",   "study",    "Matplotlib, Seaborn, Plotly"),
        ("Learn statistics",           "study",    "Mean, median, standard deviation, correlation"),
        ("EDA project",                "project",  "Exploratory Data Analysis on a Kaggle dataset"),
        ("Build a dashboard",          "project",  "Sales or HR dashboard using Tableau / Streamlit"),
        ("Learn Power BI or Tableau",  "study",    "Connect data, build charts, publish reports"),
        ("Practice SQL challenges",    "practice", "HackerRank SQL track – 30 problems"),
        ("Apply for internship",       "milestone","Attach dashboard project to your resume"),
    ],
    "AI/ML Engineer": [
        ("Master Python & NumPy",        "study",    "Python OOP, NumPy array operations"),
        ("Study linear algebra & stats", "study",    "Matrices, probability, distributions"),
        ("Learn Scikit-learn",           "study",    "Classification, regression, clustering"),
        ("Learn deep learning basics",   "study",    "Neural networks, backprop, activation functions"),
        ("Learn TensorFlow / PyTorch",   "study",    "Model building, training, evaluation"),
        ("Build image classifier",       "project",  "CNN on CIFAR-10 or MNIST"),
        ("NLP project",                  "project",  "Sentiment analysis with BERT or LSTM"),
        ("Study MLOps basics",           "study",    "Model serving, Docker, FastAPI"),
        ("Kaggle competition",           "practice", "Submit to a beginner Kaggle competition"),
        ("Build portfolio & apply",      "milestone","2 ML projects on GitHub + LinkedIn update"),
    ],
    "Web Developer": [
        ("Learn HTML & CSS",           "study",    "Semantic HTML5, Flexbox, Grid, responsive design"),
        ("Learn JavaScript",           "study",    "ES6+, DOM, fetch API, async/await"),
        ("Learn a frontend framework", "study",    "React.js – components, hooks, state"),
        ("Learn Node.js basics",       "study",    "Express server, routes, middleware"),
        ("Learn SQL / MongoDB",        "study",    "Database CRUD, schema design"),
        ("Build a portfolio website",  "project",  "Personal portfolio with HTML/CSS/JS"),
        ("Build a full-stack app",     "project",  "CRUD web app with React + Node + DB"),
        ("Learn Git & GitHub",         "study",    "Branching, PRs, collaborative workflow"),
        ("Study web security basics",  "study",    "HTTPS, CORS, XSS, SQL injection"),
        ("Apply for internship",       "milestone","Deploy app on Vercel/Render + share link"),
    ],
    "Software Developer": [
        ("Master a core language",   "study",    "Java or Python: OOP, collections, I/O"),
        ("Study Data Structures",    "study",    "Arrays, linked lists, stacks, queues, trees"),
        ("Study Algorithms",         "study",    "Sorting, searching, graph traversal, DP"),
        ("Learn design patterns",    "study",    "Singleton, Factory, Observer, MVC"),
        ("Learn SQL databases",      "study",    "Schema design, normalization, transactions"),
        ("Build a management app",   "project",  "Library or inventory system with CRUD"),
        ("System design basics",     "study",    "Scalability, caching, load balancing"),
        ("Practice DSA problems",    "practice", "50+ LeetCode problems (Easy → Medium)"),
        ("Open-source contribution", "milestone","Contribute to 1 GitHub open-source project"),
        ("Mock interview prep",      "practice", "10 mock interviews via Pramp / Interviewing.io"),
    ],
    "Frontend Developer": [
        ("Master HTML5 & CSS3",       "study",    "Semantic markup, animations, custom properties"),
        ("Master JavaScript ES6+",    "study",    "Closures, promises, modules, destructuring"),
        ("Learn React.js",            "study",    "Components, JSX, hooks, context, React Router"),
        ("Learn TypeScript",          "study",    "Types, interfaces, generics"),
        ("Learn Tailwind CSS",        "study",    "Utility-first CSS, responsive breakpoints"),
        ("Accessibility & SEO",       "study",    "ARIA labels, semantic HTML, meta tags"),
        ("Build component library",   "project",  "Reusable React components with Storybook"),
        ("Build a dashboard UI",      "project",  "Admin dashboard with charts and tables"),
        ("Learn Figma basics",        "study",    "Wireframing, prototyping, design handoff"),
        ("Deploy portfolio",          "milestone","Netlify / Vercel deployment + custom domain"),
    ],
}

DEFAULT_ROADMAP = [
    ("Assess & plan",            "study",    "List all skills you need for your target role"),
    ("Study core fundamentals",  "study",    "Focus on the most critical missing skills first"),
    ("Build a small project",    "project",  "Apply what you've learned in a mini-project"),
    ("Study advanced topics",    "study",    "Deepen knowledge in your specialization"),
    ("Build a major project",    "project",  "End-to-end project that demonstrates all skills"),
    ("Create GitHub portfolio",  "milestone","Push all projects with good README files"),
    ("Practice interview Qs",    "practice", "Do 20 technical + 10 behavioral mock questions"),
    ("Update LinkedIn & resume", "milestone","Craft a strong summary and skill section"),
    ("Apply for internships",    "milestone","Target 10 relevant openings this week"),
    ("Reflect & iterate",        "study",    "Identify gaps post-rejection and keep learning"),
]

def generate_roadmap(career_role, missing_skills, current_skills):
    template = ROADMAP_TEMPLATES.get(career_role, DEFAULT_ROADMAP)
    steps = []
    for i, (title, step_type, detail) in enumerate(template, 1):
        steps.append({
            "step":      i,
            "title":     title,
            "type":      step_type,
            "detail":    detail,
            "status":    "not_started",
        })
    return steps

# ─────────────────────────────────────────────
# AI Logic: Interview Coach
# ─────────────────────────────────────────────
INTERVIEW_BANK = {
    "hr": [
        "Tell me about yourself.",
        "Why do you want to pursue {career}?",
        "Where do you see yourself in 5 years?",
        "What are your greatest strengths and weaknesses?",
        "Describe a challenge you faced and how you overcame it.",
        "Why should we hire you?",
        "How do you handle pressure and tight deadlines?",
        "Tell me about a time you worked in a team.",
        "What motivates you?",
        "Do you have any questions for us?",
    ],
    "technical": {
        "Python Developer": [
            "Explain the difference between a list and a tuple in Python.",
            "What is a decorator in Python? Give an example.",
            "Explain RESTful API design principles.",
            "What is ORM? Which ORMs have you used?",
            "How does Python's GIL affect multithreading?",
            "What is the difference between `__str__` and `__repr__`?",
            "Explain Flask's request-response lifecycle.",
            "How do you handle exceptions in Python?",
        ],
        "Data Analyst": [
            "What is the difference between GROUP BY and HAVING in SQL?",
            "How do you handle missing values in a dataset?",
            "Explain the difference between correlation and causation.",
            "What is a pivot table? How do you create one in Pandas?",
            "How would you detect outliers in a dataset?",
            "Explain the concept of data normalization.",
            "What are window functions in SQL?",
            "How do you choose the right chart type for data?",
        ],
        "AI/ML Engineer": [
            "Explain the bias-variance tradeoff.",
            "What is overfitting? How do you prevent it?",
            "Explain the difference between supervised and unsupervised learning.",
            "What is backpropagation?",
            "How does a CNN differ from a regular neural network?",
            "What is regularization? Explain L1 vs L2.",
            "How do you evaluate a classification model?",
            "What is transfer learning?",
        ],
        "Web Developer": [
            "Explain the difference between GET and POST.",
            "What is the virtual DOM in React?",
            "How does async/await work in JavaScript?",
            "Explain CORS and how to handle it.",
            "What is the difference between cookies and localStorage?",
            "Explain the CSS box model.",
            "What is database indexing and why is it important?",
            "How does HTTPS work?",
        ],
        "Software Developer": [
            "Explain time and space complexity with Big-O notation.",
            "What is the difference between a stack and a queue?",
            "Explain the SOLID principles.",
            "What is a binary search tree? What is its time complexity?",
            "What is the difference between process and thread?",
            "Explain the MVC design pattern.",
            "What is deadlock? How do you prevent it?",
            "Explain polymorphism with an example.",
        ],
        "Frontend Developer": [
            "Explain event bubbling and event capturing.",
            "What is the difference between `null` and `undefined`?",
            "How does React's reconciliation algorithm work?",
            "What are React hooks? Name 3 and explain their use.",
            "Explain CSS specificity.",
            "What is lazy loading? How do you implement it?",
            "What is a closure in JavaScript?",
            "How do you optimize a React application?",
        ],
    },
    "project": [
        "Walk me through your most recent project.",
        "What was the biggest technical challenge in your {project} project?",
        "How did you decide which technology to use for your project?",
        "What would you do differently if you rebuilt this project?",
        "How did you test your project?",
        "What did you learn from building this project?",
    ],
    "followup": [
        "Can you elaborate on that?",
        "Can you give a specific example?",
        "How would you scale that solution?",
        "What alternative approaches did you consider?",
        "How long did that take, and could it be optimized?",
    ],
}

FEEDBACK_TEMPLATES = {
    "good": [
        "Clear and structured answer.",
        "Good use of technical terminology.",
        "Strong explanation with a real example.",
        "Concise and focused.",
        "Demonstrated solid understanding.",
    ],
    "improve": [
        "Try to include a concrete example from your experience.",
        "Structure your answer using STAR (Situation, Task, Action, Result).",
        "Explain the 'why' behind your choice, not just the 'what'.",
        "Use simpler language to ensure clarity.",
        "Back up your claim with a metric or measurable result.",
        "Mention the problem, your technology choice, and your specific contribution.",
    ],
    "communication": ["Excellent", "Good", "Average", "Needs Improvement"],
    "technical":     ["Excellent", "Strong", "Satisfactory", "Needs Improvement"],
    "structure":     ["Well Structured", "Moderate", "Needs More Structure"],
}

def evaluate_answer(question, answer, career):
    words = answer.strip().split()
    length = len(words)

    comm_score  = "Excellent" if length > 60 else "Good" if length > 30 else "Average" if length > 10 else "Needs Improvement"
    tech_score  = "Strong" if length > 50 else "Satisfactory" if length > 20 else "Needs Improvement"
    struct_score = "Well Structured" if length > 40 else "Moderate" if length > 15 else "Needs More Structure"

    positives = random.sample(FEEDBACK_TEMPLATES["good"], 2)
    improvements = random.sample(FEEDBACK_TEMPLATES["improve"], 2)

    return {
        "communication":   comm_score,
        "technical":       tech_score,
        "structure":       struct_score,
        "positives":       positives,
        "improvements":    improvements,
        "overall_score":   min(10, max(1, round(length / 10))),
        "followup":        random.choice(FEEDBACK_TEMPLATES.get("followup", ["Can you elaborate?"])),
    }

def get_interview_question(career, question_type="technical"):
    if question_type == "hr":
        q = random.choice(INTERVIEW_BANK["hr"])
        return q.replace("{career}", career)
    if question_type == "project":
        q = random.choice(INTERVIEW_BANK["project"])
        return q.replace("{project}", "your recent project")
    if question_type == "followup":
        return random.choice(INTERVIEW_BANK["followup"])
    # technical
    pool = INTERVIEW_BANK["technical"].get(career, [])
    if not pool:
        # fallback: pick from any career
        for v in INTERVIEW_BANK["technical"].values():
            pool.extend(v)
    return random.choice(pool) if pool else "Explain your approach to problem solving."

# ─────────────────────────────────────────────
# Dashboard Score Calculator
# ─────────────────────────────────────────────
def compute_dashboard(profile):
    skills_all = parse_skills(profile.get("programming_skills", "")) + \
                 parse_skills(profile.get("database_skills", "")) + \
                 parse_skills(profile.get("web_dev_skills", ""))

    tech_score   = min(10, max(1, len(skills_all)))
    comm_map     = {"Excellent": 9, "Good": 7, "Average": 5, "Poor": 3, "Basic": 4}
    ps_map       = {"Excellent": 9, "Good": 7, "Average": 5, "Poor": 3, "Basic": 4}
    comm_score   = comm_map.get(profile.get("communication_level", "Average"), 5)
    ps_score     = ps_map.get(profile.get("problem_solving_level", "Average"), 5)

    certs        = len(profile.get("certifications", "").split(",")) if profile.get("certifications") else 0
    internships  = 1 if profile.get("internship_experience", "").strip().lower() not in ["none", "", "no"] else 0
    projects_cnt = len(profile.get("projects", "").split(",")) if profile.get("projects") else 0

    interview_score = min(10, certs * 2 + internships * 3 + projects_cnt)

    # profile completeness
    fields = ["name","email","degree","specialization","year_of_study",
              "target_career","programming_skills","database_skills",
              "web_dev_skills","projects","certifications","internship_experience",
              "communication_level","problem_solving_level"]
    filled = sum(1 for f in fields if profile.get(f, "").strip() not in ["", "none", "n/a"])
    completeness = round(filled / len(fields) * 100)

    return {
        "technical_skills":     min(10, tech_score),
        "communication":        comm_score,
        "problem_solving":      ps_score,
        "interview_preparation": interview_score,
        "profile_completeness": completeness,
    }

# ─────────────────────────────────────────────
# AI: Project Description Generator
# ─────────────────────────────────────────────
def generate_project_description(project_name, tech_used, role, outcome):
    templates = [
        f"Developed {project_name} using {tech_used}. As the {role}, I designed and implemented core features, resulting in {outcome}. This project enhanced my skills in {tech_used} and exposed me to real-world software engineering practices.",
        f"Built {project_name} — a {role}-led project leveraging {tech_used}. The application addresses {outcome} by providing an intuitive interface and efficient backend. Key learnings include system design, API integration, and user-centric development.",
        f"{project_name} is a project I developed in the role of {role} using {tech_used}. The primary objective was {outcome}. Through this project, I strengthened my understanding of full project lifecycle, version control, and technical problem-solving.",
    ]
    return random.choice(templates)

# ─────────────────────────────────────────────
# Routes – Static Frontend
# ─────────────────────────────────────────────
@app.route("/")
def index():
    return send_from_directory(BASE_DIR, "index.html")

# ─────────────────────────────────────────────
# API: Career Roles
# ─────────────────────────────────────────────
@app.route("/api/careers", methods=["GET"])
def get_careers():
    roles = CAREER_DF[["career_role", "demand_level", "avg_salary", "description"]].to_dict(orient="records")
    return jsonify({"careers": roles})

# ─────────────────────────────────────────────
# API: Student Profile
# ─────────────────────────────────────────────
@app.route("/api/profile", methods=["POST"])
def save_profile():
    data = request.get_json()
    db = load_db()
    student_id = data.get("student_id") or str(uuid.uuid4())
    data["student_id"] = student_id
    data["updated_at"] = datetime.datetime.now().isoformat()
    db[student_id] = data
    save_db(db)
    return jsonify({"success": True, "student_id": student_id, "profile": data})

@app.route("/api/profile/<student_id>", methods=["GET"])
def get_profile(student_id):
    db = load_db()
    profile = db.get(student_id)
    if not profile:
        return jsonify({"error": "Profile not found"}), 404
    return jsonify({"profile": profile})

# ─────────────────────────────────────────────
# API: Skill-Gap Analysis
# ─────────────────────────────────────────────
@app.route("/api/skill-gap", methods=["POST"])
def skill_gap():
    data   = request.get_json()
    career = data.get("career_role", "")
    skills = data.get("all_skills", "")
    result = compute_skill_gap(skills, career)
    if result is None:
        return jsonify({"error": f"Career role '{career}' not found in dataset."}), 404
    return jsonify(result)

# ─────────────────────────────────────────────
# API: Roadmap
# ─────────────────────────────────────────────
@app.route("/api/roadmap", methods=["POST"])
def roadmap():
    data          = request.get_json()
    student_id    = data.get("student_id")
    career        = data.get("career_role", "")
    missing       = data.get("missing_skills", [])
    current       = data.get("current_skills", [])
    steps         = generate_roadmap(career, missing, current)
    if student_id:
        db = load_db()
        if student_id in db:
            db[student_id]["roadmap"] = steps
            save_db(db)
    return jsonify({"roadmap": steps, "career_role": career})

@app.route("/api/roadmap/update", methods=["POST"])
def update_roadmap_step():
    data       = request.get_json()
    student_id = data.get("student_id")
    step_index = data.get("step_index")
    status     = data.get("status")  # not_started | in_progress | completed
    db         = load_db()
    if student_id not in db:
        return jsonify({"error": "Student not found"}), 404
    roadmap_steps = db[student_id].get("roadmap", [])
    if 0 <= step_index < len(roadmap_steps):
        roadmap_steps[step_index]["status"] = status
        db[student_id]["roadmap"] = roadmap_steps
        save_db(db)
        return jsonify({"success": True, "roadmap": roadmap_steps})
    return jsonify({"error": "Invalid step index"}), 400

# ─────────────────────────────────────────────
# API: Interview Coach
# ─────────────────────────────────────────────
@app.route("/api/interview/question", methods=["POST"])
def interview_question():
    data    = request.get_json()
    career  = data.get("career_role", "Software Developer")
    qtype   = data.get("question_type", "technical")
    question = get_interview_question(career, qtype)
    return jsonify({"question": question, "type": qtype, "career": career})

@app.route("/api/interview/evaluate", methods=["POST"])
def interview_evaluate():
    data     = request.get_json()
    question = data.get("question", "")
    answer   = data.get("answer", "")
    career   = data.get("career_role", "Software Developer")
    if not answer.strip():
        return jsonify({"error": "Answer cannot be empty"}), 400
    feedback = evaluate_answer(question, answer, career)
    return jsonify({"feedback": feedback, "question": question})

# ─────────────────────────────────────────────
# API: Dashboard
# ─────────────────────────────────────────────
@app.route("/api/dashboard/<student_id>", methods=["GET"])
def dashboard(student_id):
    db = load_db()
    profile = db.get(student_id)
    if not profile:
        return jsonify({"error": "Profile not found"}), 404
    scores   = compute_dashboard(profile)
    roadmap_steps = profile.get("roadmap", [])
    completed = sum(1 for s in roadmap_steps if s.get("status") == "completed")
    in_prog   = sum(1 for s in roadmap_steps if s.get("status") == "in_progress")
    return jsonify({
        "scores":           scores,
        "roadmap_progress": {
            "total":       len(roadmap_steps),
            "completed":   completed,
            "in_progress": in_prog,
            "not_started": len(roadmap_steps) - completed - in_prog,
        },
    })

# ─────────────────────────────────────────────
# API: Portfolio / Project Description
# ─────────────────────────────────────────────
@app.route("/api/portfolio/generate-description", methods=["POST"])
def generate_description():
    data         = request.get_json()
    project_name = data.get("project_name", "My Project")
    tech_used    = data.get("tech_used", "various technologies")
    role         = data.get("role", "developer")
    outcome      = data.get("outcome", "improved functionality")
    description  = generate_project_description(project_name, tech_used, role, outcome)
    return jsonify({"description": description})

# ─────────────────────────────────────────────
# API: Full Analysis (one-shot for frontend)
# ─────────────────────────────────────────────
@app.route("/api/analyze", methods=["POST"])
def full_analysis():
    """
    Accepts full student profile, runs skill-gap + roadmap + dashboard in one call.
    """
    data = request.get_json()
    career = data.get("target_career", "")

    # Combine all skills
    all_skills = ", ".join(filter(None, [
        data.get("programming_skills", ""),
        data.get("database_skills", ""),
        data.get("web_dev_skills", ""),
    ]))

    gap    = compute_skill_gap(all_skills, career)
    if gap is None:
        return jsonify({"error": f"Career '{career}' not recognized."}), 404

    steps  = generate_roadmap(career, gap["missing_skills"], gap["current_skills"])
    scores = compute_dashboard(data)

    # Save profile with roadmap
    db = load_db()
    sid = data.get("student_id") or str(uuid.uuid4())
    data["student_id"] = sid
    data["roadmap"]    = steps
    data["updated_at"] = datetime.datetime.now().isoformat()
    db[sid]            = data
    save_db(db)

    return jsonify({
        "student_id":   sid,
        "skill_gap":    gap,
        "roadmap":      steps,
        "dashboard":    scores,
    })


if __name__ == "__main__":
    app.run(debug=True, port=5000)
