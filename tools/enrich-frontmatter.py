#!/usr/bin/env python3
"""Enrich skill SKILL.md files with match: frontmatter for claude-context."""

import os
import re
import sys
import yaml

SKILLS_DIR = os.path.join(os.path.dirname(__file__), "..", "dot_aictx", "skills")

# Inference rules
LANG_KEYWORDS = {
    "typescript": [
        "typescript",
        "tsx",
        "ts ",
        "angular",
        "react",
        "vue",
        "nextjs",
        "next.js",
        "node",
    ],
    "javascript": [
        "javascript",
        "jsx",
        "js ",
        "node",
        "npm",
        "express",
        "webpack",
        "vite",
    ],
    "python": [
        "python",
        "django",
        "flask",
        "fastapi",
        "pandas",
        "pytorch",
        "tensorflow",
        "pip",
    ],
    "rust": ["rust", "cargo", "tokio", "axum", "actix", "wasm"],
    "go": ["golang", " go ", "gin", "echo", "fiber", "goroutine"],
    "java": ["java", "spring", "maven", "gradle", "jvm", "jpa", "hibernate"],
    "kotlin": ["kotlin", "android", "jetpack", "compose", "coroutine", "ktor"],
    "swift": ["swift", "swiftui", "ios", "macos", "xcode", "uikit"],
    "cpp": ["c++", "cpp", "cmake", "stl", "raii", "template metaprogramming"],
    "csharp": [
        "c#",
        "csharp",
        ".net",
        "dotnet",
        "asp.net",
        "entity framework",
        "blazor",
    ],
    "ruby": ["ruby", "rails", "sinatra", "gem"],
    "php": ["php", "laravel", "symfony", "composer"],
    "lua": ["lua", "neovim", "nvim", "love2d"],
    "shell": ["shell", "bash", "zsh", "sh ", "posix", "script"],
    "elixir": ["elixir", "phoenix", "otp", "genserver"],
    "dart": ["dart", "flutter"],
    "sql": ["sql", "postgres", "mysql", "sqlite", "database", "query"],
}

TAG_KEYWORDS = {
    "frontend": [
        "frontend",
        "ui",
        "ux",
        "component",
        "css",
        "tailwind",
        "design system",
        "responsive",
        "design critique",
    ],
    "backend": ["backend", "api", "server", "microservice", "rest", "graphql", "grpc"],
    "fullstack": ["fullstack", "full-stack", "full stack", "convex"],
    "devops": ["devops", "ci/cd", "pipeline", "deploy", "infrastructure"],
    "docker": ["docker", "container", "dockerfile", "compose"],
    "kubernetes": ["kubernetes", "k8s", "helm", "kubectl"],
    "terraform": ["terraform", "iac", "infrastructure as code"],
    "aws": ["aws", "amazon", "s3", "lambda", "ec2", "dynamodb", "cloudformation"],
    "azure": ["azure", "entra", "microsoft cloud"],
    "gcp": ["gcp", "google cloud", "bigquery", "cloud run", "google workspace", "gws"],
    "database": [
        "database",
        "sql",
        "postgres",
        "mysql",
        "mongo",
        "redis",
        "orm",
        "migration",
    ],
    "api": ["api", "rest", "graphql", "openapi", "swagger", "endpoint"],
    "security": [
        "security",
        "auth",
        "oauth",
        "jwt",
        "csrf",
        "xss",
        "injection",
        "penetration",
        "audit",
        "vulnerability",
    ],
    "testing": [
        "test",
        "tdd",
        "jest",
        "pytest",
        "vitest",
        "playwright",
        "cypress",
        "e2e",
        "unit test",
        "verification",
        "verify",
    ],
    "ml": [
        "machine learning",
        "ml",
        "ai",
        "model",
        "training",
        "pytorch",
        "tensorflow",
        "llm",
        "rag",
        "fine-tun",
        "langgraph",
        "langchain",
        "agent loop",
    ],
    "data": [
        "data",
        "analytics",
        "pandas",
        "spark",
        "etl",
        "pipeline",
        "warehouse",
        "spreadsheet",
        "excel",
        "sheets",
        "csv",
    ],
    "mobile": [
        "mobile",
        "ios",
        "android",
        "react native",
        "flutter",
        "swift",
        "kotlin",
    ],
    "cli": ["cli", "command-line", "terminal", "shell", "bash"],
    "monitoring": [
        "monitor",
        "observability",
        "logging",
        "metrics",
        "grafana",
        "prometheus",
        "canary",
    ],
    "cicd": ["ci/cd", "github actions", "gitlab", "jenkins", "pipeline", "deploy"],
    "blockchain": ["blockchain", "solidity", "smart contract", "web3", "ethereum"],
    "game": ["game", "unity", "unreal", "godot", "rendering"],
    "productivity": [
        "calendar",
        "meeting",
        "email",
        "drive",
        "docs",
        "slides",
        "task",
        "schedule",
        "agenda",
        "standup",
        "persona",
        "briefing",
        "notes",
        "obsidian",
        "notion",
    ],
    "content": [
        "content",
        "seo",
        "marketing",
        "copywriting",
        "blog",
        "newsletter",
        "social media",
    ],
    "research": [
        "research",
        "search",
        "literature",
        "academic",
        "customer research",
        "account research",
    ],
    "embedded": ["embedded", "firmware", "rtos", "microcontroller", "iot", "hardware"],
    "editor": [
        "editor",
        "refactor",
        "code quality",
        "linting",
        "formatting",
        "simplif",
    ],
    "automation": [
        "automat",
        "workflow",
        "recipe",
        "cron",
        "schedule",
        "recurring",
        "self-improv",
        "continuous learn",
    ],
}

DEP_KEYWORDS = {
    "next": ["nextjs", "next.js", "next "],
    "react": ["react"],
    "vue": ["vue"],
    "angular": ["angular"],
    "svelte": ["svelte"],
    "tailwindcss": ["tailwind"],
    "@prisma/client": ["prisma"],
    "express": ["express"],
    "fastify": ["fastify"],
    "django": ["django"],
    "flask": ["flask"],
    "fastapi": ["fastapi"],
    "pytorch": ["pytorch"],
    "tensorflow": ["tensorflow"],
    "docker": ["docker"],
    "playwright": ["playwright"],
}


def extract_text(frontmatter, body=""):
    """Extract searchable text from frontmatter + first 500 chars of body."""
    parts = [
        frontmatter.get("name", ""),
        frontmatter.get("description", ""),
        frontmatter.get("category", ""),
        body[:500],  # include beginning of body for context
    ]
    meta = frontmatter.get("metadata", {})
    if isinstance(meta, dict):
        parts.append(meta.get("triggers", ""))
        parts.append(meta.get("domain", ""))
        parts.append(str(meta.get("related-skills", "")))
    return " ".join(str(p) for p in parts).lower()


def infer_match(frontmatter, body=""):
    """Infer match rules from frontmatter content + body."""
    text = extract_text(frontmatter, body)

    languages = []
    for lang, keywords in LANG_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            languages.append(lang)

    tags = []
    for tag, keywords in TAG_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            tags.append(tag)

    deps = []
    for dep, keywords in DEP_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            deps.append(dep)

    return {
        "languages": languages,
        "tags": tags,
        "deps": deps,
    }


def process_skill(skill_dir):
    """Process a single skill directory."""
    skill_md = os.path.join(skill_dir, "SKILL.md")
    if not os.path.exists(skill_md):
        return False

    with open(skill_md, "r") as f:
        content = f.read()

    # Skip if already has match:
    if "\nmatch:" in content:
        return False

    # Parse frontmatter
    if not content.startswith("---"):
        return False

    rest = content[3:]
    end_idx = rest.find("---")
    if end_idx == -1:
        return False

    yaml_str = rest[:end_idx].strip()
    body = rest[end_idx + 3 :]

    try:
        frontmatter = yaml.safe_load(yaml_str) or {}
    except yaml.YAMLError:
        return False

    if not isinstance(frontmatter, dict):
        return False

    # Infer match rules
    match_rules = infer_match(frontmatter, body)

    # Skip if nothing inferred
    if (
        not match_rules["languages"]
        and not match_rules["tags"]
        and not match_rules["deps"]
    ):
        return False

    # Build match block
    match_lines = ["match:"]
    if match_rules["languages"]:
        match_lines.append(f"  languages: {match_rules['languages']}")
    if match_rules["tags"]:
        match_lines.append(f"  tags: {match_rules['tags']}")
    if match_rules["deps"]:
        match_lines.append(f"  deps: {match_rules['deps']}")

    match_block = "\n".join(match_lines)

    # Inject before closing ---
    new_content = f"---\n{yaml_str}\n{match_block}\n---{body}"

    with open(skill_md, "w") as f:
        f.write(new_content)

    return True


def main():
    if not os.path.isdir(SKILLS_DIR):
        print(f"Skills directory not found: {SKILLS_DIR}")
        sys.exit(1)

    skills = sorted(os.listdir(SKILLS_DIR))
    enriched = 0
    skipped = 0

    for skill_name in skills:
        skill_dir = os.path.join(SKILLS_DIR, skill_name)
        if not os.path.isdir(skill_dir):
            continue

        if process_skill(skill_dir):
            enriched += 1
        else:
            skipped += 1

    print(f"Enriched {enriched} skills, skipped {skipped}")


if __name__ == "__main__":
    main()
