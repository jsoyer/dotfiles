use anyhow::Result;
use crossterm::event::{self, Event, KeyCode, KeyModifiers};
use ratatui::DefaultTerminal;

use crate::config::AppConfig;
use crate::indexer::Index;
use crate::matcher::{RecommendSource, Recommendation, Recommendations};
use crate::scanner::ProjectFingerprint;

#[derive(Debug, Clone, Copy, PartialEq)]
pub enum Tab {
    Skills,
    Agents,
    Commands,
    Mcp,
    Rules,
    Plugins,
}

impl Tab {
    pub fn all() -> &'static [Tab] {
        &[
            Tab::Skills,
            Tab::Agents,
            Tab::Commands,
            Tab::Mcp,
            Tab::Rules,
            Tab::Plugins,
        ]
    }

    pub fn label(&self) -> &'static str {
        match self {
            Tab::Skills => "Skills",
            Tab::Agents => "Agents",
            Tab::Commands => "Commands",
            Tab::Mcp => "MCP",
            Tab::Rules => "Rules",
            Tab::Plugins => "Plugins",
        }
    }

    pub fn next(&self) -> Tab {
        let tabs = Self::all();
        let idx = tabs.iter().position(|t| t == self).unwrap_or(0);
        tabs[(idx + 1) % tabs.len()]
    }

    pub fn prev(&self) -> Tab {
        let tabs = Self::all();
        let idx = tabs.iter().position(|t| t == self).unwrap_or(0);
        tabs[(idx + tabs.len() - 1) % tabs.len()]
    }
}

#[derive(Debug, Clone)]
pub struct ToggleItem {
    pub name: String,
    pub enabled: bool,
    pub score: f32,
    pub reason: String,
}

pub struct App<'a> {
    pub active_tab: Tab,
    pub cursor: usize,
    pub scroll_offset: usize,
    pub visible_height: usize,
    pub filter: String,
    pub filtering: bool,
    pub should_quit: bool,
    pub should_apply: bool,

    pub skills: Vec<ToggleItem>,
    pub agents: Vec<ToggleItem>,
    pub commands: Vec<ToggleItem>,
    pub mcp: Vec<ToggleItem>,
    pub rules: Vec<ToggleItem>,
    pub plugins: Vec<ToggleItem>,

    pub fingerprint: &'a ProjectFingerprint,
    pub project_name: String,
}

impl<'a> App<'a> {
    pub fn new(
        config: &AppConfig,
        index: &Index,
        fingerprint: &'a ProjectFingerprint,
        recommendations: &Recommendations,
    ) -> Self {
        let recommended_skill_names: Vec<String> =
            recommendations.skills.iter().map(|r| r.name.clone()).collect();
        let recommended_agent_names: Vec<String> =
            recommendations.agents.iter().map(|r| r.name.clone()).collect();
        let recommended_cmd_names: Vec<String> =
            recommendations.commands.iter().map(|r| r.name.clone()).collect();

        // Build skill list: recommended first (enabled), then all others (disabled)
        let mut skills: Vec<ToggleItem> = recommendations
            .skills
            .iter()
            .map(|r| ToggleItem {
                name: r.name.clone(),
                enabled: true,
                score: r.score,
                reason: r.reason.clone(),
            })
            .collect();

        for entry in &index.skills {
            if !recommended_skill_names.contains(&entry.name) {
                skills.push(ToggleItem {
                    name: entry.name.clone(),
                    enabled: false,
                    score: 0.0,
                    reason: String::new(),
                });
            }
        }

        // Build agent list
        let mut agents: Vec<ToggleItem> = recommendations
            .agents
            .iter()
            .map(|r| ToggleItem {
                name: r.name.clone(),
                enabled: true,
                score: r.score,
                reason: r.reason.clone(),
            })
            .collect();

        for entry in &index.agents {
            if !recommended_agent_names.contains(&entry.name) {
                agents.push(ToggleItem {
                    name: entry.name.clone(),
                    enabled: false,
                    score: 0.0,
                    reason: String::new(),
                });
            }
        }

        // Build command list
        let mut commands: Vec<ToggleItem> = recommendations
            .commands
            .iter()
            .map(|r| ToggleItem {
                name: r.name.clone(),
                enabled: true,
                score: r.score,
                reason: r.reason.clone(),
            })
            .collect();

        for entry in &index.commands {
            if !recommended_cmd_names.contains(&entry.name) {
                commands.push(ToggleItem {
                    name: entry.name.clone(),
                    enabled: false,
                    score: 0.0,
                    reason: String::new(),
                });
            }
        }

        // MCP servers
        let all_mcp = &[
            "context7", "fetch", "github", "1password", "obsidian",
            "sequential-thinking", "memory", "brave-search", "playwright",
            "slack", "linear", "discord", "notion", "drawio",
            "token-optimizer", "cloudflare-docs", "cloudflare-workers-builds",
            "cloudflare-workers-bindings", "cloudflare-observability",
        ];
        let mcp: Vec<ToggleItem> = all_mcp
            .iter()
            .map(|name| {
                let is_base = config.base.mcp.contains(&name.to_string());
                let is_recommended = recommendations.mcp.contains(&name.to_string());
                ToggleItem {
                    name: name.to_string(),
                    enabled: is_base || is_recommended,
                    score: if is_base { 1.0 } else if is_recommended { 0.8 } else { 0.0 },
                    reason: if is_base {
                        "base".to_string()
                    } else if is_recommended {
                        "recommended".to_string()
                    } else {
                        String::new()
                    },
                }
            })
            .collect();

        // Rules (language dirs)
        let all_langs = &[
            "typescript", "python", "rust", "golang", "swift", "cpp",
            "csharp", "java", "kotlin", "perl", "php",
        ];
        let rules: Vec<ToggleItem> = all_langs
            .iter()
            .map(|name| {
                let is_recommended = recommendations.rules.iter().any(|r| {
                    r == *name || (*name == "golang" && r == "go") || (*name == "go" && r == "golang")
                });
                ToggleItem {
                    name: name.to_string(),
                    enabled: is_recommended,
                    score: if is_recommended { 1.0 } else { 0.0 },
                    reason: if is_recommended {
                        "detected".to_string()
                    } else {
                        String::new()
                    },
                }
            })
            .collect();

        // Plugins (empty for now, populated from config)
        let plugins: Vec<ToggleItem> = recommendations
            .plugins
            .iter()
            .map(|name| ToggleItem {
                name: name.clone(),
                enabled: true,
                score: 0.8,
                reason: "recommended".to_string(),
            })
            .collect();

        let project_name = fingerprint
            .project_dir
            .file_name()
            .map(|n| n.to_string_lossy().to_string())
            .unwrap_or_else(|| "unknown".to_string());

        Self {
            active_tab: Tab::Skills,
            cursor: 0,
            scroll_offset: 0,
            visible_height: 20,
            filter: String::new(),
            filtering: false,
            should_quit: false,
            should_apply: false,
            skills,
            agents,
            commands,
            mcp,
            rules,
            plugins,
            fingerprint,
            project_name,
        }
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
                        self.active_tab = self.active_tab.next();
                        self.cursor = 0;
                        self.scroll_offset = 0;
                        self.filter.clear();
                    }
                    KeyCode::BackTab | KeyCode::Char('h') => {
                        self.active_tab = self.active_tab.prev();
                        self.cursor = 0;
                        self.scroll_offset = 0;
                        self.filter.clear();
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

    pub fn active_items(&self) -> &[ToggleItem] {
        match self.active_tab {
            Tab::Skills => &self.skills,
            Tab::Agents => &self.agents,
            Tab::Commands => &self.commands,
            Tab::Mcp => &self.mcp,
            Tab::Rules => &self.rules,
            Tab::Plugins => &self.plugins,
        }
    }

    fn active_items_mut(&mut self) -> &mut Vec<ToggleItem> {
        match self.active_tab {
            Tab::Skills => &mut self.skills,
            Tab::Agents => &mut self.agents,
            Tab::Commands => &mut self.commands,
            Tab::Mcp => &mut self.mcp,
            Tab::Rules => &mut self.rules,
            Tab::Plugins => &mut self.plugins,
        }
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

    pub fn enabled_count(&self, items: &[ToggleItem]) -> usize {
        items.iter().filter(|i| i.enabled).count()
    }

    fn build_selections(&self) -> Recommendations {
        Recommendations {
            skills: self
                .skills
                .iter()
                .filter(|i| i.enabled)
                .map(|i| Recommendation {
                    name: i.name.clone(),
                    score: i.score,
                    reason: i.reason.clone(),
                    source: RecommendSource::Scanner,
                })
                .collect(),
            agents: self
                .agents
                .iter()
                .filter(|i| i.enabled)
                .map(|i| Recommendation {
                    name: i.name.clone(),
                    score: i.score,
                    reason: i.reason.clone(),
                    source: RecommendSource::Scanner,
                })
                .collect(),
            commands: self
                .commands
                .iter()
                .filter(|i| i.enabled)
                .map(|i| Recommendation {
                    name: i.name.clone(),
                    score: i.score,
                    reason: i.reason.clone(),
                    source: RecommendSource::Scanner,
                })
                .collect(),
            mcp: self
                .mcp
                .iter()
                .filter(|i| i.enabled)
                .map(|i| i.name.clone())
                .collect(),
            rules: self
                .rules
                .iter()
                .filter(|i| i.enabled)
                .map(|i| i.name.clone())
                .collect(),
            plugins: self
                .plugins
                .iter()
                .filter(|i| i.enabled)
                .map(|i| i.name.clone())
                .collect(),
        }
    }
}
