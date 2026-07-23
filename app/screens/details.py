import asyncio
from textual.app import ComposeResult
from textual.screen import Screen, ModalScreen
from textual.containers import Container, Vertical, Horizontal, ScrollableContainer
from textual.widgets import Static, Button, Markdown, Label, Header, Footer
from app.installer import AsyncInstallRunner
from app.cache import get_repository_by_fullname

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


class InstallProgressScreen(ModalScreen):
    """Asynchronous install logs visualization screen."""
    
    def __init__(self, slug: str, impl_type: str) -> None:
        super().__init__()
        self.slug = slug
        self.impl_type = impl_type

    def compose(self) -> ComposeResult:
        yield Vertical(
            Label(f"Installing {self.slug}...", id="progress-title"),
            ScrollableContainer(
                Static("", id="progress-log"),
                id="log-container"
            ),
            Button("Dismiss", id="btn-dismiss", disabled=True),
            id="progress-dialog"
        )

    def on_mount(self) -> None:
        self.run_installation()

    def run_installation(self) -> None:
        asyncio.create_task(self._install_loop())

    async def _install_loop(self) -> None:
        log_widget = self.query_one("#progress-log", Static)
        log_text = ""
        
        async for line in AsyncInstallRunner.run_install(self.slug, self.impl_type):
            log_text += line + "\n"
            log_widget.update(log_text)
            # Auto scroll to bottom
            log_container = self.query_one("#log-container", ScrollableContainer)
            log_container.scroll_to(y=log_container.max_scroll_y)
            await asyncio.sleep(0.05)
            
        # Enable dismiss button once installation completes
        self.query_one("#btn-dismiss", Button).disabled = False

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-dismiss":
            self.dismiss()


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
            Static("[bold #7aa2f7]Select destination directory for SKILL.md:[/]\n\n"
                   "• [bold #9ece6a]Project (P):[/] Write to `./.opencode/skills/` (Local workspace)\n"
                   "• [bold #e0af68]Global (G):[/]  Write to `~/.config/opencode/skills/` (System user)", id="confirm-body"),
            Horizontal(
                Button("Project (.opencode)", variant="success", id="btn-project"),
                Button("Global (~/.config)", variant="primary", id="btn-global"),
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
    """Detailed inspection panel displaying full metadata and README preview."""
    
    BINDINGS = [
        ("escape", "back", "Back"),
        ("enter", "install", "Install"),
        ("e", "export_skill", "Export Skill")
    ]
    
    def __init__(self, repo_fullname: str) -> None:
        super().__init__()
        self.repo_fullname = repo_fullname
        self.repo = None

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="details-layout"):
            with Vertical(id="details-sidebar"):
                yield Label("DETAILS", classes="sidebar-title")
                yield Static("Loading details...", id="meta-text")
                yield Button("Install (Enter)", variant="success", id="btn-install")
                yield Button("Export Skill (E)", variant="primary", id="btn-export")
                yield Button("Back (Esc)", variant="default", id="btn-back")
            with ScrollableContainer(id="readme-container"):
                yield Markdown("", id="readme-preview")
        yield Footer()

    def on_mount(self) -> None:
        self.load_repository_details()

    def load_repository_details(self) -> None:
        self.repo = get_repository_by_fullname(self.repo_fullname)
        if not self.repo:
            self.query_one("#meta-text", Static).update("[red]Repository not found in cache.[/]")
            return

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
        if "skill" in impl_type.lower():
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
            f"[dim]Updated: {self.repo.get('updated_at', '')[:10]}[/]\n"
        )
        self.query_one("#meta-text", Static).update(meta_info)

        # Load Readme markdown
        readme_content = self.repo.get("readme_preview")
        if readme_content:
            self.query_one("#readme-preview", Markdown).update(readme_content)
        else:
            # Trigger background readme load from network
            asyncio.create_task(self.fetch_readme_async())

    async def fetch_readme_async(self) -> None:
        from app.client import GitHubProvider
        from app.cache import update_repository_readme
        
        provider = GitHubProvider()
        readme_widget = self.query_one("#readme-preview", Markdown)
        readme_widget.update("_Fetching README from GitHub..._")
        
        content = await provider.fetch_readme(self.repo_fullname)
        await provider.close()
        
        # Save to database
        update_repository_readme(self.repo_fullname, content)
        # Update view
        readme_widget.update(content)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-back":
            self.app.pop_screen()
        elif event.button.id == "btn-install":
            self.action_install()
        elif event.button.id == "btn-export":
            self.action_export_skill()

    def action_install(self) -> None:
        if not self.repo:
            return
        
        # First push the confirmation dialog screen
        def handle_confirmation(confirmed: bool) -> None:
            if confirmed:
                # Spawn progress log modal
                self.app.push_screen(InstallProgressScreen(self.repo["full_name"], self.repo.get("impl_type") or "Skills"))
        
        self.app.push_screen(InstallConfirmScreen(self.repo), callback=handle_confirmation)

    def action_export_skill(self) -> None:
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

    def action_back(self) -> None:
        self.app.pop_screen()


