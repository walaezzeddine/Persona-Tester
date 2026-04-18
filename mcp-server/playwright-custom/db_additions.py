"""
DB helper methods for playwright_test_executions table.
Add these methods to your existing DatabaseManager class in database/db_manager.py
"""

import json
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional


# ── Paste these methods into your DatabaseManager class ──────────────────────

def ensure_playwright_table(self):
    """Create the playwright_test_executions table if it doesn't exist."""
    conn = self._connect()
    cursor = conn.cursor()
    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS playwright_test_executions (
            id TEXT PRIMARY KEY,
            persona_id TEXT NOT NULL,
            website_id TEXT NOT NULL,
            run_id TEXT,
            url TEXT NOT NULL,
            dom_snapshot TEXT,
            generated_script TEXT NOT NULL,
            browser_name TEXT DEFAULT 'chromium',
            status TEXT DEFAULT 'pending',
            execution_log TEXT,
            error_message TEXT,
            screenshot_base64 TEXT,
            duration_ms INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            completed_at DATETIME
        );
        CREATE INDEX IF NOT EXISTS idx_pw_exec_persona
            ON playwright_test_executions(persona_id);
        CREATE INDEX IF NOT EXISTS idx_pw_exec_website
            ON playwright_test_executions(website_id);
        CREATE INDEX IF NOT EXISTS idx_pw_exec_status
            ON playwright_test_executions(status);
        CREATE INDEX IF NOT EXISTS idx_pw_exec_created
            ON playwright_test_executions(created_at);
    """)
    conn.commit()
    conn.close()


def add_playwright_execution(
    self,
    persona_id: str,
    website_id: str,
    url: str,
    generated_script: str,
    status: str,
    execution_log: List[str],
    dom_snapshot: Optional[str] = None,
    browser_name: str = "chromium",
    error_message: Optional[str] = None,
    screenshot_base64: Optional[str] = None,
    duration_ms: int = 0,
    run_id: Optional[str] = None,
) -> str:
    """Insert a new playwright test execution record. Returns the new ID."""
    exec_id = str(uuid.uuid4())
    conn = self._connect()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO playwright_test_executions
            (id, persona_id, website_id, run_id, url, dom_snapshot,
             generated_script, browser_name, status, execution_log,
             error_message, screenshot_base64, duration_ms, completed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """,
        (
            exec_id,
            persona_id,
            website_id,
            run_id,
            url,
            dom_snapshot,
            generated_script,
            browser_name,
            status,
            json.dumps(execution_log),
            error_message,
            screenshot_base64,
            duration_ms,
        ),
    )
    conn.commit()
    conn.close()
    return exec_id


def get_playwright_executions(
    self,
    persona_id: Optional[str] = None,
    website_id: Optional[str] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """Fetch playwright test execution records, optionally filtered."""
    conn = self._connect()
    cursor = conn.cursor()

    where_clauses = []
    params = []

    if persona_id:
        where_clauses.append("pte.persona_id = ?")
        params.append(persona_id)
    if website_id:
        where_clauses.append("pte.website_id = ?")
        params.append(website_id)

    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    cursor.execute(
        f"""
        SELECT
            pte.id, pte.persona_id, pte.website_id, pte.run_id,
            pte.url, pte.generated_script, pte.browser_name,
            pte.status, pte.execution_log, pte.error_message,
            pte.screenshot_base64, pte.duration_ms,
            pte.created_at, pte.completed_at,
            p.nom as persona_name,
            w.domain as website_domain,
            -- dom_snapshot is intentionally omitted from list view (large)
            length(pte.dom_snapshot) as dom_size
        FROM playwright_test_executions pte
        LEFT JOIN personas p ON pte.persona_id = p.id
        LEFT JOIN websites w ON pte.website_id = w.id
        {where_sql}
        ORDER BY pte.created_at DESC
        LIMIT ?
        """,
        params + [limit],
    )

    rows = cursor.fetchall()
    conn.close()

    result = []
    for row in rows:
        try:
            logs = json.loads(row[8]) if row[8] else []
        except (json.JSONDecodeError, TypeError):
            logs = []

        result.append({
            "id": row[0],
            "persona_id": row[1],
            "website_id": row[2],
            "run_id": row[3],
            "url": row[4],
            "generated_script": row[5],
            "browser_name": row[6],
            "status": row[7],
            "execution_log": logs,
            "error_message": row[9],
            "screenshot_base64": row[10],
            "duration_ms": row[11],
            "created_at": row[12],
            "completed_at": row[13],
            "persona_name": row[14],
            "website_domain": row[15],
            "dom_size": row[16],
        })

    return result


def get_playwright_execution_by_id(self, execution_id: str) -> Optional[Dict[str, Any]]:
    """Fetch a single playwright execution with full DOM snapshot."""
    conn = self._connect()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT
            pte.id, pte.persona_id, pte.website_id, pte.run_id,
            pte.url, pte.dom_snapshot, pte.generated_script, pte.browser_name,
            pte.status, pte.execution_log, pte.error_message,
            pte.screenshot_base64, pte.duration_ms,
            pte.created_at, pte.completed_at,
            p.nom as persona_name,
            w.domain as website_domain
        FROM playwright_test_executions pte
        LEFT JOIN personas p ON pte.persona_id = p.id
        LEFT JOIN websites w ON pte.website_id = w.id
        WHERE pte.id = ?
        """,
        (execution_id,),
    )
    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    try:
        logs = json.loads(row[9]) if row[9] else []
    except (json.JSONDecodeError, TypeError):
        logs = []

    return {
        "id": row[0],
        "persona_id": row[1],
        "website_id": row[2],
        "run_id": row[3],
        "url": row[4],
        "dom_snapshot": row[5],
        "generated_script": row[6],
        "browser_name": row[7],
        "status": row[8],
        "execution_log": logs,
        "error_message": row[10],
        "screenshot_base64": row[11],
        "duration_ms": row[12],
        "created_at": row[13],
        "completed_at": row[14],
        "persona_name": row[15],
        "website_domain": row[16],
    }
