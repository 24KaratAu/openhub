from textual.app import ComposeResult
from textual.containers import Vertical, ScrollableContainer
from textual.widgets import Static, ListView, ListItem, Label
from app.widgets import RepoListItem
from app.cache import get_repositories

COLLECTIONS_META = {
    "AI Engineer Starter Pack": ["agent", "llm", "mcp", "framework"],
    "Research Essentials": ["research", "search", "crawl", "scrape", "browse"],
    "Terminal Power User": ["terminal", "cli", "shell", "interpreter", "local-execution"],
    "Best Coding Agents": ["agent", "coding", "autogen", "browser-automation"],
    "Best MCP Servers": ["mcp", "database", "postgres", "sqlite", "devtools"],
    "Claude Workflow": ["mcp", "claude-desktop", "installer"],
    "Cursor Workflow": ["cursor", "editor-skills", "coding"],
    "Python Developer Toolkit": ["python", "devtools", "testing", "assertions"]
}

class CollectionsView(ScrollableContainer):
    """Displays thematic curated list groups dynamically matched against cache tags."""
    
    def __init__(self, collection_name: str = "AI Engineer Starter Pack", **kwargs) -> None:
        super().__init__(**kwargs)
        self.collection_name = collection_name

    def compose(self) -> ComposeResult:
        yield Label(f"COLLECTION: {self.collection_name}", id="collection-title", classes="view-title")
        yield ListView(id="collection-list")

    def update_collection(self, new_collection: str) -> None:
        self.collection_name = new_collection
        self.query_one("#collection-title", Label).update(f"COLLECTION: {self.collection_name}")
        self.refresh_list()

    def on_mount(self) -> None:
        self.refresh_list()

    def refresh_list(self) -> None:
        repos = get_repositories(limit=200)
        collection_list = self.query_one("#collection-list", ListView)
        collection_list.clear()

        keywords = COLLECTIONS_META.get(self.collection_name, [])
        filtered_repos = []

        for r in repos:
            # Build search context from name, description, tags, use case, language
            text_context = f"{r['name']} {r.get('description') or ''} {' '.join(r.get('tags') or [])} {r.get('language') or ''} {r.get('use_case') or ''}".lower()
            
            # Simple keyword matching heuristic
            match = False
            for kw in keywords:
                if kw.lower() in text_context:
                    match = True
                    break
            
            # Specialized fallback criteria for collections
            if self.collection_name == "Best Coding Agents":
                if r.get("impl_type") == "Agents" and r.get("language") in ["Python", "TypeScript"]:
                    match = True
            elif self.collection_name == "Best MCP Servers":
                if r.get("impl_type") == "MCP Servers" or "mcp" in r["full_name"].lower():
                    match = True
            
            if match:
                filtered_repos.append(r)

        if not filtered_repos:
            collection_list.append(ListItem(Label(f"No repositories matched the criteria for '{self.collection_name}'.")))
            return

        for r in filtered_repos:
            collection_list.append(RepoListItem(r))
