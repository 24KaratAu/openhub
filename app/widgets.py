from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Static, ListItem, Label
from textual.reactive import reactive
from app.classifier import calculate_quality_score, classify_repository

class RepoListItem(ListItem):
    """A highly scannable repository card displaying key metadata in a compact grid."""
    
    def __init__(self, repo: dict) -> None:
        super().__init__()
        self.repo = repo

    def compose(self) -> ComposeResult:
        # Fetch or compute classification/scores
        use_case = self.repo.get("use_case") or "Automation"
        impl_type = self.repo.get("impl_type") or "Skills"

        stars = self.repo.get("stars", 0)
        stars_formatted = f"{stars/1000:.1f}k" if stars >= 1000 else str(stars)
        
        # Calculate quality details
        q_score = self.repo.get("quality_score")
        if q_score is None:
            # Fallback calculation if worker hasn't run yet
            q_details = calculate_quality_score(self.repo)
            q_score = q_details["score"]
            q_stars = q_details["rating_stars"]
            q_label = q_details["rating_label"]
        else:
            # Load from DB parameters
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

        # Textual colors based on rating label
        color_map = {
            "Excellent": "#9ece6a", # green
            "Great": "#7aa2f7",     # blue
            "Good": "#e0af68",      # orange
            "Fair": "#bb9af7",      # purple
            "Poor": "#f7768e"       # red
        }
        score_color = color_map.get(q_label, "#a9b1d6")

        lang = self.repo.get("language") or "Other"
        license_name = self.repo.get("license") or "None"
        
        # Get difficulty (can fallback to intermediate)
        difficulty = self.repo.get("difficulty") or "Intermediate"
        diff_color = "#9ece6a" if difficulty == "Beginner" else ("#e0af68" if difficulty == "Intermediate" else "#f7768e")

        # Visual layout rendering using rich-text markup
        card_content = (
            f"[bold #a9b1d6]{self.repo['full_name']}[/] "
            f" [dim]|[/]  ★ {stars_formatted}  [dim]|[/]  {use_case}  [dim]|[/]  [bold {score_color}]Quality: {q_score} ({q_stars} {q_label})[/]\n"
            f"[dim #565f89]{lang}  •  {license_name} License  •  Difficulty: [/][bold {diff_color}]{difficulty}[/]  [dim #565f89]•  Updated: {self.repo.get('updated_at', '')[:10]}[/]"
        )
        
        yield Static(card_content, classes="repo-card-text")
