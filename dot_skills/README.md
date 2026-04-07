# AI Agent Skills Directory

Central repository for 646+ reusable AI agent skills that are synced to Claude Code, Qwen, Vibe, and Codex consumers.

## Overview

This directory is the **source of truth** for all AI agent skills. Skills are automatically symlinked to multiple AI tool configurations on every `chezmoi apply`:

```
dot_agents/skills/ (source) ──┬──> ~/.claude/skills/ (symlink)
                              ├──> ~/.qwen/skills/ (symlink)
                              ├──> ~/.vibe/skills/ (symlink)
                              └──> ~/.codex/skills/ (symlink)
```

## Directory Structure

```
dot_agents/
├── README.md                    # This file
├── skills/                      # 646+ skill directories
│   ├── ab-test-setup/
│   │   ├── SKILL.md            # Skill definition (YAML frontmatter + markdown)
│   │   └── references/          # Optional supporting files
│   ├── academic-researcher/
│   ├── agent-development/
│   └── ...
└── dot_skill-lock.json         # Lock file (triggers sync on changes)
```

## Skill Format

Each skill is a directory with at minimum:

**`SKILL.md`** — Skill definition file

```markdown
---
name: ab-test-setup
description: When the user wants to plan, design, or implement an A/B test...
metadata:
  version: 1.0.0
---

# A/B Test Setup

Skill content in markdown...
```

The **frontmatter** (YAML between `---` markers) defines:
- `name` — Skill identifier (directory name)
- `description` — When to use this skill
- `metadata` — Version and other attributes

The **body** contains:
- Detailed instructions for the AI agent
- Frameworks and methodologies
- Examples and code snippets
- References to other skills

## Sync Mechanism

### Trigger: dot_skill-lock.json

The file `dot_agents/dot_skill-lock.json` serves as a trigger. When it changes, chezmoi runs the sync script.

**Location:** `~/.local/share/chezmoi/dot_agents/dot_skill-lock.json`

**Sample content:**
```json
{
  "dismissed": { "findSkillsPrompt": true },
  "lastSelectedAgents": ["claude-code", "qwen-code", ...],
  "skills": {
    "Agent Development": {
      "installedAt": "2026-03-13T20:58:42.908Z",
      "skillFolderHash": "55323e46...",
      "source": "anthropics/claude-code",
      "sourceType": "github",
      "updatedAt": "2026-03-13T20:58:42.908Z"
    },
    ...
  }
}
```

### Run Script: sync-skill-symlinks.sh

**Trigger:** `run_onchange_sync-skill-symlinks.sh.tmpl`

**Location:** `.chezmoiscripts/03-configure/run_onchange_sync-skill-symlinks.sh.tmpl`

**What it does:**
1. Reads skill directories from `~/.agents/skills/` (symlinked from dotfiles)
2. Creates symlinks in consumer directories:
   - `~/.claude/skills/` → `../../.agents/skills/*`
   - `~/.qwen/skills/` → `../../.agents/skills/*`
   - `~/.vibe/skills/` → `../../.agents/skills/*`
   - `~/.codex/skills/` → `../../.agents/skills/*`
3. Removes stale symlinks from previous skills
4. Reports count of synced skills

**Example output:**
```
skills: synced 646 skills to .claude .qwen .vibe .codex
```

### Running the Sync Manually

To force a re-sync without modifying a skill:

```bash
# Touch the lock file to change its timestamp
touch ~/.local/share/chezmoi/dot_agents/dot_skill-lock.json

# Re-apply to trigger the sync script
chezmoi apply
```

## Adding a New Skill

### Step 1: Create the skill directory

```bash
mkdir -p ~/.local/share/chezmoi/dot_agents/skills/my-awesome-skill
```

### Step 2: Create SKILL.md

```markdown
---
name: my-awesome-skill
description: When the user needs to [specific use case], use this skill
metadata:
  version: 1.0.0
---

# My Awesome Skill

You are an expert in [domain]. Your goal is to [objective].

## Core Principles

1. Principle one
2. Principle two

## Workflow

Step-by-step instructions...
```

### Step 3: Trigger the sync

```bash
# Bump the lock file
date > ~/.local/share/chezmoi/dot_agents/dot_skill-lock.json

# Apply to sync symlinks
chezmoi apply
```

### Step 4: Verify

```bash
ls -la ~/.claude/skills/ | grep my-awesome-skill
# Should show: my-awesome-skill -> ../../.agents/skills/my-awesome-skill
```

## Updating Skills from Upstream

### Pull from known sources

```bash
update-claude-skills           # Download latest from Jeffallan/Shubhamsaboo repos
update-claude-skills --dry-run # Preview changes
```

Sources:
- Jeffallan/claude-skills (90+ skills)
- Shubhamsaboo/awesome-llm-apps (15+ skills)

See [dot_local/bin/README.md](../dot_local/bin/README.md#update-claude-skills) for details.

## Integration with Chezmoi

### File paths

**Source (chezmoi repo):**
```
~/.local/share/chezmoi/dot_agents/skills/
```

**Managed symlink target:**
```
~/.agents/skills/ (created by chezmoi from dot_agents/ -> .agents/)
```

**Consumer symlinks:**
```
~/.claude/skills/ -> ../../.agents/skills/
~/.qwen/skills/ -> ../../.agents/skills/
~/.vibe/skills/ -> ../../.agents/skills/
~/.codex/skills/ -> ../../.agents/skills/
```

### How it works

1. Chezmoi copies `dot_agents/skills/*` to `~/.agents/skills/*`
2. The sync script creates symlinks from consumer dirs to `~/.agents/skills/`
3. All consumers see the same skills via symlinks
4. When a skill updates in the chezmoi repo, all consumers automatically see the new version

## Troubleshooting

### Skills not appearing in Claude Code

**Symptom:** Created a skill but it's not showing in the editor

**Fix:**
1. Verify symlink exists: `ls -la ~/.claude/skills/my-skill`
2. Re-run sync: `touch ~/.local/share/chezmoi/dot_agents/dot_skill-lock.json && chezmoi apply`
3. Restart Claude Code editor
4. Check browser cache (hard refresh: Cmd+Shift+R or Ctrl+Shift+R)

### Symlink shows "broken" (dangling)

**Symptom:** `ls -l` shows `skill-name -> ../../.agents/skills/skill-name (broken)`

**Cause:** `~/.agents/skills/` doesn't exist or skill was deleted

**Fix:**
```bash
# Check if .agents/skills/ exists
ls -la ~/.agents/skills/

# Re-trigger sync
touch ~/.local/share/chezmoi/dot_agents/dot_skill-lock.json
chezmoi apply -v
```

### Skills not syncing on chezmoi apply

**Symptom:** Modified lock file but symlinks didn't update

**Check:**
1. Verify script is executable: `ls -l ~/.chezmoiscripts/03-configure/run_onchange_sync-skill-symlinks.sh`
2. Check script output: `chezmoi apply -v | grep skills`
3. Manually run: `bash ~/.chezmoiscripts/03-configure/run_onchange_sync-skill-symlinks.sh`

### Too many open files error

**Symptom:** Error syncing skills on machines with lots of skills

**Cause:** System file descriptor limit too low

**Fix:**
```bash
# Check current limit
ulimit -n

# Increase temporarily
ulimit -n 4096

# Make permanent (add to ~/.zshrc or ~/.bashrc)
echo "ulimit -n 4096" >> ~/.zshrc
```

## Examples

### Basic skill structure

```
my-skill/
├── SKILL.md           # Required: skill definition
└── references/        # Optional: supporting files
    ├── template.md
    └── examples.json
```

### Skill with references

Some skills include supporting files that the skill might reference:

```
rag-architect/
├── SKILL.md
└── references/
    ├── vector-db-options.md
    ├── chunking-strategies.md
    └── retrieval-patterns.json
```

## Related Documentation

- [ONBOARDING.md — Working with AI Agents and Skills](../docs/ONBOARDING.md#working-with-ai-agents-and-skills)
- [RUNBOOK.md — Updating skills from upstream](../docs/RUNBOOK.md#update-claude-code-agents-from-upstream)
- [dot_local/bin/README.md — update-claude-skills](../dot_local/bin/README.md#update-claude-skills)
- [ARCHITECTURE.md — AI Agent & Skill Ecosystem](../docs/ARCHITECTURE.md#ai-agent--skill-ecosystem)

## Performance Notes

With 646+ skills:
- Symlink creation: <1 second
- Sync script runtime: 1-2 seconds
- No performance impact on normal operations
- All symlinks are relative paths (portable across machines)

## Contributing

To contribute skills to this repository:

1. Create skill in the proper format (SKILL.md with frontmatter)
2. Test in Claude Code or your preferred AI tool
3. Open a PR with the new skill directory
4. Update lock file and sync script if adding new consumer dirs
