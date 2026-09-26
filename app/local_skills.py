import os
import re
import shutil
import tarfile
import tempfile
import logging
from datetime import datetime
from typing import AsyncGenerator

logger = logging.getLogger("opencode-hub.local_skills")

BACKUP_DIR = os.path.expanduser("~/.cache/opencode-hub/backups")

# Folders that live next to skills but are not skills themselves
IGNORED_DIR_NAMES = {"synced", "marketplaces", "node_modules", "__pycache__"}
BACKUP_NAME_RE = re.compile(r"\.bak(-|$)")
GITHUB_SLUG_RE = re.compile(r"github\.com[/:]([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)")


def skill_scan_dirs() -> list[str]:
    """Directories where agent tools look for installed skills (project dirs collapse into
    global ones when running from the home directory)."""
    dirs = [
        os.path.abspath("./.opencode/skills"),
        os.path.abspath("./.agents/skills"),
        os.path.abspath("./.claude/skills"),
        os.path.expanduser("~/.config/opencode/skills"),
        os.path.expanduser("~/.agents/skills"),
        os.path.expanduser("~/.claude/skills"),
    ]
    return list({os.path.realpath(d): d for d in dirs}.values())


def is_ignored_dir(name: str) -> bool:
    return name.startswith(".") or name in IGNORED_DIR_NAMES or bool(BACKUP_NAME_RE.search(name))


def find_skill_md(dir_path: str) -> tuple[str | None, str | None]:
    """Finds directory containing SKILL.md in dir_path or nested subdirectories."""
    if os.path.exists(os.path.join(dir_path, "SKILL.md")):
        return dir_path, os.path.join(dir_path, "SKILL.md")
    for root, dirs, files in os.walk(dir_path):
        dirs[:] = [d for d in dirs if not is_ignored_dir(d)]
        if "SKILL.md" in files:
            return root, os.path.join(root, "SKILL.md")
    return None, None


def parse_frontmatter(skill_file: str) -> dict:
    """Reads top-level scalar keys from a SKILL.md YAML frontmatter block."""
    meta = {}
    try:
        with open(skill_file, "r", encoding="utf-8", errors="replace") as f:
            lines = f.read().splitlines()
    except OSError:
        return meta
    if not lines or lines[0].strip() != "---":
        return meta
    for line in lines[1:]:
        if line.strip() == "---":
            break
        m = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if not m:
            continue  # nested or continuation line
        value = m.group(2).strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        meta[m.group(1)] = value
    return meta


def extract_repo_slug(meta: dict) -> str | None:
    """Pulls an owner/repo GitHub slug out of repository/homepage/source frontmatter fields."""
    for key in ("repository", "repo", "source", "homepage", "url"):
        m = GITHUB_SLUG_RE.search(meta.get(key, ""))
        if m:
            repo = m.group(2)
            if repo.endswith(".git"):
                repo = repo[:-4]
            return f"{m.group(1)}/{repo}"
    return None


def scan_local_skills() -> dict[str, dict]:
    """Scans skill directories on disk. Returns {skill_name: info}, merging duplicate locations."""
    skills: dict[str, dict] = {}
    for base_dir in skill_scan_dirs():
        if not os.path.isdir(base_dir):
            continue
        try:
            entries = sorted(os.listdir(base_dir))
        except OSError as e:
            logger.warning(f"Error scanning directory {base_dir} for skills: {e}")
            continue
        for item in entries:
            item_path = os.path.join(base_dir, item)
            if is_ignored_dir(item) or not os.path.isdir(item_path):
                continue
            skill_dir, skill_file = find_skill_md(item_path)
            if not skill_file:
                continue
            meta = parse_frontmatter(skill_file)
            info = skills.setdefault(item, {
                "name": item,
                "version": None,
                "description": meta.get("description", ""),
                "repo_slug": None,
                "paths": [],
            })
            # Record the folder that holds SKILL.md, so updates replace the skill itself even
            # when it sits inside a cloned repo
            info["paths"].append(skill_dir)
            info["version"] = oldest_version(info["version"], meta.get("version"))
            info["repo_slug"] = info["repo_slug"] or extract_repo_slug(meta)
    return skills


def oldest_version(a: str | None, b: str | None) -> str | None:
    """Picks the older of two versions, so an outdated copy is never hidden by a newer one."""
    if not a or not b:
        return a or b
    return b if is_newer(a, b) else a


def _version_tuple(version: str) -> tuple[int, ...] | None:
    nums = re.findall(r"\d+", (version or "").split("+")[0])
    return tuple(int(n) for n in nums) if nums else None


def normalize_version(version: str | None) -> str | None:
    if not version:
        return None
    return version.strip().lstrip("vV")


def is_newer(latest: str | None, current: str | None) -> bool | None:
    """True if latest > current, False if not, None if either version is unknown/unparseable."""
    lt, ct = _version_tuple(normalize_version(latest)), _version_tuple(normalize_version(current))
    if lt is None or ct is None:
        return None
    width = max(len(lt), len(ct))
    return lt + (0,) * (width - len(lt)) > ct + (0,) * (width - len(ct))


def _safe_extract(tar_path: str, dest: str) -> None:
    dest_real = os.path.realpath(dest)
    with tarfile.open(tar_path, "r:gz") as tar:
        for member in tar.getmembers():
            target = os.path.realpath(os.path.join(dest, member.name))
            if not target.startswith(dest_real + os.sep):
                raise ValueError(f"Unsafe path in archive: {member.name}")
            if member.issym() or member.islnk():
                link_target = os.path.realpath(os.path.join(os.path.dirname(target), member.linkname))
                if not link_target.startswith(dest_real + os.sep):
                    raise ValueError(f"Unsafe link in archive: {member.name}")
        tar.extractall(dest)


def locate_skill_root(extracted_root: str, skill_name: str) -> str | None:
    """Finds the folder inside an extracted repo that holds the skill's SKILL.md."""
    candidates = []
    for root, dirs, files in os.walk(extracted_root):
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in {"node_modules", "tests", "fixtures"}]
        if "SKILL.md" in files:
            candidates.append(root)
    if not candidates:
        return None
    by_depth = sorted(candidates, key=lambda p: p.count(os.sep))
    for path in by_depth:
        if parse_frontmatter(os.path.join(path, "SKILL.md")).get("name") == skill_name:
            return path
    for path in by_depth:
        if os.path.basename(path) == skill_name:
            return path
    return by_depth[0] if len(candidates) == 1 else None


async def update_skill(skill_name: str, paths: list[str], repo_slug: str, ref: str | None,
                       current_version: str | None) -> AsyncGenerator[str, None]:
    """
    Downloads repo_slug at ref (a release tag, or the default branch if None), backs up every
    installed copy of the skill to BACKUP_DIR, replaces it with the new files, then verifies
    the installed SKILL.md. Restores the backup if anything fails. Yields log lines; the final
    line starts with [SUCCESS] or [FAIL].
    """
    import httpx
    from app.cache import log_history, add_installed_package
    from app.client import github_headers

    ref_label = ref or "default branch"
    url = f"https://api.github.com/repos/{repo_slug}/tarball" + (f"/{ref}" if ref else "")
    work_dir = tempfile.mkdtemp(prefix="openhub-update-")
    try:
        yield f"[INFO] Updating {skill_name} from {repo_slug} ({ref_label})"
        yield f"[FETCH] Downloading {url}"
        tar_path = os.path.join(work_dir, "src.tar.gz")
        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=60.0, headers=github_headers()) as client:
                async with client.stream("GET", url) as resp:
                    if resp.status_code != 200:
                        raise RuntimeError(f"GitHub returned HTTP {resp.status_code}")
                    with open(tar_path, "wb") as f:
                        async for chunk in resp.aiter_bytes():
                            f.write(chunk)
        except Exception as e:
            reason = str(e) or type(e).__name__
            log_history(skill_name, "failed", f"Update download failed: {reason}")
            yield f"[FAIL] Download failed: {reason}. Nothing was changed."
            return

        yield f"[OK] Downloaded {os.path.getsize(tar_path) // 1024} KB"
        extract_dir = os.path.join(work_dir, "src")
        os.makedirs(extract_dir)
        try:
            _safe_extract(tar_path, extract_dir)
        except Exception as e:
            log_history(skill_name, "failed", f"Update extract failed: {e}")
            yield f"[FAIL] Could not extract archive: {e}. Nothing was changed."
            return

        new_root = locate_skill_root(extract_dir, skill_name)
        if not new_root:
            log_history(skill_name, "failed", f"No SKILL.md for '{skill_name}' found in {repo_slug}@{ref_label}")
            yield f"[FAIL] Could not find a SKILL.md for '{skill_name}' in {repo_slug}. Nothing was changed."
            return
        new_version = parse_frontmatter(os.path.join(new_root, "SKILL.md")).get("version")
        yield f"[OK] Found skill at {os.path.relpath(new_root, extract_dir)} (version {new_version or 'unknown'})"

        # Symlinked copies point at a real folder; update each real folder once
        paths = list(dict.fromkeys(os.path.realpath(p) for p in paths))
        stamp = datetime.now().strftime("%Y%m%d%H%M%S")
        backups: list[tuple[str, str]] = []
        try:
            for path in paths:
                old = parse_frontmatter(os.path.join(path, "SKILL.md")).get("version") or "unknown"
                backup = os.path.join(BACKUP_DIR, f"{skill_name}-{stamp}", f"{len(backups)}-v{old}")
                os.makedirs(os.path.dirname(backup), exist_ok=True)
                shutil.move(path, backup)
                backups.append((path, backup))
                yield f"[BACKUP] {path} -> {backup}"
                shutil.copytree(new_root, path)
                yield f"[WRITE] Installed new files to {path}"

            for path in paths:
                installed = parse_frontmatter(os.path.join(path, "SKILL.md")).get("version")
                if installed != new_version:
                    raise RuntimeError(f"verification failed: {path} reports version {installed}")
        except Exception as e:
            for path, backup in backups:
                shutil.rmtree(path, ignore_errors=True)
                shutil.move(backup, path)
            log_history(skill_name, "failed", f"Update failed and was rolled back: {e}")
            yield f"[FAIL] Update failed: {e}. Restored the previous version."
            return

        add_installed_package(skill_name, new_version or "unknown", "INSTALLED", "Skills")
        log_history(skill_name, "updated",
                    f"{current_version or 'unknown'} -> {new_version or 'unknown'} from {repo_slug}@{ref_label}. "
                    f"Backup: {os.path.dirname(backups[0][1])}")
        yield f"[SUCCESS] Updated {skill_name}: {current_version or 'unknown'} -> {new_version or 'unknown'}"
        yield f"[INFO] Backup saved to {os.path.dirname(backups[0][1])}"
        yield "[INFO] Restart Claude Code / OpenCode to load the new version."
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


UPDATE_CHECK_MAX_AGE_HOURS = 6


def update_status(pkg: dict) -> tuple[str, str]:
    """Returns (label, color) describing whether an installed skill has an update."""
    current = pkg.get("version")
    if not pkg.get("repo_slug"):
        return "no source repo in SKILL.md, can't check for updates", "#565f89"
    if not pkg.get("checked_at"):
        return "checking for updates...", "#565f89"
    latest = pkg.get("latest_version")
    if not latest:
        return "couldn't determine latest version", "#e0af68"
    newer = is_newer(latest, current)
    if newer:
        return f"update available: v{normalize_version(current)} -> v{normalize_version(latest)}", "#e0af68"
    if newer is False:
        return f"up to date (latest v{normalize_version(latest)})", "#9ece6a"
    return f"latest is v{normalize_version(latest)}, installed version unknown", "#e0af68"


def _check_is_stale(pkg: dict) -> bool:
    if not pkg.get("checked_at") or not pkg.get("latest_version"):
        return True
    try:
        checked = datetime.strptime(pkg["checked_at"], "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return True
    return (datetime.utcnow() - checked).total_seconds() > UPDATE_CHECK_MAX_AGE_HOURS * 3600


async def check_for_updates(provider, packages: list[dict], force: bool = False) -> list[str]:
    """Checks upstream versions for installed skills with a known repo. Returns error messages."""
    from app.cache import set_update_check
    errors = []
    for pkg in packages:
        if not pkg.get("repo_slug") or not (force or _check_is_stale(pkg)):
            continue
        result = await provider.fetch_latest_version(pkg["repo_slug"], pkg["package_slug"])
        if result["error"]:
            errors.append(f"{pkg['package_slug']}: {result['error']}")
            set_update_check(pkg["package_slug"], None, None)
            if "rate limit" in result["error"]:
                break
            continue
        set_update_check(pkg["package_slug"], result["version"], result["ref"])
    return errors
