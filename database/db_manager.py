"""
Database Manager for Persona Automation
Handles all database operations for websites, personas, and test runs.
"""

import sqlite3
import json
import uuid
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from urllib.parse import urlparse


class DatabaseManager:
    """Manages SQLite database operations for persona automation."""
    
    def __init__(self, db_path: str = "database/persona_automation.db"):
        self.db_path = db_path
        self._ensure_db_exists()
    
    def _ensure_db_exists(self):
        """Create database and tables if they don't exist."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        conn = self._connect()
        cursor = conn.cursor()
        
        cursor.executescript('''
            CREATE TABLE IF NOT EXISTS websites (
                id TEXT PRIMARY KEY,
                url TEXT NOT NULL UNIQUE,
                domain TEXT NOT NULL,
                type TEXT NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS website_analyses (
                id TEXT PRIMARY KEY,
                website_id TEXT NOT NULL,
                description TEXT,
                features_detected TEXT,
                llm_provider TEXT NOT NULL,
                llm_model TEXT,
                raw_json TEXT,
                analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (website_id) REFERENCES websites(id)
            );
            
            CREATE TABLE IF NOT EXISTS generation_sessions (
                id TEXT PRIMARY KEY,
                website_id TEXT NOT NULL,
                analysis_id TEXT,
                personas_requested INTEGER NOT NULL,
                personas_generated INTEGER NOT NULL,
                llm_provider TEXT NOT NULL,
                llm_model TEXT,
                duration_sec REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (website_id) REFERENCES websites(id)
            );
            
            CREATE TABLE IF NOT EXISTS personas (
                id TEXT PRIMARY KEY,
                website_id TEXT NOT NULL,
                generation_session_id TEXT,
                nom TEXT NOT NULL,
                type_persona TEXT,
                device TEXT DEFAULT 'desktop',
                vitesse TEXT DEFAULT 'moyenne',
                patience_sec INTEGER DEFAULT 30,
                objectif TEXT,
                json_file_path TEXT,
                generated_by_llm BOOLEAN DEFAULT 1,
                is_active BOOLEAN DEFAULT 1,
                persona_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (website_id) REFERENCES websites(id)
            );
            
            CREATE TABLE IF NOT EXISTS test_runs (
                id TEXT PRIMARY KEY,
                persona_id TEXT NOT NULL,
                llm_provider TEXT NOT NULL,
                llm_model TEXT NOT NULL,
                status TEXT NOT NULL,
                steps_count INTEGER DEFAULT 0,
                duration_sec REAL,
                vision_enabled BOOLEAN DEFAULT 0,
                error_message TEXT,
                report_path TEXT,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                FOREIGN KEY (persona_id) REFERENCES personas(id)
            );
            
            CREATE TABLE IF NOT EXISTS steps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                step_number INTEGER NOT NULL,
                thought TEXT,
                action TEXT,
                action_input TEXT,
                result TEXT,
                is_error BOOLEAN DEFAULT 0,
                error_message TEXT,
                duration_ms INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (run_id) REFERENCES test_runs(id)
            );
        ''')

        conn.commit()
        conn.close()

        # Run migrations
        self._run_migrations()

    def _run_migrations(self):
        """Run database migrations."""
        conn = self._connect()
        cursor = conn.cursor()

        # Migration: Add persona_json column if it doesn't exist
        try:
            cursor.execute("ALTER TABLE personas ADD COLUMN persona_json TEXT")
            conn.commit()
            print("✅ Migration: Added persona_json column to personas table")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                pass  # Column already exists
            else:
                raise
        finally:
            conn.close()

        # Migration: ensure playwright executions table exists
        self.ensure_playwright_table()
    
    def _connect(self) -> sqlite3.Connection:
        """Create database connection."""
        return sqlite3.connect(self.db_path)
    
    def _generate_id(self) -> str:
        """Generate unique ID."""
        return str(uuid.uuid4())[:8]
    
    # =========================================================================
    # WEBSITES
    # =========================================================================
    
    def add_website(self, url: str, site_type: str = "unknown", description: str = "") -> str:
        """Add or update website. Returns website_id."""
        parsed = urlparse(url)
        domain = parsed.netloc or parsed.path
        website_id = domain.replace(".", "-").replace("www-", "")
        print(f"📌 Adding website: url={url}, domain={domain}, website_id={website_id}")

        conn = self._connect()
        cursor = conn.cursor()

        # Insert or update (replace unknown type with real type)
        cursor.execute('''
            INSERT INTO websites (id, url, domain, type, description)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                type = CASE WHEN excluded.type != 'unknown' THEN excluded.type ELSE websites.type END,
                description = CASE WHEN excluded.description != '' THEN excluded.description ELSE websites.description END
        ''', (website_id, url, domain, site_type, description))

        conn.commit()
        conn.close()
        print(f"✅ Website saved with ID: {website_id}")

        return website_id
    
    def get_website(self, website_id: str) -> Optional[Dict]:
        """Get website by ID."""
        conn = self._connect()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM websites WHERE id = ?', (website_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'id': row[0], 'url': row[1], 'domain': row[2],
                'type': row[3], 'description': row[4], 'created_at': row[5]
            }
        return None
    
    # =========================================================================
    # WEBSITE ANALYSES
    # =========================================================================
    
    def add_analysis(self, website_id: str, analysis: Dict, 
                     llm_provider: str, llm_model: str = None) -> str:
        """Save website analysis. Returns analysis_id."""
        analysis_id = f"analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        conn = self._connect()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO website_analyses 
            (id, website_id, description, features_detected, llm_provider, llm_model, raw_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            analysis_id,
            website_id,
            analysis.get('description', ''),
            json.dumps(analysis.get('features', []), ensure_ascii=False),
            llm_provider,
            llm_model,
            json.dumps(analysis, ensure_ascii=False)
        ))
        
        conn.commit()
        conn.close()
        
        return analysis_id
    
    # =========================================================================
    # GENERATION SESSIONS
    # =========================================================================
    
    def start_generation_session(self, website_id: str, analysis_id: str,
                                  personas_requested: int, llm_provider: str,
                                  llm_model: str = None) -> str:
        """Start a new generation session. Returns session_id."""
        session_id = f"gen_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        conn = self._connect()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO generation_sessions 
            (id, website_id, analysis_id, personas_requested, personas_generated, llm_provider, llm_model)
            VALUES (?, ?, ?, ?, 0, ?, ?)
        ''', (session_id, website_id, analysis_id, personas_requested, llm_provider, llm_model))
        
        conn.commit()
        conn.close()
        
        return session_id
    
    def complete_generation_session(self, session_id: str, personas_generated: int, duration_sec: float):
        """Update session with results."""
        conn = self._connect()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE generation_sessions 
            SET personas_generated = ?, duration_sec = ?
            WHERE id = ?
        ''', (personas_generated, duration_sec, session_id))
        
        conn.commit()
        conn.close()
    
    # =========================================================================
    # PERSONAS
    # =========================================================================
    
    def add_persona(self, persona_data: Dict, website_id: str,
                    json_file_path: str = None, session_id: str = None) -> str:
        """Add a persona to database. Returns persona_id."""
        # Use the ID already generated by persona_generator (it's already unique with timestamp+uuid)
        # Don't generate a new one - persona_generator already ensured uniqueness
        if 'id' in persona_data:
            unique_persona_id = persona_data['id']
            print(f"📌 Using ID from persona_data: {unique_persona_id}")
        else:
            unique_persona_id = f"persona_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}"
            print(f"🆕 Generated new ID: {unique_persona_id}")
        nom = persona_data.get('nom', 'Unknown')

        try:
            conn = self._connect()
            cursor = conn.cursor()

            # Check if website exists
            cursor.execute("SELECT id FROM websites WHERE id = ?", (website_id,))
            if not cursor.fetchone():
                print(f"❌ ERROR: Website ID '{website_id}' does not exist in database!")
                conn.close()
                return unique_persona_id

            # Insert persona (NOT replace - always insert new)
            cursor.execute('''
                INSERT INTO personas
                (id, website_id, generation_session_id, nom, type_persona, device,
                 vitesse, patience_sec, objectif, json_file_path, generated_by_llm, persona_json, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, 1)
            ''', (
                unique_persona_id,
                website_id,
                session_id,
                nom,
                persona_data.get('persona_type', persona_data.get('style_navigation', 'unknown')),
                persona_data.get('device', 'desktop'),
                persona_data.get('vitesse_navigation', 'moyenne'),
                int(persona_data.get('patience_attente_sec', 30)),
                persona_data.get('objectif', ''),
                json_file_path,
                json.dumps(persona_data)  # Store full persona data as JSON
            ))

            conn.commit()
            conn.close()
            print(f"✅ Persona saved: {unique_persona_id} | {nom} | website_id={website_id}")
            return unique_persona_id

        except Exception as e:
            print(f"❌ ERROR saving persona: {str(e)}")
            conn.close()
            return unique_persona_id
    
    def get_persona(self, persona_id: str) -> Optional[Dict]:
        """Get persona by ID."""
        conn = self._connect()
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM personas WHERE id = ?', (persona_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            # Try to parse persona_json if available
            try:
                persona_json = json.loads(row[13]) if row[13] else {}
            except:
                persona_json = {}

            return {
                'id': row[0], 'website_id': row[1], 'session_id': row[2],
                'nom': row[3], 'type_persona': row[4], 'device': row[5],
                'vitesse': row[6], 'patience_sec': row[7], 'objectif': row[8],
                'json_file_path': row[9], 'generated_by_llm': row[10],
                'is_active': row[11], 'created_at': row[13],
                **persona_json  # Merge all persona fields
            }
        return None
    
    def list_personas(self, website_id: str = None) -> List[Dict]:
        """List all personas, optionally filtered by website."""
        conn = self._connect()
        cursor = conn.cursor()
        
        if website_id:
            cursor.execute('SELECT id, nom, type_persona, device, vitesse, website_id FROM personas WHERE website_id = ?', (website_id,))
        else:
            cursor.execute('SELECT id, nom, type_persona, device, vitesse, website_id FROM personas')
        
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {'id': r[0], 'nom': r[1], 'type_persona': r[2], 'device': r[3], 'vitesse': r[4], 'website_id': r[5]}
            for r in rows
        ]
    
    # =========================================================================
    # TEST RUNS
    # =========================================================================
    
    def start_test_run(self, persona_id: str, llm_provider: str, 
                       llm_model: str, vision_enabled: bool = False) -> str:
        """Start a new test run. Returns run_id."""
        run_id = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{self._generate_id()}"
        
        conn = self._connect()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO test_runs 
            (id, persona_id, llm_provider, llm_model, status, vision_enabled)
            VALUES (?, ?, ?, ?, 'running', ?)
        ''', (run_id, persona_id, llm_provider, llm_model, vision_enabled))
        
        conn.commit()
        conn.close()
        
        return run_id
    
    def complete_test_run(self, run_id: str, status: str, steps_count: int,
                          duration_sec: float, error_message: str = None,
                          report_path: str = None):
        """Update test run with results."""
        conn = self._connect()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE test_runs 
            SET status = ?, steps_count = ?, duration_sec = ?, 
                error_message = ?, report_path = ?, completed_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (status, steps_count, duration_sec, error_message, report_path, run_id))
        
        conn.commit()
        conn.close()
    
    def add_step(self, run_id: str, step_number: int, thought: str,
                 action: str, action_input: str, result: str,
                 is_error: bool = False, error_message: str = None,
                 duration_ms: int = None):
        """Add a step to a test run."""
        conn = self._connect()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO steps 
            (run_id, step_number, thought, action, action_input, result, is_error, error_message, duration_ms)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (run_id, step_number, thought, action, action_input, result, is_error, error_message, duration_ms))
        
        conn.commit()
        conn.close()

    # =========================================================================
    # PLAYWRIGHT TEST EXECUTIONS
    # =========================================================================

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
                completed_at DATETIME,
                FOREIGN KEY (persona_id) REFERENCES personas(id),
                FOREIGN KEY (website_id) REFERENCES websites(id)
            );

            CREATE INDEX IF NOT EXISTS idx_playwright_executions_persona
                ON playwright_test_executions(persona_id);
            CREATE INDEX IF NOT EXISTS idx_playwright_executions_website
                ON playwright_test_executions(website_id);
            CREATE INDEX IF NOT EXISTS idx_playwright_executions_status
                ON playwright_test_executions(status);
            CREATE INDEX IF NOT EXISTS idx_playwright_executions_created
                ON playwright_test_executions(created_at DESC);
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
        """Insert a new playwright test execution record and return its ID."""
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
        """Fetch playwright execution records with optional persona/website filters."""
        conn = self._connect()
        cursor = conn.cursor()

        where_clauses = []
        params: List[Any] = []

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
        """Fetch a single playwright execution including full dom_snapshot."""
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
    
    # =========================================================================
    # STATISTICS
    # =========================================================================
    
    def get_stats(self) -> Dict:
        """Get database statistics."""
        conn = self._connect()
        cursor = conn.cursor()

        stats = {}

        for table in ['websites', 'personas', 'test_runs', 'steps']:
            cursor.execute(f'SELECT COUNT(*) FROM {table}')
            count = cursor.fetchone()[0]
            stats[table] = count
            print(f"📊 DB Stats: {table} = {count}")

        # Success rate
        cursor.execute("SELECT COUNT(*) FROM test_runs WHERE status = 'completed'")
        completed = cursor.fetchone()[0]
        stats['success_rate'] = (completed / stats['test_runs'] * 100) if stats['test_runs'] > 0 else 0
        print(f"📊 DB Stats: success_rate = {stats['success_rate']}%")

        conn.close()
        return stats


# Singleton instance
_db_instance = None

def get_db() -> DatabaseManager:
    """Get database manager instance."""
    global _db_instance
    if _db_instance is None:
        _db_instance = DatabaseManager()
    return _db_instance
