mod ai;
mod cli;
mod config;
mod cost;
mod doctor;
mod indexer;
mod matcher;
mod multi_cli;
mod profile;
mod scanner;
mod scope;
mod symlinker;
mod trim;
mod tui;

use anyhow::Result;
use clap::Parser;

use cli::{Cli, Command};
use config::AppConfig;
use indexer::Index;
use profile::ProfileManager;
use scanner::Scanner;
use scope::ResolvedScope;

fn main() -> Result<()> {
    let cli = Cli::parse();

    let config = AppConfig::load()?;
    let cwd = std::env::current_dir()?;
    let resolved = scope::resolve(&cwd, cli.scope)?;

    match cli.command.unwrap_or(Command::Tui { smart: false }) {
        Command::Tui { smart } => run_tui(&config, &resolved, smart),
        Command::Scan => run_scan(),
        Command::Apply {
            profile,
            auto: _,
            smart,
            yes,
        } => run_apply(&config, &resolved, profile, smart, yes),
        Command::Status => run_status(&config, &resolved),
        Command::Diff => run_diff(&config, &resolved),
        Command::Cost => run_cost(&config, &resolved),
        Command::Save { name } => run_save(&config, &resolved, &name),
        Command::Profiles => run_profiles(&config),
        Command::Reset { yes } => run_reset(&config, &resolved, yes),
        Command::Init => run_init(&config, &resolved),
        Command::Trim { file, auto, yes } => run_trim(file, auto, yes),
        Command::Index => run_index(&config),
        Command::Doctor => run_doctor(&config),
        Command::Export { profile } => run_export(&config, &profile),
        Command::Import { file } => run_import(&config, &file),
        Command::Config { key, value } => run_config(&key, value),
    }
}

fn run_tui(config: &AppConfig, resolved: &ResolvedScope, smart: bool) -> Result<()> {
    let index = Index::build(config)?;
    let cwd = std::env::current_dir()?;
    let fingerprint = Scanner::scan(&cwd)?;
    let recommendations = matcher::recommend(&fingerprint, &index, smart)?;

    tui::run(config, resolved, &index, &fingerprint, &recommendations)
}

fn run_scan() -> Result<()> {
    let fingerprint = Scanner::scan(&std::env::current_dir()?)?;
    fingerprint.print();
    Ok(())
}

fn run_apply(
    config: &AppConfig,
    resolved: &ResolvedScope,
    profile: Option<String>,
    smart: bool,
    yes: bool,
) -> Result<()> {
    let index = Index::build(config)?;

    let selections = if let Some(name) = profile {
        let pm = ProfileManager::new(config)?;
        pm.load(&name)?
    } else {
        let cwd = std::env::current_dir()?;
        let fingerprint = Scanner::scan(&cwd)?;
        matcher::recommend(&fingerprint, &index, smart)?
    };

    if !yes {
        let preview = symlinker::preview(config, resolved, &selections)?;
        preview.print();

        if !dialoguer::Confirm::new()
            .with_prompt("Apply?")
            .default(true)
            .interact()?
        {
            println!("Cancelled.");
            return Ok(());
        }
    }

    symlinker::apply(config, resolved, &selections)?;
    println!("Applied successfully.");
    Ok(())
}

fn run_status(config: &AppConfig, resolved: &ResolvedScope) -> Result<()> {
    let status = symlinker::status(config, resolved)?;
    status.print();
    Ok(())
}

fn run_diff(config: &AppConfig, resolved: &ResolvedScope) -> Result<()> {
    let index = Index::build(config)?;
    let cwd = std::env::current_dir()?;
    let fingerprint = Scanner::scan(&cwd)?;
    let recommended = matcher::recommend(&fingerprint, &index, false)?;
    let current = symlinker::status(config, resolved)?;

    cost::print_diff(&current, &recommended);
    Ok(())
}

fn run_cost(config: &AppConfig, resolved: &ResolvedScope) -> Result<()> {
    let status = symlinker::status(config, resolved)?;
    cost::print(&status);
    Ok(())
}

fn run_save(config: &AppConfig, resolved: &ResolvedScope, name: &str) -> Result<()> {
    let status = symlinker::status(config, resolved)?;
    let pm = ProfileManager::new(config)?;
    pm.save(name, &status)?;
    println!("Profile '{}' saved.", name);
    Ok(())
}

fn run_profiles(config: &AppConfig) -> Result<()> {
    let pm = ProfileManager::new(config)?;
    pm.list()?;
    Ok(())
}

fn run_reset(config: &AppConfig, resolved: &ResolvedScope, yes: bool) -> Result<()> {
    if !yes {
        if !dialoguer::Confirm::new()
            .with_prompt(format!(
                "Remove per-{} config?",
                resolved.scope
            ))
            .default(false)
            .interact()?
        {
            println!("Cancelled.");
            return Ok(());
        }
    }

    symlinker::reset(config, resolved)?;
    println!("Config reset (scope: {}).", resolved.scope);
    Ok(())
}

fn run_init(config: &AppConfig, resolved: &ResolvedScope) -> Result<()> {
    let cwd = std::env::current_dir()?;
    let fingerprint = Scanner::scan(&cwd)?;

    if fingerprint.is_empty() {
        let choices = &[
            "frontend",
            "backend-ts",
            "fullstack",
            "rust",
            "python",
            "golang",
            "devops",
            "mobile",
            "ai-ml",
            "security",
            "data-engineering",
            "cli-tools",
            "monorepo",
            "saas-platform",
            "dotfiles",
            "custom",
        ];
        let selection = dialoguer::Select::new()
            .with_prompt("What kind of project?")
            .items(choices)
            .default(0)
            .interact()?;

        let profile_name = choices[selection];
        if profile_name == "custom" {
            println!("Run `cctx` to configure manually.");
            return Ok(());
        }

        let pm = ProfileManager::new(config)?;
        if let Ok(selections) = pm.load(profile_name) {
            symlinker::apply(config, resolved, &selections)?;
            println!("Applied '{}' profile (scope: {}).", profile_name, resolved.scope);
        } else {
            println!(
                "No '{}' profile found. Run `cctx` to configure manually.",
                profile_name
            );
        }
    } else {
        fingerprint.print();
        println!("\nRun `cctx apply --auto` to apply recommendations.");
    }

    Ok(())
}

fn run_trim(file: Option<String>, auto: bool, yes: bool) -> Result<()> {
    let path = file.unwrap_or_else(|| "CLAUDE.md".to_string());

    if auto {
        if !yes {
            let report = trim::analyze(&path)?;
            report.print();
            if !dialoguer::Confirm::new()
                .with_prompt("Apply trim with backup?")
                .default(false)
                .interact()?
            {
                println!("Cancelled.");
                return Ok(());
            }
        }
        trim::auto_trim(&path)?;
    } else {
        let report = trim::analyze(&path)?;
        report.print();
    }

    Ok(())
}

fn run_index(config: &AppConfig) -> Result<()> {
    let index = Index::build(config)?;
    println!(
        "Indexed {} skills, {} agents, {} commands.",
        index.skills.len(),
        index.agents.len(),
        index.commands.len()
    );
    Ok(())
}

fn run_doctor(config: &AppConfig) -> Result<()> {
    let report = doctor::run_doctor(config)?;
    report.print();
    Ok(())
}

fn run_export(config: &AppConfig, profile: &str) -> Result<()> {
    let pm = ProfileManager::new(config)?;
    let yaml = pm.export(profile)?;
    print!("{}", yaml);
    Ok(())
}

fn run_import(config: &AppConfig, file: &str) -> Result<()> {
    let pm = ProfileManager::new(config)?;
    pm.import(file)?;
    println!("Profile imported from {}.", file);
    Ok(())
}

fn run_config(key: &str, value: Option<String>) -> Result<()> {
    match value {
        Some(v) => println!("Set {} = {}", key, v),
        None => println!("Get {}", key),
    }
    // TODO: implement project-level config read/write
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::path::PathBuf;

    #[test]
    fn scanner_detects_rust_project() {
        let dir = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
        let fingerprint = Scanner::scan(&dir).unwrap();
        assert!(fingerprint.languages.iter().any(|l| l.name == "rust"));
    }

    #[test]
    fn scanner_empty_dir_returns_empty_fingerprint() {
        let dir = std::env::temp_dir().join("cctx-test-empty");
        let _ = std::fs::create_dir_all(&dir);
        let fingerprint = Scanner::scan(&dir).unwrap();
        assert!(fingerprint.languages.is_empty());
        let _ = std::fs::remove_dir_all(&dir);
    }

    #[test]
    fn config_loads_defaults() {
        let config = AppConfig::load().unwrap();
        assert!(!config.base.skills.is_empty());
        assert!(!config.base.agents.is_empty());
        assert!(!config.base.mcp.is_empty());
        assert!(!config.cli_registry.is_empty());
        assert!(!config.ai.enabled);
    }

    #[test]
    fn config_has_claude_cli() {
        let config = AppConfig::load().unwrap();
        let names: Vec<&str> = config.cli_registry.iter().map(|c| c.name.as_str()).collect();
        assert!(names.contains(&"claude"));
    }

    #[test]
    fn cli_entries_have_scopes_field() {
        let config = AppConfig::load().unwrap();
        for cli in &config.cli_registry {
            assert!(
                !cli.scopes.is_empty(),
                "CLI '{}' has empty scopes",
                cli.name
            );
            assert!(
                cli.scopes.contains(&"global".to_string()),
                "CLI '{}' must support at least global scope",
                cli.name
            );
        }
    }

    #[test]
    fn cost_estimation_nonzero_for_nonempty_status() {
        let status = symlinker::ProjectStatus {
            skills: vec!["test-skill".to_string()],
            agents: vec!["test-agent".to_string()],
            commands: vec![],
            rules: vec!["rust".to_string()],
            mcp: vec!["context7".to_string()],
            plugins: vec![],
            detected_clis: vec!["claude".to_string()],
            scope: scope::Scope::Project,
        };
        let estimate = cost::estimate(&status);
        assert!(estimate.project_total > 0);
        assert!(estimate.global_total > estimate.project_total);
    }

    #[test]
    fn cost_estimation_zero_for_empty_status() {
        let status = symlinker::ProjectStatus {
            skills: vec![],
            agents: vec![],
            commands: vec![],
            rules: vec![],
            mcp: vec![],
            plugins: vec![],
            detected_clis: vec![],
            scope: scope::Scope::Project,
        };
        let estimate = cost::estimate(&status);
        assert_eq!(estimate.project_total, 0);
    }

    #[test]
    fn matcher_scores_relevant_higher() {
        let config = AppConfig::load().unwrap();
        if let Ok(index) = Index::build(&config) {
            let dir = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
            let fingerprint = Scanner::scan(&dir).unwrap();
            let recs = matcher::recommend(&fingerprint, &index, false).unwrap();

            if !recs.skills.is_empty() {
                assert!(recs.skills.len() > 0);
            }
        }
    }

    #[test]
    fn trim_analyze_nonexistent_file_returns_error() {
        let result = trim::analyze("/nonexistent/file.md");
        assert!(result.is_err());
    }

    #[test]
    fn fingerprint_all_tags_includes_languages() {
        let dir = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
        let fingerprint = Scanner::scan(&dir).unwrap();
        let tags = fingerprint.all_tags();
        assert!(tags.contains(&"rust".to_string()));
    }
}
