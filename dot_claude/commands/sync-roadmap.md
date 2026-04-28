---
description: Sync Obsidian roadmap ↔ GitHub Project v2 (noxys-eu/3). Parses MASTER-ROADMAP-2026.md, diffs against project items, creates/updates/closes issues.
argument-hint: "[--dry-run] [--only-new] [--no-writeback]"
allowed-tools: Bash, Read, Grep, Glob, Agent
---

# /sync-roadmap

Bridge Obsidian vault master roadmap with GitHub Projects v2 under `noxys-eu` org.

## Flags

- `--dry-run` — preview diff without any mutations or write-back
- `--only-new` — apply only NEW items, skip UPDATED and CLOSED
- `--no-writeback` — apply mutations but do NOT modify roadmap file with `[#N]` markers

## Inputs (env + constants)

- ROADMAP_FILE = `/home/jeromesoyer/Documents/Github/jsoyer/obsidian-vault/Noxys/00 - Inbox/MASTER-ROADMAP-2026.md`
- GH_ORG = `noxys-eu`
- PROJECT_NUM = `3`
- PROJECT_ID = `PVT_kwDOEB4cq84BVLYy`
- Field IDs cache: run `gh project field-list 3 --owner noxys-eu --format json` once, cache to `~/.claude/cache/noxys-project-fields.json` (24h TTL).

## Behavior

1. **Parse roadmap** — extract every `### <ID> — <title>` heading, plus nested metadata (Priority, Effort, Sprint, Area). Keep the order. Ignore commented-out sections. Also extract any existing `[#N]` markers from title/row text.

2. **Fetch current project state** — `gh project item-list 3 --owner noxys-eu --format json --limit 500` → map of issue_number → item.

3. **Match roadmap → project items** using 4-tier priority:
   1. **Deterministic `[#N]` marker** — if roadmap item text contains `[#123]`, match project item with issue_number=123. Log as `[id]`.
   2. **Exact normalized title** — both sides normalize_title-equal. Log as `[exact]`.
   3. **Fuzzy Jaccard ≥ 0.75** — token Jaccard similarity after stopword removal. Best candidate above threshold wins; ties prefer shorter issue title. Log as `[fuzzy 0.NN]`.
   4. **No match** → NEW.

4. **Three diff categories:**
   - **NEW** — no match found → create issue + add to project.
   - **UPDATED** — match found but priority/effort/sprint/area changed → patch field values.
   - **CLOSED** — match found AND `completed: true` in roadmap → close issue.

5. **Dry-run mode** — print the diff table without applying. Includes a FUZZY MATCHES section (top 20). Default when `--dry-run` arg passed.

6. **--only-new flag** — apply only category NEW, skip UPDATED and CLOSED.

7. **Confirmation** — before applying ANY mutation, print a compact summary:
   ```
   SYNC PLAN
   ───────────
   +3 new items to create
   ~2 items to update (field changes)
   ✓1 item to close
   ≈15 fuzzy matches (will link to existing issues)

   Continue? (y/N)
   ```
   Wait for `y` from user.

8. **Repo inference rules** (apply in order, first match wins):
   - Title contains "extension" / "chrome" / "safari" → `noxys-extension`
   - Title contains "console" / "UI" / "dashboard" / "page" (and not "ext") → `noxys-console`
   - Area tag is `extension` → `noxys-extension`
   - Area tag is `console` OR `docs` → `noxys-console`
   - Default → `noxys-api`

9. **Issue body template** (same as bootstrap):
   ```
   ## Scope
   <description derived from roadmap or heading>

   ## Acceptance
   - [ ] Implementation complete
   - [ ] Tests added/passing
   - [ ] Docs updated
   - [ ] Merged to staging
   - [ ] CI green

   ## Refs
   - Obsidian: [[MASTER-ROADMAP-2026]]
   - Sprint: <sprint>
   - Area: <area>
   - Effort: <effort>d
   ```

10. **Idempotency** — before creating, search existing issue with same exact title (`gh issue list --repo <repo> --search "<title>" --state all --json number,title`). If match, reuse it (add to project if missing, then update fields).

11. **Field updates** use `gh project item-edit` with cached field IDs for single-select options.

12. **Write-back** (after successful apply, unless `--no-writeback`):
    - For each NEW item created: inject `[#<newIssueNum>]` into roadmap source.
    - For each fuzzy-matched item: inject `[#<existingNum>]` so future runs are deterministic.
    - For UPDATED/CLOSED items already having `[#N]`: skip (idempotent).
    - Injection point: for table rows — append before trailing `|`; for `### headings` — append at end of line.
    - Save the file, then:
      ```bash
      cd /home/jeromesoyer/Documents/Github/jsoyer/obsidian-vault
      git add "Noxys/00 - Inbox/MASTER-ROADMAP-2026.md"
      git commit -m "chore(roadmap): sync-roadmap write-back issue IDs"
      git push origin main
      ```
    - If push blocked by hook: run `~/.claude/hooks/approve.sh` and retry once.

## Execution plan

When invoked:

1. Verify prerequisites:
   ```bash
   command -v gh || { echo "ERROR: gh CLI required"; exit 1; }
   gh auth status 2>&1 | grep -q "Logged in" || { echo "ERROR: gh auth required"; exit 1; }
   ROADMAP_FILE="/home/jeromesoyer/Documents/Github/jsoyer/obsidian-vault/Noxys/00 - Inbox/MASTER-ROADMAP-2026.md"
   test -f "$ROADMAP_FILE" || { echo "ERROR: Roadmap file not found at $ROADMAP_FILE"; exit 1; }
   ```

2. Load or refresh field cache (24h TTL):
   ```bash
   CACHE_FILE="$HOME/.claude/cache/noxys-project-fields.json"
   CACHE_AGE=$(( $(date +%s) - $(stat -c %Y "$CACHE_FILE" 2>/dev/null || echo 0) ))
   if [ ! -f "$CACHE_FILE" ] || [ "$CACHE_AGE" -gt 86400 ]; then
     echo "Refreshing field cache..."
     gh project field-list 3 --owner noxys-eu --format json > "$CACHE_FILE"
   fi
   ```

3. Parse roadmap to JSON structure via Python (hybrid parser — table rows + headings):
   ```python
   #!/usr/bin/env python3
   """
   Hybrid parser for MASTER-ROADMAP-2026.md.
   Extracts items from markdown table rows inside ### sprint blocks.
   Sprint field normalized: S1-S2→W17-18, S3-S4→W19-20, S5-S6→W21-22,
   S7-S8→W23-24, S9-S10→W25-26, S11-S12→W27-28, else Backlog.
   Outputs JSON array. CLI: python3 parser.py [roadmap_file]
   """
   import re, json, sys, pathlib

   ROADMAP_FILE = sys.argv[1] if len(sys.argv) > 1 else (
       "/home/jeromesoyer/Documents/Github/jsoyer/obsidian-vault/Noxys/00 - Inbox/MASTER-ROADMAP-2026.md"
   )
   src = pathlib.Path(ROADMAP_FILE).read_text(encoding="utf-8")

   SPRINT_MAP = {
       "s1": "W17-18", "s2": "W17-18",
       "s3": "W19-20", "s4": "W19-20",
       "s5": "W21-22", "s6": "W21-22",
       "s7": "W23-24", "s8": "W23-24",
       "s9": "W25-26", "s10": "W25-26",
       "s11": "W27-28", "s12": "W27-28",
   }

   def normalize_title(t):
       t = t.strip().lower()
       t = re.sub(r'\[#\d+\]', '', t)        # strip existing [#N] markers
       t = re.sub(r'[^\w\s]', ' ', t)
       t = re.sub(r'\s+', ' ', t)
       t = re.sub(r'[.,:;!?]+$', '', t)
       t = re.sub(r'\*+', '', t)
       return t.strip()

   # ── Fuzzy matching ──────────────────────────────────────────────────────────
   STOP = {
       'the','a','an','and','or','for','with','to','of','in','by','on',
       'noxys','sprint','phase','le','la','les','un','une','de','du','des',
       'et','pour','avec',
   }

   def token_overlap(a, b):
       """
       Overlap coefficient = |A∩B| / min(|A|,|B|).
       Handles asymmetric title lengths: short project titles vs long roadmap titles.
       Score=1.0 when all tokens of the shorter title appear in the longer one.
       """
       ta = set(normalize_title(a).split()) - STOP
       tb = set(normalize_title(b).split()) - STOP
       if not ta or not tb:
           return 0.0
       return len(ta & tb) / min(len(ta), len(tb))

   # Alias kept for backward-compat references in log output
   token_jaccard = token_overlap

   FUZZY_THRESHOLD = 0.75

   def best_fuzzy_match(roadmap_title, project_items):
       """
       Returns (issue_number, score, project_title) or None.
       project_items: list of dicts with keys title, issue_number.
       Ties: prefer shorter project title (cleaner match).
       """
       best_score = 0.0
       best = None
       for item in project_items:
           score = token_overlap(roadmap_title, item["title"])
           if score > best_score or (
               score == best_score and best is not None
               and len(item["title"]) < len(best[2])
           ):
               best_score = score
               best = (item["issue_number"], score, item["title"])
       if best and best_score >= FUZZY_THRESHOLD:
           return best
       return None
   # ────────────────────────────────────────────────────────────────────────────

   def map_sprint(heading_text):
       m = re.search(r'S(\d+)(?:-S?(\d+))?', heading_text, re.IGNORECASE)
       if m:
           s_start = "s" + m.group(1)
           s_end = "s" + m.group(2) if m.group(2) else s_start
           return SPRINT_MAP.get(s_start) or SPRINT_MAP.get(s_end) or "Backlog"
       m2 = re.search(r'W(\d+)-?(\d+)', heading_text, re.IGNORECASE)
       if m2:
           return f"W{m2.group(1)}-{m2.group(2)}"
       return "Backlog"

   def is_done(status_val):
       if not status_val:
           return False
       s = status_val.strip()
       if s.startswith("✅") or s.upper() in ("DONE", "✓", "LIVRE"):
           return True
       return bool(re.match(r'(?i)✅|done|livr[eé]', s))

   def extract_issue_id(text):
       """Extract [#123] from text, return int or None."""
       m = re.search(r'\[#(\d+)\]', text or "")
       return int(m.group(1)) if m else None

   def infer_repo(title, area=""):
       t = (title or "").lower()
       a = (area or "").lower()
       if "extension" in t or "chrome" in t or "safari" in t or "firefox" in t:
           return "noxys-extension"
       if ("console" in t or " ui" in t or "dashboard" in t) and "ext" not in t:
           return "noxys-console"
       if "ux wave" in t or "noxys-console" in t:
           return "noxys-console"
       if a in ("extension",):
           return "noxys-extension"
       if a in ("console", "docs", "ux"):
           return "noxys-console"
       return "noxys-api"

   def is_task_table_header(header_row):
       cols = [c.strip().lower() for c in header_row.strip().strip("|").split("|")]
       has_task = any(re.search(r'\bitem\b|\btask\b|^#$', c) for c in cols)
       has_status = any(re.search(r'\bstatut\b|\bstatus\b', c) for c in cols)
       return has_task or has_status

   def parse_table_header(header_row):
       cols = [c.strip().lower() for c in header_row.strip().strip("|").split("|")]
       col_map = {}
       for i, c in enumerate(cols):
           if re.search(r'\bitem\b|\btask\b', c) and "title" not in col_map:
               col_map["title"] = i
           elif re.search(r'\brepo\b', c):
               col_map.setdefault("repo", i)
           elif re.search(r'\bprio\b|\bpriorit[eé]?\b|\bpriority\b', c):
               col_map.setdefault("priority", i)
           elif re.search(r'\beffort\b|\bcharge\b', c):
               col_map.setdefault("effort", i)
           elif re.search(r'\barea\b|\bdimension\b|\bdomaine\b', c):
               col_map.setdefault("area", i)
           elif re.search(r'\bstatut\b|\bstatus\b', c):
               col_map.setdefault("status", i)
           elif re.search(r'\bowner\b', c):
               col_map.setdefault("owner", i)
       if "title" not in col_map and cols:
           col_map["title"] = 0
       return col_map

   _JUNK = re.compile(r'^(\d+\.?\d*|[A-Z]\d+|jerome|vincent|claude|total|phase \d+|sprint \d+|—|-|n/a|S\d+\s*\(.*)$', re.I)

   # Bug #3 fix: detect ✅ Done / ✓ Done suffix embedded inside the title cell.
   _TITLE_DONE_SUFFIX_RE = re.compile(r'\s*(?:✅|✓)\s*Done\s*$|\s*✅\s*$', re.IGNORECASE)

   def strip_done_suffix(title):
       """Return (cleaned_title, completed_flag). If title ends with ✅ Done / ✓ Done / ✅, strip and flag."""
       if not title:
           return title, False
       if _TITLE_DONE_SUFFIX_RE.search(title):
           return _TITLE_DONE_SUFFIX_RE.sub('', title).strip(), True
       return title, False

   def is_valid_title(t):
       if not t or len(t) < 5:
           return False
       if re.match(r'^S\d+\s*\(', t.strip()):
           return False
       if re.match(r'(?i)^phase\s+\d+\s+[-—]+', t.strip()):
           return False
       return not _JUNK.match(t.strip())

   def parse_table_rows(block_text, sprint_val):
       items = []
       lines = block_text.split("\n")
       col_map = {}
       has_header = False
       skip_table = False

       for line in lines:
           stripped = line.strip()
           if not stripped.startswith("|"):
               if has_header:
                   has_header = False
                   col_map = {}
                   skip_table = False
               continue
           if re.match(r'^\|[-| :]+\|?$', stripped):
               has_header = True
               continue
           cells = [c.strip() for c in stripped.strip("|").split("|")]
           if not has_header:
               if not is_task_table_header(stripped):
                   skip_table = True
               else:
                   skip_table = False
                   col_map = parse_table_header(stripped)
               has_header = True
               continue
           if skip_table or not any(cells):
               continue

           title_idx = col_map.get("title", 0)
           if title_idx >= len(cells):
               continue
           raw_title_cell = cells[title_idx]
           # Extract [#N] before stripping
           inline_issue_id = extract_issue_id(raw_title_cell)
           raw_title = re.sub(r'\[#\d+\]', '', re.sub(r'\*+', '', raw_title_cell)).strip()
           # Bug #3: status emoji embedded in title cell
           raw_title, title_done = strip_done_suffix(raw_title)
           if raw_title.startswith("~~") or not is_valid_title(raw_title):
               continue

           def get(key):
               idx = col_map.get(key)
               return cells[idx].strip() if idx is not None and idx < len(cells) else ""

           area_val = get("area")
           repo_cell = get("repo")
           repo = repo_cell if repo_cell else infer_repo(raw_title, area_val)
           p_match = re.search(r'P[0-3]', get("priority"))
           priority = p_match.group(0) if p_match else "P2"
           e_match = re.search(r'(\d+(?:\.\d+)?)\s*[jd]', get("effort"))
           effort = float(e_match.group(1)) if e_match else None
           completed = is_done(get("status")) or title_done

           items.append({
               "id": None,
               "title": raw_title,
               "inline_issue_id": inline_issue_id,
               "priority": priority,
               "effort": effort,
               "sprint": sprint_val,
               "area": area_val or "api",
               "repo": repo,
               "completed": completed,
           })
       return items

   # ── Heading-level item parser (v3) ─────────────────────────────────────────
   # Matches:  ### ID — title  (e.g. ### ENROLL-1 — Extension enrollment endpoint)
   # Followed by metadata list block:
   #   - **Priority:** P0
   #   - **Effort:** 3j  or  - **Effort estimate:** 3j
   #   - **Sprint:** W21-22
   #   - **Area:** api
   #   - **Design:** [[some-doc]]   (skipped, not extracted)

   HEADING_ITEM_RE = re.compile(
       r'^###\s+([A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*)\s*[—\-]+\s*(.+)$',
       re.MULTILINE
   )

   # Bug #2 fix: reject sprint section dividers like
   #   "### S6 (May 5-16) --- AGENT..."
   #   "### W17-18 (Apr 7-11) --- ..."
   # Whitelist: ID must be a real task ID (alpha prefix + optional -digit/-alpha-digit),
   # never purely sprint-like (S\d+, S\d+-S?\d+, W\d+-\d+, P\d+, PHASE\d+).
   _SPRINT_ID_RE = re.compile(r'^(?:S\d+(?:-S?\d+)?|W\d+(?:-\d+)?|P\d+|PHASE\d+)$', re.IGNORECASE)
   _DIVIDER_TITLE_RE = re.compile(r'^\(.+?\).*-{2,}', re.IGNORECASE)  # "(May 5-16) --- AGENT"

   def is_sprint_divider_heading(item_id, title_part):
       """True when this ### heading is a sprint section divider, not a task heading."""
       if _SPRINT_ID_RE.match(item_id or ""):
           return True
       if title_part and _DIVIDER_TITLE_RE.match(title_part.strip()):
           return True
       # Multi-dash separator inside title => divider
       if title_part and re.search(r'\s-{3,}\s', title_part):
           return True
       return False

   def parse_heading_items(src_text):
       """
       Extract structured items from ### ID — title headings with metadata blocks.
       Returns list of item dicts (same schema as parse_table_rows output).
       """
       heading_items = []
       lines = src_text.split("\n")
       n = len(lines)
       i = 0
       while i < n:
           line = lines[i]
           m = HEADING_ITEM_RE.match(line.strip())
           if m:
               item_id = m.group(1)
               title_part = m.group(2).strip()
               # Bug #2: skip sprint section dividers
               if is_sprint_divider_heading(item_id, title_part):
                   i += 1
                   continue
               # Extract any [#N] marker from the heading line
               inline_id = extract_issue_id(line)
               # Strip [#N] from title
               title_clean = re.sub(r'\[#\d+\]', '', title_part).strip()
               # Bug #3: status emoji embedded in heading title
               title_clean, heading_done = strip_done_suffix(title_clean)

               # Read metadata from following lines (until blank line or next ## / ###)
               meta = {"priority": "P2", "effort": None, "sprint": None, "area": "api"}
               j = i + 1
               while j < n:
                   ml = lines[j].strip()
                   if not ml or re.match(r'^#{2,}\s', ml):
                       break
                   pm = re.match(r'-\s+\*\*Priority:\*\*\s*(P[0-3])', ml, re.IGNORECASE)
                   if pm:
                       meta["priority"] = pm.group(1)
                   em = re.match(r'-\s+\*\*Effort(?:\s+estimate)?:\*\*\s*(\d+(?:\.\d+)?)\s*[jd]', ml, re.IGNORECASE)
                   if em:
                       meta["effort"] = float(em.group(1))
                   sm = re.match(r'-\s+\*\*Sprint:\*\*\s*([\w\-]+)', ml, re.IGNORECASE)
                   if sm:
                       meta["sprint"] = sm.group(1)
                   am = re.match(r'-\s+\*\*Area:\*\*\s*(\w+)', ml, re.IGNORECASE)
                   if am:
                       meta["area"] = am.group(1).lower()
                   j += 1

               sprint_val = meta["sprint"] or map_sprint(title_clean)
               repo = infer_repo(title_clean, meta["area"])
               full_title = title_clean  # e.g. "Extension enrollment endpoint + JWT + refresh"

               heading_items.append({
                   "id": item_id,
                   "title": full_title,
                   "inline_issue_id": inline_id,
                   "priority": meta["priority"],
                   "effort": meta["effort"],
                   "sprint": sprint_val,
                   "area": meta["area"],
                   "repo": repo,
                   "completed": heading_done,
                   "source": "heading",
               })
           i += 1
       return heading_items

   # ── Assemble all items (table rows + heading items, deduped by norm title) ──

   # Split on ### headings
   blocks = re.split(r'^(### .+)$', src, flags=re.MULTILINE)

   all_items = []
   seen = set()

   i = 1
   while i < len(blocks) - 1:
       heading = blocks[i]
       content = blocks[i + 1] if i + 1 < len(blocks) else ""
       i += 2
       sprint_val = map_sprint(heading.lstrip("# ").strip())
       for item in parse_table_rows(content, sprint_val):
           norm = normalize_title(item["title"])
           if norm not in seen:
               seen.add(norm)
               all_items.append(item)

   # Add heading-level items (dedupe against table rows)
   for item in parse_heading_items(src):
       norm = normalize_title(item["title"])
       if norm not in seen:
           seen.add(norm)
           all_items.append(item)

   print(json.dumps(all_items, indent=2, ensure_ascii=False))
   ```

4. Fetch project items:
   ```bash
   gh project item-list 3 --owner noxys-eu --format json --limit 500
   ```
   Build two maps:
   - `normalized_title → { item_id, issue_number, title, repo, fields }`
   - `issue_number → { item_id, issue_number, title, repo, fields }`
   Also keep a flat list for fuzzy scanning.

5. Compute diff using 4-tier matching (Python, stdlib only):
   ```python
   import re, json

   STOP = {
       'the','a','an','and','or','for','with','to','of','in','by','on',
       'noxys','sprint','phase','le','la','les','un','une','de','du','des',
       'et','pour','avec',
   }
   FUZZY_THRESHOLD = 0.75

   def normalize_title(t):
       t = re.sub(r'\[#\d+\]', '', t or "")
       t = re.sub(r'[^\w\s]', ' ', t.lower().strip())
       return re.sub(r'\s+', ' ', t).strip()

   def token_overlap(a, b):
       """Overlap coefficient = |A∩B| / min(|A|,|B|). Handles short project vs long roadmap titles."""
       ta = set(normalize_title(a).split()) - STOP
       tb = set(normalize_title(b).split()) - STOP
       if not ta or not tb:
           return 0.0
       return len(ta & tb) / min(len(ta), len(tb))

   # Bug #1 fix: helper extracting just the repo NAME from full org/repo or repo string
   def short_repo(full):
       if not full:
           return ""
       return full.rsplit("/", 1)[-1]

   def match_item(rm_item, by_num, by_norm_title, project_list, by_repo_num=None):
       # Tier 1: [#N] marker — composite (repo, num) lookup post-Phase 3a moves
       if rm_item.get("inline_issue_id"):
           num = rm_item["inline_issue_id"]
           rm_repo = short_repo(rm_item.get("repo", ""))
           if by_repo_num and rm_repo and (rm_repo, num) in by_repo_num:
               return by_repo_num[(rm_repo, num)], "id", 1.0
           # Fallback: bare-num lookup for items without repo context — log warning
           if num in by_num:
               import sys
               print(f"WARNING: ambiguous [#{num}] '{rm_item.get('title','')[:60]}' — no repo context, falling back to bare-num match", file=sys.stderr)
               return by_num[num], "id-fallback", 1.0
       # Tier 2: exact normalized title
       norm = normalize_title(rm_item["title"])
       if norm in by_norm_title:
           return by_norm_title[norm], "exact", 1.0
       # Tier 3: fuzzy
       best_score = 0.0
       best_proj = None
       for proj in project_list:
           score = token_overlap(rm_item["title"], proj["title"])
           if score > best_score or (
               score == best_score and best_proj is not None
               and len(proj["title"]) < len(best_proj["title"])
           ):
               best_score = score
               best_proj = proj
       if best_proj and best_score >= FUZZY_THRESHOLD:
           return best_proj, f"fuzzy {best_score:.2f}", best_score
       return None, "new", 0.0

   new_items = []
   updated_items = []
   closed_items = []
   fuzzy_matches = []   # for dry-run display

   for rm in roadmap_items:
       proj, strategy, score = match_item(rm, by_num, by_norm_title, project_list)
       if proj is None:
           new_items.append(rm)
       else:
           if strategy.startswith("fuzzy"):
               fuzzy_matches.append({
                   "roadmap_title": rm["title"],
                   "project_title": proj["title"],
                   "issue_number": proj["issue_number"],
                   "score": score,
                   "already_has_marker": bool(rm.get("inline_issue_id")),
               })
           if rm["completed"] and not proj.get("closed"):
               closed_items.append({**rm, "proj": proj, "strategy": strategy})
           elif fields_differ(rm, proj):
               updated_items.append({**rm, "proj": proj, "strategy": strategy})
   ```

6. **Dry-run diff table output:**
   ```
   ── NEW (N items) ──────────────────────────────────────────────────────────
    + "Title of new item" [sprint] [repo]
    ...

   ── UPDATED (N items) ──────────────────────────────────────────────────────
    ~ "Title" [exact] P2→P1 sprint changed
    ~ "Title" [fuzzy 0.82] area changed
    ...

   ── CLOSED (N items) ──────────────────────────────────────────────────────
    ✓ "Title" [id] #42
    ...

   ── FUZZY MATCHES (top 20 — will link to existing issues on apply) ─────────
    ≈ [0.91] "ONNX NER extension (CamemBERT, Web Worker, <15ms)" ← roadmap: "ONNX NER extension (noms, orgs, adresses, Web Worker)" (#13)
    ≈ [0.82] "Microsoft Purview integration (Graph API)" ← roadmap: "Purview connector - Sensitivity labels sync" (#14)
    ...
    (if more than 20: "… and N more fuzzy matches")
   ```

7. If `--dry-run` flag present OR user declines confirmation: print diff table and exit 0.

8. On confirm (`y`), apply mutations sequentially:

   **NEW item:**
   ```bash
   ISSUE_NUM=$(gh issue create \
     --repo "noxys-eu/<inferred_repo>" \
     --title "<title>" \
     --body "<rendered body template>" \
     --label "roadmap" \
     --json number --jq '.number')
   gh project item-add 3 --owner noxys-eu \
     --url "https://github.com/noxys-eu/<repo>/issues/$ISSUE_NUM"
   # Then set field values via gh project item-edit
   ```

   **UPDATED item:**
   ```bash
   gh project item-edit \
     --id "<project_item_id>" \
     --project-id "PVT_kwDOEB4cq84BVLYy" \
     --field-id "<field_id>" \
     --single-select-option-id "<option_id>"
   ```

   **CLOSED item:**
   ```bash
   gh issue close <issue_number> --repo "noxys-eu/<repo>" \
     --comment "Closed via /sync-roadmap — marked complete in MASTER-ROADMAP-2026.md"
   ```

   Log each action with strategy tag: `[NEW] issue #XX created in noxys-api: "Title..."`, `[UPD][exact] item XX priority P2→P1`, `[UPD][fuzzy 0.82] item XX area changed`.
   Continue on single-item failures; collect errors for final summary.

9. **Write-back** (skip if `--no-writeback` or `--dry-run`):
   ```python
   import pathlib, re

   ROADMAP_FILE = "/home/jeromesoyer/Documents/Github/jsoyer/obsidian-vault/Noxys/00 - Inbox/MASTER-ROADMAP-2026.md"

   def inject_issue_id(line, issue_num):
       """
       Inject [#N] into a roadmap line.
       - Table row: append before trailing |
       - Heading (###): append at end of line
       - Already has [#N]: skip (idempotent)
       """
       if re.search(r'\[#\d+\]', line):
           return line   # already tagged
       marker = f"[#{issue_num}]"
       stripped = line.rstrip()
       if stripped.endswith("|"):
           return stripped[:-1].rstrip() + " " + marker + " |" + line[len(stripped):]
       return stripped + " " + marker + line[len(stripped):]

   src = pathlib.Path(ROADMAP_FILE).read_text(encoding="utf-8")
   lines = src.split("\n")

   # Build map: normalized_title → issue_num for all items needing write-back
   # (new items + fuzzy-matched items without existing [#N])
   writeback_map = {}   # normalized_title → issue_num
   for item in new_items_created:       # {"title": ..., "issue_number": N}
       writeback_map[normalize_title(item["title"])] = item["issue_number"]
   for fm in fuzzy_matches_applied:     # {"roadmap_title": ..., "issue_number": N}
       if not fm["already_has_marker"]:
           writeback_map[normalize_title(fm["roadmap_title"])] = fm["issue_number"]

   result_lines = []
   for line in lines:
       injected = False
       for norm_title, issue_num in writeback_map.items():
           # Match if line contains the title text (strip [#N] first)
           line_norm = normalize_title(re.sub(r'\[#\d+\]', '', line))
           if norm_title in line_norm and len(norm_title) > 8:
               line = inject_issue_id(line, issue_num)
               injected = True
               break
       result_lines.append(line)

   pathlib.Path(ROADMAP_FILE).write_text("\n".join(result_lines), encoding="utf-8")
   print(f"Write-back: injected [#N] markers for {len(writeback_map)} items")
   ```

   Then commit+push:
   ```bash
   cd /home/jeromesoyer/Documents/Github/jsoyer/obsidian-vault
   git add "Noxys/00 - Inbox/MASTER-ROADMAP-2026.md"
   git commit -m "chore(roadmap): sync-roadmap write-back issue IDs"
   git push origin main
   ```
   If push is blocked by hook: run `~/.claude/hooks/approve.sh` and retry once.

10. Final summary:
    ```
    SYNC COMPLETE
    ─────────────
    ✓ 3 created
    ✓ 2 updated
    ✓ 1 closed
    ≈ 15 fuzzy-matched (issue IDs written back)
    ⚠ 0 errors

    Project: https://github.com/orgs/noxys-eu/projects/3
    ```

## Notes

- First run will create the field ID cache if missing (already pre-populated at `~/.claude/cache/noxys-project-fields.json`).
- Command is safe to run frequently — idempotent by design.
- For ambiguous items (no clear area/sprint match), fall back to Backlog + `noxys-api`, log a warning.
- The `--only-new` flag is safe for frequent polling without risk of unintended closures.
- Roadmap IDs must match pattern `[A-Z0-9-]+` (e.g., `S1-01`, `W2-AUTH`, `MVP-001`).
- After first run with write-back, subsequent runs will match deterministically via `[#N]` markers and fuzzy_match_count will drop to 0.
- The fuzzy threshold of 0.75 was chosen to balance precision (avoid false matches) vs recall (close title divergences). Lower to 0.65 if too many items remain NEW; raise to 0.85 if false matches appear.
