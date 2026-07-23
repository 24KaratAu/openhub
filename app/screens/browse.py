from textual.app import ComposeResult
from textual.containers import Vertical, ScrollableContainer, Horizontal
from textual.widgets import Static, ListView, ListItem, Label
from app.widgets import RepoListItem
from app.cache import get_repositories

class BrowseView(ScrollableContainer):
    """Lists repositories grouped by specific functional Use Cases with sub-filtering."""
    
    def __init__(self, use_case: str = "Web Research", **kwargs) -> None:
        super().__init__(**kwargs)
        self.use_case = use_case
        self.impl_filter = None  # None means all types

    def compose(self) -> ComposeResult:
        yield Label(f"BROWSE: {self.use_case}", id="browse-title", classes="view-title")
        yield Label("Press [F] to cycle filters: All Types", id="filter-indicator", classes="filter-badge")
        yield ListView(id="browse-list")

    def update_use_case(self, new_use_case: str) -> None:
        self.use_case = new_use_case
        self.query_one("#browse-title", Label).update(f"BROWSE: {self.use_case}")
        self.refresh_list()

    def cycle_impl_filter(self) -> None:
        from app.classifier import IMPL_TYPES
        if self.impl_filter is None:
            self.impl_filter = IMPL_TYPES[0]
        else:
            idx = IMPL_TYPES.index(self.impl_filter)
            if idx == len(IMPL_TYPES) - 1:
                self.impl_filter = None
            else:
                self.impl_filter = IMPL_TYPES[idx + 1]
        
        filter_text = f"Filter: {self.impl_filter}" if self.impl_filter else "Filter: All Types"
        self.query_one("#filter-indicator", Label).update(f"Press [F] to cycle filters: {filter_text}")
        self.refresh_list()

    def on_mount(self) -> None:
        self.refresh_list()

    def refresh_list(self) -> None:
        repos = get_repositories(limit=200)
        browse_list = self.query_one("#browse-list", ListView)
        browse_list.clear()

        filtered_repos = [
            r for r in repos 
            if (r.get("use_case") or "").lower() == self.use_case.lower()
        ]

        if self.impl_filter:
            filtered_repos = [
                r for r in filtered_repos 
                if (r.get("impl_type") or "").lower() == self.impl_filter.lower()
            ]

        if not filtered_repos:
            browse_list.append(ListItem(Label(f"No repositories found matching '{self.use_case}' / filter '{self.impl_filter or 'All'}'")))
            return

        for r in filtered_repos:
            browse_list.append(RepoListItem(r))
