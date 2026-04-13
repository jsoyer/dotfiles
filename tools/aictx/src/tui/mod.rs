mod app;
mod ui;

use anyhow::Result;
use std::collections::HashSet;

use crate::config::AppConfig;
use crate::indexer::Index;
use crate::matcher::Recommendations;
use crate::plugins::{PluginManager, RemoteResource};
use crate::profile::ProfileManager;
use crate::scanner::ProjectFingerprint;
use crate::scope::ResolvedScope;
use crate::symlinker::ProjectStatus;
use crate::theme::Theme;

pub fn run(
    config: &AppConfig,
    resolved: &ResolvedScope,
    index: &Index,
    fingerprint: &ProjectFingerprint,
    recommendations: &Recommendations,
    remote_resources: &[RemoteResource],
    cli_statuses: &[(String, ProjectStatus)],
    theme: Theme,
) -> Result<()> {
    // Build profile list before TUI starts
    let profile_list: Vec<(String, usize, usize)> = ProfileManager::new(config)
        .ok()
        .map(|pm| {
            pm.list_names()
                .unwrap_or_default()
                .into_iter()
                .map(|name| {
                    let (skills, agents) = pm
                        .load(&name)
                        .map(|r| (r.skills.len(), r.agents.len()))
                        .unwrap_or((0, 0));
                    (name, skills, agents)
                })
                .collect()
        })
        .unwrap_or_default();

    let mut app = app::App::new(
        config,
        index,
        fingerprint,
        recommendations,
        remote_resources,
        cli_statuses,
        theme,
    );
    app.profile_list = profile_list;

    let mut terminal = ratatui::init();
    let result = app.run(&mut terminal);
    let pending_installs = app.pending_installs.clone();
    let pending_uninstalls = app.pending_uninstalls.clone();
    let pending_profile_save = app.pending_profile_save.clone();
    let pending_profile_load = app.pending_profile_load.clone();
    ratatui::restore();

    if let Some(all_selections) = result? {
        let before_status = crate::symlinker::status(config, resolved)
            .unwrap_or_else(|_| ProjectStatus::empty(resolved.scope));

        let mut merged = crate::matcher::Recommendations::default();
        for (_cli, recs) in &all_selections {
            for s in &recs.skills {
                if !merged.skills.iter().any(|m| m.name == s.name) {
                    merged.skills.push(s.clone());
                }
            }
            for a in &recs.agents {
                if !merged.agents.iter().any(|m| m.name == a.name) {
                    merged.agents.push(a.clone());
                }
            }
            for c in &recs.commands {
                if !merged.commands.iter().any(|m| m.name == c.name) {
                    merged.commands.push(c.clone());
                }
            }
            for h in &recs.hooks {
                if !merged.hooks.iter().any(|m| m.name == h.name) {
                    merged.hooks.push(h.clone());
                }
            }
            for m in &recs.mcp {
                if !merged.mcp.contains(m) {
                    merged.mcp.push(m.clone());
                }
            }
            for r in &recs.rules {
                if !merged.rules.contains(r) {
                    merged.rules.push(r.clone());
                }
            }
            for p in &recs.plugins {
                if !merged.plugins.contains(p) {
                    merged.plugins.push(p.clone());
                }
            }
        }

        println!(
            "\nApplying {} skills, {} agents, {} commands, {} hooks, {} rules, {} MCP, {} plugins (scope: {})...",
            merged.skills.len(),
            merged.agents.len(),
            merged.commands.len(),
            merged.hooks.len(),
            merged.rules.len(),
            merged.mcp.len(),
            merged.plugins.len(),
            resolved.scope,
        );

        crate::symlinker::apply(config, resolved, &merged)?;
        println!("Applied successfully.");

        // Process pending installs
        if !pending_installs.is_empty() {
            let pm = PluginManager::new(&config.paths.config_dir)?;
            let all = pm.all_available().unwrap_or_default();
            for name in &pending_installs {
                if let Some(resource) = all
                    .iter()
                    .find(|r| &r.install_id == name || &r.name == name)
                {
                    if let Err(e) = pm.install(
                        resource,
                        &config.paths.skills_dir,
                        &config.paths.agents_dir,
                        &config.paths.commands_dir,
                    ) {
                        eprintln!("Failed to install '{}': {}", name, e);
                    }
                }
            }
        }

        // Process pending uninstalls
        if !pending_uninstalls.is_empty() {
            let pm = PluginManager::new(&config.paths.config_dir)?;
            let all = pm.all_available().unwrap_or_default();
            for name in &pending_uninstalls {
                // Determine resource type from remote listing or try all types
                let resource_type = all
                    .iter()
                    .find(|r| &r.install_id == name || &r.name == name)
                    .map(|r| r.resource_type);

                if let Some(rt) = resource_type {
                    if let Err(e) = pm.uninstall(
                        name,
                        rt,
                        &config.paths.skills_dir,
                        &config.paths.agents_dir,
                        &config.paths.commands_dir,
                    ) {
                        eprintln!("Failed to uninstall '{}': {}", name, e);
                    }
                } else {
                    eprintln!("Unknown resource type for '{}', skipping uninstall", name);
                }
            }
        }

        let after_status = crate::symlinker::status(config, resolved)
            .unwrap_or_else(|_| ProjectStatus::empty(resolved.scope));
        print_status_summary(&before_status, &after_status);
    }

    // Handle pending profile save (save current symlinker state as a named profile)
    if let Some(ref save_name) = pending_profile_save {
        match ProfileManager::new(config) {
            Ok(pm) => {
                let status = crate::symlinker::status(config, resolved)
                    .unwrap_or_else(|_| ProjectStatus::empty(resolved.scope));
                match pm.save(save_name, &status) {
                    Ok(()) => println!("  Profile '{}' saved.", save_name),
                    Err(e) => eprintln!("  Failed to save profile '{}': {}", save_name, e),
                }
            }
            Err(e) => eprintln!("  Failed to initialise ProfileManager: {}", e),
        }
    }

    // Handle pending profile load (apply selected profile's selections)
    if let Some(ref load_name) = pending_profile_load {
        match ProfileManager::new(config) {
            Ok(pm) => match pm.load(load_name) {
                Ok(selections) => match crate::symlinker::apply(config, resolved, &selections) {
                    Ok(()) => println!("  Profile '{}' loaded and applied.", load_name),
                    Err(e) => eprintln!("  Failed to apply profile '{}': {}", load_name, e),
                },
                Err(e) => eprintln!("  Failed to load profile '{}': {}", load_name, e),
            },
            Err(e) => eprintln!("  Failed to initialise ProfileManager: {}", e),
        }
    }

    Ok(())
}

fn print_status_summary(before: &ProjectStatus, after: &ProjectStatus) {
    println!("\nSummary after apply:");
    summarize_category("Skills", &before.skills, &after.skills);
    summarize_category("Agents", &before.agents, &after.agents);
    summarize_category("Commands", &before.commands, &after.commands);
    summarize_category("Hooks", &before.hooks, &after.hooks);
    summarize_category("Rules", &before.rules, &after.rules);
    summarize_category("MCP", &before.mcp, &after.mcp);
    summarize_category("Plugins", &before.plugins, &after.plugins);
}

fn summarize_category(label: &str, before: &[String], after: &[String]) {
    let before_count = before.len();
    let after_count = after.len();
    let delta = after_count as isize - before_count as isize;

    if delta == 0 {
        println!("  {:<8} {} (no change)", label, after_count);
        return;
    }

    println!(
        "  {:<8} {} -> {} ({:+})",
        label, before_count, after_count, delta
    );

    let added = diff_names(after, before);
    let removed = diff_names(before, after);

    if !added.is_empty() {
        println!("      + {}", added.join(", "));
    }
    if !removed.is_empty() {
        println!("      - {}", removed.join(", "));
    }
}

fn diff_names(a: &[String], b: &[String]) -> Vec<String> {
    let bset: HashSet<&str> = b.iter().map(|s| s.as_str()).collect();
    a.iter()
        .filter(|s| !bset.contains(s.as_str()))
        .take(5)
        .cloned()
        .collect()
}
