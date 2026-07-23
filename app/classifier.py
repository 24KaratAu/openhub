import json
from datetime import datetime

# Available Taxonomies
USE_CASES = [
    "Web Research", "Coding", "Debugging", "Testing", "Documentation",
    "Automation", "Cloud", "Database", "Security", "UI", 
    "Data Science", "Multi-Agent"
]

IMPL_TYPES = [
    "Agents", "Skills", "Commands", "MCP Servers", "Plugins"
]

def classify_repository(repo: dict, readme: str = "") -> tuple[str, str, str]:
    """
    Classifies a repository into a (Use Case, Implementation Type, Difficulty).
    Combines name, description, tags/topics, and readme signals.
    """
    name = repo.get("name", "").lower()
    desc = repo.get("description", "").lower() if repo.get("description") else ""
    tags = [t.lower() for t in repo.get("tags", [])]
    readme = readme.lower()
    
    # Combined search context
    full_text = f"{name} {desc} {' '.join(tags)} {readme[:1000]}"

    # --- 1. Classify Use Case ---
    scores = {uc: 0 for uc in USE_CASES}
    words = full_text.split()
    
    # Heuristic triggers
    if any(w in full_text for w in ["research", "search", "google", "brave", "scrape", "crawl", "web-search", "wikipedia"]):
        scores["Web Research"] += 15
    if any(w in full_text for w in ["code", "coding", "compiler", "autocomplete", "refactor", "syntax", "ast", "eslint", "lsp"]):
        scores["Coding"] += 15
    if any(w in full_text for w in ["debug", "pdb", "gdb", "breakpoint", "traceback", "logging", "inspector"]):
        scores["Debugging"] += 15
    if any(w in full_text for w in ["test", "testing", "pytest", "unittest", "assertion", "cypress", "playwright"]):
        scores["Testing"] += 15
    if any(w in full_text for w in ["doc", "docs", "documentation", "readme", "wiki", "generator", "sphinx", "mkdocs"]):
        scores["Documentation"] += 15
    if any(w in full_text for w in ["automation", "automate", "cron", "workflow", "trigger", "scheduler", "script", "yaml", "installer", "pipeline", "action", "bot", "integration"]):
        scores["Automation"] += 20
    if any(w in full_text for w in ["cloud", "aws", "gcp", "azure", "docker", "kubernetes", "s3", "terraform"]):
        scores["Cloud"] += 15
    if any(w in full_text for w in ["db", "database", "postgres", "sqlite", "mysql", "redis", "mongodb", "sql"]):
        scores["Database"] += 20
    if any(w in full_text for w in ["security", "auth", "secret", "guardrail", "redact", "keyring", "cipher", "crypto"]):
        scores["Security"] += 20
    if any(w in words for w in ["ui", "gui", "tui", "textual", "css", "layout", "visual", "react", "frontend"]):
        scores["UI"] += 15
    if any(w in full_text for w in ["data", "science", "pandas", "numpy", "jupyter", "visualization", "plot", "math"]):
        scores["Data Science"] += 15
    if any(w in full_text for w in ["multi-agent", "swarm", "crewai", "autogen", "langgraph", "agents", "chat"]):
        scores["Multi-Agent"] += 15

    # Default fallback Use Case based on highest score
    best_use_case = max(scores, key=scores.get)
    if scores[best_use_case] == 0:
        best_use_case = "Automation" # Default

    # --- 2. Classify Implementation Type ---
    type_scores = {it: 0 for it in IMPL_TYPES}
    
    if "mcp" in full_text or "model-context" in full_text:
        type_scores["MCP Servers"] += 30
    if "plugin" in full_text or "extension" in full_text:
        type_scores["Plugins"] += 20
    if "agent" in full_text or "autonomous" in full_text or "swarm" in full_text:
        type_scores["Agents"] += 15
    if "skill" in full_text or "tool" in full_text:
        type_scores["Skills"] += 10
    if "command" in full_text or "cli" in full_text or "runner" in full_text:
        type_scores["Commands"] += 10

    best_type = max(type_scores, key=type_scores.get)
    if type_scores[best_type] == 0:
        best_type = "Skills" # Default

    # --- 3. Classify Difficulty ---
    # Simple check for docker, postgres, complex compiled languages or db requirements
    if any(w in full_text for w in ["docker", "postgres", "kubernetes", "c++", "rust", "compile", "libpq"]):
        difficulty = "Advanced"
    elif any(w in full_text for w in ["beginner", "easy", "simple", "starter", "tutorial"]):
        difficulty = "Beginner"
    else:
        difficulty = "Intermediate"

    return best_use_case, best_type, difficulty

def calculate_quality_score(repo: dict, readme: str = "") -> dict:
    """
    Computes a balanced score from 0-100 reflecting repository quality.
    Returns a dict with:
        score: int (0-100)
        rating_stars: str (e.g. "★★★★★")
        rating_label: str (e.g. "Excellent")
        breakdown: dict (detailed breakdown)
    """
    stars = repo.get("stars", 0)
    forks = repo.get("forks", 0)
    license_name = repo.get("license") or "None"
    pushed_at_str = repo.get("pushed_at") or repo.get("updated_at")

    # 1. Popularity (max 30 pts)
    # Scaled logarithmically so smaller stars still get credit, but 1000+ stars maxes out.
    star_pts = min(15, (stars / 100) * 1.5) if stars < 1000 else 15
    fork_pts = min(15, (forks / 50) * 1.5) if forks < 500 else 15
    popularity_score = round(star_pts + fork_pts)

    # 2. Maintenance Activity (max 30 pts)
    activity_score = 0
    if pushed_at_str:
        try:
            # strip trailing Z if present
            clean_date = pushed_at_str.replace("Z", "")
            pushed_dt = datetime.fromisoformat(clean_date)
            days_ago = (datetime.utcnow() - pushed_dt).days
            if days_ago <= 15:
                activity_score = 30
            elif days_ago <= 45:
                activity_score = 25
            elif days_ago <= 90:
                activity_score = 20
            elif days_ago <= 180:
                activity_score = 15
            elif days_ago <= 365:
                activity_score = 10
            else:
                activity_score = 5
        except Exception:
            activity_score = 15
    else:
        activity_score = 15

    # 3. Documentation (max 20 pts)
    doc_score = 0
    readme_len = len(readme)
    if readme_len > 2500:
        doc_score += 15
    elif readme_len > 1000:
        doc_score += 10
    elif readme_len > 100:
        doc_score += 5

    # License check
    if license_name and license_name.lower() != "none":
        doc_score += 5

    # 4. Open Issue Health Ratio (max 20 pts)
    # Low issue count relative to stars suggests active maintenance
    issue_score = 20
    open_issues = repo.get("open_issues", 0)
    if stars > 0:
        issue_ratio = open_issues / stars
        if issue_ratio > 0.5:
            issue_score = 5
        elif issue_ratio > 0.2:
            issue_score = 10
        elif issue_ratio > 0.05:
            issue_score = 15

    total_score = popularity_score + activity_score + doc_score + issue_score
    total_score = max(0, min(100, total_score))

    # Ratings Mapping
    if total_score >= 90:
        stars_str = "★★★★★"
        label = "Excellent"
    elif total_score >= 75:
        stars_str = "★★★★☆"
        label = "Great"
    elif total_score >= 60:
        stars_str = "★★★☆☆"
        label = "Good"
    elif total_score >= 40:
        stars_str = "★★☆☆☆"
        label = "Fair"
    else:
        stars_str = "★☆☆☆☆"
        label = "Poor"

    return {
        "score": total_score,
        "rating_stars": stars_str,
        "rating_label": label,
        "breakdown": {
            "popularity": popularity_score,
            "activity": activity_score,
            "documentation": doc_score,
            "issue_health": issue_score
        }
    }
