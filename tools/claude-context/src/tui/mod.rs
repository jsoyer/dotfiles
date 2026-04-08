mod app;
mod ui;

use anyhow::Result;

use crate::config::AppConfig;
use crate::indexer::Index;
use crate::matcher::Recommendations;
use crate::plugins::PluginEntry;
use crate::scanner::ProjectFingerprint;
use crate::scope::ResolvedScope;

pub fn run(
    config: &AppConfig,
    resolved: &ResolvedScope,
    index: &Index,
    fingerprint: &ProjectFingerprint,
    recommendations: &Recommendations,
    available_plugins: &[PluginEntry],
) -> Result<()> {
    let mut app = app::App::new(config, index, fingerprint, recommendations, available_plugins);

    let mut terminal = ratatui::init();
    let result = app.run(&mut terminal);
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
    }

    Ok(())
}
