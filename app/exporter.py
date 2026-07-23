import os
import re
import logging
from app.cache import log_history

logger = logging.getLogger("opencode-hub.exporter")

def sanitize_skill_name(name: str) -> str:
    """Sanitizes a repository name into a valid skill directory slug."""
    slug = re.sub(r'[^a-zA-Z0-9_-]', '-', name).lower().strip('-')
    return slug or "custom-skill"

def export_skill(repo: dict, readme_content: str = "", target: str = "project") -> tuple[bool, str, str]:
    """
    Exports a repository skill/agent into OpenCode skills & agent directories.
    Creates both:
      1. SKILL.md under skills/<slug>/SKILL.md (for automatic skill loading)
      2. <slug>.md under agent/<slug>.md (for inclusion in OpenCode's Select Agent menu)
    
    Parameters:
        repo: Repository dict containing name, description, full_name, etc.
        readme_content: Content of README.md to format into body.
        target: 'project' (./.opencode/ & ./.agents/) or 'global' (~/.config/opencode/ & ~/.agents/)
        
    Returns:
        tuple[bool, str, str]: (Success boolean, Primary Target File Path, User Message)
    """
    repo_name = repo.get("name") or repo.get("full_name", "").split("/")[-1] or "skill"
    skill_slug = sanitize_skill_name(repo_name)
    desc = repo.get("description") or "OpenCode custom skill."
    safe_desc = desc.replace('"', '\\"')
    
    if target == "global":
        skill_base_dirs = [
            os.path.expanduser("~/.config/opencode/skills"),
            os.path.expanduser("~/.agents/skills")
        ]
        agent_dirs = [
            os.path.expanduser("~/.config/opencode/agent"),
            os.path.expanduser("~/.config/opencode/agents"),
            os.path.expanduser("~/.agents/agents")
        ]
    else: # default to project
        skill_base_dirs = [
            os.path.abspath("./.opencode/skills"),
            os.path.abspath("./.agents/skills")
        ]
        agent_dirs = [
            os.path.abspath("./.opencode/agent"),
            os.path.abspath("./.opencode/agents"),
            os.path.abspath("./.agents/agents")
        ]

    # Format SKILL.md content
    clean_readme = readme_content.strip() if readme_content else f"# {repo.get('full_name', repo_name)}\n\n{desc}"
    
    if not clean_readme.startswith("---"):
        skill_md_content = (
            f"---\n"
            f"name: {skill_slug}\n"
            f"description: \"{safe_desc}\"\n"
            f"---\n\n"
            f"{clean_readme}\n"
        )
    else:
        skill_md_content = clean_readme

    # Format Agent .md content for OpenCode Agent Menu
    agent_md_content = (
        f"---\n"
        f"description: \"{safe_desc}\"\n"
        f"mode: all\n"
        f"---\n\n"
        f"{clean_readme}\n"
    )

    created_files = []

    # 1. Save SKILL.md in skills directories
    for base_dir in skill_base_dirs:
        skill_dir = os.path.join(base_dir, skill_slug)
        skill_file = os.path.join(skill_dir, "SKILL.md")
        try:
            os.makedirs(skill_dir, exist_ok=True)
            with open(skill_file, "w", encoding="utf-8") as f:
                f.write(skill_md_content)
            created_files.append(skill_file)
        except Exception as e:
            logger.warning(f"Could not write skill file to {skill_file}: {e}")

    # 2. Save <slug>.md in agent directories for OpenCode UI Menu
    for agent_dir in agent_dirs:
        agent_file = os.path.join(agent_dir, f"{skill_slug}.md")
        try:
            os.makedirs(agent_dir, exist_ok=True)
            with open(agent_file, "w", encoding="utf-8") as f:
                f.write(agent_md_content)
            created_files.append(agent_file)
        except Exception as e:
            logger.warning(f"Could not write agent file to {agent_file}: {e}")

    if created_files:
        primary_file = created_files[0]
        log_history(repo.get("full_name", skill_slug), "EXPORTED", f"Exported skill and agent definition to {', '.join(created_files)}")
        logger.info(f"Skill and Agent exported successfully. Primary path: {primary_file}")
        msg = f"Successfully exported Skill and Agent to {target} destination: {primary_file}"
        return True, primary_file, msg
    else:
        error_msg = f"Failed to write skill/agent files to destination directories."
        logger.error(error_msg)
        log_history(repo.get("full_name", skill_slug), "FAILED_EXPORT", error_msg)
        return False, "", error_msg
