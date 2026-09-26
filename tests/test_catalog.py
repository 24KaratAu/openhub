import os
import sys
import shutil
import asyncio
import sqlite3
import tempfile
import unittest
from unittest import mock

# Sandbox HOME and cwd before importing app modules, which resolve ~ and ./ at import/call time
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SANDBOX = tempfile.mkdtemp(prefix="openhub-test-")
os.environ["HOME"] = SANDBOX
os.chdir(SANDBOX)
sys.path.insert(0, PROJECT_ROOT)

import httpx
from app import cache
from app.client import GitHubProvider, github_headers


def repo(i, use_case="Automation", impl_type="Skills", readme=None):
    return {
        "id": i, "name": f"repo{i}", "owner": "acme", "full_name": f"acme/repo{i}",
        "description": "", "html_url": f"https://github.com/acme/repo{i}", "stars": 10_000 - i,
        "use_case": use_case, "impl_type": impl_type, "difficulty": "Beginner", "readme_preview": readme,
    }


def provider(handler):
    p = GitHubProvider()
    p.client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return p


class TestCatalogQueries(unittest.TestCase):
    def setUp(self):
        shutil.rmtree(os.path.join(SANDBOX, ".cache"), ignore_errors=True)
        cache.init_db()

    def test_no_cap_and_filter_in_sql(self):
        # 250 popular Automation repos used to push every other category out of the top-200 window
        repos = [repo(i) for i in range(250)] + [repo(1000 + i, use_case="Security") for i in range(5)]
        repos.append(repo(2000, use_case="Security", impl_type="MCP Servers"))
        cache.save_repositories(repos)
        self.assertEqual(len(cache.get_repositories()), 256)
        self.assertEqual(len(cache.get_repositories(limit=10)), 10)
        self.assertEqual(len(cache.get_repositories(use_case="security")), 6)
        self.assertEqual([r["full_name"] for r in cache.get_repositories(use_case="Security", impl_type="MCP Servers")],
                         ["acme/repo2000"])

    def test_renamed_repo_does_not_break_sync(self):
        cache.save_repositories([repo(1, readme="# kept"), repo(2)])
        renamed = {**repo(1), "full_name": "new-owner/repo1", "owner": "new-owner"}
        cache.save_repositories([renamed, repo(3)])
        names = sorted(r["full_name"] for r in cache.get_repositories())
        self.assertEqual(names, ["acme/repo2", "acme/repo3", "new-owner/repo1"])
        self.assertEqual(cache.get_repository_by_fullname("new-owner/repo1")["readme_preview"], "# kept")

    def test_migration_clears_placeholder_readmes(self):
        placeholder = "# acme/repo1\n\nCould not fetch README from GitHub. Ensure you are connected to the internet."
        cache.save_repositories([repo(1, readme=placeholder), repo(2, readme="# real readme")])
        conn = sqlite3.connect(cache.DB_PATH)
        conn.execute("UPDATE repositories SET quality_score = 42")
        conn.commit()
        conn.close()
        cache.init_db()
        r1, r2 = cache.get_repository_by_fullname("acme/repo1"), cache.get_repository_by_fullname("acme/repo2")
        self.assertIsNone(r1["readme_preview"])
        self.assertIsNone(r1["quality_score"])  # re-queued for the scorer
        self.assertEqual(r2["readme_preview"], "# real readme")
        self.assertEqual(r2["quality_score"], 42)


class TestGitHubClient(unittest.TestCase):
    def test_token_header(self):
        with mock.patch.dict(os.environ, {"GITHUB_TOKEN": "abc\n"}, clear=False):
            self.assertEqual(github_headers()["Authorization"], "Bearer abc")
        with mock.patch.dict(os.environ, {"GH_TOKEN": "xyz"}, clear=False):
            os.environ.pop("GITHUB_TOKEN", None)
            self.assertEqual(github_headers()["Authorization"], "Bearer xyz")
        env = {k: v for k, v in os.environ.items() if k not in ("GITHUB_TOKEN", "GH_TOKEN")}
        with mock.patch.dict(os.environ, env, clear=True):
            self.assertNotIn("Authorization", github_headers())

    def test_readme_distinguishes_missing_from_failed(self):
        missing = provider(lambda r: httpx.Response(404))
        self.assertEqual(asyncio.run(missing.fetch_readme("acme/repo1")), "")
        self.assertFalse(missing.rate_limited)

        limited = provider(lambda r: httpx.Response(404 if "raw.githubusercontent" in str(r.url) else 403))
        self.assertIsNone(asyncio.run(limited.fetch_readme("acme/repo1")))
        self.assertTrue(limited.rate_limited)

        def offline(r):
            raise httpx.ConnectError("offline")
        self.assertIsNone(asyncio.run(provider(offline).fetch_readme("acme/repo1")))

    def test_sync_requests_100_per_query_and_flags_rate_limit(self):
        seen = []

        def handler(r):
            seen.append(r.url.params.get("per_page"))
            if r.url.params.get("q") == "topic:mcp-server":
                return httpx.Response(403)
            return httpx.Response(200, json={"items": []})
        p = provider(handler)
        with mock.patch("asyncio.sleep", new=mock.AsyncMock()):
            asyncio.run(p.fetch_trending())
        self.assertEqual(set(seen), {"100"})
        self.assertTrue(p.rate_limited)
        self.assertEqual((p.failed_queries, p.total_queries), (1, 8))

    def test_sync_counts_network_failures(self):
        def handler(r):
            if r.url.params.get("q") in ("topic:ai-agent", "topic:llm-tools"):
                raise httpx.ConnectError("No address associated with hostname")
            return httpx.Response(200, json={"items": []})
        p = provider(handler)
        with mock.patch("asyncio.sleep", new=mock.AsyncMock()):
            asyncio.run(p.fetch_trending())
        self.assertEqual(p.failed_queries, 2)
        self.assertFalse(p.rate_limited)


if __name__ == "__main__":
    try:
        unittest.main()
    finally:
        shutil.rmtree(SANDBOX, ignore_errors=True)
