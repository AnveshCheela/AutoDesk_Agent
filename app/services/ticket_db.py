"""
Mock enterprise ticketing system backed by SQLite.

Provides:
  - Ticket creation (with auto-incrementing IDs)
  - Ticket status lookup
  - Ticket listing
"""

import sqlite3
import logging
import os
from datetime import datetime
from typing import Optional, Dict, List

from app.config import settings

logger = logging.getLogger(__name__)

# ============================================
# Database Setup
# ============================================
def get_db_path() -> str:
    """Get the absolute path to the SQLite database."""
    db_path = os.path.abspath(settings.SQLITE_DB_PATH)
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    return db_path


def get_connection() -> sqlite3.Connection:
    """Get a new SQLite connection with row factory enabled."""
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize the tickets database schema."""
    conn = get_connection()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                issue TEXT NOT NULL,
                priority TEXT NOT NULL DEFAULT 'medium',
                status TEXT NOT NULL DEFAULT 'open',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                assigned_to TEXT DEFAULT 'Unassigned',
                notes TEXT DEFAULT ''
            )
        """)
        conn.commit()
        logger.info("Tickets database initialized successfully.")
    finally:
        conn.close()


# ============================================
# Ticket Operations
# ============================================
def create_ticket(issue: str, priority: str = "medium") -> Dict:
    """
    Create a new support ticket.

    Args:
        issue: Description of the issue.
        priority: Priority level — 'low', 'medium', 'high', or 'critical'.

    Returns:
        Dict with the created ticket details.
    """
    # Validate priority
    valid_priorities = {"low", "medium", "high", "critical"}
    priority = priority.lower().strip()
    if priority not in valid_priorities:
        priority = "medium"

    now = datetime.now().isoformat()

    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            INSERT INTO tickets (issue, priority, status, created_at, updated_at)
            VALUES (?, ?, 'open', ?, ?)
            """,
            (issue, priority, now, now),
        )
        conn.commit()
        ticket_id = cursor.lastrowid

        ticket = {
            "ticket_id": ticket_id,
            "issue": issue,
            "priority": priority,
            "status": "open",
            "created_at": now,
            "assigned_to": "Unassigned",
        }

        logger.info(f"Created ticket #{ticket_id}: {issue} (priority: {priority})")
        return ticket

    finally:
        conn.close()


def check_ticket_status(ticket_id: int) -> Optional[Dict]:
    """
    Look up the status and details of a ticket by ID.

    Args:
        ticket_id: The ticket ID number.

    Returns:
        Dict with ticket details, or None if not found.
    """
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM tickets WHERE id = ?", (ticket_id,)
        ).fetchone()

        if row is None:
            logger.warning(f"Ticket #{ticket_id} not found.")
            return None

        ticket = {
            "ticket_id": row["id"],
            "issue": row["issue"],
            "priority": row["priority"],
            "status": row["status"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "assigned_to": row["assigned_to"],
            "notes": row["notes"],
        }

        logger.info(f"Retrieved ticket #{ticket_id}: status={ticket['status']}")
        return ticket

    finally:
        conn.close()


def list_tickets(limit: int = 10) -> List[Dict]:
    """List the most recent tickets."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM tickets ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()

        tickets = []
        for row in rows:
            tickets.append({
                "ticket_id": row["id"],
                "issue": row["issue"],
                "priority": row["priority"],
                "status": row["status"],
                "created_at": row["created_at"],
            })

        return tickets

    finally:
        conn.close()


# Initialize DB on module import
init_db()
