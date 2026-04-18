from flask import Flask, request, redirect, render_template, session, jsonify
import mysql.connector
import random
import os
import json
from functools import wraps
from mcq_dataset import MCQ_DATASET

app = Flask(__name__)
app.secret_key = "secret123"

# Login Required Decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user" not in session:
            return redirect("/")
        return f(*args, **kwargs)
    return decorated_function

# Database connection
def get_db_connection():
    return mysql.connector.connect(
        host="mysql-357474b6-mdsamim8321-d050.d.aivencloud.com",
        port=16348,
        user="avnadmin",
        password="AVNS_7ssf7Tjqhv4FtyLVrZ1",
        database="defaultdb",
        ssl_mode="REQUIRED"
    )
def ensure_table_questions(cursor):
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS question_bank (
            id INT AUTO_INCREMENT PRIMARY KEY,
            text TEXT NOT NULL,
            category VARCHAR(50) NOT NULL,
            difficulty VARCHAR(20) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

def ensure_table_resumes(cursor):
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS resumes (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_email VARCHAR(255) NOT NULL,
            candidate_name VARCHAR(255) NOT NULL,
            target_role VARCHAR(100) NOT NULL,
            ats_score INT NOT NULL,
            missing_keywords TEXT NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'Pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

def ensure_table_chat_logs(cursor):
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS chat_logs (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT,
            user_query TEXT,
            ai_response TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cursor.execute("SELECT COUNT(*) as c FROM chat_logs")
    if cursor.fetchone()[0] == 0:
        mocks = [
            (42, "What topics are covered in the React interview?", "React hooks, context API, and component lifecycle."),
            (89, "My microphone is not working.", "Please check browser permissions in site settings.")
        ]
        cursor.executemany("INSERT INTO chat_logs (user_id, user_query, ai_response) VALUES (%s, %s, %s)", mocks)

# DATABASE INIT
def init_db():
    db = get_db_connection()
    cursor = db.cursor()
    
    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            full_name VARCHAR(100) NOT NULL,
            email VARCHAR(100) UNIQUE NOT NULL,
            password VARCHAR(100) NOT NULL,
            field VARCHAR(100),
            role VARCHAR(20) DEFAULT 'user',
            location VARCHAR(100),
            bio TEXT,
            skills TEXT,
            level INT DEFAULT 1,
            xp INT DEFAULT 0,
            profile_photo VARCHAR(255),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Interviews table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS interviews (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_email VARCHAR(100),
            role VARCHAR(100),
            score INT,
            feedback TEXT,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    ensure_table_questions(cursor)
    ensure_table_resumes(cursor)
    ensure_table_chat_logs(cursor)
    
    db.commit()
    cursor.close()
    db.close()

init_db()

# LOGIN PAGE
@app.route("/")
def home():
    return render_template("login.html")

# REGISTER PAGE
@app.route("/register")
def register_page():
    return render_template("register.html")

# REGISTER
@app.route("/register", methods=["POST"])
def register():
    name = request.form.get("full_name")
    email = request.form.get("email")
    field = request.form.get("field")
    password = request.form.get("password")

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
    if cursor.fetchone():
        cursor.close()
        db.close()
        return "Email already exists"

    cursor.execute(
        "INSERT INTO users (full_name, email, field, password, role) VALUES (%s, %s, %s, %s, 'user')",
        (name, email, field, password)
    )
    db.commit()
    cursor.close()
    db.close()

    return redirect("/")

# LOGIN
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        cursor.execute(
            "SELECT * FROM users WHERE email=%s AND password=%s",
            (email, password)
        )
        user = cursor.fetchone()
        cursor.close()
        db.close()

        if user:
            session["user"] = user["full_name"]
            session["field"] = user["field"]
            session["email"] = user["email"]
            session["role"] = user.get("role", "user") # Get role from DB
            
            if session["role"] == "admin":
                return redirect("/admin/dashboard")
            return redirect("/dashboard")
        else:
            return "Invalid Email or Password"

    return redirect("/")

# DASHBOARD
@app.route("/dashboard")
def dashboard():
    if "user" in session:
        email = session.get("email")
        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        # 1. User Profile Section
        cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
        user_db_data = cursor.fetchone()
        
        user_profile = {
            "name": user_db_data["full_name"],
            "field": user_db_data.get("field") or "Not Specified",
            "profile_photo": user_db_data.get("profile_photo") or f"https://ui-avatars.com/api/?name={user_db_data['full_name']}&background=random",
            "level": user_db_data.get("level") or 1,
            "xp_percentage": (user_db_data.get("xp") or 0) % 100,
            "skills": user_db_data.get("skills").split(",") if user_db_data and user_db_data.get("skills") else []
        }

        # 2. Real Interview History
        cursor.execute("""
            SELECT role, score, feedback, DATE_FORMAT(date, '%b %d, %Y') as date_str 
            FROM interviews 
            WHERE user_email=%s 
            ORDER BY date DESC LIMIT 5
        """, (email,))
        db_history = cursor.fetchall()
        
        interview_history = []
        for item in db_history:
            interview_history.append({
                "date": item["date_str"],
                "role": item["role"],
                "score": item["score"],
                "feedback": item["feedback"][:50] + "..." if len(item["feedback"]) > 50 else item["feedback"]
            })

        # 3. Interview Stats (Real-time calculation)
        cursor.execute("SELECT COUNT(*) as total, AVG(score) as avg_score FROM interviews WHERE user_email=%s", (email,))
        stats_res = cursor.fetchone()
        
        total_ints = stats_res["total"] or 0
        avg_score = int(stats_res["avg_score"]) if stats_res["avg_score"] else 0
        
        # Calculate success rate (e.g., score > 70)
        cursor.execute("SELECT COUNT(*) as success FROM interviews WHERE user_email=%s AND score >= 70", (email,))
        success_count = cursor.fetchone()["success"] or 0
        success_rate = int((success_count / total_ints * 100)) if total_ints > 0 else 0

        interview_stats = {
            "avg_score": avg_score,
            "total_interviews": total_ints,
            "success_rate": success_rate,
            "confidence_level": "High" if avg_score > 80 else "Medium" if avg_score > 60 else "Low",
            "ai_recommendation": "Ready" if avg_score > 75 else "Practice More" if avg_score > 50 else "Focus on Basics"
        }

        # 4. Performance Analytics (Chart Data)
        cursor.execute("""
            SELECT DATE_FORMAT(date, '%b %d') as label, score 
            FROM interviews 
            WHERE user_email=%s 
            ORDER BY date ASC LIMIT 10
        """, (email,))
        chart_res = cursor.fetchall()
        
        performance_data = {
            "labels": [row["label"] for row in chart_res] if chart_res else ["Start"],
            "data": [row["score"] for row in chart_res] if chart_res else [0]
        }

        # 5. Leaderboard (Real-time based on all users)
        cursor.execute("""
            SELECT u.full_name as name, AVG(i.score) as avg_score 
            FROM users u 
            JOIN interviews i ON u.email = i.user_email 
            GROUP BY u.email 
            ORDER BY avg_score DESC LIMIT 5
        """)
        lb_res = cursor.fetchall()
        leaderboard = []
        for i, row in enumerate(lb_res):
            leaderboard.append({
                "rank": i + 1,
                "name": row["name"],
                "score": int(row["avg_score"])
            })

        # 6. Weekly Progress (Mocking goal for now, but counting real interviews)
        cursor.execute("SELECT COUNT(*) as weekly_count FROM interviews WHERE user_email=%s AND date >= DATE_SUB(NOW(), INTERVAL 7 DAY)", (email,))
        weekly_count = cursor.fetchone()["weekly_count"] or 0
        goal = 5
        weekly_progress = {
            "goal_percentage": int((weekly_count / goal) * 100) if weekly_count < goal else 100,
            "interviews_completed": weekly_count,
            "total_interviews": goal
        }

        # 7. Resume Analysis (Requirement 9)
        resume_analysis = {
            "match_score": 88,
            "last_updated": "Oct 28, 2026",
            "suggestions": ["Add more project metrics", "Highlight cloud experience"]
        }

        # 8. Practice Mode Topics (Requirement 7)
        practice_topics = [
            {"id": "dsa", "name": "DSA", "icon": "code-2", "questions": "500+"},
            {"id": "hr", "name": "HR & Behavioral", "icon": "users", "questions": "200+"},
            {"id": "aptitude", "name": "Aptitude", "icon": "brain", "questions": "300+"}
        ]

        improvement_plan = {
            "weak_areas": [
                "Technical: Deepen knowledge of **System Design Patterns** (Microservices vs Monolith).",
                "Communication: Reduce use of **filler words** (like 'um', 'actually') during long explanations.",
                "Behavioral: Use the **STAR method** more effectively for situational questions."
            ],
            "strong_areas": [
                "Confidence: Maintained excellent **eye contact** and steady tone throughout.",
                "Technical: Strong grasp of **React Component Lifecycle** and State Management.",
                "Logic: Clear and structured approach to **Problem Solving**."
            ]
        }

        # AI Agent Features Description
        ai_features = [
            {"title": "Question Engine", "desc": "Generates role-specific questions using NLP."},
            {"title": "Evaluation API", "desc": "Real-time keyword and sentiment scoring."},
            {"title": "Feedback Loop", "desc": "Context-aware improvement suggestions."}
        ]

        cursor.close()
        db.close()

        return render_template(
            "dashboard.html",
            user=user_profile,
            performance_data=performance_data,
            weekly_progress=weekly_progress,
            interview_history=interview_history,
            interview_stats=interview_stats,
            leaderboard=leaderboard,
            resume_analysis=resume_analysis,
            practice_topics=practice_topics,
            improvement_plan=improvement_plan,
            ai_features=ai_features
        )
    return redirect("/")

# RESUME PAGE
@app.route("/resume")
def resume_page():
    if "user" in session:
        email = session.get("email")
        db = get_db_connection()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
        user_data = cursor.fetchone()
        cursor.close()
        db.close()
        return render_template("resume.html", user=user_data)
    return redirect("/")

# INTERVIEW PAGE
@app.route("/interview")
def interview_page():
    if "user" in session:
        email = session.get("email")
        db = get_db_connection()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
        user_data = cursor.fetchone()
        cursor.close()
        db.close()
        return render_template("interview.html", user=user_data)
    return redirect("/")

# PROFILE PAGE
@app.route("/profile")
def profile_page():
    if "user" in session:
        email = session.get("email")
        db = get_db_connection()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
        user_data = cursor.fetchone()
        cursor.close()
        db.close()
        
        # Default skills if not set
        if not user_data.get("skills"):
            user_data["skills"] = "Python,React,SQL,Flask"
            
        return render_template("profile.html", user=user_data)
    return redirect("/")

# UPDATE PROFILE API
@app.route("/api/update-profile", methods=["POST"])
@login_required
def update_profile():
    email = session.get("email")
    data = request.json
    full_name = data.get("full_name")
    field = data.get("field")
    location = data.get("location")
    skills = data.get("skills")
    bio = data.get("bio")
    experience = data.get("experience")
    dream_company = data.get("dream_company")
    
    try:
        db = get_db_connection()
        cursor = db.cursor()
        
        # Check if columns exist, if not add them (basic migration)
        cols = ["location", "bio", "skills", "experience", "dream_company"]
        for col in cols:
            try:
                cursor.execute(f"ALTER TABLE users ADD COLUMN {col} TEXT")
            except:
                pass

        cursor.execute(
            """UPDATE users 
               SET full_name=%s, field=%s, location=%s, skills=%s, bio=%s, experience=%s, dream_company=%s 
               WHERE email=%s""",
            (full_name, field, location, skills, bio, experience, dream_company, email)
        )
        db.commit()
        cursor.close()
        db.close()
        
        # Update session name if changed
        session["user"] = full_name
        session["field"] = field
        
        return jsonify({"status": "success", "message": "Profile updated successfully"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

# MOCK INTERVIEW PAGE
@app.route("/mock-interview")
def mock_interview_page():
    if "user" in session:
        email = session.get("email")
        db = get_db_connection()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
        user_data = cursor.fetchone()
        cursor.close()
        db.close()
        
        # 20+ Companies list
        companies = [
            {"name": "Google", "role": "Software Engineer", "match": "98%", "logo": "cpu"},
            {"name": "Microsoft", "role": "Frontend Developer", "match": "94%", "logo": "cloud"},
            {"name": "Amazon", "role": "SDE-1", "match": "89%", "logo": "shopping-bag"},
            {"name": "Meta", "role": "Product Engineer", "match": "92%", "logo": "layers"},
            {"name": "Apple", "role": "iOS Developer", "match": "88%", "logo": "smartphone"},
            {"name": "Netflix", "role": "Backend Engineer", "match": "85%", "logo": "tv"},
            {"name": "Adobe", "role": "UI/UX Designer", "match": "91%", "logo": "pen-tool"},
            {"name": "TCS", "role": "Full Stack Developer", "match": "85%", "logo": "database"},
            {"name": "Infosys", "role": "Systems Engineer", "match": "82%", "logo": "monitor"},
            {"name": "Wipro", "role": "Associate Consultant", "match": "80%", "logo": "briefcase"},
            {"name": "Uber", "role": "Full Stack Engineer", "match": "93%", "logo": "car"},
            {"name": "Zomato", "role": "Product Manager", "match": "87%", "logo": "utensils"},
            {"name": "Flipkart", "role": "Supply Chain Analyst", "match": "84%", "logo": "truck"},
            {"name": "Salesforce", "role": "CRM Developer", "match": "90%", "logo": "cloud-lightning"},
            {"name": "Atlassian", "role": "Cloud Architect", "match": "95%", "logo": "server"},
            {"name": "IBM", "role": "Data Scientist", "match": "86%", "logo": "binary"},
            {"name": "Oracle", "role": "Database Administrator", "match": "89%", "logo": "hard-drive"},
            {"name": "Intel", "role": "Hardware Engineer", "match": "83%", "logo": "microchip"},
            {"name": "Nvidia", "role": "Graphics Engineer", "match": "96%", "logo": "zap"},
            {"name": "Cisco", "role": "Network Engineer", "match": "81%", "logo": "wifi"}
        ]
        
        return render_template("mock_interview.html", user=user_data, companies=companies)
    return redirect("/")

# RESULTS PAGE (Feedback & Score)
@app.route("/results")
@login_required
def results_page():
    email = session.get("email")
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    
    # Fetch the latest interview result for this user
    cursor.execute("SELECT * FROM interviews WHERE user_email=%s ORDER BY date DESC LIMIT 1", (email,))
    latest_interview = cursor.fetchone()
    
    if latest_interview:
        try:
            feedback_data = json.loads(latest_interview["feedback"])
            score = feedback_data.get("score", 0)
            strong_topics = feedback_data.get("strong_topics", ["N/A"])
            weak_topics = feedback_data.get("weak_topics", ["N/A"])
            overall_feedback = feedback_data.get("overall_feedback", "Great job!")
        except:
            score = latest_interview["score"]
            strong_topics = ["N/A"]
            weak_topics = ["N/A"]
            overall_feedback = latest_interview["feedback"]
    else:
        score = 0
        strong_topics = []
        weak_topics = []
        overall_feedback = "No interviews completed yet. Start your first session to see analytics!"
        
    feedback = {
        "score": score,
        "strong_topics": strong_topics,
        "weak_topics": weak_topics,
        "overall_feedback": overall_feedback
    }
    
    # Fetch user data for sidebar
    cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
    user_data = cursor.fetchone()
    
    cursor.close()
    db.close()
    return render_template("results.html", feedback=feedback, user=user_data)

@app.route("/api/analyze-resume", methods=["POST"])
@login_required
def analyze_resume():
    if "resume" not in request.files:
        return jsonify({"status": "error", "message": "No resume file provided"}), 400

    resume_file = request.files["resume"]
    if resume_file.filename == "":
        return jsonify({"status": "error", "message": "No selected file"}), 400

    # In a real app, use PyPDF2 or similar to extract text. 
    # For now, we simulate extraction and analysis.
    resume_content = resume_file.read().decode("utf-8", errors="ignore").lower()

    # Calculate ATS Score based on keywords and length
    base_score = 65
    keywords = ["python", "flask", "sql", "react", "javascript", "aws", "docker", "kubernetes", "api", "machine learning", "ai", "git", "agile"]
    found_keywords = [kw for kw in keywords if kw in resume_content]
    
    ats_score = base_score + (len(found_keywords) * 3)
    if len(resume_content) > 1000: ats_score += 5
    ats_score = min(ats_score, 98)

    # Missing Keywords
    missing_keywords = [kw.capitalize() for kw in keywords if kw not in resume_content][:5]

    # Suggestions
    suggestions = [
        "Quantify your achievements using the STAR method (Situation, Task, Action, Result).",
        f"Consider adding more keywords like {', '.join(missing_keywords[:2])} to improve ATS visibility.",
        "Ensure your contact information and LinkedIn profile are clearly visible.",
        "Use a clean, professional template that is easy for AI parsers to read."
    ]

    # Company Suggestions based on keywords
    all_companies = [
        {"name": "Google", "role": "Software Engineer", "logo": "cpu", "match": "95%", "min_score": 90},
        {"name": "Microsoft", "role": "Full Stack Developer", "logo": "cloud", "match": "92%", "min_score": 85},
        {"name": "Amazon", "role": "SDE-1", "logo": "shopping-bag", "match": "88%", "min_score": 80},
        {"name": "Meta", "role": "Product Engineer", "logo": "layers", "match": "94%", "min_score": 88},
        {"name": "Netflix", "role": "Backend Engineer", "logo": "tv", "match": "85%", "min_score": 82},
        {"name": "TCS", "role": "System Engineer", "logo": "database", "match": "80%", "min_score": 60},
        {"name": "Infosys", "role": "Associate Consultant", "logo": "monitor", "match": "78%", "min_score": 55}
    ]
    
    suggested_companies = [c for c in all_companies if ats_score >= c["min_score"] - 10][:4]

    # Update user's skills in DB if found
    email = session.get("email")
    if found_keywords:
        db = get_db_connection()
        cursor = db.cursor()
        skills_str = ",".join([kw.capitalize() for kw in found_keywords])
        cursor.execute("UPDATE users SET skills=%s WHERE email=%s", (skills_str, email))
        db.commit()
        cursor.close()
        db.close()

    return jsonify({
        "status": "success",
        "scores": {
            "ats_score": ats_score,
            "readability": random.randint(75, 95),
            "impact": random.randint(70, 90)
        },
        "missing_keywords": missing_keywords,
        "suggestions": suggestions,
        "companies": suggested_companies
    })

@app.route("/api/mcq-questions")
@login_required
def get_mcq_questions():
    category = request.args.get("category", "All")
    difficulty = request.args.get("difficulty", "All")
    
    filtered = MCQ_DATASET
    if category != "All":
        filtered = [q for q in filtered if q["category"] == category]
    if difficulty != "All":
        filtered = [q for q in filtered if q["difficulty"] == difficulty]
    
    # Return 10 random questions
    questions = random.sample(filtered, min(10, len(filtered)))
    return jsonify(questions)
@app.route("/api/get-question")
def get_ai_question():
    role = (request.args.get("role") or session.get("field") or "Software Engineer").strip()
    interview_type = (request.args.get("category") or "Technical").strip()
    difficulty_raw = (request.args.get("difficulty") or "Medium").strip()
    exclude_raw = (request.args.get("exclude") or "").strip()

    category_map = {
        "Technical": "Role-based",
        "HR": "HR",
        "Managerial": "HR",
        "Mixed": "All",
    }
    difficulty_map = {
        "Easy": "Beginner",
        "Medium": "Intermediate",
        "Hard": "Advanced",
        "Beginner": "Beginner",
        "Intermediate": "Intermediate",
        "Advanced": "Advanced",
    }
    mapped_category = category_map.get(interview_type, "All")
    mapped_difficulty = difficulty_map.get(difficulty_raw, "Intermediate")

    exclude_ids = []
    if exclude_raw:
        for part in exclude_raw.split(","):
            part = part.strip()
            if part.isdigit():
                exclude_ids.append(int(part))

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    ensure_table_questions(cursor)
    db.commit()

    cursor.execute("SELECT COUNT(*) as total FROM question_bank")
    total = cursor.fetchone()["total"]
    if total == 0:
        seed = [
            ("Explain time complexity of binary search.", "DSA", "Beginner"),
            ("Solve: Two Sum. Explain approach and trade-offs.", "DSA", "Beginner"),
            ("Solve: Merge Intervals. Explain edge cases and complexity.", "DSA", "Intermediate"),
            ("Explain BFS vs DFS and when to use each.", "DSA", "Intermediate"),
            ("Design a rate limiter for an API.", "Role-based", "Advanced"),
            ("Design an authentication system with refresh tokens.", "Role-based", "Intermediate"),
            ("How do you optimize a slow SQL query? Walk through your approach.", "Role-based", "Intermediate"),
            ("Explain caching strategies for a high-traffic application.", "Role-based", "Intermediate"),
            ("What are indexes in MySQL and when do they hurt performance?", "Role-based", "Intermediate"),
            ("Tell me about a time you handled conflict in a team.", "HR", "Intermediate"),
            ("Tell me about a failure and what you learned from it.", "HR", "Beginner"),
            ("How do you handle conflicting priorities?", "HR", "Intermediate"),
            ("A train crosses a pole in 12 seconds at 54 km/h. Find its length.", "Aptitude", "Beginner"),
            ("Probability: Two dice are rolled. What is the probability of sum 9?", "Aptitude", "Intermediate"),
            ("If 5 workers finish a task in 12 days, how long will 8 workers take?", "Aptitude", "Beginner"),
        ]
        cursor.executemany(
            "INSERT INTO question_bank (text, category, difficulty) VALUES (%s, %s, %s)",
            seed,
        )
        db.commit()

    query_str = "SELECT id, text, category, difficulty FROM question_bank"
    conditions = []
    params = []

    if mapped_category != "All":
        conditions.append("category=%s")
        params.append(mapped_category)
    if mapped_difficulty and mapped_difficulty != "All":
        conditions.append("difficulty=%s")
        params.append(mapped_difficulty)
    if exclude_ids:
        placeholders = ", ".join(["%s"] * len(exclude_ids))
        conditions.append(f"id NOT IN ({placeholders})")
        params.extend(exclude_ids)

    if conditions:
        query_str += " WHERE " + " AND ".join(conditions)
    query_str += " ORDER BY RAND() LIMIT 1"

    cursor.execute(query_str, tuple(params))
    row = cursor.fetchone()
    cursor.close()
    db.close()

    if row:
        return jsonify(
            {
                "status": "success",
                "question": {
                    "id": row["id"],
                    "text": row["text"],
                    "category": row["category"],
                    "difficulty": row["difficulty"],
                }
            }
        )

    fallback_questions = [
        f"Tell me about a time you had to solve a complex {role} challenge.",
        f"How do you stay updated with the latest trends in {role}?",
        f"Explain a difficult technical problem you solved recently as a {role}.",
        "What is your approach to teamwork in a fast-paced environment?",
        f"Why do you want to join this company as a {role}?",
        "What are your greatest strengths and how do they apply to this role?",
        "Can you describe a situation where you had to work with a difficult team member?",
        "How do you handle pressure and tight deadlines?",
        f"Where do you see yourself in five years as a {role}?",
    ]
    q = random.choice(fallback_questions)
    return jsonify({
        "status": "success", 
        "question": {
            "id": random.randint(1000, 9999),
            "text": q,
            "category": "Fallback", 
            "difficulty": mapped_difficulty
        }
    })

@app.route("/api/submit-answer", methods=["POST"])
@login_required
def submit_answer():
    data = request.get_json()
    if not data or "answer" not in data:
        return jsonify({"status": "error", "message": "Invalid request"}), 400

    user_answer = data.get("answer", "").strip()
    question_id = data.get("question_id")
    
    # Real-ish analysis
    word_count = len(user_answer.split())
    
    # Check for keywords related to tech
    tech_keywords = ["code", "design", "pattern", "system", "scale", "optimize", "test", "debug", "deploy", "cloud", "database"]
    found_tech = [w for w in tech_keywords if w in user_answer.lower()]
    
    # Scoring logic
    clarity = min(40 + (word_count // 2), 95) if word_count > 10 else 30
    relevance = min(50 + (len(found_tech) * 10), 98)
    confidence = random.randint(60, 95)

    observation = ""
    if word_count < 20:
        observation = "Your answer is a bit short. Try to elaborate more on your thought process."
    elif len(found_tech) < 2:
        observation = "Good start, but try to include more technical terminology related to the question."
    else:
        observation = "Excellent depth! You covered the technical aspects very well."

    return jsonify({
        "status": "success",
        "feedback": {
            "observation": observation,
            "scores": {
                "clarity": clarity,
                "relevance": relevance,
                "confidence": confidence
            }
        }
    })

# SAVE INTERVIEW RESULT API
@app.route("/api/save-interview", methods=["POST"])
@login_required
def save_interview():
    email = session.get("email")
    data = request.get_json()

    interview_details = data.get("interview_details", {})
    results_summary = data.get("results_summary", {})

    role = interview_details.get("role", "Software Engineer")
    score = results_summary.get("final_score", 0)
    
    # Extract strong and weak topics from feedback
    feedback_list = results_summary.get("feedback", [])
    
    # Mocking strong/weak topics based on scores
    strong_topics = ["Professionalism", "Problem Solving"]
    weak_topics = ["Technical Depth"]
    
    if score > 85:
        strong_topics.append("System Architecture")
    else:
        weak_topics.append("Optimization")

    full_feedback = {
        "score": score,
        "strong_topics": strong_topics,
        "weak_topics": weak_topics,
        "overall_feedback": f"Completed {role} interview with a score of {score}%."
    }

    try:
        db = get_db_connection()
        cursor = db.cursor()
        cursor.execute(
            "INSERT INTO interviews (user_email, role, score, feedback) VALUES (%s, %s, %s, %s)",
            (email, role, score, json.dumps(full_feedback))
        )
        db.commit()
        cursor.close()
        db.close()

        return jsonify({"status": "success", "message": "Interview saved successfully"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# LOGOUT
@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect("/")

@app.route("/admin/dashboard")
def admin_dashboard():
    if "user" not in session or session.get("role") != "admin":
        return redirect("/")

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    # 1. Real Stats
    cursor.execute("SELECT COUNT(*) as total FROM users WHERE role='user'")
    total_candidates = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) as total, AVG(score) as avg_score FROM interviews")
    int_stats = cursor.fetchone()
    total_interviews = int_stats["total"] or 0
    avg_score = int(int_stats["avg_score"]) if int_stats["avg_score"] else 0

    cursor.execute("SELECT COUNT(*) as success FROM interviews WHERE score >= 70")
    success_count = cursor.fetchone()["success"] or 0
    selection_rate = int((success_count / total_interviews * 100)) if total_interviews > 0 else 0

    # 2. Real Candidate List (Latest 10 users)
    cursor.execute("""
        SELECT u.id, u.full_name as name, u.field as role, 
        COALESCE(AVG(i.score), 0) as score,
        CASE 
            WHEN AVG(i.score) >= 80 THEN 'Selected'
            WHEN AVG(i.score) >= 70 THEN 'Shortlisted'
            WHEN AVG(i.score) > 0 THEN 'Pending'
            ELSE 'New'
        END as status
        FROM users u
        LEFT JOIN interviews i ON u.email = i.user_email
        WHERE u.role = 'user'
        GROUP BY u.id, u.full_name, u.field
        ORDER BY u.id DESC
        LIMIT 10
    """)
    candidates = cursor.fetchall()

    # 3. Real Recent Activity
    cursor.execute("""
        (SELECT 'interview' as type, CONCAT('Candidate ', user_email, ' completed ', role, ' Interview') as event, 
        DATE_FORMAT(date, '%M %d, %H:%i') as time, date as sort_date
        FROM interviews)
        UNION
        (SELECT 'registration' as type, CONCAT('New candidate registered: ', full_name) as event,
        'Just now' as time, NOW() as sort_date
        FROM users WHERE role='user' AND id > (SELECT MAX(id)-5 FROM users))
        ORDER BY sort_date DESC
        LIMIT 10
    """)
    recent_activity = cursor.fetchall()

    # 4. Hiring Trends (Real data grouped by month)
    cursor.execute("""
        SELECT DATE_FORMAT(date, '%b') as label, COUNT(*) as count 
        FROM interviews 
        GROUP BY label, DATE_FORMAT(date, '%m')
        ORDER BY DATE_FORMAT(date, '%m') ASC
    """)
    trends_res = cursor.fetchall()
    hiring_trends = {
        "labels": [row["label"] for row in trends_res] if trends_res else ["Jan", "Feb", "Mar"],
        "data": [row["count"] for row in trends_res] if trends_res else [0, 0, 0]
    }

    admin_data = {
        "stats": {
            "total_candidates": total_candidates,
            "total_interviews": total_interviews,
            "selection_rate": selection_rate,
            "avg_score": avg_score
        },
        "candidates": candidates,
        "hiring_trends": hiring_trends,
        "recent_activity": recent_activity
    }
    
    cursor.close()
    db.close()
    return render_template("admin_dashboard.html", data=admin_data)

@app.route("/admin/api/users")
def admin_api_users():
    if "user" not in session or session.get("role") != "admin":
        return jsonify({"error": "Unauthorized"}), 401
    
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    
    # Check if status column exists, if not create it
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN status VARCHAR(20) DEFAULT 'active'")
        db.commit()
    except Exception:
        pass # Column already exists
        
    cursor.execute("""
        SELECT u.id, u.full_name as name, u.email, u.field as field, u.role, u.status,
        COALESCE(AVG(i.score), 0) as score
        FROM users u
        LEFT JOIN interviews i ON u.email = i.user_email
        GROUP BY u.id, u.full_name, u.email, u.field, u.role, u.status
        ORDER BY u.id DESC
    """)
    users = cursor.fetchall()
    cursor.close()
    db.close()
    return jsonify(users)

@app.route("/admin/api/users/<int:user_id>/role", methods=["POST"])
def admin_api_user_role(user_id):
    if "user" not in session or session.get("role") != "admin":
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.json
    new_role = data.get("role")
    if new_role not in ["admin", "user"]:
        return jsonify({"error": "Invalid role"}), 400

    db = get_db_connection()
    cursor = db.cursor()
    cursor.execute("UPDATE users SET role=%s WHERE id=%s", (new_role, user_id))
    db.commit()
    cursor.close()
    db.close()
    return jsonify({"success": True})

@app.route("/admin/api/users/<int:user_id>/status", methods=["POST"])
def admin_api_user_status(user_id):
    if "user" not in session or session.get("role") != "admin":
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.json
    new_status = data.get("status")
    if new_status not in ["active", "blocked"]:
        return jsonify({"error": "Invalid status"}), 400

    db = get_db_connection()
    cursor = db.cursor()
    cursor.execute("UPDATE users SET status=%s WHERE id=%s", (new_status, user_id))
    db.commit()
    cursor.close()
    db.close()
    return jsonify({"success": True})

@app.route("/admin/api/users/<int:user_id>", methods=["DELETE"])
def admin_api_user_delete(user_id):
    if "user" not in session or session.get("role") != "admin":
        return jsonify({"error": "Unauthorized"}), 401

    db = get_db_connection()
    cursor = db.cursor()
    cursor.execute("DELETE FROM users WHERE id=%s", (user_id,))
    db.commit()
    cursor.close()
    db.close()
    return jsonify({"success": True})

@app.route("/admin/api/questions", methods=["GET"])
def admin_api_questions_list():
    if "user" not in session or session.get("role") != "admin":
        return jsonify({"error": "Unauthorized"}), 401

    category = request.args.get("category")
    difficulty = request.args.get("difficulty")
    q = request.args.get("q")

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    ensure_table_questions(cursor)
    db.commit()

    cursor.execute("SELECT COUNT(*) as total FROM question_bank")
    total = cursor.fetchone()["total"]
    if total == 0:
        seed = [
            ("Explain time complexity of binary search.", "DSA", "Beginner"),
            ("Design a rate limiter for an API.", "Role-based", "Advanced"),
            ("Tell me about a time you handled conflict in a team.", "HR", "Intermediate"),
            ("Solve: Two Sum. Explain approach and trade-offs.", "DSA", "Beginner"),
            ("What are indexes in MySQL and when do they hurt performance?", "Role-based", "Intermediate"),
        ]
        cursor.executemany(
            "INSERT INTO question_bank (text, category, difficulty) VALUES (%s, %s, %s)",
            seed,
        )
        db.commit()

    query_str = "SELECT id, text, category, difficulty, DATE_FORMAT(created_at, '%%b %%d, %%Y') as created_at FROM question_bank"
    conditions = []
    params = []
    
    if category and category != "All":
        conditions.append("category=%s")
        params.append(category)
    if difficulty and difficulty != "All":
        conditions.append("difficulty=%s")
        params.append(difficulty)
    if q:
        conditions.append("text LIKE %s")
        params.append(f"%{q}%")

    if conditions:
        query_str += " WHERE " + " AND ".join(conditions)
        
    query_str += " ORDER BY id DESC"

    cursor.execute(query_str, tuple(params))
    questions = cursor.fetchall()
    cursor.close()
    db.close()
    return jsonify(questions)

@app.route("/admin/api/questions/stats", methods=["GET"])
def admin_api_questions_stats():
    if "user" not in session or session.get("role") != "admin":
        return jsonify({"error": "Unauthorized"}), 401

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    ensure_table_questions(cursor)
    db.commit()

    cursor.execute("SELECT COUNT(*) as total FROM question_bank")
    total = cursor.fetchone()["total"] or 0

    cursor.execute("SELECT category, COUNT(*) as count FROM question_bank GROUP BY category ORDER BY category ASC")
    by_category = cursor.fetchall()

    cursor.execute("SELECT difficulty, COUNT(*) as count FROM question_bank GROUP BY difficulty ORDER BY difficulty ASC")
    by_difficulty = cursor.fetchall()

    cursor.close()
    db.close()
    return jsonify({"total": total, "by_category": by_category, "by_difficulty": by_difficulty})

@app.route("/admin/api/questions", methods=["POST"])
def admin_api_questions_create():
    if "user" not in session or session.get("role") != "admin":
        return jsonify({"error": "Unauthorized"}), 401

    payload = request.get_json(silent=True) or {}
    text = (payload.get("text") or "").strip()
    category = (payload.get("category") or "").strip()
    difficulty = (payload.get("difficulty") or "").strip()

    if not text or not category or not difficulty:
        return jsonify({"error": "Missing fields"}), 400

    db = get_db_connection()
    cursor = db.cursor()
    ensure_table_questions(cursor)
    cursor.execute(
        "INSERT INTO question_bank (text, category, difficulty) VALUES (%s, %s, %s)",
        (text, category, difficulty),
    )
    db.commit()
    new_id = cursor.lastrowid
    cursor.close()
    db.close()
    return jsonify({"success": True, "id": new_id})

@app.route("/admin/api/questions/bulk", methods=["POST"])
def admin_api_questions_bulk_create():
    if "user" not in session or session.get("role") != "admin":
        return jsonify({"error": "Unauthorized"}), 401

    payload = request.get_json(silent=True)
    if payload is None:
        return jsonify({"error": "Invalid JSON"}), 400

    items = []
    if isinstance(payload, list):
        items = payload
    elif isinstance(payload, dict):
        bulk_items = payload.get("items")
        if isinstance(bulk_items, str):
            bulk_items = [line.strip() for line in bulk_items.splitlines() if line.strip()]
        if isinstance(bulk_items, list):
            category = (payload.get("category") or "").strip()
            difficulty = (payload.get("difficulty") or "").strip()
            for t in bulk_items:
                if isinstance(t, str):
                    items.append({"text": t, "category": category, "difficulty": difficulty})
                elif isinstance(t, dict):
                    items.append(t)
        else:
            return jsonify({"error": "Invalid items"}), 400
    else:
        return jsonify({"error": "Invalid payload"}), 400

    normalized = []
    for it in items[:200]:
        if not isinstance(it, dict):
            continue
        text = (it.get("text") or it.get("question") or "").strip()
        category = (it.get("category") or "").strip()
        difficulty = (it.get("difficulty") or "").strip()
        if not text or not category or not difficulty:
            continue
        normalized.append((text, category, difficulty))

    if not normalized:
        return jsonify({"error": "No valid items"}), 400

    db = get_db_connection()
    cursor = db.cursor()
    ensure_table_questions(cursor)
    cursor.executemany(
        "INSERT INTO question_bank (text, category, difficulty) VALUES (%s, %s, %s)",
        normalized,
    )
    db.commit()
    inserted = cursor.rowcount or len(normalized)
    cursor.close()
    db.close()
    return jsonify({"success": True, "inserted": inserted})

@app.route("/admin/api/questions/<int:question_id>", methods=["PUT"])
def admin_api_questions_update(question_id):
    if "user" not in session or session.get("role") != "admin":
        return jsonify({"error": "Unauthorized"}), 401

    payload = request.get_json(silent=True) or {}
    text = (payload.get("text") or "").strip()
    category = (payload.get("category") or "").strip()
    difficulty = (payload.get("difficulty") or "").strip()

    if not text or not category or not difficulty:
        return jsonify({"error": "Missing fields"}), 400

    db = get_db_connection()
    cursor = db.cursor()
    ensure_table_questions(cursor)
    cursor.execute(
        "UPDATE question_bank SET text=%s, category=%s, difficulty=%s WHERE id=%s",
        (text, category, difficulty, question_id),
    )
    db.commit()
    cursor.close()
    db.close()
    return jsonify({"success": True})

@app.route("/admin/api/questions/<int:question_id>", methods=["DELETE"])
def admin_api_questions_delete(question_id):
    if "user" not in session or session.get("role") != "admin":
        return jsonify({"error": "Unauthorized"}), 401

    db = get_db_connection()
    cursor = db.cursor()
    ensure_table_questions(cursor)
    cursor.execute("DELETE FROM question_bank WHERE id=%s", (question_id,))
    db.commit()
    cursor.close()
    db.close()
    return jsonify({"success": True})

@app.route("/admin/api/questions/generate", methods=["POST"])
def admin_api_questions_generate():
    if "user" not in session or session.get("role") != "admin":
        return jsonify({"error": "Unauthorized"}), 401

    payload = request.get_json(silent=True) or {}
    category = (payload.get("category") or "Role-based").strip()
    difficulty = (payload.get("difficulty") or "Intermediate").strip()

    templates = {
        "DSA": [
            "Solve: Longest Substring Without Repeating Characters. Explain complexity.",
            "Solve: Merge Intervals. Explain edge cases and time complexity.",
            "Explain BFS vs DFS and when to use each.",
        ],
        "HR": [
            "Tell me about a failure and what you learned from it.",
            "Describe a time you took ownership in a critical situation.",
            "How do you handle conflicting priorities?",
        ],
        "Aptitude": [
            "If 5 workers finish a task in 12 days, how long will 8 workers take?",
            "A train crosses a pole in 12 seconds at 54 km/h. Find its length.",
            "Probability: Two dice are rolled. What is the probability of sum 9?",
        ],
        "Role-based": [
            "Explain how you would design an authentication system with refresh tokens.",
            "How do you optimize a slow SQL query? Walk through your approach.",
            "Explain caching strategies for a high-traffic application.",
        ],
    }

    pool = templates.get(category, templates["Role-based"])
    text = random.choice(pool)

    db = get_db_connection()
    cursor = db.cursor()
    ensure_table_questions(cursor)
    cursor.execute(
        "INSERT INTO question_bank (text, category, difficulty) VALUES (%s, %s, %s)",
        (text, category, difficulty),
    )
    db.commit()
    new_id = cursor.lastrowid
    cursor.close()
    db.close()
    return jsonify({"success": True, "id": new_id, "text": text, "category": category, "difficulty": difficulty})

@app.route("/admin/api/stats")
def admin_api_stats():
    if "user" not in session or session.get("role") != "admin":
        return jsonify({"error": "Unauthorized"}), 401
    
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT COUNT(*) as total FROM users WHERE role='user'")
    total_users = cursor.fetchone()["total"]
    
    cursor.execute("SELECT COUNT(*) as active FROM users WHERE status='active' AND role='user'")
    active_users = cursor.fetchone()["active"]

    cursor.execute("SELECT COUNT(*) as total, AVG(score) as avg_score FROM interviews")
    int_stats = cursor.fetchone()
    
    cursor.execute("""
        SELECT DATE_FORMAT(date, '%b') as label, COUNT(*) as count 
        FROM interviews 
        GROUP BY label, DATE_FORMAT(date, '%m')
        ORDER BY DATE_FORMAT(date, '%m') ASC
    """)
    trends_res = cursor.fetchall()
    
    cursor.close()
    db.close()
    
    return jsonify({
        "total_users": total_users,
        "active_users": active_users,
        "total_interviews": int_stats["total"] or 0,
        "avg_score": int(int_stats["avg_score"]) if int_stats["avg_score"] else 0,
        "trends": {
            "labels": [row["label"] for row in trends_res] if trends_res else ["Jan", "Feb", "Mar"],
            "data": [row["count"] for row in trends_res] if trends_res else [0, 0, 0]
        }
    })

@app.route("/admin/api/resumes")
def admin_api_resumes():
    if "user" not in session or session.get("role") != "admin":
        return jsonify({"error": "Unauthorized"}), 401

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    ensure_table_resumes(cursor)
    db.commit()

    cursor.execute("SELECT COUNT(*) as total FROM resumes")
    total = cursor.fetchone()["total"]
    if total == 0:
        cursor.execute("SELECT full_name, email, field FROM users WHERE role='user' ORDER BY id DESC LIMIT 10")
        recent_users = cursor.fetchall()
        seed_source = recent_users if recent_users else [
            {"full_name": "Alice Johnson", "email": "alice@example.com", "field": "Frontend"},
            {"full_name": "Bob Smith", "email": "bob@example.com", "field": "Backend"},
            {"full_name": "Charlie Brown", "email": "charlie@example.com", "field": "Data Science"},
        ]
        keyword_pools = {
            "Frontend": ["Redux", "Webpack", "TypeScript", "Testing", "Performance"],
            "Backend": ["Docker", "Kubernetes", "Caching", "Indexes", "Queues"],
            "Data Science": ["NLP", "Feature Engineering", "Model Monitoring", "Statistics", "Pandas"],
        }
        rows = []
        for u in seed_source[:3]:
            role = u.get("field") or "Role-based"
            pool = keyword_pools.get(role, ["System Design", "Testing", "Cloud"])
            missing = random.sample(pool, k=min(2, len(pool)))
            rows.append(
                (
                    u.get("email") or "unknown@example.com",
                    u.get("full_name") or "Candidate",
                    role,
                    random.randint(60, 95),
                    ",".join(missing),
                    random.choice(["Pending", "Reviewed"]),
                )
            )
        cursor.executemany(
            "INSERT INTO resumes (user_email, candidate_name, target_role, ats_score, missing_keywords, status) VALUES (%s, %s, %s, %s, %s, %s)",
            rows,
        )
        db.commit()

    cursor.execute(
        "SELECT id, candidate_name as candidate, target_role as role, ats_score, missing_keywords, status FROM resumes ORDER BY id DESC"
    )
    resumes = cursor.fetchall()
    for r in resumes:
        r["missing_keys"] = [k for k in (r.get("missing_keywords") or "").split(",") if k]
        r.pop("missing_keywords", None)

    cursor.close()
    db.close()
    return jsonify(resumes)

@app.route("/admin/api/resumes/keyword-trends")
def admin_api_resumes_keyword_trends():
    if "user" not in session or session.get("role") != "admin":
        return jsonify({"error": "Unauthorized"}), 401

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    ensure_table_resumes(cursor)
    db.commit()

    cursor.execute("SELECT missing_keywords, ats_score FROM resumes")
    rows = cursor.fetchall()
    counts = {}
    total_score = 0
    total_processed = len(rows)
    for row in rows:
        total_score += row.get("ats_score", 0)
        keys = [k.strip() for k in (row.get("missing_keywords") or "").split(",") if k.strip()]
        for k in keys:
            counts[k] = counts.get(k, 0) + 1

    avg_score = int(total_score / total_processed) if total_processed > 0 else 0
    top = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:8]
    top_keyword = top[0][0] if top else "None"
    cursor.close()
    db.close()
    return jsonify({
        "avg_score": avg_score,
        "total_processed": total_processed,
        "top_keyword": top_keyword,
        "chart": {
            "labels": [t[0] for t in top],
            "data": [t[1] for t in top]
        }
    })

@app.route("/admin/api/resumes/<int:resume_id>/recalculate", methods=["POST"])
def admin_api_resumes_recalculate(resume_id):
    if "user" not in session or session.get("role") != "admin":
        return jsonify({"error": "Unauthorized"}), 401

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    ensure_table_resumes(cursor)
    db.commit()

    cursor.execute("SELECT target_role FROM resumes WHERE id=%s", (resume_id,))
    row = cursor.fetchone()
    if not row:
        cursor.close()
        db.close()
        return jsonify({"error": "Not found"}), 404

    role = row.get("target_role") or "Role-based"
    keyword_pools = {
        "Frontend": ["Redux", "Webpack", "TypeScript", "Testing", "Performance", "Accessibility"],
        "Backend": ["Docker", "Kubernetes", "Caching", "Indexes", "Queues", "Observability"],
        "Data Science": ["NLP", "Feature Engineering", "Model Monitoring", "Statistics", "Pandas", "ML Ops"],
    }
    pool = keyword_pools.get(role, ["System Design", "Testing", "Cloud", "Security", "CI/CD"])
    missing = random.sample(pool, k=min(3, len(pool)))
    new_score = random.randint(55, 96)

    cursor2 = db.cursor()
    cursor2.execute(
        "UPDATE resumes SET ats_score=%s, missing_keywords=%s, status=%s WHERE id=%s",
        (new_score, ",".join(missing), "Reviewed", resume_id),
    )
    db.commit()
    cursor2.close()
    cursor.close()
    db.close()
    return jsonify({"success": True, "ats_score": new_score, "missing_keys": missing, "status": "Reviewed"})

@app.route("/admin/api/analytics")
def admin_api_analytics():
    if "user" not in session or session.get("role") != "admin":
        return jsonify({"error": "Unauthorized"}), 401
    
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT u.full_name as name, AVG(i.score) as score, u.field as role
        FROM users u JOIN interviews i ON u.email = i.user_email
        WHERE u.role = 'user' GROUP BY u.id, u.full_name, u.field
        ORDER BY score DESC LIMIT 5
    """)
    leaderboard = cursor.fetchall()
    
    cursor.execute("SELECT role, COUNT(*) as count FROM interviews GROUP BY role ORDER BY count DESC LIMIT 3")
    popular_roles = cursor.fetchall()
    
    cursor.close()
    db.close()
    
    return jsonify({
        "leaderboard": [{"name": l["name"], "score": int(l["score"]), "role": l["role"]} for l in leaderboard],
        "popular_roles": [{"role": p["role"], "count": p["count"]} for p in popular_roles]
    })

@app.route("/admin/api/health")
def admin_api_health():
    if "user" not in session or session.get("role") != "admin":
        return jsonify({"error": "Unauthorized"}), 401
    
    return jsonify({
        "cpu": random.randint(30, 75),
        "ram": random.randint(40, 85),
        "api_latency": random.randint(120, 300),
        "errors": [
            {"time": "10:42 AM", "module": "Database", "msg": "Connection timeout retry 1"},
            {"time": "09:15 AM", "module": "AI Gen", "msg": "OpenAI API rate limit warning"},
            {"time": "08:30 AM", "module": "Auth", "msg": "Failed login attempt (IP: 192.168.1.5)"}
        ]
    })


@app.route("/admin/api/sessions")
def admin_api_sessions():
    if "user" not in session or session.get("role") != "admin":
        return jsonify({"error": "Unauthorized"}), 401
    
    # Mock sessions for now, can be connected to a 'sessions' table later
    sessions = [
        {"id": 1, "name": "Q2 Recruitment", "target": "Senior Frontend Devs", "duration": "45 Minutes", "flow": "Adaptive", "status": "Active"},
        {"id": 2, "name": "Campus Drive 2026", "target": "Graduate Trainees", "duration": "30 Minutes", "flow": "Linear", "status": "Scheduled"}
    ]
    return jsonify(sessions)

@app.route("/admin/api/settings", methods=["GET", "POST"])
def admin_api_settings():
    if "user" not in session or session.get("role") != "admin":
        return jsonify({"error": "Unauthorized"}), 401
    
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    ensure_table_settings(cursor)
    db.commit()

    if request.method == "POST":
        data = request.json
        for key, value in data.items():
            cursor.execute("UPDATE settings SET setting_value=%s WHERE setting_key=%s", (str(value), key))
            if cursor.rowcount == 0:
                cursor.execute("INSERT INTO settings (setting_key, setting_value) VALUES (%s, %s)", (key, str(value)))
        db.commit()
        cursor.close()
        db.close()
        return jsonify({"success": True})

    cursor.execute("SELECT * FROM settings")
    settings = {row["setting_key"]: row["setting_value"] for row in cursor.fetchall()}
    cursor.close()
    db.close()
    return jsonify(settings)

@app.route("/admin/api/chat_logs", methods=["GET"])
def admin_api_chat_logs():
    if "user" not in session or session.get("role") != "admin":
        return jsonify({"error": "Unauthorized"}), 401
    
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    ensure_table_chat_logs(cursor)
    db.commit()

    cursor.execute("SELECT * FROM chat_logs ORDER BY id DESC LIMIT 20")
    logs = cursor.fetchall()
    
    # Convert timestamps to string
    for log in logs:
        if log.get("timestamp"):
            log["timestamp"] = log["timestamp"].strftime("%I:%M %p")
    
    cursor.close()
    db.close()
    return jsonify(logs)

@app.route("/admin/api/chat_logs/train", methods=["POST"])
def admin_api_chat_train():
    if "user" not in session or session.get("role") != "admin":
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.json
    new_response = data.get("response")
    
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    ensure_table_chat_logs(cursor)
    
    # Just mock inserting it as a system training log for now
    cursor.execute(
        "INSERT INTO chat_logs (user_id, user_query, ai_response) VALUES (0, 'System Training', %s)",
        (new_response,)
    )
    db.commit()
    cursor.close()
    db.close()
    
    return jsonify({"success": True})

import csv
from io import StringIO
from flask import make_response

@app.route("/admin/api/export/users")
def admin_api_export_users():
    if "user" not in session or session.get("role") != "admin":
        return jsonify({"error": "Unauthorized"}), 401
        
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN status VARCHAR(20) DEFAULT 'active'")
        db.commit()
    except Exception:
        pass
        
    cursor.execute("""
        SELECT u.id, u.full_name, u.email, u.field, u.role, u.status, 
               COALESCE(AVG(i.score), 0) as avg_score
        FROM users u 
        LEFT JOIN interviews i ON u.email = i.user_email
        GROUP BY u.id
    """)
    users = cursor.fetchall()
    cursor.close()
    db.close()
    
    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(['ID', 'Name', 'Email', 'Field', 'Role', 'Status', 'Avg Score'])
    
    for u in users:
        cw.writerow([u['id'], u['full_name'], u['email'], u['field'], u['role'], u['status'], round(u['avg_score'], 2)])
        
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=export_users.csv"
    output.headers["Content-type"] = "text/csv"
    return output

if __name__ == "__main__":
    app.run(debug=True, port=5000)
