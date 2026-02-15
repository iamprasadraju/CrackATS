"""Database models for job application tracking."""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

DB_PATH = Path(__file__).parent / "applications.db"


def init_db():
    """Initialize SQLite database with applications table."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company TEXT NOT NULL,
            title TEXT NOT NULL,
            url TEXT,
            status TEXT DEFAULT 'saved',
            notes TEXT,
            date_applied TEXT,
            date_created TEXT DEFAULT CURRENT_TIMESTAMP,
            resume_path TEXT,
            cover_letter_path TEXT,
            salary TEXT,
            location TEXT,
            tags TEXT
        )
    """)

    conn.commit()
    conn.close()


class Application:
    """Job application model."""

    STATUSES = ["saved", "applied", "phone_screen", "interview", "technical", "offer", "rejected", "withdrawn"]

    def __init__(self, **kwargs):
        self.id = kwargs.get("id")
        self.company = kwargs.get("company", "")
        self.title = kwargs.get("title", "")
        self.url = kwargs.get("url", "")
        self.status = kwargs.get("status", "saved")
        self.notes = kwargs.get("notes", "")
        self.date_applied = kwargs.get("date_applied")
        self.date_created = kwargs.get("date_created")
        self.resume_path = kwargs.get("resume_path", "")
        self.cover_letter_path = kwargs.get("cover_letter_path", "")
        self.salary = kwargs.get("salary", "")
        self.location = kwargs.get("location", "")
        self.tags = kwargs.get("tags", "[]")

    def to_dict(self):
        return {
            "id": self.id,
            "company": self.company,
            "title": self.title,
            "url": self.url,
            "status": self.status,
            "notes": self.notes,
            "date_applied": self.date_applied,
            "date_created": self.date_created,
            "resume_path": self.resume_path,
            "cover_letter_path": self.cover_letter_path,
            "salary": self.salary,
            "location": self.location,
            "tags": json.loads(self.tags) if isinstance(self.tags, str) else self.tags,
        }


class ApplicationDB:
    """Database operations for applications."""

    @staticmethod
    def _get_connection():
        return sqlite3.connect(DB_PATH)

    @classmethod
    def create(cls, app: Application) -> int:
        """Create new application, return ID."""
        conn = cls._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO applications 
            (company, title, url, status, notes, date_applied, resume_path, cover_letter_path, salary, location, tags)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                app.company,
                app.title,
                app.url,
                app.status,
                app.notes,
                app.date_applied,
                app.resume_path,
                app.cover_letter_path,
                app.salary,
                app.location,
                json.dumps(app.tags) if isinstance(app.tags, list) else app.tags,
            ),
        )

        app_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return app_id

    @classmethod
    def get_all(cls, status: Optional[str] = None) -> list:
        """Get all applications, optionally filtered by status."""
        conn = cls._get_connection()
        cursor = conn.cursor()

        if status:
            cursor.execute("SELECT * FROM applications WHERE status = ? ORDER BY date_created DESC", (status,))
        else:
            cursor.execute("SELECT * FROM applications ORDER BY date_created DESC")

        rows = cursor.fetchall()
        conn.close()

        applications = []
        for row in rows:
            app = Application(
                id=row[0],
                company=row[1],
                title=row[2],
                url=row[3],
                status=row[4],
                notes=row[5],
                date_applied=row[6],
                date_created=row[7],
                resume_path=row[8],
                cover_letter_path=row[9],
                salary=row[10],
                location=row[11],
                tags=row[12],
            )
            applications.append(app.to_dict())

        return applications

    @classmethod
    def get_by_id(cls, app_id: int) -> Optional[Application]:
        """Get application by ID."""
        conn = cls._get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM applications WHERE id = ?", (app_id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return Application(
            id=row[0],
            company=row[1],
            title=row[2],
            url=row[3],
            status=row[4],
            notes=row[5],
            date_applied=row[6],
            date_created=row[7],
            resume_path=row[8],
            cover_letter_path=row[9],
            salary=row[10],
            location=row[11],
            tags=row[12],
        )

    @classmethod
    def update(cls, app_id: int, **kwargs):
        """Update application fields."""
        conn = cls._get_connection()
        cursor = conn.cursor()

        allowed_fields = [
            "company",
            "title",
            "url",
            "status",
            "notes",
            "date_applied",
            "resume_path",
            "cover_letter_path",
            "salary",
            "location",
            "tags",
        ]

        updates = []
        values = []

        for key, value in kwargs.items():
            if key in allowed_fields:
                updates.append(f"{key} = ?")
                if key == "tags" and isinstance(value, list):
                    values.append(json.dumps(value))
                else:
                    values.append(value)

        if not updates:
            return

        values.append(app_id)
        query = f"UPDATE applications SET {', '.join(updates)} WHERE id = ?"

        cursor.execute(query, values)
        conn.commit()
        conn.close()

    @classmethod
    def delete(cls, app_id: int):
        """Delete application."""
        conn = cls._get_connection()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM applications WHERE id = ?", (app_id,))
        conn.commit()
        conn.close()

    @classmethod
    def get_stats(cls) -> dict:
        """Get application statistics."""
        conn = cls._get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT status, COUNT(*) FROM applications GROUP BY status")
        stats = dict(cursor.fetchall())
        conn.close()

        # Ensure all statuses exist
        for status in Application.STATUSES:
            if status not in stats:
                stats[status] = 0

        return stats


# Initialize database on import
init_db()
