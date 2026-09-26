import asyncio
import os
from textual.app import ComposeResult
from textual.screen import Screen, ModalScreen
from textual.containers import Container, Vertical, Horizontal, ScrollableContainer
from textual.widgets import Static, Button, Markdown, Label, Header, Footer
from textual.markup import escape
from app.installer import AsyncInstallRunner
from app.cache import get_repository_by_fullname, get_installed_package, get_installed_by_repo, save_repositories

class InstallConfirmScreen(ModalScreen[bool]):
    """Modal dialog asking user to confirm installation with full repository preview."""
    
    BINDINGS = [
        ("y", "confirm_yes", "Confirm"),
        ("n", "confirm_no", "Cancel"),
        ("escape", "confirm_no", "Cancel")
    ]
    
    def __init__(self, repo: dict) -> None:
        super().__init__()
        self.repo = repo

    def compose(self) -> ComposeResult:
        slug = self.repo.get("full_name", "Unknown/Repo")
        impl_type = self.repo.get("impl_type", "Skills")
        lang = self.repo.get("language", "Python")
        desc = self.repo.get("description", "No description provided.")
        
        # Estimate dependencies based on topics/language/metadata
        deps = "None detected"
        if lang.lower() == "python":
            deps = "python>=3.10"
        elif lang.lower() == "typescript" or lang.lower() == "javascript":
            deps = "nodejs>=18"
        
        # Add some custom deps based on keywords
        if "postgres" in slug or "postgres" in desc.lower():
            deps += ", postgresql-client, libpq-dev"
        elif "sqlite" in slug or "sqlite" in desc.lower():
            deps += ", sqlite3"
        elif "browser" in slug or "playwright" in desc.lower():
            deps += ", playwright-dependencies"

        yield Vertical(
            Label("Confirm Installation", id="confirm-title"),
            Static(f"[bold #7aa2f7]Repository:[/]   {slug}\n"
                   f"[bold #7aa2f7]Type:[/]         {impl_type}\n"
                   f"[bold #7aa2f7]Language:[/]     {lang}\n"
                   f"[bold #7aa2f7]Description:[/]  {desc}\n"
                   f"[bold #7aa2f7]Command:[/]      opencode get {slug}\n"
                   f"[bold #7aa2f7]Dependencies:[/] {deps}", id="confirm-body"),
            Horizontal(
                Button("Install (Y)", variant="success", id="btn-yes"),
                Button("Cancel (N)", variant="error", id="btn-no"),
                classes="confirm-buttons"
            ),
            id="confirm-dialog"
        )

    def action_confirm_yes(self) -> None:
        self.dismiss(True)

    def action_confirm_no(self) -> None:
        self.dismiss(False)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-yes":
            self.dismiss(True)
        else:
            self.dismiss(False)


class ProgressScreen(ModalScreen):
    """Streams log lines from an async generator (install, update) into a modal."""

    def __init__(self, title: str, make_lines) -> None:
        super().__init__()
        self.title_text = title
        self.make_lines = make_lines

    def compose(self) -> ComposeResult:
        yield Vertical(
            Label(self.title_text, id="progress-title"),
            ScrollableContainer(
                Static("", id="progress-log", markup=False),
                id="log-container"
            ),
            Button("Dismiss", id="btn-dismiss", disabled=True),
            id="progress-dialog"
        )

    def on_mount(self) -> None:
        asyncio.create_task(self._run_loop())

    async def _run_loop(self) -> None:
        log_widget = self.query_one("#progress-log", Static)
        log_container = self.query_one("#log-container", ScrollableContainer)
        log_text = ""
        try:
            async for line in self.make_lines():
                log_text += line + "\n"
                log_widget.update(log_text)
                log_container.scroll_to(y=log_container.max_scroll_y)
                await asyncio.sleep(0.05)
        except Exception as e:
            log_text += f"[FAIL] Unexpected error: {e}\n"
            log_widget.update(log_text)

        # Enable dismiss button once the operation completes
        self.query_one("#btn-dismiss", Button).disabled = False

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-dismiss":
            self.dismiss()


class UpdateConfirmScreen(ModalScreen[bool]):
    """Asks the user to confirm replacing an installed skill with the upstream version."""

    BINDINGS = [
        ("y", "confirm_yes", "Confirm"),
        ("n", "confirm_no", "Cancel"),
        ("escape", "confirm_no", "Cancel")
    ]

    def __init__(self, pkg: dict) -> None:
        super().__init__()
        self.pkg = pkg

    def compose(self) -> ComposeResult:
        from app.local_skills import BACKUP_DIR, normalize_version
        current = normalize_version(self.pkg.get("version")) or "unknown"
        latest = normalize_version(self.pkg.get("latest_version")) or "unknown"
        source = self.pkg["repo_slug"] + (f" @ {self.pkg['latest_ref']}" if self.pkg.get("latest_ref") else " (default branch)")
        paths = "\n".join(f"  {escape(p)}" for p in self.pkg.get("local_paths", []))
        yield Vertical(
            Label(f"Update {self.pkg['package_slug']}", id="confirm-title"),
            Static(f"[bold #7aa2f7]Version:[/]  {current} -> [bold #9ece6a]{latest}[/]\n"
                   f"[bold #7aa2f7]Source:[/]   {escape(source)}\n"
                   f"[bold #7aa2f7]Replaces:[/]\n{paths}\n"
                   f"[bold #7aa2f7]Backup to:[/] {escape(BACKUP_DIR)}", id="confirm-body"),
            Horizontal(
                Button("Update (Y)", variant="success", id="btn-yes"),
                Button("Cancel (N)", variant="error", id="btn-no"),
                classes="confirm-buttons"
            ),
            id="confirm-dialog"
        )

    def action_confirm_yes(self) -> None:
        self.dismiss(True)

    def action_confirm_no(self) -> None:
        self.dismiss(False)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "btn-yes")


class ExportConfirmScreen(ModalScreen[str]):
    """Modal dialog allowing user to choose target export directory for SKILL.md."""
    
    BINDINGS = [
        ("p", "choose_project", "Project (.opencode/skills)"),
        ("g", "choose_global", "Global (~/.config/opencode/skills)"),
        ("escape", "cancel", "Cancel")
    ]
    
    def __init__(self, repo_slug: str) -> None:
        super().__init__()
        self.repo_slug = repo_slug

    def compose(self) -> ComposeResult:
        yield Vertical(
            Label(f"Export Skill: {self.repo_slug}", id="confirm-title"),
            Static("[bold #7aa2f7]Select destination target scope for SKILL.md:[/]\n\n"
                   "• [bold #9ece6a]Project Workspace (P):[/] Writes to `./.agents/skills/`, `./.claude/skills/`, & `./.opencode/skills/`\n"
                   "• [bold #e0af68]Global System (G):[/]      Writes to `~/.agents/skills/`, `~/.claude/skills/`, & `~/.config/opencode/skills/`", id="confirm-body"),
            Horizontal(
                Button("Project Workspace (P)", variant="success", id="btn-project"),
                Button("Global System (G)", variant="primary", id="btn-global"),
                Button("Cancel", variant="error", id="btn-cancel"),
                classes="confirm-buttons"
            ),
            id="confirm-dialog"
        )

    def action_choose_project(self) -> None:
        self.dismiss("project")

    def action_choose_global(self) -> None:
        self.dismiss("global")

    def action_cancel(self) -> None:
        self.dismiss("")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-project":
            self.dismiss("project")
        elif event.button.id == "btn-global":
            self.dismiss("global")
        else:
            self.dismiss("")


class RepoDetailsScreen(Screen):
    """Detailed inspection panel displaying full metadata and README preview.

    Opened with either a GitHub "owner/repo" or the folder name of a locally installed skill.
    """

    BINDINGS = [
        ("escape", "back", "Back"),
        ("enter", "install", "Install"),
        ("u", "update_skill", "Update"),
        ("e", "export_skill", "Export Skill")
    ]

    def __init__(self, repo_fullname: str) -> None:
        super().__init__()
        self.repo_fullname = repo_fullname
        self.repo = None
        self.installed = None
        self._update_check_started = False
        self._repo_fetch_failed = False

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="details-layout"):
            with Vertical(id="details-sidebar"):
                yield Label("DETAILS", classes="sidebar-title")
                yield Static("Loading details...", id="meta-text")
                yield Button("Update (U)", variant="warning", id="btn-update")
                yield Button("Install (Enter)", variant="success", id="btn-install")
                yield Button("Export Skill (E)", variant="primary", id="btn-export")
                yield Button("Back (Esc)", variant="default", id="btn-back")
            with ScrollableContainer(id="readme-container"):
                yield Markdown("", id="readme-preview")
        yield Footer()

    def on_mount(self) -> None:
        self.load_repository_details()

    def load_repository_details(self) -> None:
        self.installed = get_installed_package(self.repo_fullname) or get_installed_by_repo(self.repo_fullname)
        repo_slug = self.repo_fullname if "/" in self.repo_fullname else (self.installed or {}).get("repo_slug")
        self.repo = get_repository_by_fullname(repo_slug) if repo_slug else None

        can_update = bool(self.installed and self.installed.get("repo_slug"))
        self.query_one("#btn-update", Button).display = can_update
        self.query_one("#btn-install", Button).display = self.installed is None

        if not self.repo:
            self.show_local_details(repo_slug)
            if repo_slug and not self._repo_fetch_failed:
                asyncio.create_task(self.fetch_repo_async(repo_slug))
            if can_update and not self._update_check_started:
                self._update_check_started = True
                asyncio.create_task(self.ensure_update_checked())
            return

        self.render_repo_meta()

        # Load Readme markdown
        readme_content = self.repo.get("readme_preview")
        if readme_content:
            self.query_one("#readme-preview", Markdown).update(readme_content)
        else:
            # Trigger background readme load from network
            asyncio.create_task(self.fetch_readme_async())

        if can_update and not self._update_check_started:
            self._update_check_started = True
            asyncio.create_task(self.ensure_update_checked())

    def render_repo_meta(self) -> None:
        # Prepare meta summary
        stars = self.repo.get("stars", 0)
        forks = self.repo.get("forks", 0)
        license_name = self.repo.get("license") or "None"
        lang = self.repo.get("language") or "Other"
        difficulty = self.repo.get("difficulty") or "Intermediate"
        
        # Calculate quality details
        q_score = self.repo.get("quality_score") or 50
        q_stars = "★" * (q_score // 20) + "☆" * (5 - (q_score // 20))
        if q_score >= 90:
            q_stars, q_label = "★★★★★", "Excellent"
        elif q_score >= 75:
            q_stars, q_label = "★★★★☆", "Great"
        elif q_score >= 60:
            q_stars, q_label = "★★★☆☆", "Good"
        elif q_score >= 40:
            q_stars, q_label = "★★☆☆☆", "Fair"
        else:
            q_stars, q_label = "★☆☆☆☆", "Poor"

        impl_type = self.repo.get("impl_type") or "Skills"
        if self.installed:
            action_hint = self.installed_summary()
        elif "skill" in impl_type.lower():
            action_hint = "[bold #9ece6a]Recommended: Press E to Export Skill (no download needed)[/]"
        else:
            action_hint = "[bold #7aa2f7]Recommended: Press Enter to Install Binary / Server[/]"

        meta_info = (
            f"[bold #7aa2f7]{self.repo['name']}[/]\n\n"
            f"[bold #7aa2f7]Type:[/] {impl_type}\n"
            f"[bold #e0af68]Stars:[/] {stars}\n"
            f"[bold #e0af68]Forks:[/] {forks}\n"
            f"[bold #e0af68]Language:[/] {lang}\n"
            f"[bold #bb9af7]License:[/] {license_name}\n"
            f"[bold #9ece6a]Difficulty:[/] {difficulty}\n"
            f"[bold #7aa2f7]Score:[/] {q_score}\n"
            f"[bold #f7768e]Rating:[/] {q_stars} {q_label}\n\n"
            f"{action_hint}\n\n"
            f"[dim]Owner: {self.repo['owner']}[/]\n"
            f"[dim]Updated: {(self.repo.get('updated_at') or '')[:10]}[/]\n"
        )
        self.query_one("#meta-text", Static).update(meta_info)

    def installed_summary(self) -> str:
        """Rich-markup block describing the local install and its update status."""
        from app.local_skills import update_status
        pkg = self.installed
        label, color = update_status(pkg)
        from app.local_skills import parse_frontmatter
        paths = "\n".join(
            f"  {escape(p.replace(os.path.expanduser('~'), '~', 1))} "
            f"(v{escape(parse_frontmatter(os.path.join(p, 'SKILL.md')).get('version') or 'unknown')})"
            for p in pkg.get("local_paths", [])
        )
        text = (
            f"[bold #9ece6a]INSTALLED[/] [dim](as {escape(pkg['package_slug'])})[/]\n"
            f"[bold #7aa2f7]Version:[/] {escape(pkg.get('version') or 'unknown')}"
            f"{' (oldest copy)' if len(pkg.get('local_paths', [])) > 1 else ''}\n"
            f"[bold {color}]{escape(label)}[/]\n"
        )
        if paths:
            text += f"[dim]Location:\n{paths}[/]\n"
        if "update available" in label:
            text += "[bold #e0af68]Press U to update[/]\n"
        return text

    def show_local_details(self, repo_slug: str | None) -> None:
        """Shows what we know from disk when the repo is not in the GitHub cache."""
        meta = self.query_one("#meta-text", Static)
        if not self.installed:
            meta.update(f"[bold #7aa2f7]{escape(self.repo_fullname)}[/]\n\n"
                        + ("[dim]Fetching repository info from GitHub...[/]" if repo_slug
                           else "[red]Not found in the catalog or in your installed skills.[/]"))
            return
        if not repo_slug:
            source = "[dim]No GitHub repository listed in SKILL.md (add a 'repository:' field to enable updates).[/]"
        elif self._repo_fetch_failed:
            source = f"[bold #7aa2f7]Source:[/] {escape(repo_slug)}\n[dim]Could not load repository info from GitHub.[/]"
        else:
            source = f"[bold #7aa2f7]Source:[/] {escape(repo_slug)}\n[dim]Fetching repository info from GitHub...[/]"
        meta.update(f"[bold #7aa2f7]{escape(self.installed['package_slug'])}[/]\n\n"
                    f"{self.installed_summary()}\n{source}\n")
        paths = self.installed.get("local_paths") or []
        skill_md = os.path.join(paths[0], "SKILL.md") if paths else None
        if skill_md and os.path.exists(skill_md):
            with open(skill_md, "r", encoding="utf-8", errors="replace") as f:
                self.query_one("#readme-preview", Markdown).update(f.read())

    async def fetch_repo_async(self, repo_slug: str) -> None:
        repo = await self.app.provider.fetch_repo(repo_slug)
        if repo:
            save_repositories([repo])
            self.load_repository_details()
        else:
            self._repo_fetch_failed = True
            self.show_local_details(repo_slug)

    async def ensure_update_checked(self) -> None:
        errors = await self._run_update_check(force=False)
        if errors:
            self.notify(errors[0], title="Update Check Failed", severity="warning")
        if self.repo:
            self.render_repo_meta()
        else:
            self.show_local_details(self.installed.get("repo_slug"))

    async def fetch_readme_async(self) -> None:
        from app.client import GitHubProvider
        from app.cache import update_repository_readme
        
        full_name = self.repo["full_name"]
        provider = GitHubProvider()
        readme_widget = self.query_one("#readme-preview", Markdown)
        readme_widget.update("_Fetching README from GitHub..._")
        
        content = await provider.fetch_readme(full_name)
        rate_limited = provider.rate_limited
        await provider.close()

        if content is None:
            from app.client import RATE_LIMIT_HINT
            reason = f"GitHub rate limit reached ({RATE_LIMIT_HINT})" if rate_limited else "couldn't reach GitHub"
            readme_widget.update(f"_Couldn't load the README: {reason}. Reopen this page to retry._")
            return
        if not content:
            readme_widget.update("_This repository has no README._")
            return
        # Save to database
        update_repository_readme(full_name, content)
        # Update view
        readme_widget.update(content)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-back":
            self.app.pop_screen()
        elif event.button.id == "btn-install":
            self.action_install()
        elif event.button.id == "btn-update":
            self.action_update_skill()
        elif event.button.id == "btn-export":
            self.action_export_skill()

    def action_install(self) -> None:
        if self.installed:
            self.notify(f"Already installed as '{self.installed['package_slug']}'. Press U to update.",
                        title="Already Installed")
            return
        if not self.repo:
            return
        
        # First push the confirmation dialog screen
        def handle_confirmation(confirmed: bool) -> None:
            if confirmed:
                # Spawn progress log modal
                slug, impl_type = self.repo["full_name"], self.repo.get("impl_type") or "Skills"
                self.app.push_screen(ProgressScreen(f"Installing {slug}...",
                                                    lambda: AsyncInstallRunner.run_install(slug, impl_type)),
                                     callback=lambda _: self.after_change())
        
        self.app.push_screen(InstallConfirmScreen(self.repo), callback=handle_confirmation)

    def action_export_skill(self) -> None:
        if self.installed:
            self.notify(f"Already installed as '{self.installed['package_slug']}'. Exporting would write a second, "
                        "README-only copy. Press U to update instead.", title="Already Installed", severity="warning")
            return
        if not self.repo:
            return

        from app.exporter import export_skill

        def handle_export_target(target: str) -> None:
            if target:
                readme = self.repo.get("readme_preview") or ""
                success, path, msg = export_skill(self.repo, readme, target=target)
                if success:
                    self.notify(f"Exported to {path}", title="Skill Exported", severity="information")
                else:
                    self.notify(msg, title="Export Failed", severity="error")

        self.app.push_screen(ExportConfirmScreen(self.repo["full_name"]), callback=handle_export_target)

    def action_update_skill(self) -> None:
        if not self.installed:
            self.notify("This isn't installed locally.", title="Nothing to Update", severity="warning")
            return
        if not self.installed.get("repo_slug"):
            self.notify("SKILL.md has no 'repository:' GitHub link, so there's no source to update from.",
                        title="Can't Update", severity="warning")
            return
        asyncio.create_task(self._update_flow())

    async def _update_flow(self) -> None:
        from app.local_skills import is_newer, normalize_version, update_skill

        self.notify(f"Checking {self.installed['repo_slug']} for the latest version...", title="Update")
        errors = await self._run_update_check(force=True)
        pkg = self.installed
        if errors or not pkg.get("latest_version"):
            self.notify(errors[0] if errors else "Couldn't determine the latest version.",
                        title="Update Check Failed", severity="error")
            return
        if is_newer(pkg["latest_version"], pkg.get("version")) is False:
            self.notify(f"{pkg['package_slug']} is already up to date (v{normalize_version(pkg.get('version'))}).",
                        title="Up to Date", severity="information")
            return

        def handle_confirmation(confirmed: bool) -> None:
            if not confirmed:
                return
            name, paths, repo_slug = pkg["package_slug"], pkg["local_paths"], pkg["repo_slug"]
            ref, current = pkg.get("latest_ref"), pkg.get("version")
            self.app.push_screen(
                ProgressScreen(f"Updating {name}...", lambda: update_skill(name, paths, repo_slug, ref, current)),
                callback=lambda _: self.after_change()
            )

        self.app.push_screen(UpdateConfirmScreen(pkg), callback=handle_confirmation)

    async def _run_update_check(self, force: bool) -> list[str]:
        from app.local_skills import check_for_updates
        errors = await check_for_updates(self.app.provider, [self.installed], force=force)
        self.installed = get_installed_package(self.installed["package_slug"])
        return errors

    def after_change(self) -> None:
        """Re-reads disk and cache after an install/update so the screen shows the real state."""
        from app.cache import get_installed_packages
        get_installed_packages()  # rescans disk
        self.load_repository_details()
        self.app.refresh_active_views()

    def action_back(self) -> None:
        self.app.pop_screen()


