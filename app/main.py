import asyncio
import json
import logging
from datetime import datetime
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Footer, ListView, ListItem, Label, Static, ContentSwitcher
from textual.screen import Screen

from app.cache import (
    init_db, get_repositories, get_installed_packages, save_repositories, 
    update_repository_quality_score, get_connection
)
from app.client import GitHubProvider
from app.widgets import RepoListItem
from app.classifier import classify_repository, calculate_quality_score
from app.screens import HomeView, BrowseView, CollectionsView, SearchScreen, RepoDetailsScreen, HistoryView

# Configure logger
logging.basicConfig(level=logging.INFO, filename="opencode-hub.log", format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("opencode-hub")

class InstalledView(Vertical):
    """Lists locally installed OpenCode tools with version and status."""
    
    def compose(self) -> ComposeResult:
        yield Label("📦 INSTALLED PACKAGES", classes="view-title")
        yield ListView(id="installed-list")

    def on_mount(self) -> None:
        self.refresh_list()

    def refresh_list(self) -> None:
        installed = get_installed_packages()
        inst_list = self.query_one("#installed-list", ListView)
        inst_list.clear()

        if not installed:
            inst_list.append(ListItem(Label("No packages installed yet. Select a repo and press Enter to install.")))
            return

        for inst in installed:
            slug = inst["package_slug"]
            version = inst["version"]
            status = inst["status"]
            impl_type = inst["impl_type"]
            date_inst = inst["installed_at"]
            
            # Type tag formatting
            icon = "[Agent]"
            if "mcp" in impl_type.lower():
                icon = "[MCP]"
            elif "plugin" in impl_type.lower():
                icon = "[Plugin]"
            elif "skill" in impl_type.lower():
                icon = "[Skill]"
            elif "command" in impl_type.lower():
                icon = "[CLI]"

            text = (
                f"[bold #9ece6a]{icon} {slug}[/]  [dim]|[/]  [bold #7aa2f7]Type:[/] {impl_type}  "
                f"[dim]|[/]  [bold #e0af68]Version:[/] {version}  [dim]|[/]  [bold #9ece6a]Status:[/] {status}\n"
                f"   [dim #565f89]Installed on: {date_inst}[/]"
            )
            
            # Attach metadata to list item for selection details
            item = ListItem(Static(text))
            item.package_slug = slug
            inst_list.append(item)


class OpenCodeHubApp(App):
    """The visual, keyboard-first Hub for the OpenCode Ecosystem."""

    CSS = """
    Screen {
        background: #1a1b26;
        color: #a9b1d6;
    }
    
    #main-layout {
        layout: horizontal;
    }

    #sidebar {
        width: 30%;
        background: #16161e;
        border-right: tall #24283b;
        padding: 1;
    }

    #content-area {
        width: 70%;
        padding: 1 2;
    }

    /* Sidebar list styling */
    #sidebar-list {
        background: transparent;
        border: none;
    }

    .sidebar-header {
        text-style: bold;
        color: #bb9af7;
        margin: 1 0 0 1;
    }

    .sidebar-item {
        padding: 0 1;
        margin-bottom: 0;
        background: transparent;
        color: #a9b1d6;
        height: 1;
    }

    .sidebar-item:focus {
        background: #24283b;
        color: #7aa2f7;
        text-style: bold;
    }

    /* List styling */
    ListView {
        background: transparent;
        border: none;
    }

    ListItem {
        background: #1e2030;
        border: solid #24283b;
        margin-bottom: 1;
        padding: 1 2;
    }

    ListItem:focus {
        background: #2f334d;
        border: solid #7aa2f7;
        color: #c0caf5;
    }

    /* Header visual titles */
    .view-title {
        text-style: bold;
        color: #7aa2f7;
        margin-bottom: 1;
        background: #16161e;
        padding: 1 2;
        border-left: solid #bb9af7;
    }

    .section-header-text {
        text-style: bold;
        color: #bb9af7;
        margin-top: 1;
        margin-bottom: 1;
    }

    /* Modals & Dialogs styling */
    #spotlight-dialog {
        width: 60%;
        height: 60%;
        background: #16161e;
        border: tall #7aa2f7;
        padding: 1 2;
        margin: 2 4;
    }

    #search-input {
        background: #1a1b26;
        border: solid #24283b;
        color: #a9b1d6;
        margin-bottom: 1;
    }

    #search-input:focus {
        border: solid #7aa2f7;
    }

    #confirm-dialog, #progress-dialog {
        width: 50%;
        height: auto;
        background: #16161e;
        border: tall #7aa2f7;
        padding: 2;
        margin: 2 4;
    }

    #confirm-title, #progress-title {
        text-style: bold;
        color: #7aa2f7;
        margin-bottom: 1;
        text-align: center;
    }

    #confirm-body {
        margin: 1 0;
        padding: 1;
        background: #1e2030;
        border: solid #24283b;
    }

    .confirm-buttons {
        align: center middle;
        margin-top: 1;
        height: 3;
    }

    #log-container {
        height: 10;
        background: #1a1b26;
        border: solid #24283b;
        padding: 1;
        margin: 1 0;
    }

    #progress-log {
        color: #a9b1d6;
    }
    
    .filter-badge {
        color: #e0af68;
        background: #24283b;
        padding: 0 1;
        margin-bottom: 1;
        align: right middle;
    }
    
    .dim-text {
        color: #565f89;
    }
    
    .repo-card-text {
    }
    """

    BINDINGS = [
        ("h", "switch_view('home')", "Home"),
        ("b", "switch_view('browse')", "Browse"),
        ("c", "switch_view('collections')", "Collections"),
        ("s", "open_search", "Search"),
        ("/", "open_search", "Search"),
        ("enter", "show_details", "Details"),
        ("e", "export_skill", "Export Skill"),
        ("i", "switch_view('installed')", "Installed"),
        ("l", "switch_view('history')", "History"),
        ("f", "cycle_filter", "Filter"),
        ("r", "refresh_registry", "Refresh"),
        ("q", "quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container(id="main-layout"):
            # Sidebar Left Panel
            with Vertical(id="sidebar"):
                yield Label("OPENHUB", classes="sidebar-title", id="hub-logo")
                
                with ListView(id="sidebar-list"):
                    # Navigation Items
                    yield ListItem(Label("Home Dashboard"), id="nav-home")
                    yield ListItem(Label("Installed Packages"), id="nav-installed")
                    yield ListItem(Label("Operation History"), id="nav-history")
                    
                    # Use Cases Categories
                    yield ListItem(Label("USE CASES:"), disabled=True)
                    yield ListItem(Label("  Web Research"), id="uc-web")
                    yield ListItem(Label("  Coding"), id="uc-code")
                    yield ListItem(Label("  Debugging"), id="uc-debug")
                    yield ListItem(Label("  Testing"), id="uc-test")
                    yield ListItem(Label("  Documentation"), id="uc-doc")
                    yield ListItem(Label("  Automation"), id="uc-auto")
                    yield ListItem(Label("  Cloud"), id="uc-cloud")
                    yield ListItem(Label("  Database"), id="uc-db")
                    yield ListItem(Label("  Security"), id="uc-sec")
                    yield ListItem(Label("  UI"), id="uc-ui")
                    yield ListItem(Label("  Data Science"), id="uc-data")
                    yield ListItem(Label("  Multi-Agent"), id="uc-multi")
                    
                    # Curated Collections
                    yield ListItem(Label("CURATED COLLECTIONS:"), disabled=True)
                    yield ListItem(Label("  AI Engineer Pack"), id="coll-ai")
                    yield ListItem(Label("  Research Essentials"), id="coll-research")
                    yield ListItem(Label("  Terminal Power User"), id="coll-terminal")
                    yield ListItem(Label("  Best Coding Agents"), id="coll-coding")
                    yield ListItem(Label("  Best MCP Servers"), id="coll-mcp")
                    yield ListItem(Label("  Claude Workflow"), id="coll-claude")
                    yield ListItem(Label("  Cursor Workflow"), id="coll-cursor")
                    yield ListItem(Label("  Python Toolkit"), id="coll-python")
            
            # Content Area Right Panel
            with Container(id="content-area"):
                with ContentSwitcher(initial="home"):
                    yield HomeView(id="home")
                    yield BrowseView(id="browse")
                    yield CollectionsView(id="collections")
                    yield InstalledView(id="installed")
                    yield HistoryView(id="history")
        yield Footer()

    def on_mount(self) -> None:
        init_db()
        self.provider = GitHubProvider()
        
        # INSTANT BOOT: Load cached repos from SQLite first, or seed if empty
        cached = get_repositories(limit=500)
        if not cached:
            from app.client import SEED_REPOSITORIES
            save_repositories(SEED_REPOSITORIES)
            logger.info("No cache found — seeded with offline catalog for instant boot.")
        
        # Render immediately from cache/seeds
        self.refresh_active_views()
        
        # Background: sync fresh data from GitHub (user sees UI instantly)
        asyncio.create_task(self.fetch_registry_async())
        # Background: quality scorer
        asyncio.create_task(self.run_quality_scorer_worker())

    async def fetch_registry_async(self) -> None:
        """Fetches trending items from GitHub in the background without blocking UI."""
        logger.info("Starting background repository synchronization")
        try:
            repos = await self.provider.fetch_trending()
            if repos:
                save_repositories(repos)
                self.refresh_active_views()
                self.notify(f"Registry synced: {len(repos)} repos loaded from GitHub.", title="Sync Complete", severity="information")
                logger.info(f"Background sync complete: {len(repos)} repos")
        except Exception as e:
            logger.warning(f"Background sync failed: {e}")
            self.notify("GitHub sync failed. Showing cached data.", title="Sync Error", severity="warning")

    async def run_quality_scorer_worker(self) -> None:
        """Background loop calculating quality scores and classifications asynchronously."""
        while True:
            await asyncio.sleep(2.0)
            try:
                # Find unscored items in database
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute("""
                SELECT id, name, owner, full_name, description, tags, stars, forks, open_issues, license, updated_at
                FROM repositories 
                WHERE quality_score IS NULL 
                LIMIT 5
                """)
                unscored = [dict(row) for row in cursor.fetchall()]
                conn.close()

                if not unscored:
                    continue

                for r in unscored:
                    r["tags"] = eval(r["tags"]) if isinstance(r["tags"], str) else r["tags"]
                    
                    logger.info(f"Worker scoring: {r['full_name']}")
                    # Fetch readme for smart classification/scoring
                    readme = await self.provider.fetch_readme(r["full_name"])
                    
                    # Compute classification and quality scores
                    use_case, impl_type, difficulty = classify_repository(r, readme)
                    q = calculate_quality_score(r, readme)
                    
                    # Save details back to SQLite
                    conn = get_connection()
                    cursor = conn.cursor()
                    cursor.execute("""
                    UPDATE repositories 
                    SET use_case=?, impl_type=?, difficulty=?, readme_preview=?, quality_score=?, quality_breakdown=? 
                    WHERE full_name=?
                    """, (
                        use_case, impl_type, difficulty, readme, q["score"], 
                        json.dumps(q["breakdown"]), r["full_name"]
                    ))
                    conn.commit()
                    conn.close()
                    
                    await asyncio.sleep(0.5)  # Throttling
                
                # Refresh UI
                self.refresh_active_views()

            except Exception as e:
                logger.error(f"Scorer worker exception: {e}")

    def refresh_active_views(self) -> None:
        """Forces lists in switcher views to refresh logs and databases."""
        switcher = self.query_one(ContentSwitcher)
        
        if switcher.current == "home":
            self.query_one("#home", HomeView).refresh_dashboard()
        elif switcher.current == "browse":
            self.query_one("#browse", BrowseView).refresh_list()
        elif switcher.current == "collections":
            self.query_one("#collections", CollectionsView).refresh_list()
        elif switcher.current == "installed":
            self.query_one("#installed", InstalledView).refresh_list()
        elif switcher.current == "history":
            self.query_one("#history", HistoryView).refresh_logs()

    def action_switch_view(self, view_name: str) -> None:
        """Triggers view swaps inside ContentSwitcher."""
        switcher = self.query_one(ContentSwitcher)
        switcher.current = view_name
        self.refresh_active_views()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handles selections inside lists (sidebar switches and card detail viewing)."""
        list_id = event.list_view.id
        
        if list_id == "sidebar-list":
            # Sidebar Navigation
            item_id = event.item.id
            if item_id == "nav-home":
                self.action_switch_view("home")
            elif item_id == "nav-installed":
                self.action_switch_view("installed")
            elif item_id == "nav-history":
                self.action_switch_view("history")
            
            # Use Case selection
            elif item_id.startswith("uc-"):
                uc_map = {
                    "uc-web": "Web Research",
                    "uc-code": "Coding",
                    "uc-debug": "Debugging",
                    "uc-test": "Testing",
                    "uc-doc": "Documentation",
                    "uc-auto": "Automation",
                    "uc-cloud": "Cloud",
                    "uc-db": "Database",
                    "uc-sec": "Security",
                    "uc-ui": "UI",
                    "uc-data": "Data Science",
                    "uc-multi": "Multi-Agent"
                }
                uc_name = uc_map.get(item_id)
                self.action_switch_view("browse")
                self.query_one("#browse", BrowseView).update_use_case(uc_name)

            # Curated Collections selection
            elif item_id.startswith("coll-"):
                coll_map = {
                    "coll-ai": "AI Engineer Starter Pack",
                    "coll-research": "Research Essentials",
                    "coll-terminal": "Terminal Power User",
                    "coll-coding": "Best Coding Agents",
                    "coll-mcp": "Best MCP Servers",
                    "coll-claude": "Claude Workflow",
                    "coll-cursor": "Cursor Workflow",
                    "coll-python": "Python Developer Toolkit"
                }
                coll_name = coll_map.get(item_id)
                self.action_switch_view("collections")
                self.query_one("#collections", CollectionsView).update_collection(coll_name)

        elif list_id in ["home-list", "browse-list", "collection-list", "installed-list"]:
            # Repository Card selected -> Push Details Screen
            selected_item = event.item
            # Extract fullname
            if hasattr(selected_item, "repo"):
                fullname = selected_item.repo["full_name"]
                self.push_screen(RepoDetailsScreen(fullname))
            elif hasattr(selected_item, "package_slug"):
                self.push_screen(RepoDetailsScreen(selected_item.package_slug))

    def action_open_search(self) -> None:
        """Spotlight Search shortcut (S or /)."""
        self.push_screen(SearchScreen())

    def action_show_details(self) -> None:
        """Details hotkey (i) - Opens highlighted list item details."""
        focused_list = self.query("ListView").first() # checks current active lists
        if focused_list and focused_list.highlighted_child:
            selected = focused_list.highlighted_child
            if hasattr(selected, "repo"):
                self.push_screen(RepoDetailsScreen(selected.repo["full_name"]))

    def action_export_skill(self) -> None:
        """Export skill hotkey (e) - Opens export dialog for highlighted item."""
        focused_list = self.query("ListView").first()
        if focused_list and focused_list.highlighted_child:
            selected = focused_list.highlighted_child
            if hasattr(selected, "repo"):
                self.push_screen(RepoDetailsScreen(selected.repo["full_name"]))

    def action_refresh_registry(self) -> None:
        """Force refresh registry data (r)."""
        asyncio.create_task(self.fetch_registry_async())

    def action_cycle_filter(self) -> None:
        """Cycle implementation type filters (f)."""
        switcher = self.query_one(ContentSwitcher)
        if switcher.current == "browse":
            self.query_one("#browse", BrowseView).cycle_impl_filter()

    async def on_close(self) -> None:
        await self.provider.close()

def cli():
    """Main CLI entrypoint for openhub command."""
    OpenCodeHubApp().run()

if __name__ == "__main__":
    cli()
