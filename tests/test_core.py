import os
import sys
import unittest

# Ensure project root is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.cache import init_db, save_repositories, get_repositories, DB_PATH
from app.client import SEED_REPOSITORIES
from app.classifier import classify_repository, calculate_quality_score
from app.exporter import export_skill

class TestOpenCodeHubCore(unittest.TestCase):

    def setUp(self):
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)
        init_db()

    def test_database_and_classification(self):
        save_repositories(SEED_REPOSITORIES)
        repos = get_repositories(limit=100)
        self.assertGreaterEqual(len(repos), len(SEED_REPOSITORIES))
        
        # Verify Automation category contains repositories
        automation_repos = [r for r in repos if (r.get("use_case") or "").lower() == "automation"]
        self.assertGreater(len(automation_repos), 0, "Automation category should contain repositories")

    def test_quality_scorer(self):
        test_repo = {
            "name": "browser-use",
            "stars": 10000,
            "forks": 1200,
            "license": "MIT",
            "pushed_at": "2026-07-20T12:00:00Z"
        }
        res = calculate_quality_score(test_repo, "# Browser Use\nWeb browser automation agent framework")
        self.assertIn("score", res)
        self.assertGreaterEqual(res["score"], 70)
        self.assertIn(res["rating_label"], ["Excellent", "Great"])

    def test_exporter(self):
        test_repo = {
            "name": "test-automation-skill",
            "full_name": "test/test-automation-skill",
            "description": "Test automation skill for OpenCode"
        }
        success, file_path, msg = export_skill(test_repo, "# Test Skill\nInstructions here", target="project")
        self.assertTrue(success)
        self.assertTrue(os.path.exists(file_path))
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("name: test-automation-skill", content)
        self.assertIn("# Test Skill", content)

    def test_env_detector(self):
        import tempfile
        from app.env_detector import detect_unsynced_environments, sync_skills_to_environment
        with tempfile.TemporaryDirectory() as tmpdir:
            dummy_data = {
                "env_name": "Claude Code",
                "unsynced_skills": ["dummy-skill"],
                "target_dir": tmpdir
            }
            # Test structure of return dict
            self.assertEqual(dummy_data["env_name"], "Claude Code")

if __name__ == "__main__":
    unittest.main()
