"""Database models for job application tracking."""

import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from exceptions import DatabaseError, ValidationError

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent / "applications.db"


def init_db() -> None:
    """Initialize SQLite database with applications table."""
    try:
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
        logger.debug("Database initialized successfully")
    except Exception as e:
        raise DatabaseError("Failed to initialize database", details=str(e)) from e


class Application:
    """Job application model."""

    STATUSES = [
        "saved",
        "applied",
        "phone_screen",
        "interview",
        "technical",
        "offer",
        "rejected",
        "withdrawn",
    ]

    def __init__(self, **kwargs: Any) -> None:
        self.id: int | None = kwargs.get("id")
        self.company: str = kwargs.get("company", "")
        self.title: str = kwargs.get("title", "")
        self.url: str = kwargs.get("url", "")
        self.status: str = kwargs.get("status", "saved")
        self.notes: str = kwargs.get("notes", "")
        self.date_applied: str | None = kwargs.get("date_applied")
        self.date_created: str | None = kwargs.get("date_created")
        self.resume_path: str = kwargs.get("resume_path", "")
        self.cover_letter_path: str = kwargs.get("cover_letter_path", "")
        self.salary: str = kwargs.get("salary", "")
        self.location: str = kwargs.get("location", "")
        self.tags: str | list = kwargs.get("tags", "[]")

    def to_dict(self) -> dict[str, Any]:
        """Convert application to dictionary."""
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
    def _get_connection() -> sqlite3.Connection:
        """Get database connection."""
        return sqlite3.connect(DB_PATH)

    @classmethod
    def create(cls, app: Application) -> int:
        """Create new application, return ID.

        Args:
            app: Application to create

        Returns:
            ID of created application

        Raises:
            DatabaseError: If creation fails
        """
        try:
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
            if app_id is None:
                raise DatabaseError("Failed to get last row ID after insert")
            app_id = int(app_id)  # type: ignore[redundant-cast]

            conn.commit()
            conn.close()
            logger.info(f"Created application with ID: {app_id}")
            return app_id
        except Exception as e:
            raise DatabaseError("Failed to create application", details=str(e)) from e

    @classmethod
    def get_all(cls, status: str | None = None) -> list[dict[str, Any]]:
        """Get all applications, optionally filtered by status.

        Args:
            status: Optional status filter

        Returns:
            List of application dictionaries

        Raises:
            DatabaseError: If query fails
        """
        try:
            conn = cls._get_connection()
            cursor = conn.cursor()

            if status:
                cursor.execute(
                    "SELECT * FROM applications WHERE status = ? ORDER BY date_created DESC",
                    (status,),
                )
            else:
                cursor.execute("SELECT * FROM applications ORDER BY date_created DESC")

            rows = cursor.fetchall()
            conn.close()

            applications: list[dict[str, Any]] = []
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
        except Exception as e:
            raise DatabaseError("Failed to get applications", details=str(e)) from e

    @classmethod
    def get_by_id(cls, app_id: int) -> Application | None:
        """Get application by ID.

        Args:
            app_id: Application ID

        Returns:
            Application object or None if not found

        Raises:
            DatabaseError: If query fails
        """
        try:
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
        except Exception as e:
            raise DatabaseError(f"Failed to get application {app_id}", details=str(e)) from e

    @classmethod
    def update(cls, app_id: int, **kwargs: Any) -> None:
        """Update application fields.

        Args:
            app_id: Application ID to update
            **kwargs: Fields to update

        Raises:
            DatabaseError: If update fails
            ValidationError: If invalid fields provided
        """
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

        updates: list[str] = []
        values: list[Any] = []

        for key, value in kwargs.items():
            if key not in allowed_fields:
                raise ValidationError(f"Invalid field: {key}")
            updates.append(f"{key} = ?")
            if key == "tags" and isinstance(value, list):
                values.append(json.dumps(value))
            else:
                values.append(value)

        if not updates:
            return

        try:
            values.append(app_id)
            query = f"UPDATE applications SET {', '.join(updates)} WHERE id = ?"

            conn = cls._get_connection()
            cursor = conn.cursor()
            cursor.execute(query, values)
            conn.commit()
            conn.close()
            logger.info(f"Updated application {app_id}")
        except Exception as e:
            raise DatabaseError(f"Failed to update application {app_id}", details=str(e)) from e

    @classmethod
    def delete(cls, app_id: int) -> None:
        """Delete application.

        Args:
            app_id: Application ID to delete

        Raises:
            DatabaseError: If deletion fails
        """
        try:
            conn = cls._get_connection()
            cursor = conn.cursor()

            cursor.execute("DELETE FROM applications WHERE id = ?", (app_id,))
            conn.commit()
            conn.close()
            logger.info(f"Deleted application {app_id}")
        except Exception as e:
            raise DatabaseError(f"Failed to delete application {app_id}", details=str(e)) from e

    @classmethod
    def get_stats(cls) -> dict[str, int]:
        """Get application statistics.

        Returns:
            Dictionary with status counts

        Raises:
            DatabaseError: If query fails
        """
        try:
            conn = cls._get_connection()
            cursor = conn.cursor()

            cursor.execute("SELECT status, COUNT(*) FROM applications GROUP BY status")
            stats: dict[str, int] = dict(cursor.fetchall())
            conn.close()

            # Ensure all statuses exist
            for status in Application.STATUSES:
                if status not in stats:
                    stats[status] = 0

            return stats
        except Exception as e:
            raise DatabaseError("Failed to get statistics", details=str(e)) from e


# Initialize database on import
init_db()
