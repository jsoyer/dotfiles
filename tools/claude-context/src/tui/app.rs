use anyhow::Result;
use crossterm::event::{self, Event, KeyCode, KeyModifiers};
use ratatui::DefaultTerminal;

use crate::config::AppConfig;
use crate::indexer::Index;
use crate::matcher::{RecommendSource, Recommendation, Recommendations};
use crate::plugins::{Origin, RemoteResource, ResourceType};
use crate::scanner::ProjectFingerprint;
use crate::symlinker::ProjectStatus;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum ResourceTab {
    Skills,
    Agents,
    Commands,
    Mcp,
    Rules,
    Plugins,
}

impl ResourceTab {
    pub fn label(&self) -> &'static str {
        match self {
            ResourceTab::Skills => "Skills",
            ResourceTab::Agents => "Agents",
            ResourceTab::Commands => "Commands",
            ResourceTab::Mcp => "MCP",
            ResourceTab::Rules => "Rules",
            ResourceTab::Plugins => "Plugins",
        }
    }

    pub fn from_support(supports: &[String]) -> Vec<ResourceTab> {
        let mut tabs = Vec::new();
        if supports.contains(&"skills".to_string()) { tabs.push(ResourceTab::Skills); }
        if supports.contains(&"agents".to_string()) { tabs.push(ResourceTab::Agents); }
        if supports.contains(&"commands".to_string()) { tabs.push(ResourceTab::Commands); }
        if supports.contains(&"mcp".to_string()) { tabs.push(ResourceTab::Mcp); }
        if supports.contains(&"rules".to_string()) { tabs.push(ResourceTab::Rules); }
        if supports.contains(&"plugins".to_string()) { tabs.push(ResourceTab::Plugins); }
        if tabs.is_empty() { tabs.push(ResourceTab::Skills); }
        tabs
    }
}

#[derive(Debug, Clone)]
pub struct CliTab {
    pub cli_name: String,
    pub resource_tabs: Vec<ResourceTab>,
    pub active_resource_idx: usize,
}

impl CliTab {
    pub fn active_resource(&self) -> ResourceTab {
        self.resource_tabs[self.active_resource_idx]
    }

    pub fn next_resource(&mut self) {
        self.active_resource_idx = (self.active_resource_idx + 1) % self.resource_tabs.len();
    }

    pub fn prev_resource(&mut self) {
        self.active_resource_idx = (self.active_resource_idx + self.resource_tabs.len() - 1)
            % self.resource_tabs.len();
    }
}

#[derive(Debug, Clone, Copy, PartialEq)]
pub enum SortMode {
    Default,  // enabled > suggested > alpha
    Score,    // highest score first
    Name,     // alphabetical
}

impl SortMode {
    pub fn next(self) -> Self {
        match self {
            SortMode::Default => SortMode::Score,
            SortMode::Score => SortMode::Name,
            SortMode::Name => SortMode::Default,
        }
    }

    #[allow(dead_code)]
    pub fn label(self) -> &'static str {
        match self {
            SortMode::Default => "default",
            SortMode::Score => "score",
            SortMode::Name => "name",
        }
    }
}

#[derive(Debug, Clone)]
pub struct ToggleItem {
    pub name: String,
    pub enabled: bool,
    pub suggested: bool,
    pub score: f32,
    pub reason: String,
    pub origin: Origin,
}

pub struct App<'a> {
    pub cli_tabs: Vec<CliTab>,
    pub active_cli_idx: usize,
    pub cursor: usize,
    pub scroll_offset: usize,
    pub visible_height: usize,
    pub filter: String,
    pub filtering: bool,
    pub sort_mode: SortMode,
    pub should_quit: bool,
    pub should_apply: bool,

    /// Items keyed by (cli_name, resource_tab)
    pub items: std::collections::HashMap<(String, ResourceTab), Vec<ToggleItem>>,

    /// Cross-CLI status: for each skill name, which CLIs have it active
    pub cli_active_map: std::collections::HashMap<String, Vec<String>>,

    pub fingerprint: &'a ProjectFingerprint,
    pub project_name: String,

    pub pending_installs: Vec<String>,
    pub pending_uninstalls: Vec<String>,
}

impl<'a> App<'a> {
    pub fn new(
        config: &AppConfig,
        index: &Index,
        fingerprint: &'a ProjectFingerprint,
        recommendations: &Recommendations,
        remote_resources: &[RemoteResource],
        cli_statuses: &[(String, ProjectStatus)],
    ) -> Self {
        use std::collections::HashMap;

        let scope_s = crate::scope::scope_str(
            cli_statuses.first().map(|(_, s)| s.scope).unwrap_or(crate::scope::Scope::Global)
        );

        // Build CLI tabs from detected CLIs
        let cli_tabs: Vec<CliTab> = config
            .detected_clis()
            .iter()
            .filter(|c| c.scopes.contains(&scope_s.to_string()))
            .map(|cli| CliTab {
                cli_name: cli.name.clone(),
                resource_tabs: ResourceTab::from_support(&cli.supports),
                active_resource_idx: 0,
            })
            .collect();

        // Build cross-CLI active map for skills
        let mut cli_active_map: HashMap<String, Vec<String>> = HashMap::new();
        for (cli_name, status) in cli_statuses {
            for skill in &status.skills {
                cli_active_map.entry(skill.clone()).or_default().push(cli_name.clone());
            }
        }

        let mut items: HashMap<(String, ResourceTab), Vec<ToggleItem>> = HashMap::new();

        for cli_tab in &cli_tabs {
            // Find this CLI's status
            let status = cli_statuses
                .iter()
                .find(|(name, _)| name == &cli_tab.cli_name)
                .map(|(_, s)| s);

            let empty_status = ProjectStatus {
                skills: Vec::new(), agents: Vec::new(), commands: Vec::new(),
                rules: Vec::new(), mcp: Vec::new(), plugins: Vec::new(),
                detected_clis: Vec::new(),
                scope: crate::scope::Scope::Global,
            };
            let status = status.unwrap_or(&empty_status);
            // Build items for each supported resource tab
            for &rtab in &cli_tab.resource_tabs {
                let key = (cli_tab.cli_name.clone(), rtab);
                let tab_items = Self::build_resource_items(
                    rtab, config, index, recommendations, remote_resources, status,
                );
                items.insert(key, tab_items);
            }
        } // end for cli_tab

        let project_name = fingerprint
            .project_dir
            .file_name()
            .map(|n| n.to_string_lossy().to_string())
            .unwrap_or_else(|| "unknown".to_string());

        Self {
            cli_tabs,
            active_cli_idx: 0,
            cursor: 0,
            scroll_offset: 0,
            visible_height: 20,
            filter: String::new(),
            filtering: false,
            sort_mode: SortMode::Default,
            should_quit: false,
            should_apply: false,
            items,
            cli_active_map,
            fingerprint,
            project_name,
            pending_installs: Vec::new(),
            pending_uninstalls: Vec::new(),
        }
    }

    fn build_resource_items(
        rtab: ResourceTab,
        config: &AppConfig,
        index: &Index,
        recommendations: &Recommendations,
        remote_resources: &[RemoteResource],
        status: &ProjectStatus,
    ) -> Vec<ToggleItem> {
        match rtab {
            ResourceTab::Skills => Self::build_items_from_index(
                &index.skills, &recommendations.skills, &status.skills,
                remote_resources, ResourceType::Skill,
            ),
            ResourceTab::Agents => Self::build_items_from_index(
                &index.agents, &recommendations.agents, &status.agents,
                remote_resources, ResourceType::Agent,
            ),
            ResourceTab::Commands => Self::build_items_from_index(
                &index.commands, &recommendations.commands, &status.commands,
                remote_resources, ResourceType::Command,
            ),
            ResourceTab::Mcp => Self::build_mcp_items(config, recommendations, status),
            ResourceTab::Rules => Self::build_rules_items(recommendations, status),
            ResourceTab::Plugins => Self::build_plugin_items(recommendations, remote_resources, status),
        }
    }

    fn build_items_from_index(
        index_entries: &[crate::indexer::ResourceEntry],
        recs: &[Recommendation],
        active: &[String],
        remote_resources: &[RemoteResource],
        resource_type: ResourceType,
    ) -> Vec<ToggleItem> {
        let mut items = Vec::new();
        let mut seen = Vec::new();

        for entry in index_entries {
            let rec = recs.iter().find(|r| r.name == entry.name);
            items.push(ToggleItem {
                name: entry.name.clone(),
                enabled: active.contains(&entry.name),
                suggested: rec.is_some(),
                score: rec.map(|r| r.score).unwrap_or(0.0),
                reason: rec.map(|r| r.reason.clone()).unwrap_or_default(),
                origin: Origin::Local,
            });
            seen.push(entry.name.clone());
        }

        for remote in remote_resources {
            if remote.resource_type == resource_type && !seen.contains(&remote.install_id) {
                items.push(ToggleItem {
                    name: remote.install_id.clone(),
                    enabled: false,
                    suggested: false,
                    score: 0.0,
                    reason: format!("{} ({})", remote.description, remote.source_name),
                    origin: Origin::Remote,
                });
            }
        }

        items.sort_by(|a, b| {
            b.enabled.cmp(&a.enabled)
                .then(b.suggested.cmp(&a.suggested))
                .then(a.name.cmp(&b.name))
        });
        items
    }

    fn build_mcp_items(
        config: &AppConfig,
        recommendations: &Recommendations,
        status: &ProjectStatus,
    ) -> Vec<ToggleItem> {
        let all_mcp = &[
            "context7", "fetch", "github", "1password", "obsidian",
            "sequential-thinking", "memory", "brave-search", "playwright",
            "slack", "linear", "discord", "notion", "drawio",
            "token-optimizer", "cloudflare-docs", "cloudflare-workers-builds",
            "cloudflare-workers-bindings", "cloudflare-observability",
        ];
        all_mcp.iter().map(|name| {
            let is_active = status.mcp.contains(&name.to_string());
            let is_base = config.base.mcp.contains(&name.to_string());
            let is_recommended = recommendations.mcp.contains(&name.to_string());
            ToggleItem {
                name: name.to_string(),
                enabled: is_active,
                suggested: is_base || is_recommended,
                score: if is_base { 1.0 } else if is_recommended { 0.8 } else { 0.0 },
                reason: if is_active { "active".into() }
                    else if is_base { "base".into() }
                    else if is_recommended { "recommended".into() }
                    else { String::new() },
                origin: Origin::Local,
            }
        }).collect()
    }

    fn build_rules_items(
        recommendations: &Recommendations,
        status: &ProjectStatus,
    ) -> Vec<ToggleItem> {
        let all_langs = &[
            "typescript", "python", "rust", "golang", "swift", "cpp",
            "csharp", "java", "kotlin", "perl", "php",
        ];
        all_langs.iter().map(|name| {
            let is_active = status.rules.contains(&name.to_string());
            let is_recommended = recommendations.rules.iter().any(|r| {
                r == *name || (*name == "golang" && r == "go") || (*name == "go" && r == "golang")
            });
            ToggleItem {
                name: name.to_string(),
                enabled: is_active,
                suggested: is_recommended,
                score: if is_recommended { 1.0 } else { 0.0 },
                reason: if is_active { "active".into() }
                    else if is_recommended { "detected".into() }
                    else { String::new() },
                origin: Origin::Local,
            }
        }).collect()
    }

    fn build_plugin_items(
        recommendations: &Recommendations,
        remote_resources: &[RemoteResource],
        status: &ProjectStatus,
    ) -> Vec<ToggleItem> {
        let mut items = Vec::new();
        let mut seen = Vec::new();

        for name in &recommendations.plugins {
            items.push(ToggleItem {
                name: name.clone(),
                enabled: status.plugins.contains(name),
                suggested: true,
                score: 0.8,
                reason: "recommended".to_string(),
                origin: Origin::Local,
            });
            seen.push(name.clone());
        }
        for remote in remote_resources {
            if remote.resource_type == ResourceType::Plugin && !seen.contains(&remote.install_id) {
                items.push(ToggleItem {
                    name: remote.install_id.clone(),
                    enabled: status.plugins.contains(&remote.install_id),
                    suggested: false,
                    score: 0.0,
                    reason: format!("{} ({})", remote.description, remote.source_name),
                    origin: Origin::Remote,
                });
            }
        }
        items
    }

    pub fn run(&mut self, terminal: &mut DefaultTerminal) -> Result<Option<Recommendations>> {
        loop {
            terminal.draw(|frame| {
                // Update visible height from terminal size
                self.visible_height = frame.area().height.saturating_sub(12) as usize;
                super::ui::draw(frame, self);
            })?;

            if let Event::Key(key) = event::read()? {
                if self.filtering {
                    match key.code {
                        KeyCode::Esc => {
                            self.filter.clear();
                            self.filtering = false;
                        }
                        KeyCode::Enter => {
                            self.filtering = false;
                        }
                        KeyCode::Backspace => {
                            self.filter.pop();
                        }
                        KeyCode::Char(c) => {
                            self.filter.push(c);
                        }
                        _ => {}
                    }
                    continue;
                }

                match key.code {
                    KeyCode::Char('q') | KeyCode::Esc => {
                        self.should_quit = true;
                    }
                    KeyCode::Char('c') if key.modifiers.contains(KeyModifiers::CONTROL) => {
                        self.should_quit = true;
                    }
                    KeyCode::Tab | KeyCode::Char('l') => {
                        self.cli_tabs[self.active_cli_idx].next_resource();
                        self.cursor = 0;
                        self.scroll_offset = 0;
                        self.filter.clear();
                    }
                    KeyCode::BackTab | KeyCode::Char('h') => {
                        self.cli_tabs[self.active_cli_idx].prev_resource();
                        self.cursor = 0;
                        self.scroll_offset = 0;
                        self.filter.clear();
                    }
                    KeyCode::Char('L') => {
                        // Next CLI tab
                        if !self.cli_tabs.is_empty() {
                            self.active_cli_idx = (self.active_cli_idx + 1) % self.cli_tabs.len();
                            self.cursor = 0;
                            self.scroll_offset = 0;
                            self.filter.clear();
                        }
                    }
                    KeyCode::Char('H') => {
                        // Previous CLI tab
                        if !self.cli_tabs.is_empty() {
                            self.active_cli_idx = (self.active_cli_idx + self.cli_tabs.len() - 1) % self.cli_tabs.len();
                            self.cursor = 0;
                            self.scroll_offset = 0;
                            self.filter.clear();
                        }
                    }
                    KeyCode::Down | KeyCode::Char('j') => {
                        let len = self.filtered_items().len();
                        if len > 0 {
                            self.cursor = (self.cursor + 1) % len;
                            self.ensure_cursor_visible();
                        }
                    }
                    KeyCode::Up | KeyCode::Char('k') => {
                        let len = self.filtered_items().len();
                        if len > 0 {
                            self.cursor = (self.cursor + len - 1) % len;
                            self.ensure_cursor_visible();
                        }
                    }
                    KeyCode::PageDown => {
                        let len = self.filtered_items().len();
                        if len > 0 {
                            self.cursor = (self.cursor + self.visible_height).min(len - 1);
                            self.ensure_cursor_visible();
                        }
                    }
                    KeyCode::PageUp => {
                        let len = self.filtered_items().len();
                        if len > 0 {
                            self.cursor = self.cursor.saturating_sub(self.visible_height);
                            self.ensure_cursor_visible();
                        }
                    }
                    KeyCode::Home | KeyCode::Char('g') => {
                        self.cursor = 0;
                        self.scroll_offset = 0;
                    }
                    KeyCode::End | KeyCode::Char('G') => {
                        let len = self.filtered_items().len();
                        if len > 0 {
                            self.cursor = len - 1;
                            self.ensure_cursor_visible();
                        }
                    }
                    KeyCode::Char(' ') | KeyCode::Enter => {
                        self.toggle_current();
                    }
                    KeyCode::Char('/') => {
                        self.filtering = true;
                        self.filter.clear();
                    }
                    KeyCode::Char('a') => {
                        self.should_apply = true;
                    }
                    KeyCode::Char('A') => {
                        // Select all filtered
                        self.select_all_filtered(true);
                    }
                    KeyCode::Char('N') => {
                        // Deselect all filtered
                        self.select_all_filtered(false);
                    }
                    KeyCode::Char('s') => {
                        self.sort_mode = self.sort_mode.next();
                        self.resort_active();
                        self.cursor = 0;
                        self.scroll_offset = 0;
                    }
                    KeyCode::Char('i') => {
                        // Install/uninstall current item
                        self.toggle_install_current();
                    }
                    _ => {}
                }
            }

            if self.should_quit {
                return Ok(None);
            }

            if self.should_apply {
                return Ok(Some(self.build_selections()));
            }
        }
    }

    pub fn active_cli(&self) -> &CliTab {
        &self.cli_tabs[self.active_cli_idx]
    }

    fn active_key(&self) -> (String, ResourceTab) {
        let cli = &self.cli_tabs[self.active_cli_idx];
        (cli.cli_name.clone(), cli.active_resource())
    }

    pub fn active_items(&self) -> &[ToggleItem] {
        let key = self.active_key();
        self.items.get(&key).map(|v| v.as_slice()).unwrap_or(&[])
    }

    fn active_items_mut(&mut self) -> &mut Vec<ToggleItem> {
        let key = self.active_key();
        self.items.entry(key).or_default()
    }

    pub fn filtered_items(&self) -> Vec<(usize, &ToggleItem)> {
        self.active_items()
            .iter()
            .enumerate()
            .filter(|(_, item)| {
                if self.filter.is_empty() {
                    return true;
                }
                let filter_lower = self.filter.to_lowercase();
                item.name.to_lowercase().contains(&filter_lower)
                    || item.reason.to_lowercase().contains(&filter_lower)
            })
            .collect()
    }

    pub fn ensure_cursor_visible(&mut self) {
        if self.cursor < self.scroll_offset {
            self.scroll_offset = self.cursor;
        }
        if self.cursor >= self.scroll_offset + self.visible_height {
            self.scroll_offset = self.cursor - self.visible_height + 1;
        }
    }

    fn resort_active(&mut self) {
        let mode = self.sort_mode;
        let items = self.active_items_mut();
        match mode {
            SortMode::Default => {
                items.sort_by(|a, b| {
                    b.enabled.cmp(&a.enabled)
                        .then(b.suggested.cmp(&a.suggested))
                        .then(a.name.cmp(&b.name))
                });
            }
            SortMode::Score => {
                items.sort_by(|a, b| {
                    b.score.partial_cmp(&a.score).unwrap_or(std::cmp::Ordering::Equal)
                        .then(a.name.cmp(&b.name))
                });
            }
            SortMode::Name => {
                items.sort_by(|a, b| a.name.cmp(&b.name));
            }
        }
    }

    fn toggle_current(&mut self) {
        let filtered = self.filtered_items();
        if let Some(&(real_idx, _)) = filtered.get(self.cursor) {
            let items = self.active_items_mut();
            items[real_idx].enabled = !items[real_idx].enabled;
        }
    }

    fn select_all_filtered(&mut self, state: bool) {
        let indices: Vec<usize> = self.filtered_items().iter().map(|(i, _)| *i).collect();
        let items = self.active_items_mut();
        for idx in indices {
            items[idx].enabled = state;
        }
    }

    fn toggle_install_current(&mut self) {
        let filtered = self.filtered_items();
        let info = filtered.get(self.cursor).map(|&(idx, item)| {
            (idx, item.name.clone(), item.origin)
        });

        if let Some((real_idx, name, origin)) = info {
            match origin {
                Origin::Remote => {
                    if self.pending_installs.contains(&name) {
                        self.pending_installs.retain(|n| n != &name);
                        let items = self.active_items_mut();
                        items[real_idx].reason = items[real_idx].reason.replace(" [INSTALL]", "");
                    } else {
                        self.pending_installs.push(name);
                        let items = self.active_items_mut();
                        items[real_idx].reason.push_str(" [INSTALL]");
                    }
                }
                Origin::Local => {
                    if self.pending_uninstalls.contains(&name) {
                        self.pending_uninstalls.retain(|n| n != &name);
                        let items = self.active_items_mut();
                        items[real_idx].reason = items[real_idx].reason.replace(" [UNINSTALL]", "");
                    } else {
                        self.pending_uninstalls.push(name);
                        let items = self.active_items_mut();
                        items[real_idx].reason.push_str(" [UNINSTALL]");
                    }
                }
            }
        }
    }

    fn build_selections(&self) -> Recommendations {
        let get_items = |cli: &str, tab: ResourceTab| -> &[ToggleItem] {
            self.items.get(&(cli.to_string(), tab)).map(|v| v.as_slice()).unwrap_or(&[])
        };

        // Build from the active CLI's selections
        let cli_name = &self.cli_tabs[self.active_cli_idx].cli_name;

        let to_recs = |items: &[ToggleItem]| -> Vec<Recommendation> {
            items.iter()
                .filter(|i| i.enabled)
                .map(|i| Recommendation {
                    name: i.name.clone(),
                    score: i.score,
                    reason: i.reason.clone(),
                    source: RecommendSource::Scanner,
                })
                .collect()
        };

        Recommendations {
            skills: to_recs(get_items(cli_name, ResourceTab::Skills)),
            agents: to_recs(get_items(cli_name, ResourceTab::Agents)),
            commands: to_recs(get_items(cli_name, ResourceTab::Commands)),
            mcp: get_items(cli_name, ResourceTab::Mcp).iter()
                .filter(|i| i.enabled).map(|i| i.name.clone()).collect(),
            rules: get_items(cli_name, ResourceTab::Rules).iter()
                .filter(|i| i.enabled).map(|i| i.name.clone()).collect(),
            plugins: get_items(cli_name, ResourceTab::Plugins).iter()
                .filter(|i| i.enabled).map(|i| i.name.clone()).collect(),
        }
    }
}
