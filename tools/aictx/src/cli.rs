use clap::{Parser, Subcommand};

use crate::scope::Scope;

#[derive(Parser)]
#[command(
    name = "aictx",
    about = "Smart per-project context manager for AI coding CLIs",
    version,
    after_help = "Alias: cctx"
)]
pub struct Cli {
    #[command(subcommand)]
    pub command: Option<Command>,

    /// Enable AI-powered recommendations (requires Ollama or API key)
    #[arg(long, global = true)]
    pub smart: bool,

    /// Resource scope: global, project, or user-project
    #[arg(long, global = true, value_enum)]
    pub scope: Option<Scope>,

    /// Enable verbose output (show what aictx is doing)
    #[arg(short, long, global = true)]
    pub verbose: bool,

    /// Enable debug output (includes verbose + internal details)
    #[arg(long, global = true)]
    pub debug: bool,
}

#[derive(Subcommand)]
pub enum Command {
    /// Launch interactive TUI with project scan and recommendations
    Tui {
        /// Enable AI-powered recommendations
        #[arg(long)]
        smart: bool,

        /// Skip remote resource refresh (use cached data only)
        #[arg(long)]
        offline: bool,
    },

    /// Show project fingerprint (detected tech stack)
    Scan,

    /// Apply a profile or auto-detected recommendations
    Apply {
        /// Profile name to apply
        profile: Option<String>,

        /// Auto-apply based on scan results
        #[arg(long)]
        auto: bool,

        /// Enable AI-powered recommendations
        #[arg(long)]
        smart: bool,

        /// Skip confirmation prompt
        #[arg(long, short)]
        yes: bool,
    },

    /// Show current project configuration
    Status,

    /// Compare active config vs current recommendations
    Diff,

    /// Estimate token overhead of current config
    Cost,

    /// Save current config as a reusable profile
    Save {
        /// Profile name
        name: String,
    },

    /// List available profiles
    Profiles,

    /// Remove per-project config, revert to global
    Reset {
        /// Skip confirmation prompt
        #[arg(long, short)]
        yes: bool,
    },

    /// Bootstrap a new project with a starter profile
    Init,

    /// Analyze CLAUDE.md for token reduction opportunities
    Trim {
        /// File to analyze (defaults to CLAUDE.md)
        file: Option<String>,

        /// Auto-apply suggestions with backup
        #[arg(long)]
        auto: bool,

        /// Skip confirmation prompt
        #[arg(long, short)]
        yes: bool,
    },

    /// Re-index skills, agents, and commands from source
    Index,

    /// Check integrity (broken symlinks, stale profiles, all scopes)
    Doctor,

    /// Export profile to portable YAML
    Export {
        /// Profile name to export
        profile: String,
    },

    /// Import profile from YAML file
    Import {
        /// Path to .aictx.yaml file
        file: String,
    },

    /// Get or set project-specific config
    Config {
        #[command(subcommand)]
        action: ConfigAction,
    },

    /// Generate shell hook for auto-apply on cd
    Hook {
        /// Shell type: zsh, bash, or fish
        shell: String,
    },

    /// Resource management (discover, search, install/uninstall, enable/disable)
    Plugin {
        #[command(subcommand)]
        action: PluginAction,
    },

    /// Update all installed remote resources to latest version
    Update,

    /// Refresh remote resource cache (skills, agents, commands, plugins)
    Refresh,

    /// Generate shell completions (prints to stdout, or installs with --install)
    Completions {
        /// Shell type: bash, zsh, fish, elvish, powershell
        shell: clap_complete::Shell,

        /// Install completions to the standard location for the shell
        #[arg(long)]
        install: bool,
    },

    /// Generate man page
    Man,

    /// Watch project files and re-apply recommendations on change
    Watch {
        /// Polling interval in seconds
        #[arg(long, default_value = "5")]
        interval: u64,
    },
}

#[derive(Subcommand)]
pub enum ConfigAction {
    /// Get a config value
    Get {
        /// Config key (e.g., ai.enabled, paths.skills_dir)
        key: String,
    },
    /// Set a config value
    Set {
        /// Config key
        key: String,
        /// Value to set
        value: String,
    },
    /// List all config values with scope indicators
    List,
}

#[derive(Subcommand)]
pub enum PluginAction {
    /// List available resources from all sources
    List,
    /// Search resources by name or description
    Search {
        /// Search query
        query: String,
    },
    /// Refresh resource cache from all sources
    Refresh,
    /// Install a remote resource (skill, agent, command) to local dirs
    Install {
        /// Resource name or install_id
        name: String,
    },
    /// Uninstall a previously downloaded resource from local dirs
    Uninstall {
        /// Resource name or install_id
        name: String,
    },
    /// Add a new source URL to sources.yaml
    Add {
        /// Source name (unique identifier)
        name: String,
        /// Source URL or GitHub repo (owner/repo)
        url: String,
        /// Resource types this source provides (comma-separated: skill,agent,command,plugin)
        #[arg(long, default_value = "skill")]
        resources: String,
    },
    /// Disable all plugins globally
    DisableAll,
    /// Enable all plugins globally
    EnableAll,
}
