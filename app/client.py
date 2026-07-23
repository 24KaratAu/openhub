import httpx
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any

logger = logging.getLogger("opencode-hub.client")

# Curated list of high-quality fallback seed repositories for offline or rate-limited states
SEED_REPOSITORIES = [
    {
        "id": 89456100,
        "name": "browser-use-agent",
        "owner": "browser-use",
        "full_name": "browser-use/browser-use",
        "description": "Make websites usable for AI agents. An open-source web browser automation framework.",
        "html_url": "https://github.com/browser-use/browser-use",
        "stars": 24500,
        "forks": 2800,
        "open_issues": 120,
        "language": "Python",
        "license": "MIT",
        "created_at": "2024-01-10T12:00:00Z",
        "updated_at": "2026-07-11T12:00:00Z",
        "pushed_at": "2026-07-11T12:00:00Z",
        "use_case": "Automation",
        "impl_type": "Agents",
        "difficulty": "Intermediate",
        "tags": ["agent", "browser-automation", "web-research", "mcp-server", "llm"],
        "is_verified": True
    },
    {
        "id": 99201948,
        "name": "composio-agent-tools",
        "owner": "composiohq",
        "full_name": "composiohq/composio",
        "description": "Equips AI agents with 100+ production tools and automation workflows: GitHub, Gmail, Slack, Salesforce.",
        "html_url": "https://github.com/composiohq/composio",
        "stars": 14200,
        "forks": 1200,
        "open_issues": 38,
        "language": "Python",
        "license": "Apache-2.0",
        "created_at": "2024-03-01T09:00:00Z",
        "updated_at": "2026-07-11T17:00:00Z",
        "pushed_at": "2026-07-11T17:00:00Z",
        "use_case": "Automation",
        "impl_type": "Skills",
        "difficulty": "Intermediate",
        "tags": ["skills", "tools", "automation", "mcp"],
        "is_verified": True
    },
    {
        "id": 66203920,
        "name": "mcp-installer",
        "owner": "coleam00",
        "full_name": "coleam00/mcp-installer",
        "description": "One-click shell script installer and automation tool for Claude Desktop and OpenCode MCP servers.",
        "html_url": "https://github.com/coleam00/mcp-installer",
        "stars": 980,
        "forks": 140,
        "open_issues": 3,
        "language": "Shell",
        "license": "MIT",
        "created_at": "2024-11-28T18:00:00Z",
        "updated_at": "2026-07-10T10:00:00Z",
        "pushed_at": "2026-07-10T10:00:00Z",
        "use_case": "Automation",
        "impl_type": "Commands",
        "difficulty": "Beginner",
        "tags": ["mcp", "installer", "claude-desktop", "devtools"],
        "is_verified": False
    },
    {
        "id": 91823700,
        "name": "mcp-official-servers",
        "owner": "modelcontextprotocol",
        "full_name": "modelcontextprotocol/servers",
        "description": "Official Model Context Protocol servers including postgres, sqlite, git, filesystem, and brave-search.",
        "html_url": "https://github.com/modelcontextprotocol/servers",
        "stars": 18500,
        "forks": 2100,
        "open_issues": 45,
        "language": "TypeScript",
        "license": "MIT",
        "created_at": "2024-11-05T08:00:00Z",
        "updated_at": "2026-07-11T14:30:00Z",
        "pushed_at": "2026-07-11T14:30:00Z",
        "use_case": "Database",
        "impl_type": "MCP Servers",
        "difficulty": "Advanced",
        "tags": ["mcp", "database", "postgres", "sqlite", "devtools"],
        "is_verified": True
    },
    {
        "id": 73829400,
        "name": "open-interpreter-core",
        "owner": "OpenInterpreter",
        "full_name": "OpenInterpreter/open-interpreter",
        "description": "A natural language interface for computers. Let LLMs run code locally in Python, Bash, JS.",
        "html_url": "https://github.com/OpenInterpreter/open-interpreter",
        "stars": 54000,
        "forks": 4800,
        "open_issues": 310,
        "language": "Python",
        "license": "MIT",
        "created_at": "2023-08-01T15:00:00Z",
        "updated_at": "2026-07-10T22:15:00Z",
        "pushed_at": "2026-07-11T05:00:00Z",
        "use_case": "Coding",
        "impl_type": "Agents",
        "difficulty": "Intermediate",
        "tags": ["agent", "local-execution", "coding", "terminal-tools"],
        "is_verified": True
    },
    {
        "id": 81029384,
        "name": "crewai-framework",
        "owner": "crewAIInc",
        "full_name": "crewAIInc/crewAI",
        "description": "Framework for orchestrating role-playing, autonomous AI agents and complex task workflows.",
        "html_url": "https://github.com/crewAIInc/crewAI",
        "stars": 23000,
        "forks": 3100,
        "open_issues": 140,
        "language": "Python",
        "license": "MIT",
        "created_at": "2023-11-10T10:00:00Z",
        "updated_at": "2026-07-11T16:00:00Z",
        "pushed_at": "2026-07-11T16:00:00Z",
        "use_case": "Multi-Agent",
        "impl_type": "Agents",
        "difficulty": "Intermediate",
        "tags": ["multi-agent", "agentic-ai", "framework", "automation"],
        "is_verified": True
    },
    {
        "id": 83920193,
        "name": "pydantic-ai-agent",
        "owner": "pydantic",
        "full_name": "pydantic/pydantic-ai",
        "description": "Python Agent Framework powered by Pydantic for type-safe LLM tool calling and structured outputs.",
        "html_url": "https://github.com/pydantic/pydantic-ai",
        "stars": 7800,
        "forks": 650,
        "open_issues": 25,
        "language": "Python",
        "license": "MIT",
        "created_at": "2024-11-15T12:00:00Z",
        "updated_at": "2026-07-11T18:00:00Z",
        "pushed_at": "2026-07-11T18:00:00Z",
        "use_case": "Coding",
        "impl_type": "Agents",
        "difficulty": "Intermediate",
        "tags": ["agent", "python", "type-safety", "coding"],
        "is_verified": True
    },
    {
        "id": 78192039,
        "name": "mem0-ai-memory",
        "owner": "mem0ai",
        "full_name": "mem0ai/mem0",
        "description": "The Memory Layer for AI Agents & Assistants. Enables persistent personalized long-term memory.",
        "html_url": "https://github.com/mem0ai/mem0",
        "stars": 21500,
        "forks": 2400,
        "open_issues": 60,
        "language": "Python",
        "license": "Apache-2.0",
        "created_at": "2024-04-20T11:00:00Z",
        "updated_at": "2026-07-11T13:00:00Z",
        "pushed_at": "2026-07-11T13:00:00Z",
        "use_case": "Database",
        "impl_type": "Skills",
        "difficulty": "Intermediate",
        "tags": ["memory", "agent", "vector-db", "database"],
        "is_verified": True
    },
    {
        "id": 55102930,
        "name": "cursor-agent-skills",
        "owner": "coleam00",
        "full_name": "coleam00/cursor-agent-skills",
        "description": "A set of custom system instructions and tools to supercharge Cursor and OpenCode AI agents.",
        "html_url": "https://github.com/coleam00/cursor-agent-skills",
        "stars": 3200,
        "forks": 420,
        "open_issues": 8,
        "language": "Markdown",
        "license": "MIT",
        "created_at": "2025-01-20T10:00:00Z",
        "updated_at": "2026-07-11T11:00:00Z",
        "pushed_at": "2026-07-11T11:00:00Z",
        "use_case": "Coding",
        "impl_type": "Skills",
        "difficulty": "Beginner",
        "tags": ["cursor", "editor-skills", "coding", "automation"],
        "is_verified": False
    },
    {
        "id": 65123900,
        "name": "sequential-search-mcp",
        "owner": "open-web-partners",
        "full_name": "open-web-partners/sequential-search-mcp",
        "description": "Perform deep multi-query research on Google and Brave engines sequentially.",
        "html_url": "https://github.com/open-web-partners/sequential-search-mcp",
        "stars": 1450,
        "forks": 180,
        "open_issues": 12,
        "language": "Python",
        "license": "Apache-2.0",
        "created_at": "2025-02-14T09:00:00Z",
        "updated_at": "2026-07-11T16:00:00Z",
        "pushed_at": "2026-07-11T16:00:00Z",
        "use_case": "Web Research",
        "impl_type": "MCP Servers",
        "difficulty": "Intermediate",
        "tags": ["mcp", "search", "web-research", "brave-api"],
        "is_verified": False
    },
    {
        "id": 78912345,
        "name": "gpt-researcher",
        "owner": "assafelovic",
        "full_name": "assafelovic/gpt-researcher",
        "description": "An autonomous agent that conducts deep research on any topic or data source with detailed web synthesis.",
        "html_url": "https://github.com/assafelovic/gpt-researcher",
        "stars": 28550,
        "forks": 3100,
        "open_issues": 95,
        "language": "Python",
        "license": "MIT",
        "created_at": "2023-06-01T10:00:00Z",
        "updated_at": "2026-07-11T18:00:00Z",
        "pushed_at": "2026-07-11T18:00:00Z",
        "use_case": "Web Research",
        "impl_type": "Agents",
        "difficulty": "Intermediate",
        "tags": ["research", "agent", "web-research", "gpt-researcher", "llm"],
        "is_verified": True
    },
    {
        "id": 98765432,
        "name": "autoresearch",
        "owner": "karpathy",
        "full_name": "karpathy/autoresearch",
        "description": "AI agents running autonomous research experiments on code, datasets, and training pipelines.",
        "html_url": "https://github.com/karpathy/autoresearch",
        "stars": 91800,
        "forks": 7200,
        "open_issues": 120,
        "language": "Python",
        "license": "MIT",
        "created_at": "2024-02-10T12:00:00Z",
        "updated_at": "2026-07-11T19:00:00Z",
        "pushed_at": "2026-07-11T19:00:00Z",
        "use_case": "Web Research",
        "impl_type": "Agents",
        "difficulty": "Advanced",
        "tags": ["autoresearch", "research-agent", "agent", "karpathy", "ai"],
        "is_verified": True
    },
    {
        "id": 87654321,
        "name": "deep-research",
        "owner": "dzhng",
        "full_name": "dzhng/deep-research",
        "description": "An AI-powered research assistant that performs iterative, deep web research and generates comprehensive reports.",
        "html_url": "https://github.com/dzhng/deep-research",
        "stars": 19400,
        "forks": 1800,
        "open_issues": 45,
        "language": "TypeScript",
        "license": "MIT",
        "created_at": "2024-12-01T08:00:00Z",
        "updated_at": "2026-07-11T15:00:00Z",
        "pushed_at": "2026-07-11T15:00:00Z",
        "use_case": "Web Research",
        "impl_type": "Agents",
        "difficulty": "Intermediate",
        "tags": ["deep-research", "research-agent", "web-search", "agent"],
        "is_verified": True
    },
    {
        "id": 43210980,
        "name": "autogen-studio",
        "owner": "microsoft",
        "full_name": "microsoft/autogen",
        "description": "A programming framework for agentic AI. Autogen enables multi-agent conversation workflows.",
        "html_url": "https://github.com/microsoft/autogen",
        "stars": 37500,
        "forks": 5200,
        "open_issues": 412,
        "language": "Python",
        "license": "MIT",
        "created_at": "2023-08-15T09:00:00Z",
        "updated_at": "2026-07-11T10:00:00Z",
        "pushed_at": "2026-07-11T17:00:00Z",
        "use_case": "Multi-Agent",
        "impl_type": "Agents",
        "difficulty": "Intermediate",
        "tags": ["agentic-ai", "multi-agent", "framework", "coding"],
        "is_verified": True
    },
    {
        "id": 12903820,
        "name": "pytest-suite",
        "owner": "pytest-dev",
        "full_name": "pytest-dev/pytest",
        "description": "The pytest framework makes it easy to write simple tests, yet scales to support complex functional testing.",
        "html_url": "https://github.com/pytest-dev/pytest",
        "stars": 11500,
        "forks": 2500,
        "open_issues": 380,
        "language": "Python",
        "license": "MIT",
        "created_at": "2010-01-01T00:00:00Z",
        "updated_at": "2026-07-11T09:00:00Z",
        "pushed_at": "2026-07-11T15:00:00Z",
        "use_case": "Testing",
        "impl_type": "Skills",
        "difficulty": "Beginner",
        "tags": ["testing", "python-devtools", "assertions"],
        "is_verified": True
    },
    {
        "id": 93821049,
        "name": "sentry-mcp-debugger",
        "owner": "getsentry",
        "full_name": "getsentry/sentry-mcp",
        "description": "Real-time exception logging, stack traceback inspection, and error debugging MCP server for AI agents.",
        "html_url": "https://github.com/getsentry/sentry-mcp",
        "stars": 4200,
        "forks": 350,
        "open_issues": 15,
        "language": "Python",
        "license": "MIT",
        "created_at": "2024-10-01T10:00:00Z",
        "updated_at": "2026-07-11T14:00:00Z",
        "pushed_at": "2026-07-11T14:00:00Z",
        "use_case": "Debugging",
        "impl_type": "MCP Servers",
        "difficulty": "Intermediate",
        "tags": ["debugging", "traceback", "logging", "mcp"],
        "is_verified": True
    },
    {
        "id": 73820194,
        "name": "mkdocs-generator",
        "owner": "mkdocs",
        "full_name": "mkdocs/mkdocs",
        "description": "Fast, simple static site generator for project documentation and developer wikis.",
        "html_url": "https://github.com/mkdocs/mkdocs",
        "stars": 18200,
        "forks": 2300,
        "open_issues": 110,
        "language": "Python",
        "license": "BSD-3-Clause",
        "created_at": "2014-03-01T12:00:00Z",
        "updated_at": "2026-07-11T10:00:00Z",
        "pushed_at": "2026-07-11T10:00:00Z",
        "use_case": "Documentation",
        "impl_type": "Skills",
        "difficulty": "Beginner",
        "tags": ["documentation", "readme", "wiki", "sphinx"],
        "is_verified": True
    },
    {
        "id": 61928374,
        "name": "terraform-cloud",
        "owner": "hashicorp",
        "full_name": "hashicorp/terraform",
        "description": "Infrastructure as Code tool to build, change, and version cloud infrastructure safely on AWS, GCP, Azure.",
        "html_url": "https://github.com/hashicorp/terraform",
        "stars": 41200,
        "forks": 9100,
        "open_issues": 890,
        "language": "Go",
        "license": "BSL-1.1",
        "created_at": "2014-05-15T09:00:00Z",
        "updated_at": "2026-07-11T16:00:00Z",
        "pushed_at": "2026-07-11T16:00:00Z",
        "use_case": "Cloud",
        "impl_type": "Commands",
        "difficulty": "Advanced",
        "tags": ["cloud", "aws", "gcp", "azure", "docker", "kubernetes"],
        "is_verified": True
    },
    {
        "id": 84930291,
        "name": "gitleaks-security",
        "owner": "gitleaks",
        "full_name": "gitleaks/gitleaks",
        "description": "Audit git repositories for secrets, keys, and credentials to enforce security guardrails.",
        "html_url": "https://github.com/gitleaks/gitleaks",
        "stars": 19400,
        "forks": 1400,
        "open_issues": 40,
        "language": "Go",
        "license": "MIT",
        "created_at": "2018-01-10T08:00:00Z",
        "updated_at": "2026-07-11T12:00:00Z",
        "pushed_at": "2026-07-11T12:00:00Z",
        "use_case": "Security",
        "impl_type": "Commands",
        "difficulty": "Intermediate",
        "tags": ["security", "auth", "secret", "guardrail"],
        "is_verified": True
    },
    {
        "id": 92830192,
        "name": "textual-ui-framework",
        "owner": "Textualize",
        "full_name": "Textualize/textual",
        "description": "Rapid TUI development framework for Python terminal user interfaces and agent dashboards.",
        "html_url": "https://github.com/Textualize/textual",
        "stars": 26800,
        "forks": 850,
        "open_issues": 130,
        "language": "Python",
        "license": "MIT",
        "created_at": "2021-06-01T10:00:00Z",
        "updated_at": "2026-07-11T15:00:00Z",
        "pushed_at": "2026-07-11T15:00:00Z",
        "use_case": "UI",
        "impl_type": "Skills",
        "difficulty": "Intermediate",
        "tags": ["ui", "gui", "tui", "textual", "css", "layout"],
        "is_verified": True
    },
    {
        "id": 83920194,
        "name": "pandas-data-science",
        "owner": "pandas-dev",
        "full_name": "pandas-dev/pandas",
        "description": "Flexible data analysis and manipulation library for AI data science agents and computing.",
        "html_url": "https://github.com/pandas-dev/pandas",
        "stars": 43500,
        "forks": 17800,
        "open_issues": 3200,
        "language": "Python",
        "license": "BSD-3-Clause",
        "created_at": "2010-08-24T18:00:00Z",
        "updated_at": "2026-07-11T17:00:00Z",
        "pushed_at": "2026-07-11T17:00:00Z",
        "use_case": "Data Science",
        "impl_type": "Skills",
        "difficulty": "Intermediate",
        "tags": ["data", "science", "pandas", "numpy", "jupyter"],
        "is_verified": True
    },
    {
        "id": 10293847,
        "name": "kubernetes-agent-orchestrator",
        "owner": "kubernetes",
        "full_name": "kubernetes/kubernetes",
        "description": "Production-grade container orchestration system for deploying multi-node AI agent clusters on cloud.",
        "html_url": "https://github.com/kubernetes/kubernetes",
        "stars": 112000,
        "forks": 40500,
        "open_issues": 2100,
        "language": "Go",
        "license": "Apache-2.0",
        "created_at": "2014-06-06T18:00:00Z",
        "updated_at": "2026-07-11T19:00:00Z",
        "pushed_at": "2026-07-11T19:00:00Z",
        "use_case": "Cloud",
        "impl_type": "Commands",
        "difficulty": "Advanced",
        "tags": ["cloud", "kubernetes", "docker", "gcp", "aws"],
        "is_verified": True
    },
    {
        "id": 59382019,
        "name": "trufflehog-security-scanner",
        "owner": "trufflesecurity",
        "full_name": "trufflesecurity/trufflehog",
        "description": "Find secrets, API keys, and credentials hidden across git repositories and secret storage.",
        "html_url": "https://github.com/trufflesecurity/trufflehog",
        "stars": 16500,
        "forks": 1600,
        "open_issues": 85,
        "language": "Go",
        "license": "AGPL-3.0",
        "created_at": "2016-12-20T10:00:00Z",
        "updated_at": "2026-07-11T14:00:00Z",
        "pushed_at": "2026-07-11T14:00:00Z",
        "use_case": "Security",
        "impl_type": "Commands",
        "difficulty": "Intermediate",
        "tags": ["security", "auth", "secret", "guardrail"],
        "is_verified": True
    },
    {
        "id": 48291039,
        "name": "jupyter-notebook",
        "owner": "jupyter",
        "full_name": "jupyter/notebook",
        "description": "Interactive computing environment for data science, AI model evaluation, and Python visualization.",
        "html_url": "https://github.com/jupyter/notebook",
        "stars": 12400,
        "forks": 3800,
        "open_issues": 290,
        "language": "TypeScript",
        "license": "BSD-3-Clause",
        "created_at": "2014-04-10T12:00:00Z",
        "updated_at": "2026-07-11T16:00:00Z",
        "pushed_at": "2026-07-11T16:00:00Z",
        "use_case": "Data Science",
        "impl_type": "Skills",
        "difficulty": "Intermediate",
        "tags": ["data", "science", "jupyter", "pandas", "visualization"],
        "is_verified": True
    },
    {
        "id": 39201928,
        "name": "playwright-browser-testing",
        "owner": "microsoft",
        "full_name": "microsoft/playwright-python",
        "description": "Python library to automate Chromium, Firefox and WebKit for web agent testing and web scraping.",
        "html_url": "https://github.com/microsoft/playwright-python",
        "stars": 13800,
        "forks": 980,
        "open_issues": 120,
        "language": "Python",
        "license": "Apache-2.0",
        "created_at": "2020-07-01T10:00:00Z",
        "updated_at": "2026-07-11T18:00:00Z",
        "pushed_at": "2026-07-11T18:00:00Z",
        "use_case": "Testing",
        "impl_type": "Skills",
        "difficulty": "Intermediate",
        "tags": ["testing", "playwright", "browser-automation", "assertions"],
        "is_verified": True
    }
]

class Provider(ABC):
    @abstractmethod
    async def fetch_trending(self) -> List[Dict[str, Any]]:
        """Fetch trending / featured repositories in the ecosystem."""
        pass

    @abstractmethod
    async def fetch_readme(self, full_name: str) -> str:
        """Fetch raw readme file content for markdown preview."""
        pass

    @abstractmethod
    async def search(self, query: str) -> List[Dict[str, Any]]:
        """Search repositories on the remote registry."""
        pass

class GitHubProvider(Provider):
    def __init__(self):
        # Public queries do not require authentication for simple searches, keeping things zero-config
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "OpenCode-Hub-TUI/1.0"
        }
        self.client = httpx.AsyncClient(headers=headers, timeout=12.0)

    def _map_repo(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Maps GitHub raw API response format to standard OpenCode structure."""
        return {
            "id": item["id"],
            "name": item["name"],
            "owner": item["owner"]["login"],
            "full_name": item["full_name"],
            "description": item.get("description", "") or "",
            "html_url": item["html_url"],
            "stars": item.get("stargazers_count", 0),
            "forks": item.get("forks_count", 0),
            "open_issues": item.get("open_issues_count", 0),
            "language": item.get("language") or "Other",
            "license": item.get("license", {}).get("spdx_id") if item.get("license") else "None",
            "created_at": item.get("created_at"),
            "updated_at": item.get("updated_at"),
            "pushed_at": item.get("pushed_at"),
            "tags": item.get("topics", []),
            "is_verified": item["owner"]["login"].lower() in [
                "modelcontextprotocol", "browser-use", "openinterpreter", "microsoft", "google", "pytest-dev", "crewaiinc", "composiohq", "pydantic", "mem0ai"
            ]
        }

    async def _github_search(self, q: str, per_page: int = 30) -> List[Dict[str, Any]]:
        """Execute a single GitHub search query using httpx params dict for correct encoding."""
        try:
            response = await self.client.get(
                "https://api.github.com/search/repositories",
                params={"q": q, "sort": "stars", "order": "desc", "per_page": str(per_page)}
            )
            if response.status_code in (403, 429):
                logger.warning(f"GitHub rate limit hit for query: {q[:40]}")
                return []
            if response.status_code == 422:
                logger.warning(f"GitHub rejected query syntax (422): {q[:40]}")
                return []
            response.raise_for_status()
            data = response.json()
            return data.get("items", [])
        except Exception as e:
            logger.warning(f"GitHub search failed for '{q[:40]}': {e}")
            return []

    async def fetch_trending(self) -> List[Dict[str, Any]]:
        """Fetches trending AI agent/skill/MCP repositories using concurrent queries.
        
        GitHub caveat: the topic: qualifier does NOT support OR operator.
        Each topic must be queried individually. We use asyncio.Semaphore(3) to
        limit concurrency and avoid secondary rate limiting.
        """
        import asyncio
        # Single-topic queries — GitHub only supports one topic: per query
        all_queries = [
            "topic:mcp-server",
            "topic:ai-agent",
            "topic:agent-skills",
            "topic:llm-tools",
            "topic:claude-skills",
            "topic:cursor-skills",
            "mcp server in:name,description",
            "ai agent skills in:name,description",
        ]
        
        # Semaphore limits concurrent requests to avoid secondary rate limiting
        sem = asyncio.Semaphore(3)
        
        async def throttled_search(q: str) -> List[Dict[str, Any]]:
            async with sem:
                result = await self._github_search(q, per_page=30)
                await asyncio.sleep(1)  # Brief pause after each request
                return result
        
        # Fire all queries concurrently (semaphore limits to 3 at a time)
        results = await asyncio.gather(*[throttled_search(q) for q in all_queries], return_exceptions=True)
        
        all_repos = []
        seen = set()
        for batch in results:
            if isinstance(batch, Exception):
                logger.warning(f"A trending query failed: {batch}")
                continue
            for item in batch:
                fn = item["full_name"]
                if fn not in seen:
                    seen.add(fn)
                    all_repos.append(self._map_repo(item))

        if not all_repos:
            logger.warning("All GitHub queries failed or returned empty, loading seeds.")
            return SEED_REPOSITORIES
        return all_repos

    async def fetch_readme(self, full_name: str) -> str:
        """Fetches the README file for a given repository."""
        branches = ["main", "master", "develop"]
        for branch in branches:
            url = f"https://raw.githubusercontent.com/{full_name}/{branch}/README.md"
            try:
                response = await self.client.get(url)
                if response.status_code == 200:
                    return response.text
            except Exception:
                continue

        url = f"https://api.github.com/repos/{full_name}/readme"
        try:
            response = await self.client.get(url)
            if response.status_code == 200:
                import base64
                content_b64 = response.json().get("content", "")
                return base64.b64decode(content_b64).decode("utf-8", errors="ignore")
        except Exception as e:
            logger.error(f"Failed to fetch readme for {full_name}: {e}")
            
        return f"# {full_name}\n\nCould not fetch README from GitHub. Ensure you are connected to the internet."

    async def search(self, query: str) -> List[Dict[str, Any]]:
        """Performs remote search on GitHub using httpx params dict for correct encoding."""
        items = await self._github_search(f"{query} in:name,description", per_page=30)
        return [self._map_repo(item) for item in items]

    async def close(self):
        await self.client.aclose()
