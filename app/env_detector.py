import os
import shutil
import logging

logger = logging.getLogger("opencode-hub.env_detector")

def find_skill_md(dir_path: str) -> tuple[str | None, str | None]:
    """Finds directory containing SKILL.md in dir_path or nested subdirectories."""
    if os.path.exists(os.path.join(dir_path, "SKILL.md")):
        return dir_path, os.path.join(dir_path, "SKILL.md")
    for root, dirs, files in os.walk(dir_path):
        if "SKILL.md" in files:
            return root, os.path.join(root, "SKILL.md")
    return None, None

def detect_unsynced_environments() -> dict | None:
    """
    Detects installed AI coding agent environments (e.g. Claude Code)
    and checks if there are skills in .agents/skills or ~/.agents/skills
    that are not yet present in .claude/skills or ~/.claude/skills.
    """
    claude_dir = os.path.expanduser("~/.claude")
    if not os.path.exists(claude_dir):
        return None

    # Source skill directories to check
    source_dirs = [
        os.path.abspath("./.agents/skills"),
        os.path.abspath("./.opencode/skills"),
        os.path.expanduser("~/.agents/skills"),
        os.path.expanduser("~/.config/opencode/skills"),
    ]

    # Target Claude skill directories
    target_global = os.path.expanduser("~/.claude/skills")
    target_project = os.path.abspath("./.claude/skills")

    unsynced = set()

    for src in source_dirs:
        if not os.path.exists(src):
            continue
        try:
            for item in os.listdir(src):
                item_path = os.path.join(src, item)
                if os.path.isdir(item_path):
                    skill_dir, skill_file = find_skill_md(item_path)
                    if skill_file:
                        in_global = os.path.exists(os.path.join(target_global, item, "SKILL.md"))
                        in_project = os.path.exists(os.path.join(target_project, item, "SKILL.md"))
                        if not (in_global or in_project):
                            unsynced.add(item)
        except Exception as e:
            logger.warning(f"Error checking source directory {src}: {e}")

    if unsynced:
        return {
            "env_name": "Claude Code",
            "unsynced_skills": sorted(list(unsynced)),
            "target_dir": "~/.claude/skills"
        }
    return None

def sync_skills_to_environment(env_data: dict) -> tuple[bool, int, str]:
    """
    Syncs unsynced skills to the detected environment target directories.
    """
    if not env_data or "unsynced_skills" not in env_data:
        return False, 0, "No skills to sync."

    skills_to_sync = env_data["unsynced_skills"]
    source_dirs = [
        os.path.abspath("./.agents/skills"),
        os.path.abspath("./.opencode/skills"),
        os.path.expanduser("~/.agents/skills"),
        os.path.expanduser("~/.config/opencode/skills"),
    ]
    
    target_dirs = [
        os.path.expanduser("~/.claude/skills"),
        os.path.abspath("./.claude/skills"),
    ]

    synced_count = 0
    for skill_slug in skills_to_sync:
        found_src_dir = None
        for src in source_dirs:
            skill_dir = os.path.join(src, skill_slug)
            if os.path.exists(skill_dir):
                real_dir, skill_file = find_skill_md(skill_dir)
                if real_dir:
                    found_src_dir = real_dir
                    break
        
        if found_src_dir:
            for target_base in target_dirs:
                dest = os.path.join(target_base, skill_slug)
                try:
                    os.makedirs(dest, exist_ok=True)
                    shutil.copytree(found_src_dir, dest, dirs_exist_ok=True)
                except Exception as e:
                    logger.warning(f"Failed copying {skill_slug} to {dest}: {e}")
            synced_count += 1

    return True, synced_count, f"Synced {synced_count} skills to {env_data.get('env_name', 'target environment')}!"
