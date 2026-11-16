# Agent Guidelines for UltimateSkillStore (`usk`)

> **Notice to AI Coding Agents (Claude Code, Cursor, Codex, Gemini CLI):**  
> Do not attempt to load all skills or read the entire `data/` directory into your context window. Doing so will exhaust your token budget, degrade reasoning capabilities, and introduce conflicting instructions.  
> Always use the `usk` CLI to discover, inspect, and activate skills selectively.

---

## 1. Mandatory First Step: Auto-Recommend Skills on Every Task

At the start of **every task**, before writing code or giving an answer, run the project recommender so the store selects the smallest effective skill set for your specific project:

```bash
# 1. Analyze the project to detect its stack
python -m usk project analyze --project-dir .

# 2. Get ranked, conflict-checked skill recommendations
python -m usk project recommend --project-dir . --agent claude
```

**Why:** The recommender inspects `package.json`, `pyproject.toml`, `tsconfig.json`, `Dockerfile`, etc., then returns a ranked list (max 3 primary + 2 supporting skills) with reasons and token cost. This prevents context bloat and skill conflicts.

**Rule:** Do not activate skills manually without first running `usk project recommend`, unless the task is trivial and requires no specialized skill.

---

## 2. Progressive Disclosure Workflow

Follow this exact sequence for every skill you use:

```mermaid
flowchart LR
    A[Task Prompt] --> B[usk project recommend]
    B --> C[usk search <keywords>]
    C --> D[usk inspect <skill>]
    D --> E[usk activate <skill> --agent claude]
    E --> F[Execute Task]
    F --> G[usk deactivate <skill> | --all]
    G --> H[usk vote <skill> --up/--down]
```

### Step-by-step:

| Step | Command | Purpose |
|------|---------|---------|
| **1. Recommend** | `usk project recommend --project-dir . --agent claude` | Get project-matched, conflict-free skill candidates |
| **2. Search** | `usk search "<task keywords>"` | Find additional skills by topic if recommender missed something |
| **3. Inspect** | `usk inspect <skill-name>` | Review token cost, security status, license, integrity before activating |
| **4. Activate** | `usk activate <skill-name> --agent claude --project-dir .` | Stage only the selected skill into the workspace |
| **5. Execute** | Do the task using the activated skill's instructions | — |
| **6. Deactivate** | `usk deactivate <skill-name>` or `usk deactivate --all` | Clean up context when task is complete |
| **7. Feedback** | `usk vote <skill-name> --up` or `--down` | Record whether the skill helped improve ranking |

---

## 3. Operating Rules

1. **Query via CLI, Never Load Raw Dirs**:  
   Use `usk search "<task keywords>"` to find capabilities. Never read `data/approved/` or `curated_skills/` directly into context.

2. **Inspect Only the Top Candidate**:  
   Review the trigger description and token cost before reading/activating:
   ```bash
   usk inspect playwright-testing
   ```

3. **Respect Security Quarantine**:  
   Never activate skills marked with status `quarantine` or `untrusted` without developer confirmation. Verify with:
   ```bash
   usk audit <skill-name>
   ```
   A skill with `security_status: quarantine` must not be activated merely because it is popular.

4. **Autonomous Self-Activation**:  
   You do not need the human developer to activate skills for you. Run `usk activate <skill-name>` directly using your terminal execution tool. The agent environment (Claude Code, Cursor, etc.) is auto-detected.

5. **Clean Up After Completion**:  
   Deactivate or remove staged skills when your task is complete so subsequent tasks remain unaffected:
   ```bash
   usk deactivate <skill-name>
   ```

6. **Context Budget**:  
   Maximum 3 active skills by default. Check current allocation with:
   ```bash
   usk active
   ```

---

## 4. Command Reference

### Discovery & Sync
| Command | Description |
|---------|-------------|
| `usk project analyze --project-dir <path>` | Inspect project manifests and print capability profile |
| `usk project recommend --project-dir <path> --agent <agent>` | Recommend minimum effective skill set |
| `usk discover <path>` | Recursively index SKILL.md files from a local directory |
| `usk discover --git <url>` | Clone a remote git repo and index all agent skills |
| `usk sync` | Pull upstream git sources and update modified skills |
| `usk sources list` | List all tracked repositories |

### Search & Inspection
| Command | Description |
|---------|-------------|
| `usk search "<query>"` | Full-text search with SQLite FTS5 BM25 relevance ranking |
| `usk list [--category <c>] [--status <s>]` | List registered skills |
| `usk inspect <skill-id>` | View metadata, token cost, Bayesian score, tamper status |
| `usk export <skill-id> --out <dir>` | Export immutable canonical skill snapshot |

### Security, Provenance & Quarantine
| Command | Description |
|---------|-------------|
| `usk audit <skill-id>` | Run AST script and prompt injection scan |
| `usk quarantine list` | List quarantined skills |
| `usk quarantine inspect <id>` | View security scan findings |
| `usk approve <skill-id>` | Promote quarantined skill to approved (manual review) |
| `usk reject <skill-id>` | Reject and deactivate untrusted skill |

### Knowledge Graph
| Command | Description |
|---------|-------------|
| `usk graph query "<term>"` | Find skills linked to a technology/task |
| `usk graph dependencies <id>` | Resolve transitive dependency closure |
| `usk graph conflicts <s1> <s2>` | Check mutual conflicts between skills |

### Multi-Agent Staging & Activation
| Command | Description |
|---------|-------------|
| `usk activate <skill> --agent <claude\|cursor\|gemini\|codex\|markdown>` | Stage capability into agent workspace |
| `usk deactivate <skill>` | Unstage a capability |
| `usk deactivate --all` | Clean all active skills from workspace |
| `usk active` | List active skills and token budget |

### Quality, Feedback & Token
| Command | Description |
|---------|-------------|
| `usk vote <skill> --up \| --down` | Record feedback and update Bayesian quality score |
| `usk benchmark <skill> --cmd "<cmd>"` | Execute empirical test and record outcome |
| `usk token report` | Display token usage ledger summary |
| `usk token history` | Display recent token usage entries |
| `usk status` | Display registry health and metrics |
| `usk dashboard --out data/dashboard_export.json` | Export data for professional dashboard |

---

## 5. How to Activate a Skill for This Agent (Claude Code)

This environment is Claude Code. When the recommender returns a skill, stage it into `.claude/skills/`:

```bash
python -m usk activate <skill-name> --agent claude --project-dir .
```

Verify activation:
```bash
python -m usk active
```

When done:
```bash
python -m usk deactivate --all
```

---

## 6. Example: End-to-End Task Flow

**Task:** "Add Playwright E2E tests to the Next.js frontend."

```bash
# Step 1: Auto-recommend (mandatory first step)
python -m usk project recommend --project-dir . --agent claude

# Step 2: If recommender didn't cover testing, search
python -m usk search "playwright e2e testing"

# Step 3: Inspect before activating
python -m usk inspect playwright-testing

# Step 4: Activate
python -m usk activate playwright-testing --agent claude --project-dir .

# Step 5: Write the tests using the skill's instructions
# ...

# Step 6: Deactivate
python -m usk deactivate playwright-testing

# Step 7: Record feedback
python -m usk vote playwright-testing --up --notes "Helped write E2E test suite"
```

---

## 7. Tool Permission Guidelines

Skills declaring `allowed-tools` in frontmatter must not exceed the agent's safe sandbox boundary:

- **Read-only tools** (`Read`, `Glob`, `Grep`) can be auto-approved.
- **Execution tools** (`Bash`, `Write`, `Edit`) must be scoped strictly to the current workspace.

Never grant a skill access to `rm -rf`, `curl ... \| bash`, or credential exfiltration. The security scanner (`usk audit`) enforces this; respect its findings.

---

## 8. When NOT to Use a Skill

- The task is simple enough to solve with built-in knowledge.
- The skill's `security_status` is `quarantine` and you haven't run `usk audit`.
- Activating would exceed the max-3-skills context budget.
- Another active skill already covers the same capability (check `usk graph conflicts`).
- The skill's license is incompatible with your project (GPL/AGPL in proprietary work).

---

## 9. Record Keeping

After every task, update the store's feedback loop:

```bash
python -m usk vote <skill-name> --up   # skill was useful
python -m usk vote <skill-name> --down # skill was redundant or harmful
```

This feeds the Bayesian quality score used by `usk project recommend`, making recommendations better over time.

---

> **Remember:** The end goal is not to activate every skill. It is to activate **exactly the skills needed for the current task**, for **exactly as long as needed**, then clean up.
