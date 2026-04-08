mod app;
mod ui;

use anyhow::Result;

use crate::config::AppConfig;
use crate::indexer::Index;
use crate::matcher::Recommendations;
use crate::plugins::{PluginManager, RemoteResource};
use crate::scanner::ProjectFingerprint;
use crate::scope::ResolvedScope;

pub fn run(
    config: &AppConfig,
    resolved: &ResolvedScope,
    index: &Index,
    fingerprint: &ProjectFingerprint,
    recommendations: &Recommendations,
    remote_resources: &[RemoteResource],
) -> Result<()> {
    let mut app = app::App::new(config, index, fingerprint, recommendations, remote_resources);

    let mut terminal = ratatui::init();
    let result = app.run(&mut terminal);
    let pending_installs = app.pending_installs.clone();
    let pending_uninstalls = app.pending_uninstalls.clone();
    ratatui::restore();

    if let Some(selections) = result? {
        println!(
            "\nApplying {} skills, {} agents, {} commands, {} rules, {} MCP, {} plugins (scope: {})...",
            selections.skills.len(),
            selections.agents.len(),
            selections.commands.len(),
            selections.rules.len(),
            selections.mcp.len(),
            selections.plugins.len(),
            resolved.scope,
        );

        crate::symlinker::apply(config, resolved, &selections)?;
        println!("Applied successfully.");

        // Process pending installs
        if !pending_installs.is_empty() {
            let pm = PluginManager::new(&config.paths.config_dir)?;
            let all = pm.all_available().unwrap_or_default();
            for name in &pending_installs {
                if let Some(resource) = all.iter().find(|r| &r.install_id == name || &r.name == name) {
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
    }

    Ok(())
}
