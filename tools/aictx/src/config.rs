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

fn default_theme() -> String {
    "catppuccin-mocha".to_string()
}

#[derive(Debug, Serialize, Deserialize)]
pub struct BaseConfig {
    pub skills: Vec<String>,
    pub agents: Vec<String>,
    pub commands: Vec<String>,
    pub mcp: Vec<String>,
    pub rules: Vec<String>,
    pub plugins: Vec<String>,
    #[serde(default = "default_theme")]
    pub theme: String,
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

fn default_hooks_dir() -> PathBuf {
    dirs::home_dir()
        .unwrap_or_else(|| PathBuf::from("~"))
        .join(".claude")
        .join("hooks")
}

#[derive(Debug, Serialize, Deserialize)]
pub struct PathsConfig {
    pub skills_dir: PathBuf,
    pub agents_dir: PathBuf,
    pub commands_dir: PathBuf,
    #[serde(default = "default_hooks_dir")]
    pub hooks_dir: PathBuf,
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
        self.hooks_dir = expand(&self.hooks_dir);
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
    #[serde(default = "default_scopes")]
    pub scopes: Vec<String>,
    pub detect: Option<String>,
}

fn default_scopes() -> Vec<String> {
    vec![
        "global".to_string(),
        "project".to_string(),
        "user-project".to_string(),
    ]
}

impl AppConfig {
    pub fn load() -> Result<Self> {
        let config_dir = Self::config_dir();
        let defaults_path = config_dir.join("defaults.yaml");

        if defaults_path.exists() {
            let content = std::fs::read_to_string(&defaults_path)
                .with_context(|| format!("Failed to read {}", defaults_path.display()))?;
            let mut config: AppConfig =
                serde_yaml::from_str(&content).with_context(|| "Failed to parse defaults.yaml")?;
            config.paths.expand_tildes();
            config.expand_cli_tildes();
            Ok(config)
        } else {
            Ok(Self::default())
        }
    }

    pub fn config_dir() -> PathBuf {
        let base = dirs::config_dir().unwrap_or_else(|| PathBuf::from("~/.config"));
        // Primary: ~/.config/aictx/
        let new_dir = base.join("aictx");
        if new_dir.exists() {
            return new_dir;
        }
        // Legacy fallback 1: ~/.config/ai-context/ (deprecated)
        let legacy_ai_context = base.join("ai-context");
        if legacy_ai_context.exists() {
            eprintln!("aictx: using legacy config dir ~/.config/ai-context/ — rename to ~/.config/aictx/ to silence this");
            return legacy_ai_context;
        }
        // Legacy fallback 2: ~/.config/claude-context/ (older, deprecated)
        let legacy_claude_context = base.join("claude-context");
        if legacy_claude_context.exists() {
            eprintln!("aictx: using legacy config dir ~/.config/claude-context/ — rename to ~/.config/aictx/ to silence this");
            return legacy_claude_context;
        }
        new_dir
    }

    fn default() -> Self {
        let home = dirs::home_dir().unwrap_or_else(|| PathBuf::from("~"));

        Self {
            base: BaseConfig {
                skills: vec![
                    "git-commit",
                    "git-workflow",
                    "code-review",
                    "code-refactoring",
                    "tdd-workflow",
                    "plan",
                    "verify",
                    "debugger",
                    "debugging-wizard",
                    "security-review",
                    "documentation",
                    "testing-strategy",
                    "refactor",
                    "search",
                    "deep-research",
                    "self-improvement",
                    "continuous-learning",
                    "prompt-engineer",
                    "health",
                    "context-budget",
                    "aside",
                    "build-fix",
                    "learn",
                    "checkpoint",
                    "save-session",
                    "resume-session",
                ]
                .into_iter()
                .map(String::from)
                .collect(),
                agents: vec![
                    "code-reviewer",
                    "planner",
                    "debugger",
                    "security-reviewer",
                    "build-error-resolver",
                    "refactoring-specialist",
                    "tdd-guide",
                    "documentation-engineer",
                    "shell-script-engineer",
                    "performance-engineer",
                    "search-specialist",
                    "error-detective",
                ]
                .into_iter()
                .map(String::from)
                .collect(),
                commands: vec![
                    "plan",
                    "verify",
                    "code-review",
                    "tdd",
                    "build-fix",
                    "refactor-clean",
                    "checkpoint",
                    "save-session",
                    "resume-session",
                    "context-budget",
                    "learn",
                    "aside",
                    "quality-gate",
                    "update-docs",
                    "update-codemaps",
                ]
                .into_iter()
                .map(String::from)
                .collect(),
                mcp: vec!["context7", "fetch", "github", "1password", "obsidian"]
                    .into_iter()
                    .map(String::from)
                    .collect(),
                rules: vec!["common".to_string()],
                plugins: vec![],
                theme: default_theme(),
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
                skills_dir: home.join(".aictx").join("skills"),
                agents_dir: if home.join(".aictx").join("agents").exists() {
                    home.join(".aictx").join("agents")
                } else {
                    home.join(".claude").join("agents")
                },
                commands_dir: if home.join(".aictx").join("commands").exists() {
                    home.join(".aictx").join("commands")
                } else {
                    home.join(".claude").join("commands")
                },
                hooks_dir: if home.join(".aictx").join("hooks").exists() {
                    home.join(".aictx").join("hooks")
                } else {
                    home.join(".claude").join("hooks")
                },
                rules_dir: if home.join(".aictx").join("rules").exists() {
                    home.join(".aictx").join("rules")
                } else {
                    home.join(".claude").join("rules")
                },
                config_dir: Self::config_dir(),
                profiles_dir: Self::config_dir().join("profiles"),
            },
            cli_registry: vec![
                CliEntry {
                    name: "claude".to_string(),
                    config_dir: home.join(".claude"),
                    project_dir: ".claude".to_string(),
                    supports: vec!["skills", "agents", "commands", "rules", "mcp", "plugins"]
                        .into_iter()
                        .map(String::from)
                        .collect(),
                    scopes: vec!["global", "project", "user-project"]
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
                    scopes: vec!["global".to_string()],
                    detect: Some("which qwen".to_string()),
                },
                CliEntry {
                    name: "vibe".to_string(),
                    config_dir: home.join(".vibe"),
                    project_dir: ".vibe".to_string(),
                    supports: vec!["skills".to_string()],
                    scopes: vec!["global".to_string()],
                    detect: Some("which vibe".to_string()),
                },
                CliEntry {
                    name: "codex".to_string(),
                    config_dir: home.join(".codex"),
                    project_dir: ".codex".to_string(),
                    supports: vec!["skills".to_string()],
                    scopes: vec!["global".to_string()],
                    detect: Some("which codex".to_string()),
                },
                CliEntry {
                    name: "kimi".to_string(),
                    config_dir: home.join(".kimi"),
                    project_dir: ".kimi".to_string(),
                    supports: vec!["skills".to_string()],
                    scopes: vec!["global".to_string()],
                    detect: Some("which kimi".to_string()),
                },
                CliEntry {
                    name: "opencode".to_string(),
                    config_dir: home.join(".config").join("opencode"),
                    project_dir: ".opencode".to_string(),
                    supports: vec!["skills".to_string()],
                    scopes: vec!["global".to_string()],
                    detect: Some("which opencode".to_string()),
                },
                CliEntry {
                    name: "gemini-cli".to_string(),
                    config_dir: home.join(".gemini"),
                    project_dir: ".gemini".to_string(),
                    supports: vec!["skills".to_string()],
                    scopes: vec!["global".to_string()],
                    detect: Some("which gemini".to_string()),
                },
                CliEntry {
                    name: "copilot-cli".to_string(),
                    config_dir: home.join(".copilot"),
                    project_dir: ".copilot".to_string(),
                    supports: vec!["skills".to_string()],
                    scopes: vec!["global".to_string()],
                    detect: Some("which copilot".to_string()),
                },
            ],
        }
    }

    /// Expand ~ in cli_registry config_dir paths
    pub fn expand_cli_tildes(&mut self) {
        let home = dirs::home_dir().unwrap_or_else(|| PathBuf::from("/tmp"));
        for cli in &mut self.cli_registry {
            let s = cli.config_dir.to_string_lossy();
            if s.starts_with("~/") {
                cli.config_dir = home.join(&s[2..]);
            } else if s == "~" {
                cli.config_dir = home.clone();
            }
        }
    }

    pub fn detected_clis(&self) -> Vec<&CliEntry> {
        self.cli_registry
            .iter()
            .filter(|cli| {
                match &cli.detect {
                    None => true, // always present (e.g., claude)
                    Some(_) => {
                        // Fast check: if the CLI's config_dir exists, it's installed
                        cli.config_dir.exists()
                    }
                }
            })
            .collect()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn default_skills_dir_is_aictx() {
        let home = dirs::home_dir().unwrap_or_else(|| PathBuf::from("/tmp"));
        let config = AppConfig::default();
        let expected = home.join(".aictx").join("skills");
        assert_eq!(
            config.paths.skills_dir, expected,
            "skills_dir must be ~/.aictx/skills (no legacy fallback)"
        );
    }

    #[test]
    fn default_agents_dir_is_not_bare_dot_agents() {
        let home = dirs::home_dir().unwrap_or_else(|| PathBuf::from("/tmp"));
        let config = AppConfig::default();
        let legacy = home.join(".agents");
        assert_ne!(
            config.paths.agents_dir, legacy,
            "agents_dir must not be bare ~/.agents"
        );
    }
}
