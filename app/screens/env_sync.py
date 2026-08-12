from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.widgets import Label, Static, Button
from textual.screen import ModalScreen

class EnvSyncModal(ModalScreen[bool]):
    """Modal dialog prompting user to sync skills when a new AI coding environment (e.g. Claude Code) is detected."""

    BINDINGS = [
        ("s", "sync", "Sync Skills"),
        ("escape", "cancel", "Skip")
    ]

    def __init__(self, env_data: dict) -> None:
        super().__init__()
        self.env_data = env_data

    def compose(self) -> ComposeResult:
        env_name = self.env_data.get("env_name", "AI Environment")
        unsynced = self.env_data.get("unsynced_skills", [])
        skills_str = "\n".join([f"  • {s}" for s in unsynced[:5]])
        if len(unsynced) > 5:
            skills_str += f"\n  ...and {len(unsynced) - 5} more"

        yield Vertical(
            Label(f"🚀 New Environment Detected: {env_name}", id="confirm-title"),
            Static(
                f"[bold #7aa2f7]OpenHub detected a new installation of {env_name}![/]\n\n"
                f"Found [bold #9ece6a]{len(unsynced)} skill(s)[/] not yet synced to {env_name}:\n"
                f"{skills_str}\n\n"
                f"Would you like to sync these skills to [bold #e0af68]{self.env_data.get('target_dir')}[/]?\n",
                id="confirm-body"
            ),
            Horizontal(
                Button("Sync Skills Now (S)", variant="success", id="btn-sync"),
                Button("Skip / Remind Later", variant="error", id="btn-skip"),
                classes="confirm-buttons"
            ),
            id="confirm-dialog"
        )

    def action_sync(self) -> None:
        self.dismiss(True)

    def action_cancel(self) -> None:
        self.dismiss(False)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-sync":
            self.dismiss(True)
        else:
            self.dismiss(False)
