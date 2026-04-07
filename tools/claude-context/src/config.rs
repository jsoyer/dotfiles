use anyhow::{Context, Result};
use serde::{Deserialize, Serialize};
use std::path::PathBuf;

#[derive(Debug, Serialize, Deserialize)]
pub struct AppConfig {
    pub base: BaseConfig,
    pub ai: AiConfig,
    pub paths: PathsConfig,
    pub cli_registry: Vec<CliEntry>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct BaseConfig {
    pub skills: Vec<String>,
    pub agents: Vec<String>,
    pub commands: Vec<String>,
    pub mcp: Vec<String>,
    pub rules: Vec<String>,
    pub plugins: Vec<String>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct AiConfig {
    pub enabled: bool,
    pub provider: String,
    pub model: String,
    pub fallback: Option<String>,
    pub max_tokens: u32,
    pub cache_ttl: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct PathsConfig {
    pub skills_dir: PathBuf,
    pub agents_dir: PathBuf,
    pub commands_dir: PathBuf,
    pub rules_dir: PathBuf,
    pub config_dir: PathBuf,
    pub profiles_dir: PathBuf,
}

impl PathsConfig {
    /// Expand ~ to home directory in all paths
    pub fn expand_tildes(&mut self) {
        let home = dirs::home_dir().unwrap_or_else(|| PathBuf::from("/tmp"));
        let expand = |p: &PathBuf| -> PathBuf {
            let s = p.to_string_lossy();
            if s.starts_with("~/") {
                home.join(&s[2..])
            } else if s == "~" {
                home.clone()
            } else {
                p.clone()
            }
        };
        self.skills_dir = expand(&self.skills_dir);
        self.agents_dir = expand(&self.agents_dir);
        self.commands_dir = expand(&self.commands_dir);
        self.rules_dir = expand(&self.rules_dir);
        self.config_dir = expand(&self.config_dir);
        self.profiles_dir = expand(&self.profiles_dir);
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CliEntry {
    pub name: String,
    pub config_dir: PathBuf,
    pub project_dir: String,
    pub supports: Vec<String>,
    pub detect: Option<String>,
}

impl AppConfig {
    pub fn load() -> Result<Self> {
        let config_dir = Self::config_dir();
        let defaults_path = config_dir.join("defaults.yaml");

        if defaults_path.exists() {
            let content = std::fs::read_to_string(&defaults_path)
                .with_context(|| format!("Failed to read {}", defaults_path.display()))?;
            let mut config: AppConfig = serde_yaml::from_str(&content)
                .with_context(|| "Failed to parse defaults.yaml")?;
            config.paths.expand_tildes();
            Ok(config)
        } else {
            Ok(Self::default())
        }
    }

    pub fn config_dir() -> PathBuf {
        dirs::config_dir()
            .unwrap_or_else(|| PathBuf::from("~/.config"))
            .join("claude-context")
    }

    fn default() -> Self {
        let home = dirs::home_dir().unwrap_or_else(|| PathBuf::from("~"));

        Self {
            base: BaseConfig {
                skills: vec![
                    "git-commit", "git-workflow", "code-review", "code-refactoring",
                    "tdd-workflow", "plan", "verify", "debugger", "debugging-wizard",
                    "security-review", "documentation", "testing-strategy", "refactor",
                    "search", "deep-research", "self-improvement", "continuous-learning",
                    "prompt-engineer", "health", "context-budget", "aside", "build-fix",
                    "learn", "checkpoint", "save-session", "resume-session",
                ]
                .into_iter()
                .map(String::from)
                .collect(),
                agents: vec![
                    "code-reviewer", "planner", "debugger", "security-reviewer",
                    "build-error-resolver", "refactoring-specialist", "tdd-guide",
                    "documentation-engineer", "shell-script-engineer",
                    "performance-engineer", "search-specialist", "error-detective",
                ]
                .into_iter()
                .map(String::from)
                .collect(),
                commands: vec![
                    "plan", "verify", "code-review", "tdd", "build-fix", "refactor-clean",
                    "checkpoint", "save-session", "resume-session", "context-budget",
                    "learn", "aside", "quality-gate", "update-docs", "update-codemaps",
                ]
                .into_iter()
                .map(String::from)
                .collect(),
                mcp: vec![
                    "context7", "fetch", "github", "1password", "obsidian",
                ]
                .into_iter()
                .map(String::from)
                .collect(),
                rules: vec!["common".to_string()],
                plugins: vec![],
            },
            ai: AiConfig {
                enabled: false,
                provider: "ollama".to_string(),
                model: "qwen3:8b".to_string(),
                fallback: Some("claude".to_string()),
                max_tokens: 500,
                cache_ttl: "7d".to_string(),
            },
            paths: PathsConfig {
                // Use ~/.skills/ if it exists (post-migration), fallback to ~/.agents/skills/ (current)
                skills_dir: if home.join(".skills").exists() {
                    home.join(".skills")
                } else {
                    home.join(".agents").join("skills")
                },
                // Use ~/.agents/ if it contains .md files (post-migration), fallback to ~/.claude/agents/ (current)
                agents_dir: if home.join(".agents").join("code-reviewer.md").exists() {
                    home.join(".agents")
                } else {
                    home.join(".claude").join("agents")
                },
                commands_dir: home.join(".claude").join("commands"),
                rules_dir: home.join(".claude").join("rules"),
                config_dir: Self::config_dir(),
                profiles_dir: Self::config_dir().join("profiles"),
            },
            cli_registry: vec![
                CliEntry {
                    name: "claude".to_string(),
                    config_dir: home.join(".claude"),
                    project_dir: ".claude".to_string(),
                    supports: vec![
                        "skills", "agents", "commands", "rules", "mcp", "plugins",
                    ]
                    .into_iter()
                    .map(String::from)
                    .collect(),
                    detect: None,
                },
                CliEntry {
                    name: "qwen".to_string(),
                    config_dir: home.join(".qwen"),
                    project_dir: ".qwen".to_string(),
                    supports: vec!["skills".to_string()],
                    detect: Some("which qwen".to_string()),
                },
                CliEntry {
                    name: "vibe".to_string(),
                    config_dir: home.join(".vibe"),
                    project_dir: ".vibe".to_string(),
                    supports: vec!["skills".to_string()],
                    detect: Some("which vibe".to_string()),
                },
                CliEntry {
                    name: "codex".to_string(),
                    config_dir: home.join(".codex"),
                    project_dir: ".codex".to_string(),
                    supports: vec!["skills".to_string()],
                    detect: Some("which codex".to_string()),
                },
                CliEntry {
                    name: "kimi".to_string(),
                    config_dir: home.join(".kimi"),
                    project_dir: ".kimi".to_string(),
                    supports: vec!["skills".to_string()],
                    detect: Some("which kimi".to_string()),
                },
                CliEntry {
                    name: "opencode".to_string(),
                    config_dir: home.join(".config").join("opencode"),
                    project_dir: ".opencode".to_string(),
                    supports: vec!["skills".to_string()],
                    detect: Some("which opencode".to_string()),
                },
            ],
        }
    }

    pub fn detected_clis(&self) -> Vec<&CliEntry> {
        self.cli_registry
            .iter()
            .filter(|cli| {
                match &cli.detect {
                    None => true, // always present (e.g., claude)
                    Some(cmd) => {
                        std::process::Command::new("sh")
                            .args(["-c", cmd])
                            .output()
                            .map(|o| o.status.success())
                            .unwrap_or(false)
                    }
                }
            })
            .collect()
    }
}
