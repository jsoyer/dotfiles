use anyhow::{Context, Result};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::path::Path;

#[allow(unused_imports)]
use crate::debug_log;

use crate::config::AppConfig;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ResourceEntry {
    pub name: String,
    pub description: String,
    pub match_rules: MatchRules,
    pub path: String,
    pub token_estimate: usize,
}

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct MatchRules {
    #[serde(default)]
    pub files: Vec<String>,
    #[serde(default)]
    pub deps: Vec<String>,
    #[serde(default)]
    pub languages: Vec<String>,
    #[serde(default)]
    pub tags: Vec<String>,
    #[serde(default)]
    pub min_confidence: f32,
}

#[derive(Debug)]
pub struct Index {
    pub skills: Vec<ResourceEntry>,
    pub agents: Vec<ResourceEntry>,
    pub commands: Vec<ResourceEntry>,
    pub hooks: Vec<ResourceEntry>,
}

impl Index {
    pub fn build(config: &AppConfig) -> Result<Self> {
        let skills = Self::index_dir(&config.paths.skills_dir, "skill")?;
        let agents = Self::index_dir(&config.paths.agents_dir, "agent")?;
        let commands = Self::index_dir(&config.paths.commands_dir, "command")?;
        let hooks = Self::index_hooks_dir(&config.paths.hooks_dir)?;

        Ok(Self {
            skills,
            agents,
            commands,
            hooks,
        })
    }

    /// Index a hooks directory: each `.sh` file becomes a ResourceEntry.
    fn index_hooks_dir(dir: &Path) -> Result<Vec<ResourceEntry>> {
        let mut entries = Vec::new();

        if !dir.exists() {
            return Ok(entries);
        }

        for entry in std::fs::read_dir(dir)
            .with_context(|| format!("Failed to read {}", dir.display()))?
        {
            let entry = entry?;
            let path = entry.path();
            if path.is_file() && path.extension().map_or(false, |e| e == "sh") {
                let name = path
                    .file_stem()
                    .map(|n| n.to_string_lossy().to_string())
                    .unwrap_or_default();
                if name.is_empty() {
                    continue;
                }
                entries.push(ResourceEntry {
                    name: name.clone(),
                    description: format!("Hook: {}", name),
                    match_rules: MatchRules::default(),
                    path: path.to_string_lossy().to_string(),
                    token_estimate: 0,
                });
            }
        }

        Ok(entries)
    }

    fn index_dir(dir: &Path, kind: &str) -> Result<Vec<ResourceEntry>> {
        let mut entries = Vec::new();

        if !dir.exists() {
            return Ok(entries);
        }

        if dir.is_dir() {
            for entry in std::fs::read_dir(dir)
                .with_context(|| format!("Failed to read {}", dir.display()))?
            {
                let entry = entry?;
                let path = entry.path();

                // Skills are directories with SKILL.md inside
                if path.is_dir() {
                    // Skip directories named "README" or similar metadata dirs
                    let dir_name = path.file_name().unwrap_or_default().to_string_lossy();
                    if dir_name.eq_ignore_ascii_case("readme") {
                        debug_log!("Skipping README dir: {}", path.display());
                        continue;
                    }
                    let skill_file = path.join("SKILL.md");
                    if skill_file.exists() {
                        if let Ok(resource) = Self::parse_resource(&skill_file, kind) {
                            entries.push(resource);
                        }
                    }
                }

                // Agents and commands are .md files directly (skip README and non-.md)
                if path.is_file() && path.extension().map_or(false, |e| e == "md") {
                    let file_name = path.file_stem().unwrap_or_default().to_string_lossy();
                    if file_name.eq_ignore_ascii_case("readme") {
                        debug_log!("Skipping README file: {}", path.display());
                        continue;
                    }
                    if let Ok(resource) = Self::parse_resource(&path, kind) {
                        entries.push(resource);
                    }
                }
            }
        }

        Ok(entries)
    }

    fn parse_resource(path: &Path, kind: &str) -> Result<ResourceEntry> {
        let content = std::fs::read_to_string(path)?;
        let name = path
            .file_stem()
            .or_else(|| path.parent().and_then(|p| p.file_name()))
            .map(|n| n.to_string_lossy().to_string())
            .unwrap_or_default();

        // Handle SKILL.md inside directories — use parent dir name
        let name = if name == "SKILL" {
            path.parent()
                .and_then(|p| p.file_name())
                .map(|n| n.to_string_lossy().to_string())
                .unwrap_or(name)
        } else {
            name
        };

        let (frontmatter, body) = Self::split_frontmatter(&content);

        let description = Self::extract_description(&body, &frontmatter);
        let match_rules = Self::extract_match_rules(&frontmatter, &name, &description, kind);
        let token_estimate = content.len() / 4; // rough approximation

        Ok(ResourceEntry {
            name,
            description,
            match_rules,
            path: path.to_string_lossy().to_string(),
            token_estimate,
        })
    }

    fn split_frontmatter(content: &str) -> (HashMap<String, serde_yaml::Value>, String) {
        if !content.starts_with("---") {
            return (HashMap::new(), content.to_string());
        }

        let rest = &content[3..];
        if let Some(end) = rest.find("---") {
            let yaml_str = &rest[..end].trim();
            let body = &rest[end + 3..];

            let frontmatter: HashMap<String, serde_yaml::Value> =
                serde_yaml::from_str(yaml_str).unwrap_or_default();

            (frontmatter, body.to_string())
        } else {
            (HashMap::new(), content.to_string())
        }
    }

    fn extract_description(
        body: &str,
        frontmatter: &HashMap<String, serde_yaml::Value>,
    ) -> String {
        // Try frontmatter description first
        if let Some(desc) = frontmatter.get("description") {
            if let Some(s) = desc.as_str() {
                return s.to_string();
            }
        }

        // Fallback: first non-empty line from body
        body.lines()
            .map(|l| l.trim())
            .find(|l| !l.is_empty() && !l.starts_with('#'))
            .unwrap_or("")
            .to_string()
    }

    fn extract_match_rules(
        frontmatter: &HashMap<String, serde_yaml::Value>,
        name: &str,
        description: &str,
        _kind: &str,
    ) -> MatchRules {
        // Try explicit match: block in frontmatter
        if let Some(match_val) = frontmatter.get("match") {
            if let Ok(rules) = serde_yaml::from_value::<MatchRules>(match_val.clone()) {
                return rules;
            }
        }

        // Infer from name and description
        Self::infer_match_rules(name, description)
    }

    fn infer_match_rules(name: &str, description: &str) -> MatchRules {
        let combined = format!("{} {}", name, description).to_lowercase();
        let mut tags = Vec::new();
        let mut languages = Vec::new();
        let mut deps = Vec::new();

        // Language inference
        let lang_keywords: &[(&str, &str)] = &[
            ("typescript", "typescript"),
            ("javascript", "javascript"),
            ("python", "python"),
            ("rust", "rust"),
            ("golang", "go"),
            ("go-", "go"),
            ("react", "typescript"),
            ("vue", "typescript"),
            ("angular", "typescript"),
            ("nextjs", "typescript"),
            ("django", "python"),
            ("flask", "python"),
            ("fastapi", "python"),
            ("rails", "ruby"),
            ("laravel", "php"),
            ("spring", "java"),
            ("kotlin", "kotlin"),
            ("swift", "swift"),
            ("cpp", "cpp"),
            ("csharp", "csharp"),
            ("dotnet", "csharp"),
            ("lua", "lua"),
            ("shell", "shell"),
            ("bash", "shell"),
            ("elixir", "elixir"),
            ("flutter", "dart"),
            ("dart", "dart"),
        ];

        for (keyword, lang) in lang_keywords {
            if combined.contains(keyword) {
                if !languages.contains(&lang.to_string()) {
                    languages.push(lang.to_string());
                }
            }
        }

        // Tag inference
        let tag_keywords: &[(&str, &str)] = &[
            ("frontend", "frontend"),
            ("backend", "backend"),
            ("fullstack", "fullstack"),
            ("devops", "devops"),
            ("docker", "docker"),
            ("kubernetes", "kubernetes"),
            ("k8s", "kubernetes"),
            ("terraform", "terraform"),
            ("aws", "aws"),
            ("azure", "azure"),
            ("gcp", "gcp"),
            ("database", "database"),
            ("postgres", "database"),
            ("sql", "database"),
            ("api", "api"),
            ("graphql", "graphql"),
            ("rest", "api"),
            ("security", "security"),
            ("test", "testing"),
            ("ci/cd", "cicd"),
            ("ci-cd", "cicd"),
            ("deploy", "deployment"),
            ("mobile", "mobile"),
            ("ios", "mobile"),
            ("android", "mobile"),
            ("react-native", "mobile"),
            ("flutter", "mobile"),
            ("ml", "ml"),
            ("machine-learning", "ml"),
            ("data", "data"),
            ("cli", "cli"),
            ("shell", "cli"),
        ];

        for (keyword, tag) in tag_keywords {
            if combined.contains(keyword) {
                if !tags.contains(&tag.to_string()) {
                    tags.push(tag.to_string());
                }
            }
        }

        // Dep inference from common tool names
        let dep_keywords: &[(&str, &str)] = &[
            ("nextjs", "next"),
            ("next-", "next"),
            ("prisma", "@prisma/client"),
            ("tailwind", "tailwindcss"),
            ("playwright", "playwright"),
            ("jest", "jest"),
            ("vitest", "vitest"),
        ];

        for (keyword, dep) in dep_keywords {
            if combined.contains(keyword) {
                deps.push(dep.to_string());
            }
        }

        MatchRules {
            files: Vec::new(),
            deps,
            languages,
            tags,
            min_confidence: 0.5,
        }
    }
}
