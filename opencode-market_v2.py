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
    """A terminal UI marketplace for OpenCode tools sorted by functional utilities."""
    
    CSS = """
    Screen {
        background: #1a1b26;
    }
    #main-layout {
        layout: horizontal;
    }
    #sidebar {
        width: 38%;
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
        width: 62%;
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
        self.all_repos = []

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container(id="main-layout"):
            with Vertical(id="sidebar"):
                yield Label("🌐 OpenCode Utility Registry", classes="title")
                yield Tabs(
                    "🔥 All", 
                    "🔍 Research", 
                    "🧠 Memory", 
                    "🛠️ DevTools", 
                    "🛡️ Safety/Auth",
                    "📦 Misc",
                    id="category-tabs"
                )
                yield ListView(id="repo-list")
            with Vertical(id="details-panel"):
                yield Label("ℹ️ Extension Details", classes="title")
                yield Static("Select an entry from the registry to inspect parameters.", id="details-text")
        yield Footer()

    def on_mount(self) -> None:
        self.fetch_trending_repos()

    def fetch_trending_repos(self) -> None:
        self.query_one("#details-text", Static).update("Querying global GitHub registry logs...")
        url = "https://api.github.com/search/repositories?q=opencode+OR+openagent&sort=stars&order=desc&per_page=100"
        try:
            response = requests.get(url, headers={"User-Agent": "OpenCodeMarketplace"}).json()
            self.all_repos = response.get("items", [])
            
            # Explicitly enforce star sorting (Most -> Least) as a defensive programming fallback
            self.all_repos.sort(key=lambda x: x.get("stargazers_count", 0), reverse=True)
            
            current_tab = self.query_one("#category-tabs", Tabs).active_tab
            category_name = str(current_tab.label) if current_tab else "🔥 All"
            self.filter_repos(category_name)
        except Exception as e:
            repo_list = self.query_one("#repo-list", ListView)
            repo_list.clear()
            repo_list.append(ListItem(Label(f"API Error: {str(e)}")))

    def classify_repo(self, repo: dict) -> str:
        """Heuristic scoring matrix to assign tools to clear functional domains."""
        name = repo.get("name", "").lower()
        desc = repo.get("description", "").lower()
        
        # 🔍 Research Utilities (Scrapers, search engines, paper reading tools)
        if any(w in name or w in desc for w in ["research", "search", "crawl", "browse", "osint", "find", "fetch", "web"]):
            return "🔍 Research"
            
        # 🧠 Memory & Context Systems (Vector databases, long term memory, state trees)
        if any(w in name or w in desc for w in ["memory", "mem", "db", "sqlite", "vector", "index", "store", "context", "prun"]):
            return "🧠 Memory"
            
        # 🛡️ Safety, Obfuscation, & Provider Billing Auth wrappers
        if any(w in name or w in desc for w in ["safety", "guard", "auth", "redact", "secret", "key", "token", "credential", "quota"]):
            return "🛡️ Safety/Auth"
            
        # 🛠️ Developer Environment UX Enhancements (PTYs, Snippets, Git isolation loops)
        if any(w in name or w in desc for w in ["pty", "code", "snippet", "worktree", "workspace", "terminal", "git", "make", "lsp"]):
            return "🛠️ DevTools"
            
        return "📦 Misc"

    def filter_repos(self, category: str) -> None:
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
        if event.tab:
            self.filter_repos(str(event.tab.label))

    def on_list_view_selected(self, event: ListView.Selected) -> None:
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
