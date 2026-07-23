import math
import asyncio
from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.containers import Vertical, ScrollableContainer
from textual.widgets import Input, ListView, ListItem, Label
from rapidfuzz import fuzz
from app.widgets import RepoListItem
from app.cache import get_repositories
from app.screens.details import RepoDetailsScreen

def _normalize_word(w: str) -> str:
    w = w.lower()
    if w.endswith("s") and len(w) > 3:
        w = w[:-1]
    return w

class SearchScreen(ModalScreen):
    """A Spotlight-style modal search bar overlaying the active workspace."""

    def compose(self) -> ComposeResult:
        yield Vertical(
            Input(placeholder="Search skills, agents, MCP servers... (fetches live from GitHub)", id="search-input"),
            ListView(id="search-results-list"),
            id="spotlight-dialog"
        )

    def on_mount(self) -> None:
        self.repos = get_repositories(limit=500)
        self._remote_fetched_for = set()
        self._debounce_timer = None
        self.query_one("#search-input", Input).focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        query = event.value.strip()
        results_list = self.query_one("#search-results-list", ListView)
        results_list.clear()

        if not query or len(query) < 2:
            return

        # Perform high-precision local search
        matched = self._local_search(query)

        # Render all local matched results (up to 100)
        for r, score in matched[:100]:
            results_list.append(RepoListItem(r))

        # Cancel any previous debounced remote search timer
        if self._debounce_timer is not None:
            self._debounce_timer.cancel()

        # Schedule debounced remote GitHub search if not fetched yet
        if query not in self._remote_fetched_for and len(query) >= 3:
            if not matched:
                results_list.append(ListItem(Label("Searching GitHub...")))
            else:
                results_list.append(ListItem(Label("Loading more from GitHub...")))
            
            # Debounce by 350ms to prevent flooding GitHub API on keystrokes
            self._debounce_timer = asyncio.get_event_loop().call_later(
                0.35, lambda q=query: asyncio.create_task(self._fetch_remote_and_refresh(q))
            )

    def _local_search(self, query: str) -> list:
        """Run token-matching and fuzzy search against locally cached repositories."""
        matched = []
        query_tokens = [_normalize_word(w) for w in query.split() if len(w) > 1]
        
        for repo in self.repos:
            full_text = f"{repo['name']} {repo['owner']} {repo.get('description', '')} {' '.join(repo.get('tags', []))} {repo.get('use_case', '')} {repo.get('impl_type', '')}".lower()
            full_tokens = [_normalize_word(w) for w in full_text.split()]
            
            # 1. Calculate token overlap ratio
            matched_tokens = sum(1 for qt in query_tokens if any(qt in ft for ft in full_tokens))
            overlap_ratio = matched_tokens / len(query_tokens) if query_tokens else 0
            
            # 2. Fuzzy score using token_set_ratio
            fuzzy_score = fuzz.token_set_ratio(query, full_text)
            
            # 3. Base composite score
            score = (overlap_ratio * 75) + (fuzzy_score * 0.25)
            
            # 4. Exact name / token boost
            name_text = f"{repo['name']} {repo['owner']}".lower()
            if query_tokens and all(qt in name_text for qt in query_tokens):
                score += 35
                
            # 5. Stargazer popularity boost
            stars = repo.get("stars", 0)
            if stars > 0:
                score += math.log10(stars) * 2

            if score > 35 or overlap_ratio > 0.4:
                matched.append((repo, score))

        matched.sort(key=lambda x: x[1], reverse=True)
        return matched

    async def _fetch_remote_and_refresh(self, query: str) -> None:
        """Fetch results from GitHub API and merge into local cache, then re-render."""
        if query in self._remote_fetched_for:
            return
        self._remote_fetched_for.add(query)

        from app.client import GitHubProvider
        from app.cache import save_repositories, get_repositories

        try:
            provider = GitHubProvider()
            remote_repos = await provider.search(query)
            await provider.close()
        except Exception:
            remote_repos = []

        results_list = self.query_one("#search-results-list", ListView)

        if remote_repos:
            save_repositories(remote_repos)
            self.repos = get_repositories(limit=500)

            # Re-render if the user's active query matches
            input_widget = self.query_one("#search-input", Input)
            current_query = input_widget.value.strip()
            if current_query == query:
                results_list.clear()
                matched = self._local_search(current_query)
                if matched:
                    for r, score in matched[:100]:
                        results_list.append(RepoListItem(r))
                else:
                    results_list.append(ListItem(Label("No results found on GitHub.")))
        else:
            # Remote returned nothing, clear loading indicator if still present
            input_widget = self.query_one("#search-input", Input)
            if input_widget.value.strip() == query:
                if results_list.children:
                    last = results_list.children[-1]
                    if not hasattr(last, "repo"):
                        last.remove()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Pressing Enter on an item opens the details screen."""
        item = event.item
        if item and hasattr(item, "repo"):
            self.app.pop_screen()
            self.app.push_screen(RepoDetailsScreen(item.repo["full_name"]))

    def on_key(self, event) -> None:
        input_widget = self.query_one("#search-input", Input)
        results_list = self.query_one("#search-results-list", ListView)

        if event.key == "escape":
            self.app.pop_screen()
        elif event.key == "down" and input_widget.has_focus:
            results_list.focus()
            if results_list.children:
                results_list.index = 0
        elif event.key == "up" and results_list.has_focus and results_list.index == 0:
            input_widget.focus()
        elif event.key == "enter" and results_list.has_focus:
            selected = results_list.highlighted_child
            if selected and hasattr(selected, "repo"):
                self.app.pop_screen()
                self.app.push_screen(RepoDetailsScreen(selected.repo["full_name"]))
