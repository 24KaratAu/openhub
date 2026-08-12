# OpenHub

A keyboard-first, terminal user interface (TUI) discovery hub and package installer for AI coding tools, skills, and agents.

Built with Python, Textual, and SQLite — zero configuration required out of the box.

---

## Requirements & Platform Support

* **Python**: 3.10+
* **Operating Systems**: Linux, macOS, Windows (PowerShell / Windows Terminal)

---

## Ecosystem & AI Agent Compatibility

OpenHub exports tools using the **Universal Open Agent Skills Standard** (`SKILL.md`), making exported tools instantly usable across modern AI coding assistants and IDEs:

| AI Tool / Agent IDE | Supported | Export Integration Path |
| :--- | :---: | :--- |
| **OpenCode** | Yes | `./.opencode/skills/` & `~/.config/opencode/` |
| **Claude Code / Desktop** | Yes | `./.agents/skills/` & `~/.agents/skills/` |
| **Cursor Editor** | Yes | `./.agents/skills/` |
| **Windsurf / Cascade** | Yes | `./.agents/skills/` |
| **Roo Code / Cline** | Yes | `./.agents/skills/` |
| **AutoGen / CrewAI** | Yes | Standard `SKILL.md` format |

---

## Quick Start

### Install via pipx (Recommended)
```bash
pipx install git+https://github.com/24KaratAu/openhub.git
openhub
```

### Install via pip
```bash
pip install git+https://github.com/24KaratAu/openhub.git
openhub
```

### Local Development
```bash
git clone https://github.com/24KaratAu/openhub.git
cd openhub
pip install -e .
openhub
```

---

## Features & Architecture

1. **Dashboard-Centric Catalog**: Displays scannable catalog panels showing trending repositories, recent releases, fast-growing utilities, and hidden gems.
2. **Intent-Driven Fuzzy Search**: Pressing `/` or `S` opens a Spotlight-style command palette dropdown. Typo-tolerant matching runs locally using `rapidfuzz` across names, descriptions, topics, and use cases.
3. **Curated Collections**: Browse curated workflows such as "AI Engineer Starter Pack", "Claude Desktop Servers", "Cursor Editor Skills", or "Python Toolkit".
4. **Scannable Metadata Cards**: Repository items render with visual quality ratings (`★★★★★`), language tags, and difficulty levels.
5. **Instant Boot & Background Sync**: Boots instantly (< 100ms) from local SQLite cache while fresh GitHub data syncs silently in background threads.
6. **Universal Skill Export**: Press `E` to export 1-click `SKILL.md` prompt instructions directly to `./.agents/skills/` and `./.opencode/skills/`.
7. **Activity History Log**: Logs all actions (Installed, Exported, Failed, Removed) to a persistent local SQLite database.

---

## Technical Documentation & Heuristics

OpenHub relies on deterministic algorithms rather than subjective metrics to score quality, classify difficulty levels, and curate sections.

Read the full technical documentation in [HOW_IT_WORKS.md](HOW_IT_WORKS.md).

---

## Keyboard Shortcuts

| Shortcut | Action |
| :--- | :--- |
| **`H`** | Navigate to Home Dashboard |
| **`B`** | Browse by Use Cases |
| **`C`** | Browse Curated Collections |
| **`S`** / **`/`** | Toggle Spotlight Search palette |
| **`I`** | View Installed packages |
| **`E`** | Export Skill directly (`SKILL.md` & Agent definition) |
| **`L`** | View Operation History logs |
| **`R`** | Refresh cache and sync repositories |
| **`F`** | Cycle implementation type filters (in Browse mode) |
| **`Enter`** | Show Details / Install selected repository |
| **`Esc`** | Exit details / Cancel modal / Close Search |
| **`Q`** | Quit application |

---

## Codebase Layout

```
openhub/
│
├── README.md               # Quickstart guide, system requirements & documentation
├── HOW_IT_WORKS.md          # Technical engine & scoring documentation
├── pyproject.toml          # Package configuration & openhub CLI entrypoint
├── install.sh              # Shell installer script
├── run.py                  # Standalone runner script
├── requirements.txt        # Package dependencies (textual, httpx, rapidfuzz)
├── .github/
│   └── workflows/
│       ├── ci.yml          # Automated test workflow on PRs
│       └── release.yml     # Automated GitHub release workflow
│
└── app/
    ├── __init__.py
    ├── main.py             # Main application orchestrator & background worker loop
    ├── cache.py            # SQLite database connection manager
    ├── client.py           # GitHub API client & caching
    ├── classifier.py       # Heuristic classification & Quality Score algorithms
    ├── exporter.py         # Universal SKILL.md & Agent exporter
    ├── installer.py        # Asynchronous installation runner subprocess
    │
    ├── screens/            # UI Screen views
    │   ├── home.py         # Home Dashboard view
    │   ├── browse.py       # Use-case browse list view
    │   ├── collections.py  # Curated Lists view
    │   ├── search.py       # Spotlight overlay dropdown view
    │   ├── details.py      # Markdown readme preview & Install confirm overlays
    │   └── history.py      # Operations activity log view
    │
    └── widgets.py          # Custom scannable card layout elements
```
