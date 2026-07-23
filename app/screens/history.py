from textual.app import ComposeResult
from textual.containers import ScrollableContainer
from textual.widgets import Static, ListView, ListItem, Label
from app.cache import get_history_logs

class HistoryView(ScrollableContainer):
    """Visual operations activity logger screen displaying installed/failed commands."""
    
    def compose(self) -> ComposeResult:
        yield Label("OPERATION HISTORY LOG", classes="view-title")
        yield ListView(id="history-list")

    def on_mount(self) -> None:
        self.refresh_logs()

    def refresh_logs(self) -> None:
        logs = get_history_logs()
        history_list = self.query_one("#history-list", ListView)
        history_list.clear()

        if not logs:
            history_list.append(ListItem(Label("No operations logged yet. Try installing some repositories!")))
            return

        # Render each history entry as a scannable grid row
        for log in logs:
            action = log["action"].upper()
            slug = log["package_slug"]
            ts = log["timestamp"]
            details = log.get("details") or ""
            
            # Action Colors
            action_color = "#a9b1d6"
            if action == "INSTALLED":
                action_color = "#9ece6a" # green
            elif action == "FAILED":
                action_color = "#f7768e" # red
            elif action == "REMOVED":
                action_color = "#e0af68" # orange
            elif action == "UPDATED":
                action_color = "#7aa2f7" # blue

            log_text = (
                f"[dim #565f89]{ts}[/]  [bold {action_color}]{action:<10}[/]  "
                f"[bold #a9b1d6]{slug}[/]\n"
                f"   [dim #565f89]Details: {details}[/]"
            )
            
            history_list.append(ListItem(Static(log_text)))
