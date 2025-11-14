"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import os
from pathlib import Path
import sqlite3
import json
from typing import Dict, Any

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")

# Database path (SQLite)
DB_PATH = current_dir / "activities.db"


def get_db_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables and seed initial activities if needed."""
    conn = get_db_conn()
    cur = conn.cursor()

    cur.execute(
        """
    CREATE TABLE IF NOT EXISTS activities (
        name TEXT PRIMARY KEY,
        description TEXT,
        schedule TEXT,
        max_participants INTEGER
    )
    """
    )

    cur.execute(
        """
    CREATE TABLE IF NOT EXISTS participants (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        activity_name TEXT,
        email TEXT,
        UNIQUE(activity_name, email),
        FOREIGN KEY(activity_name) REFERENCES activities(name) ON DELETE CASCADE
    )
    """
    )

    # Seed initial data only if activities table is empty
    cur.execute("SELECT COUNT(1) as cnt FROM activities")
    if cur.fetchone()[0] == 0:
        initial = {
            "Chess Club": {
                "description": "Learn strategies and compete in chess tournaments",
                "schedule": "Fridays, 3:30 PM - 5:00 PM",
                "max_participants": 12,
                "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
            },
            "Programming Class": {
                "description": "Learn programming fundamentals and build software projects",
                "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
                "max_participants": 20,
                "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
            },
            "Gym Class": {
                "description": "Physical education and sports activities",
                "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
                "max_participants": 30,
                "participants": ["john@mergington.edu", "olivia@mergington.edu"]
            },
            "Soccer Team": {
                "description": "Join the school soccer team and compete in matches",
                "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
                "max_participants": 22,
                "participants": ["liam@mergington.edu", "noah@mergington.edu"]
            },
            "Basketball Team": {
                "description": "Practice and play basketball with the school team",
                "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
                "max_participants": 15,
                "participants": ["ava@mergington.edu", "mia@mergington.edu"]
            },
            "Art Club": {
                "description": "Explore your creativity through painting and drawing",
                "schedule": "Thursdays, 3:30 PM - 5:00 PM",
                "max_participants": 15,
                "participants": ["amelia@mergington.edu", "harper@mergington.edu"]
            },
            "Drama Club": {
                "description": "Act, direct, and produce plays and performances",
                "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
                "max_participants": 20,
                "participants": ["ella@mergington.edu", "scarlett@mergington.edu"]
            },
            "Math Club": {
                "description": "Solve challenging problems and participate in math competitions",
                "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
                "max_participants": 10,
                "participants": ["james@mergington.edu", "benjamin@mergington.edu"]
            },
            "Debate Team": {
                "description": "Develop public speaking and argumentation skills",
                "schedule": "Fridays, 4:00 PM - 5:30 PM",
                "max_participants": 12,
                "participants": ["charlotte@mergington.edu", "henry@mergington.edu"]
            }
        }

        for name, data in initial.items():
            cur.execute(
                "INSERT INTO activities (name, description, schedule, max_participants) VALUES (?, ?, ?, ?)",
                (name, data["description"], data["schedule"], data["max_participants"])
            )
            for email in data.get("participants", []):
                cur.execute(
                    "INSERT OR IGNORE INTO participants (activity_name, email) VALUES (?, ?)",
                    (name, email)
                )

    conn.commit()
    conn.close()


def db_get_activities() -> Dict[str, Any]:
    conn = get_db_conn()
    cur = conn.cursor()
    activities: Dict[str, Any] = {}

    cur.execute("SELECT name, description, schedule, max_participants FROM activities")
    rows = cur.fetchall()
    for r in rows:
        name = r["name"]
        cur.execute("SELECT email FROM participants WHERE activity_name = ?", (name,))
        parts = [row[0] for row in cur.fetchall()]
        activities[name] = {
            "description": r["description"],
            "schedule": r["schedule"],
            "max_participants": r["max_participants"],
            "participants": parts,
        }

    conn.close()
    return activities


def db_signup(activity_name: str, email: str):
    conn = get_db_conn()
    cur = conn.cursor()
    cur.execute("SELECT max_participants FROM activities WHERE name = ?", (activity_name,))
    row = cur.fetchone()
    if not row:
        conn.close()
        raise KeyError("Activity not found")

    max_p = row["max_participants"]
    cur.execute("SELECT COUNT(1) FROM participants WHERE activity_name = ?", (activity_name,))
    count = cur.fetchone()[0]
    cur.execute("SELECT 1 FROM participants WHERE activity_name = ? AND email = ?", (activity_name, email))
    exists = cur.fetchone()
    if exists:
        conn.close()
        raise ValueError("already_signed_up")

    if count >= max_p:
        conn.close()
        raise ValueError("full")

    cur.execute("INSERT INTO participants (activity_name, email) VALUES (?, ?)", (activity_name, email))
    conn.commit()
    conn.close()


def db_unregister(activity_name: str, email: str):
    conn = get_db_conn()
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM activities WHERE name = ?", (activity_name,))
    if not cur.fetchone():
        conn.close()
        raise KeyError("Activity not found")

    cur.execute("SELECT 1 FROM participants WHERE activity_name = ? AND email = ?", (activity_name, email))
    if not cur.fetchone():
        conn.close()
        raise ValueError("not_signed_up")

    cur.execute("DELETE FROM participants WHERE activity_name = ? AND email = ?", (activity_name, email))
    conn.commit()
    conn.close()


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.on_event("startup")
def on_startup():
    # Ensure DB exists and is seeded
    init_db()


@app.get("/activities")
def get_activities():
    return db_get_activities()


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(activity_name: str, email: str):
    """Sign up a student for an activity"""
    try:
        db_signup(activity_name, email)
    except KeyError:
        raise HTTPException(status_code=404, detail="Activity not found")
    except ValueError as e:
        if str(e) == "already_signed_up":
            raise HTTPException(status_code=400, detail="Student is already signed up")
        if str(e) == "full":
            raise HTTPException(status_code=400, detail="Activity is full")
        raise HTTPException(status_code=400, detail=str(e))

    return {"message": f"Signed up {email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(activity_name: str, email: str):
    """Unregister a student from an activity"""
    try:
        db_unregister(activity_name, email)
    except KeyError:
        raise HTTPException(status_code=404, detail="Activity not found")
    except ValueError as e:
        if str(e) == "not_signed_up":
            raise HTTPException(status_code=400, detail="Student is not signed up for this activity")
        raise HTTPException(status_code=400, detail=str(e))

    return {"message": f"Unregistered {email} from {activity_name}"}
