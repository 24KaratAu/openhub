import os
import subprocess
import requests
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Footer, ListView, ListItem, Label, Static, Tabs

class RepoItem(ListItem):
    """Custom list item to store repository metadata cleanly."""
    def __init__(self, repo_data: dict) -> None:
        super().__init__()
        self.repo_data = repo_data
        self.repo_name = repo_data.get("full_name", "Unknown/Repo")
        self.stars = repo_data.get("stargazers_count", 0)

    def compose(self) -> ComposeResult:
        yield Label(f"⭐ {self.stars:<6} | {self.repo_name}")

class OpenCodeMarketplace(App):
    """A beautiful terminal UI marketplace for OpenCode tools with smart categories."""
    
    CSS = """
    Screen {
        background: #1a1b26;
    }
    #main-layout {
        layout: horizontal;
    }
    #sidebar {
        width: 35%;
        background: #16161e;
        border-right: tall #24283b;
        padding: 1;
    }
    #category-tabs {
        background: #16161e;
        border: none;
        margin-bottom: 1;
        min-height: 3;
    }
    #details-panel {
        width: 65%;
        padding: 2;
        background: #1f2335;
    }
    .title {
        text-style: bold;
        color: #7aa2f7;
        margin-bottom: 1;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "refresh", "Refresh Trends"),
        ("enter", "install", "Install Selected"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.all_repos = []  # Local memory cache to prevent API rate throttling

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container(id="main-layout"):
            with Vertical(id="sidebar"):
                yield Label("🌐 OpenCode Ecosystem Hub", classes="title")
                yield Tabs(
                    "🔥 All", 
                    "🤖 Agents", 
                    "⚡ Skills", 
                    "🔌 MCP", 
                    id="category-tabs"
                )
                yield ListView(id="repo-list")
            with Vertical(id="details-panel"):
                yield Label("ℹ️ Extension Details", classes="title")
                yield Static("Select an entry from the registry to inspect parameters.", id="details-text")
        yield Footer()

    def on_mount(self) -> None:
        """Fetch primary data from GitHub on load."""
        self.fetch_trending_repos()

    def fetch_trending_repos(self) -> None:
        self.query_one("#details-text", Static).update("Querying global GitHub registry logs...")
        url = "https://api.github.com/search/repositories?q=opencode+OR+openagent&sort=stars&order=desc&per_page=50"
        try:
            response = requests.get(url, headers={"User-Agent": "OpenCodeMarketplace"}).json()
            self.all_repos = response.get("items", [])
            
            # Re-trigger current tab view classification
            current_tab = self.query_one("#category-tabs", Tabs).active_tab
            category_name = str(current_tab.label) if current_tab else "🔥 All"
            self.filter_repos(category_name)
        except Exception as e:
            repo_list = self.query_one("#repo-list", ListView)
            repo_list.clear()
            repo_list.append(ListItem(Label(f"API Error: {str(e)}")))

    def classify_repo(self, repo: dict) -> str:
        """Heuristic analyzer sorting items into ecosystem taxonomy slots."""
        name = repo.get("name", "").lower()
        desc = repo.get("description", "").lower()
        
        if "mcp" in name or "mcp" in desc:
            return "🔌 MCP"
        if "agent" in name or "agent" in desc or "swarm" in name:
            return "🤖 Agents"
        if "skill" in name or "skill" in desc or "plugin" in name:
            return "⚡ Skills"
        return "Other"

    def filter_repos(self, category: str) -> None:
        """Renders items from local cache matching the targeted tab classification."""
        repo_list = self.query_one("#repo-list", ListView)
        repo_list.clear()
        
        if not self.all_repos:
            repo_list.append(ListItem(Label("No data cached yet.")))
            return

        for repo in self.all_repos:
            if category == "🔥 All":
                repo_list.append(RepoItem(repo))
            elif self.classify_repo(repo) == category:
                repo_list.append(RepoItem(repo))

    def on_tabs_tab_activated(self, event: Tabs.TabActivated) -> None:
        """Listens for active tab updates and repaints UI from cache instantly."""
        if event.tab:
            self.filter_repos(str(event.tab.label))

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Update display details panel with proper character escaping flags."""
        if hasattr(event.item, "repo_data"):
            data = event.item.repo_data
            details = (
                f"[bold #7aa2f7]Name:[/] {data.get('name')}\n"
                f"[bold #7aa2f7]Author:[/] {data.get('owner', {}).get('login')}\n"
                f"[bold #e0af68]Stars:[/] {data.get('stargazers_count')} | "
                f"[bold #9ece6a]Forks:[/] {data.get('forks_count')}\n\n"
                f"[bold #bb9af7]Description:[/]\n{data.get('description', 'No description provided.')}\n\n"
                f"[dim]URL: {data.get('html_url')}[/dim]\n\n"
                f"[bold #f7768e]Press (Enter) to run installation background thread.[/]"
            )
            self.query_one("#details-text", Static).update(details)

    def action_refresh(self) -> None:
        self.fetch_trending_repos()

    def action_install(self) -> None:
        repo_list = self.query_one("#repo-list", ListView)
        selected_item = repo_list.highlighted_child
        
        if selected_item and hasattr(selected_item, "repo_data"):
            slug = selected_item.repo_data.get("full_name")
            details_panel = self.query_one("#details-text", Static)
            
            details_panel.update(f"[bold color=#e0af68]🚀 Running background install for {slug}...[/bold color]")
            cmd = f"zsh -i -c 'opencode get {slug}'"
            
            try:
                process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                stdout, stderr = process.communicate(timeout=15)
                
                if process.returncode == 0:
                    details_panel.update(f"[bold color=#9ece6a]✅ Successfully installed {slug}![/bold color]\n\n{stdout}")
                else:
                    details_panel.update(f"[bold color=#f7768e]❌ Installation failed.[/bold color]\n\n{stderr}")
            except Exception as e:
                details_panel.update(f"[bold color=#f7768e]❌ Error: {str(e)}[/bold color]")

if __name__ == "__main__":
    OpenCodeMarketplace().run()
