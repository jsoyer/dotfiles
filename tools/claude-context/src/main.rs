mod cli;
mod config;
mod cost;
mod indexer;
mod matcher;
mod multi_cli;
mod profile;
mod scanner;
mod symlinker;
mod tui;

use anyhow::Result;
use clap::Parser;

use cli::{Cli, Command};
use config::AppConfig;
use indexer::Index;
use profile::ProfileManager;
use scanner::Scanner;

fn main() -> Result<()> {
    let cli = Cli::parse();

    let config = AppConfig::load()?;

    match cli.command.unwrap_or(Command::Tui { smart: false }) {
        Command::Tui { smart } => run_tui(&config, smart),
        Command::Scan => run_scan(&config),
        Command::Apply { profile, auto, smart, yes } => {
            run_apply(&config, profile, auto, smart, yes)
        }
        Command::Status => run_status(&config),
        Command::Diff => run_diff(&config),
        Command::Cost => run_cost(&config),
        Command::Save { name } => run_save(&config, &name),
        Command::Profiles => run_profiles(&config),
        Command::Reset { yes } => run_reset(&config, yes),
        Command::Init => run_init(&config),
        Command::Trim { file, auto, yes } => run_trim(&config, file, auto, yes),
        Command::Index => run_index(&config),
        Command::Doctor => run_doctor(&config),
        Command::Export { profile } => run_export(&config, &profile),
        Command::Import { file } => run_import(&config, &file),
        Command::Config { key, value } => run_config(&config, &key, value),
    }
}

fn run_tui(config: &AppConfig, smart: bool) -> Result<()> {
    let index = Index::build(config)?;
    let fingerprint = Scanner::scan(&std::env::current_dir()?)?;
    let recommendations = matcher::recommend(&fingerprint, &index, smart)?;

    tui::run(config, &index, &fingerprint, &recommendations)
}

fn run_scan(_config: &AppConfig) -> Result<()> {
    let fingerprint = Scanner::scan(&std::env::current_dir()?)?;
    fingerprint.print();
    Ok(())
}

fn run_apply(
    config: &AppConfig,
    profile: Option<String>,
    _auto: bool,
    smart: bool,
    yes: bool,
) -> Result<()> {
    let project_dir = std::env::current_dir()?;
    let index = Index::build(config)?;

    let selections = if let Some(name) = profile {
        let pm = ProfileManager::new(config)?;
        pm.load(&name)?
    } else {
        let fingerprint = Scanner::scan(&project_dir)?;
        matcher::recommend(&fingerprint, &index, smart)?
    };

    if !yes {
        let preview = symlinker::preview(config, &project_dir, &selections)?;
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

    symlinker::apply(config, &project_dir, &selections)?;
    println!("Applied successfully.");
    Ok(())
}

fn run_status(config: &AppConfig) -> Result<()> {
    let project_dir = std::env::current_dir()?;
    let status = symlinker::status(config, &project_dir)?;
    status.print();
    Ok(())
}

fn run_diff(config: &AppConfig) -> Result<()> {
    let project_dir = std::env::current_dir()?;
    let index = Index::build(config)?;
    let fingerprint = Scanner::scan(&project_dir)?;
    let recommended = matcher::recommend(&fingerprint, &index, false)?;
    let current = symlinker::status(config, &project_dir)?;

    cost::print_diff(&current, &recommended);
    Ok(())
}

fn run_cost(config: &AppConfig) -> Result<()> {
    let project_dir = std::env::current_dir()?;
    let status = symlinker::status(config, &project_dir)?;
    cost::print(&status);
    Ok(())
}

fn run_save(config: &AppConfig, name: &str) -> Result<()> {
    let project_dir = std::env::current_dir()?;
    let status = symlinker::status(config, &project_dir)?;
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

fn run_reset(config: &AppConfig, yes: bool) -> Result<()> {
    let project_dir = std::env::current_dir()?;

    if !yes {
        if !dialoguer::Confirm::new()
            .with_prompt("Remove all per-project config?")
            .default(false)
            .interact()?
        {
            println!("Cancelled.");
            return Ok(());
        }
    }

    symlinker::reset(config, &project_dir)?;
    println!("Project config reset.");
    Ok(())
}

fn run_init(config: &AppConfig) -> Result<()> {
    let project_dir = std::env::current_dir()?;
    let fingerprint = Scanner::scan(&project_dir)?;

    if fingerprint.is_empty() {
        let choices = &[
            "frontend", "backend", "fullstack", "devops", "cli", "dotfiles", "rust", "custom",
        ];
        let selection = dialoguer::Select::new()
            .with_prompt("What kind of project?")
            .items(choices)
            .default(0)
            .interact()?;

        let pm = ProfileManager::new(config)?;
        let profile_name = choices[selection];
        if let Ok(selections) = pm.load(profile_name) {
            symlinker::apply(config, &project_dir, &selections)?;
            println!("Applied '{}' profile.", profile_name);
        } else {
            println!("No '{}' profile found. Run `cctx` to configure manually.", profile_name);
        }
    } else {
        fingerprint.print();
        println!("\nRun `cctx apply --auto` to apply recommendations.");
    }

    Ok(())
}

fn run_trim(_config: &AppConfig, file: Option<String>, _auto: bool, _yes: bool) -> Result<()> {
    let path = file.unwrap_or_else(|| "CLAUDE.md".to_string());
    println!("Analyzing {} for token reduction...", path);
    // TODO: implement CLAUDE.md analysis
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

fn run_doctor(_config: &AppConfig) -> Result<()> {
    println!("Running health checks...");
    // TODO: check broken symlinks, stale profiles, missing sources
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

fn run_config(_config: &AppConfig, key: &str, value: Option<String>) -> Result<()> {
    match value {
        Some(v) => println!("Set {} = {}", key, v),
        None => println!("Get {}", key),
    }
    // TODO: implement project-level config
    Ok(())
}
