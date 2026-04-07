mod app;
mod ui;

use anyhow::Result;

use crate::config::AppConfig;
use crate::indexer::Index;
use crate::matcher::Recommendations;
use crate::scanner::ProjectFingerprint;

pub fn run(
    config: &AppConfig,
    index: &Index,
    fingerprint: &ProjectFingerprint,
    recommendations: &Recommendations,
) -> Result<()> {
    let mut app = app::App::new(config, index, fingerprint, recommendations);

    let mut terminal = ratatui::init();
    let result = app.run(&mut terminal);
    ratatui::restore();

    if let Some(selections) = result? {
        println!("\nApplying {} skills, {} agents, {} commands, {} rules, {} MCP, {} plugins...",
            selections.skills.len(),
            selections.agents.len(),
            selections.commands.len(),
            selections.rules.len(),
            selections.mcp.len(),
            selections.plugins.len(),
        );

        let project_dir = std::env::current_dir()?;
        crate::symlinker::apply(config, &project_dir, &selections)?;
        println!("Applied successfully.");
    }

    Ok(())
}
