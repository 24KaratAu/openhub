import os
import sqlite3
import json
from datetime import datetime

DB_DIR = os.path.expanduser("~/.cache/opencode-hub")
DB_PATH = os.path.join(DB_DIR, "repos.db")

def init_db():
    """Initializes the database directory and tables."""
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Table 1: Repositories (Cache)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS repositories (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        owner TEXT NOT NULL,
        full_name TEXT UNIQUE NOT NULL,
        description TEXT,
        html_url TEXT NOT NULL,
        stars INTEGER DEFAULT 0,
        forks INTEGER DEFAULT 0,
        open_issues INTEGER DEFAULT 0,
        language TEXT,
        license TEXT,
        created_at TEXT,
        updated_at TEXT,
        pushed_at TEXT,
        use_case TEXT,
        impl_type TEXT,
        difficulty TEXT,
        tags TEXT,                      -- JSON array of topics / tags
        quality_score INTEGER,          -- Calculated asynchronously
        quality_breakdown TEXT,         -- JSON breakdown of scoring
        readme_preview TEXT,            -- Cached README markdown
        is_verified INTEGER DEFAULT 0,  -- 0 or 1
        cached_at TEXT NOT NULL         -- ISO timestamp of caching
    );
    """)

    # Table 2: Installed Packages
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS installed_packages (
        package_slug TEXT PRIMARY KEY,  -- "owner/repo"
        version TEXT NOT NULL,
        installed_at TEXT NOT NULL,
        status TEXT NOT NULL,           -- 'installed', 'upgrading', 'broken'
        impl_type TEXT NOT NULL
    );
    """)

    # Table 3: History Log
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS history_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        package_slug TEXT NOT NULL,
        action TEXT NOT NULL,           -- 'installed', 'updated', 'failed', 'removed'
        timestamp TEXT NOT NULL,
        details TEXT                    -- output or error details
    );
    """)

    conn.commit()
    conn.close()

def get_connection():
    """Returns a sqlite3 connection with dict-like row parsing."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def save_repositories(repos):
    """Saves or updates a list of repositories in the cache."""
    conn = get_connection()
    cursor = conn.cursor()
    now_str = datetime.utcnow().isoformat()

    for r in repos:
        # Check if we already have this repository and preserve details like readme_preview or quality_score if they aren't provided
        cursor.execute("SELECT quality_score, quality_breakdown, readme_preview, use_case, impl_type, difficulty FROM repositories WHERE full_name = ?", (r["full_name"],))
        existing = cursor.fetchone()
        
        q_score = r.get("quality_score")
        q_breakdown = r.get("quality_breakdown")
        readme = r.get("readme_preview")
        use_case = r.get("use_case")
        impl_type = r.get("impl_type")
        difficulty = r.get("difficulty")

        if existing:
            if q_score is None:
                q_score = existing["quality_score"]
            if q_breakdown is None:
                q_breakdown = existing["quality_breakdown"]
            if readme is None:
                readme = existing["readme_preview"]
            if use_case is None:
                use_case = existing["use_case"]
            if impl_type is None:
                impl_type = existing["impl_type"]
            if difficulty is None:
                difficulty = existing["difficulty"]

        # Run classification immediately if fields are still missing
        if not use_case or not impl_type or not difficulty:
            from app.classifier import classify_repository
            c_uc, c_it, c_diff = classify_repository(r, readme or "")
            use_case = use_case or c_uc
            impl_type = impl_type or c_it
            difficulty = difficulty or c_diff

        tags_str = json.dumps(r.get("tags", []))
        if isinstance(q_breakdown, dict):
            q_breakdown = json.dumps(q_breakdown)

        cursor.execute("""
        INSERT INTO repositories (
            id, name, owner, full_name, description, html_url, stars, forks, open_issues,
            language, license, created_at, updated_at, pushed_at, use_case, impl_type, difficulty,
            tags, quality_score, quality_breakdown, readme_preview, is_verified, cached_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(full_name) DO UPDATE SET
            name=excluded.name,
            owner=excluded.owner,
            description=excluded.description,
            html_url=excluded.html_url,
            stars=excluded.stars,
            forks=excluded.forks,
            open_issues=excluded.open_issues,
            language=excluded.language,
            license=excluded.license,
            updated_at=excluded.updated_at,
            pushed_at=excluded.pushed_at,
            use_case=coalesce(?, use_case),
            impl_type=coalesce(?, impl_type),
            difficulty=coalesce(?, difficulty),
            tags=excluded.tags,
            quality_score=coalesce(?, quality_score),
            quality_breakdown=coalesce(?, quality_breakdown),
            readme_preview=coalesce(?, readme_preview),
            is_verified=excluded.is_verified,
            cached_at=excluded.cached_at
        """, (
            r["id"], r["name"], r["owner"], r["full_name"], r.get("description"), r["html_url"],
            r.get("stars", 0), r.get("forks", 0), r.get("open_issues", 0), r.get("language"),
            r.get("license"), r.get("created_at"), r.get("updated_at"), r.get("pushed_at"),
            use_case, impl_type, difficulty, tags_str, q_score, q_breakdown, readme,
            1 if r.get("is_verified") else 0, now_str,
            use_case, impl_type, difficulty, q_score, q_breakdown, readme
        ))

    conn.commit()
    conn.close()

def get_repositories(limit=100):
    """Fetches cached repositories from the database."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM repositories ORDER BY stars DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    
    repos = []
    for row in rows:
        repo = dict(row)
        repo["tags"] = json.loads(repo["tags"]) if repo["tags"] else []
        repo["quality_breakdown"] = json.loads(repo["quality_breakdown"]) if repo["quality_breakdown"] else {}
        repo["is_verified"] = bool(repo["is_verified"])
        repos.append(repo)
        
    conn.close()
    return repos

def get_repository_by_fullname(full_name):
    """Fetches a single repository by its full name."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM repositories WHERE full_name = ?", (full_name,))
    row = cursor.fetchone()
    if row:
        repo = dict(row)
        repo["tags"] = json.loads(repo["tags"]) if repo["tags"] else []
        repo["quality_breakdown"] = json.loads(repo["quality_breakdown"]) if repo["quality_breakdown"] else {}
        repo["is_verified"] = bool(repo["is_verified"])
        conn.close()
        return repo
    conn.close()
    return None

def update_repository_quality_score(full_name, score, breakdown):
    """Updates the quality score of a repository."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE repositories 
    SET quality_score = ?, quality_breakdown = ?
    WHERE full_name = ?
    """, (score, json.dumps(breakdown), full_name))
    conn.commit()
    conn.close()

def update_repository_readme(full_name, readme_content):
    """Updates the README content of a repository."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE repositories 
    SET readme_preview = ?
    WHERE full_name = ?
    """, (readme_content, full_name))
    conn.commit()
    conn.close()

def find_skill_md(dir_path: str) -> tuple[str | None, str | None]:
    """Finds directory containing SKILL.md in dir_path or nested subdirectories."""
    if os.path.exists(os.path.join(dir_path, "SKILL.md")):
        return dir_path, os.path.join(dir_path, "SKILL.md")
    for root, dirs, files in os.walk(dir_path):
        if "SKILL.md" in files:
            return root, os.path.join(root, "SKILL.md")
    return None, None

def sync_installed_from_disk():
    """Scans local project and global skill directories to populate installed_packages table."""
    dirs_to_scan = [
        os.path.abspath("./.opencode/skills"),
        os.path.abspath("./.agents/skills"),
        os.path.abspath("./.claude/skills"),
        os.path.expanduser("~/.config/opencode/skills"),
        os.path.expanduser("~/.agents/skills"),
        os.path.expanduser("~/.claude/skills"),
        os.path.expanduser("~/.claude/plugins"),
    ]
    for base_dir in dirs_to_scan:
        if not os.path.exists(base_dir):
            continue
        try:
            for item in os.listdir(base_dir):
                item_path = os.path.join(base_dir, item)
                if os.path.isdir(item_path):
                    skill_dir, skill_file = find_skill_md(item_path)
                    if skill_file or os.path.exists(os.path.join(item_path, ".claude-plugin")):
                        add_installed_package(item, "1.0.0", "INSTALLED", "Skills")
        except Exception as e:
            logger.warning(f"Error scanning directory {base_dir} for skills: {e}")

def get_installed_packages():
    """Gets all installed packages (syncing with disk first)."""
    try:
        sync_installed_from_disk()
    except Exception as e:
        logger.warning(f"Error syncing installed packages from disk: {e}")
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM installed_packages ORDER BY installed_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_installed_package(slug):
    """Gets a specific installed package details."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM installed_packages WHERE package_slug = ?", (slug,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def add_installed_package(slug, version, status, impl_type):
    """Adds or updates an installed package."""
    impl_type = impl_type or "Skills"
    conn = get_connection()
    cursor = conn.cursor()
    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
    INSERT INTO installed_packages (package_slug, version, installed_at, status, impl_type)
    VALUES (?, ?, ?, ?, ?)
    ON CONFLICT(package_slug) DO UPDATE SET
        version=excluded.version,
        installed_at=excluded.installed_at,
        status=excluded.status,
        impl_type=excluded.impl_type
    """, (slug, version, now_str, status, impl_type))
    conn.commit()
    conn.close()

def remove_installed_package(slug):
    """Removes an installed package from database."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM installed_packages WHERE package_slug = ?", (slug,))
    conn.commit()
    conn.close()

def log_history(slug, action, details=None):
    """Adds a log to the history."""
    conn = get_connection()
    cursor = conn.cursor()
    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
    INSERT INTO history_log (package_slug, action, timestamp, details)
    VALUES (?, ?, ?, ?)
    """, (slug, action, now_str, details))
    conn.commit()
    conn.close()

def get_history_logs():
    """Gets all history logs."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM history_log ORDER BY timestamp DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]
