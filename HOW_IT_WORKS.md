# OpenHub — Heuristics, Scoring & Curation Engine

OpenHub uses deterministic algorithms and repository metadata rather than subjective labels or placeholder metrics to evaluate, categorize, and rank packages.

This document details the mathematical formulas, classification criteria, and curation rules used by the engine.

---

## 1. Repository Quality Score (0 – 100)

Repositories fetched from GitHub undergo quantitative evaluation in `app/classifier.py`. The overall quality score is a composite index (0–100) calculated as:

$$\text{Quality Score} = \text{Popularity (30)} + \text{Activity (30)} + \text{Documentation (20)} + \text{Issue Health (20)}$$

### Score Component Breakdown

| Category | Max Points | Evaluation Criteria | Formulas & Thresholds |
| :--- | :--- | :--- | :--- |
| **Popularity** | **30 pts** | Logarithmic scaling of Stars & Forks | • **Stars (15 pts)**: $\min(15, \frac{\text{stars}}{100} \times 1.5)$ for $<1000$ stars; $15$ pts for $\ge 1000$ stars.<br>• **Forks (15 pts)**: $\min(15, \frac{\text{forks}}{50} \times 1.5)$ for $<500$ forks; $15$ pts for $\ge 500$ forks. |
| **Maintenance Activity** | **30 pts** | Recency of last pushed commit (`pushed_at` / `updated_at`) | • $\le 15$ days ago: **30 pts**<br>• $\le 45$ days ago: **25 pts**<br>• $\le 90$ days ago: **20 pts**<br>• $\le 180$ days ago: **15 pts**<br>• $\le 365$ days ago: **10 pts**<br>• $> 365$ days ago: **5 pts** |
| **Documentation & License** | **20 pts** | Length of `README.md` and presence of open-source license | • README $> 2500$ chars: **15 pts** (1000–2500: **10 pts**, >100: **5 pts**)<br>• Valid Open Source License attached: **+5 pts** |
| **Issue Health Ratio** | **20 pts** | Ratio of unresolved issues to overall community size ($\frac{\text{Open Issues}}{\text{Stars}}$) | • Ratio $< 0.05$ (5%): **20 pts** (high responsiveness)<br>• Ratio $0.05 - 0.20$: **15 pts**<br>• Ratio $0.20 - 0.50$: **10 pts**<br>• Ratio $> 0.50$: **5 pts** (unresolved bug backlog) |

### Quality Rating & Tier Mapping

Based on the final score, repositories are assigned a rating star string and tier label:

| Score Range | Stars | Rating Label | Description |
| :--- | :--- | :--- | :--- |
| **90 – 100** | `★★★★★` | **Excellent** | High activity, comprehensive documentation, strong adoption, low issue ratio. |
| **75 – 89** | `★★★★☆` | **Great** | Well-maintained, solid documentation, active community. |
| **60 – 74** | `★★★☆☆` | **Good** | Functional utility with moderate activity or documentation. |
| **40 – 59** | `★★☆☆☆` | **Fair** | Minimal documentation or less recent commit activity. |
| **0 – 39** | `★☆☆☆☆` | **Poor** | Incomplete setup information, stale codebase, or high issue ratio. |

---

## 2. Difficulty Level Matrix

Difficulty levels reflect operational setup complexity and prerequisite knowledge:

- **Advanced**: Applied when setup requires containerization, native compilation, or external database systems (keywords: `docker`, `kubernetes`, `postgres`, `c++`, `rust`, `compile`, `libpq`).
- **Beginner**: Applied when documentation targets entry-level integration (keywords: `beginner`, `easy`, `simple`, `starter`, `tutorial`).
- **Intermediate**: Default classification for standard tools, skills, and CLI applications with standard runtime dependencies.

---

## 3. Dashboard Curation Sections

The Home Dashboard (`app/screens/home.py`) categorizes packages into automated sections:

1. **TRENDING TODAY**: Top 3 repositories sorted by GitHub star count.
2. **JUST RELEASED**: Top 3 repositories sorted by creation timestamp (`created_at`).
3. **FASTEST GROWING**: Top 3 repositories sorted by fork count.
4. **HIDDEN GEMS**: Repositories matching `Quality Score >= 80` AND `Stars < 2000`. Identifies high-quality, well-maintained tools that are not yet widely known.
5. **EDITOR'S PICKS**: Selected core ecosystem tools (`browser-use/browser-use`, `modelcontextprotocol/servers`, `OpenInterpreter/open-interpreter`).
6. **RECENTLY INSTALLED**: Packages installed locally and recorded in `repos.db`.

---

## 4. Taxonomy & Intent Classification

Repositories are classified into **12 Use Case Categories** and **5 Implementation Types** using multi-label heuristic keyword matching across names, descriptions, GitHub topics, and README excerpts:

### Use Case Categories
- **Web Research**: `research`, `search`, `google`, `scrape`, `crawl`, `web-search`
- **Coding**: `code`, `coding`, `compiler`, `autocomplete`, `refactor`, `ast`, `lsp`
- **Debugging**: `debug`, `pdb`, `gdb`, `traceback`, `logging`, `inspector`
- **Testing**: `test`, `pytest`, `unittest`, `assertion`, `cypress`, `playwright`
- **Documentation**: `doc`, `readme`, `wiki`, `sphinx`, `mkdocs`
- **Automation**: `automation`, `cron`, `workflow`, `scheduler`, `script`
- **Cloud**: `aws`, `gcp`, `azure`, `docker`, `kubernetes`, `terraform`
- **Database**: `database`, `postgres`, `sqlite`, `mysql`, `redis`, `sql`
- **Security**: `security`, `auth`, `secret`, `guardrail`, `cipher`
- **UI**: `ui`, `gui`, `tui`, `textual`, `css`, `layout`, `react`
- **Data Science**: `pandas`, `numpy`, `jupyter`, `visualization`, `math`
- **Multi-Agent**: `multi-agent`, `swarm`, `crewai`, `autogen`, `langgraph`

### Implementation Types
- **MCP Servers**: Matches `mcp`, `model-context-protocol`
- **Plugins**: Matches `plugin`, `extension`
- **Agents**: Matches `agent`, `autonomous`, `swarm`
- **Skills**: Matches `skill`, `tool`
- **Commands**: Matches `command`, `cli`, `runner`

---

## 5. Spotlight Search Engine

The Spotlight search overlay uses `RapidFuzz` to calculate token-ratio similarity scores between user queries and pre-indexed repository fields (`name`, `owner`, `description`, `use_case`, `impl_type`, `tags`). Search executes locally with zero external latency.

---

## 6. Skill Export Engine (`.opencode/skills/`)

OpenCode Hub supports exporting repository instructions directly into OpenCode-native skill formats via `app/exporter.py`:

- **Project Destination (`P`)**: `./.agents/skills/<skill-slug>/SKILL.md`, `./.opencode/skills/<skill-slug>/SKILL.md`, and `./.claude/skills/<skill-slug>/SKILL.md` (Local project root)
- **Global Destination (`G`)**: `~/.agents/skills/<skill-slug>/SKILL.md`, `~/.config/opencode/skills/<skill-slug>/SKILL.md`, and `~/.claude/skills/<skill-slug>/SKILL.md` (System user config)

Exported files are structured with YAML frontmatter headers:
```markdown
---
name: <skill-slug>
description: "<repository-description>"
---

<readme-instructions>
```

OpenCode automatically discovers and loads exported skills upon startup.
