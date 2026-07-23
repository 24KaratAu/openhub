from textual.app import ComposeResult
from textual.containers import Vertical, ScrollableContainer
from textual.widgets import Static, ListView, ListItem, Label
from app.widgets import RepoListItem
from app.cache import get_repositories, get_installed_packages

class SectionHeader(ListItem):
    """Visual header divider in the main ListView."""
    def __init__(self, title: str) -> None:
        super().__init__()
        self.title = title
        self.disabled = True  # Prevent focusing on headers

    def compose(self) -> ComposeResult:
        yield Label(f"\n{self.title}", classes="section-header-text")


class HomeView(ScrollableContainer):
    """The central catalog dashboard showing trending, new, and installed tools."""
    
    def compose(self) -> ComposeResult:
        yield Label("HOME DASHBOARD", classes="view-title")
        yield ListView(id="home-list")

    def on_mount(self) -> None:
        self.refresh_dashboard()

    def refresh_dashboard(self) -> None:
        repos = get_repositories(limit=150)
        installed = get_installed_packages()
        
        home_list = self.query_one("#home-list", ListView)
        home_list.clear()

        if not repos:
            home_list.append(ListItem(Label("No repositories cached yet. Run Refresh [r].")))
            return

        # 1. Trending Today (Sorted by Stars)
        trending = sorted(repos, key=lambda x: x.get("stars", 0), reverse=True)[:3]
        home_list.append(SectionHeader("TRENDING TODAY"))
        for r in trending:
            home_list.append(RepoListItem(r))

        # 2. Just Released (Sorted by created_at)
        new_released = sorted(repos, key=lambda x: x.get("created_at") or "", reverse=True)[:3]
        home_list.append(SectionHeader("JUST RELEASED"))
        for r in new_released:
            home_list.append(RepoListItem(r))

        # 3. Fastest Growing (Sorted by forks)
        fast_growing = sorted(repos, key=lambda x: x.get("forks", 0), reverse=True)[:3]
        home_list.append(SectionHeader("FASTEST GROWING"))
        for r in fast_growing:
            home_list.append(RepoListItem(r))

        # 4. Hidden Gems (High Quality, Lower Stars)
        hidden_gems = [r for r in repos if (r.get("quality_score") or 0) >= 80 and r.get("stars", 0) < 2000][:3]
        if hidden_gems:
            home_list.append(SectionHeader("HIDDEN GEMS"))
            for r in hidden_gems:
                home_list.append(RepoListItem(r))

        # 5. Editor's Picks (Curated selections)
        editors_picks = [r for r in repos if r["full_name"] in [
            "browser-use/browser-use", "modelcontextprotocol/servers", "OpenInterpreter/open-interpreter"
        ]]
        if editors_picks:
            home_list.append(SectionHeader("EDITOR'S PICKS"))
            for r in editors_picks:
                home_list.append(RepoListItem(r))

        # 6. Recently Installed
        home_list.append(SectionHeader("RECENTLY INSTALLED"))
        if installed:
            installed_slugs = [inst["package_slug"] for inst in installed[:3]]
            installed_repos = [r for r in repos if r["full_name"] in installed_slugs]
            for r in installed_repos:
                home_list.append(RepoListItem(r))
            if not installed_repos:
                for inst in installed[:3]:
                    # Draw a mini text representation if the full repo is missing
                    home_list.append(ListItem(Label(f"INSTALLED: {inst['package_slug']} - Version {inst['version']}")))
        else:
            home_list.append(ListItem(Label("   No packages installed yet. Select a repo and press Enter.", classes="dim-text")))
