use clap::{Parser, Subcommand};

#[derive(Parser)]
#[command(
    name = "claude-context",
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
}

#[derive(Subcommand)]
pub enum Command {
    /// Launch interactive TUI with project scan and recommendations
    Tui {
        /// Enable AI-powered recommendations
        #[arg(long)]
        smart: bool,
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

    /// Check integrity (broken symlinks, stale profiles)
    Doctor,

    /// Export profile to portable YAML
    Export {
        /// Profile name to export
        profile: String,
    },

    /// Import profile from YAML file
    Import {
        /// Path to .cctx.yaml file
        file: String,
    },

    /// Get or set project-specific config
    Config {
        /// Config key (e.g., ai.enabled)
        key: String,

        /// Value to set (omit to get current value)
        value: Option<String>,
    },
}
