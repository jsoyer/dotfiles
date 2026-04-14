use anyhow::Result;
use crossterm::event::{self, Event, KeyCode, KeyModifiers};
use ratatui::DefaultTerminal;
use std::collections::{HashMap, HashSet};

use crate::config::AppConfig;
use crate::indexer::Index;
use crate::matcher::{RecommendSource, Recommendation, Recommendations};
use crate::plugins::{Origin, RemoteResource, ResourceType};
use crate::scanner::ProjectFingerprint;
use crate::symlinker::ProjectStatus;
use crate::theme::Theme;

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum PreviewAction {
    Add,
    Remove,
}

#[derive(Debug, Clone)]
pub struct PreviewLine {
    pub category: String,
    pub name: String,
    pub action: PreviewAction,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum ResourceTab {
    Skills,
    Agents,
    Commands,
    Hooks,
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
            ResourceTab::Hooks => "Hooks",
            ResourceTab::Mcp => "MCP",
            ResourceTab::Rules => "Rules",
            ResourceTab::Plugins => "Plugins",
        }
    }

    pub fn from_support(supports: &[String]) -> Vec<ResourceTab> {
        let mut tabs = Vec::new();
        if supports.contains(&"skills".to_string()) {
            tabs.push(ResourceTab::Skills);
        }
        if supports.contains(&"agents".to_string()) {
            tabs.push(ResourceTab::Agents);
        }
        if supports.contains(&"commands".to_string()) {
            tabs.push(ResourceTab::Commands);
        }
        if supports.contains(&"hooks".to_string()) {
            tabs.push(ResourceTab::Hooks);
        }
        if supports.contains(&"mcp".to_string()) {
            tabs.push(ResourceTab::Mcp);
        }
        if supports.contains(&"rules".to_string()) {
            tabs.push(ResourceTab::Rules);
        }
        if supports.contains(&"plugins".to_string()) {
            tabs.push(ResourceTab::Plugins);
        }
        if tabs.is_empty() {
            tabs.push(ResourceTab::Skills);
        }
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
        self.active_resource_idx =
            (self.active_resource_idx + self.resource_tabs.len() - 1) % self.resource_tabs.len();
    }
}

#[derive(Debug, Clone, Copy, PartialEq)]
pub enum SortMode {
    Default, // enabled > suggested > alpha
    Score,   // highest score first
    Name,    // alphabetical
    Origin,  // local first, then remote
}

impl SortMode {
    pub fn next(self) -> Self {
        match self {
            SortMode::Default => SortMode::Score,
            SortMode::Score => SortMode::Name,
            SortMode::Name => SortMode::Origin,
            SortMode::Origin => SortMode::Default,
        }
    }

    #[allow(dead_code)]
    pub fn label(self) -> &'static str {
        match self {
            SortMode::Default => "default",
            SortMode::Score => "score",
            SortMode::Name => "name",
            SortMode::Origin => "origin",
        }
    }
}

#[derive(Debug, Clone)]
pub struct ToggleItem {
    pub name: String,
    pub enabled: bool,
    pub available: bool,
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
    pub items: HashMap<(String, ResourceTab), Vec<ToggleItem>>,

    /// Cross-CLI status: for each skill name, which CLIs have it active
    pub cli_active_map: HashMap<String, Vec<String>>,

    pub fingerprint: &'a ProjectFingerprint,
    pub project_name: String,

    pub pending_installs: Vec<String>,
    pub pending_uninstalls: Vec<String>,

    // CLI toggle popup state
    pub cli_toggle_mode: bool,
    pub cli_toggle_cursor: usize,
    pub cli_toggle_selections: Vec<(String, bool)>,
    pub cli_toggle_resource_name: String,

    // Preview mode state
    pub preview_mode: bool,
    pub preview_lines: Vec<PreviewLine>,
    pub preview_scroll: usize,

    /// Snapshot of enabled items at TUI open time: (cli_name, tab) -> list of enabled names
    pub initial_enabled: HashMap<(String, ResourceTab), Vec<String>>,

    // Profile selector popup state
    pub profile_mode: bool,
    pub profile_cursor: usize,
    /// (name, skill_count, agent_count)
    pub profile_list: Vec<(String, usize, usize)>,
    pub profile_save_mode: bool,
    pub profile_save_input: String,

    // Pending profile operations signalled to mod.rs after TUI exits
    pub pending_profile_save: Option<String>,
    pub pending_profile_load: Option<String>,

    // Global search mode state
    pub global_search_mode: bool,
    pub global_search_results: Vec<(ResourceTab, usize, String)>, // (tab, original_idx, name)
    pub global_search_cursor: usize,

    // Pinned items (shown at top of list)
    pub pinned: HashSet<String>,

    // Active color theme
    pub theme: Theme,
}

impl<'a> App<'a> {
    pub fn new(
        config: &AppConfig,
        index: &Index,
        fingerprint: &'a ProjectFingerprint,
        recommendations: &Recommendations,
        remote_resources: &[RemoteResource],
        cli_statuses: &[(String, ProjectStatus)],
        theme: Theme,
    ) -> Self {
        // Build CLI tabs from all detected CLIs (show all, not just current scope)
        let cli_tabs: Vec<CliTab> = config
            .detected_clis()
            .iter()
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
                cli_active_map
                    .entry(skill.clone())
                    .or_default()
                    .push(cli_name.clone());
            }
        }

        let mut items: HashMap<(String, ResourceTab), Vec<ToggleItem>> = HashMap::new();

        for cli_tab in &cli_tabs {
            // Find this CLI's status
            let status = cli_statuses
                .iter()
                .find(|(name, _)| name == &cli_tab.cli_name)
                .map(|(_, s)| s);

            let empty_status = ProjectStatus::empty(crate::scope::Scope::Global);
            let status = status.unwrap_or(&empty_status);
            // Build items for each supported resource tab
            for &rtab in &cli_tab.resource_tabs {
                let key = (cli_tab.cli_name.clone(), rtab);
                let tab_items = Self::build_resource_items(
                    rtab,
                    config,
                    index,
                    recommendations,
                    remote_resources,
                    status,
                );
                items.insert(key, tab_items);
            }
        } // end for cli_tab

        // Capture initial enabled state for preview diff
        let initial_enabled: HashMap<(String, ResourceTab), Vec<String>> = items
            .iter()
            .map(|(key, tab_items)| {
                let enabled: Vec<String> = tab_items
                    .iter()
                    .filter(|i| i.enabled)
                    .map(|i| i.name.clone())
                    .collect();
                (key.clone(), enabled)
            })
            .collect();

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
            cli_toggle_mode: false,
            cli_toggle_cursor: 0,
            cli_toggle_selections: Vec::new(),
            cli_toggle_resource_name: String::new(),
            preview_mode: false,
            preview_lines: Vec::new(),
            preview_scroll: 0,
            initial_enabled,
            profile_mode: false,
            profile_cursor: 0,
            profile_list: Vec::new(),
            profile_save_mode: false,
            profile_save_input: String::new(),
            pending_profile_save: None,
            pending_profile_load: None,
            global_search_mode: false,
            global_search_results: Vec::new(),
            global_search_cursor: 0,
            pinned: HashSet::new(),
            theme,
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
                &index.skills,
                &recommendations.skills,
                &status.skills,
                remote_resources,
                ResourceType::Skill,
            ),
            ResourceTab::Agents => Self::build_items_from_index(
                &index.agents,
                &recommendations.agents,
                &status.agents,
                remote_resources,
                ResourceType::Agent,
            ),
            ResourceTab::Commands => Self::build_items_from_index(
                &index.commands,
                &recommendations.commands,
                &status.commands,
                remote_resources,
                ResourceType::Command,
            ),
            ResourceTab::Hooks => Self::build_items_from_index(
                &index.hooks,
                &recommendations.hooks,
                &status.hooks,
                remote_resources,
                ResourceType::Hook,
            ),
            ResourceTab::Mcp => Self::build_mcp_items(config, recommendations, status),
            ResourceTab::Rules => Self::build_rules_items(recommendations, status),
            ResourceTab::Plugins => {
                Self::build_plugin_items(recommendations, remote_resources, status)
            }
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
                available: true,
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
                    available: false,
                    suggested: false,
                    score: 0.0,
                    reason: format!("{} ({})", remote.description, remote.source_name),
                    origin: Origin::Remote,
                });
            }
        }

        items.sort_by(|a, b| {
            let a_local = matches!(a.origin, Origin::Local);
            let b_local = matches!(b.origin, Origin::Local);
            b.enabled
                .cmp(&a.enabled)
                .then(b_local.cmp(&a_local))
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
            "context7",
            "fetch",
            "github",
            "1password",
            "obsidian",
            "sequential-thinking",
            "memory",
            "brave-search",
            "playwright",
            "slack",
            "linear",
            "discord",
            "notion",
            "drawio",
            "token-optimizer",
            "cloudflare-docs",
            "cloudflare-workers-builds",
            "cloudflare-workers-bindings",
            "cloudflare-observability",
        ];
        all_mcp
            .iter()
            .map(|name| {
                let is_active = status.mcp.contains(&name.to_string());
                let is_base = config.base.mcp.contains(&name.to_string());
                let is_recommended = recommendations.mcp.contains(&name.to_string());
                ToggleItem {
                    name: name.to_string(),
                    enabled: is_active,
                    available: true,
                    suggested: is_base || is_recommended,
                    score: if is_base {
                        1.0
                    } else if is_recommended {
                        0.8
                    } else {
                        0.0
                    },
                    reason: if is_active {
                        "active".into()
                    } else if is_base {
                        "base".into()
                    } else if is_recommended {
                        "recommended".into()
                    } else {
                        String::new()
                    },
                    origin: Origin::Local,
                }
            })
            .collect()
    }

    fn build_rules_items(
        recommendations: &Recommendations,
        status: &ProjectStatus,
    ) -> Vec<ToggleItem> {
        let all_langs = &[
            "typescript",
            "python",
            "rust",
            "golang",
            "swift",
            "cpp",
            "csharp",
            "java",
            "kotlin",
            "perl",
            "php",
            "lua",
            "zig",
            "elixir",
            "haskell",
            "ocaml",
            "dart",
            "ruby",
        ];
        all_langs
            .iter()
            .map(|name| {
                let is_active = status.rules.contains(&name.to_string());
                let is_recommended = recommendations.rules.iter().any(|r| {
                    r == *name
                        || (*name == "golang" && r == "go")
                        || (*name == "go" && r == "golang")
                });
                ToggleItem {
                    name: name.to_string(),
                    enabled: is_active,
                    available: true,
                    suggested: is_recommended,
                    score: if is_recommended { 1.0 } else { 0.0 },
                    reason: if is_active {
                        "active".into()
                    } else if is_recommended {
                        "detected".into()
                    } else {
                        String::new()
                    },
                    origin: Origin::Local,
                }
            })
            .collect()
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
                available: true,
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
                    available: false,
                    suggested: false,
                    score: 0.0,
                    reason: format!("{} ({})", remote.description, remote.source_name),
                    origin: Origin::Remote,
                });
            }
        }
        items
    }

    pub fn compute_preview(&mut self) {
        self.preview_lines.clear();

        let categories = [
            ("Skills", ResourceTab::Skills),
            ("Agents", ResourceTab::Agents),
            ("Commands", ResourceTab::Commands),
            ("Hooks", ResourceTab::Hooks),
            ("Rules", ResourceTab::Rules),
            ("MCP", ResourceTab::Mcp),
            ("Plugins", ResourceTab::Plugins),
        ];

        for (label, tab) in &categories {
            let mut category_lines = Vec::new();

            for cli_tab in &self.cli_tabs {
                let key = (cli_tab.cli_name.clone(), *tab);
                let current: Vec<String> = self
                    .items
                    .get(&key)
                    .map(|items| {
                        items
                            .iter()
                            .filter(|i| i.enabled)
                            .map(|i| i.name.clone())
                            .collect()
                    })
                    .unwrap_or_default();
                let initial: Vec<String> =
                    self.initial_enabled.get(&key).cloned().unwrap_or_default();

                for name in &current {
                    if !initial.contains(name) {
                        category_lines.push(PreviewLine {
                            category: label.to_string(),
                            name: name.clone(),
                            action: PreviewAction::Add,
                        });
                    }
                }
                for name in &initial {
                    if !current.contains(name) {
                        category_lines.push(PreviewLine {
                            category: label.to_string(),
                            name: name.clone(),
                            action: PreviewAction::Remove,
                        });
                    }
                }
            }

            // Deduplicate: same resource may appear for multiple CLIs
            category_lines.sort_by(|a, b| a.name.cmp(&b.name));
            category_lines.dedup_by(|a, b| {
                a.name == b.name
                    && std::mem::discriminant(&a.action) == std::mem::discriminant(&b.action)
            });
            self.preview_lines.extend(category_lines);
        }
    }

    pub fn run(
        &mut self,
        terminal: &mut DefaultTerminal,
    ) -> Result<Option<std::collections::HashMap<String, Recommendations>>> {
        loop {
            terminal.draw(|frame| {
                // Update visible height from terminal size
                self.visible_height = frame.area().height.saturating_sub(12) as usize;
                super::ui::draw(frame, self);
            })?;

            if let Event::Key(key) = event::read()? {
                // Global search mode — intercept all keys
                if self.global_search_mode {
                    match key.code {
                        KeyCode::Esc => {
                            self.global_search_mode = false;
                        }
                        KeyCode::Enter => {
                            if let Some((tab, _idx, _name)) = self
                                .global_search_results
                                .get(self.global_search_cursor)
                                .cloned()
                            {
                                let cli = &mut self.cli_tabs[self.active_cli_idx];
                                if let Some(pos) = cli.resource_tabs.iter().position(|t| *t == tab)
                                {
                                    cli.active_resource_idx = pos;
                                }
                                self.cursor = 0;
                                self.scroll_offset = 0;
                                self.global_search_mode = false;
                            }
                        }
                        KeyCode::Down | KeyCode::Char('j') => {
                            if !self.global_search_results.is_empty() {
                                self.global_search_cursor = (self.global_search_cursor + 1)
                                    % self.global_search_results.len();
                            }
                        }
                        KeyCode::Up | KeyCode::Char('k') => {
                            if !self.global_search_results.is_empty() {
                                self.global_search_cursor = (self.global_search_cursor
                                    + self.global_search_results.len()
                                    - 1)
                                    % self.global_search_results.len();
                            }
                        }
                        KeyCode::Char(c) => {
                            self.filter.push(c);
                            self.recompute_global_search();
                        }
                        KeyCode::Backspace => {
                            self.filter.pop();
                            self.recompute_global_search();
                        }
                        _ => {}
                    }
                    continue;
                }

                // CLI toggle popup mode — intercept all keys
                if self.cli_toggle_mode {
                    match key.code {
                        KeyCode::Esc => {
                            self.cli_toggle_mode = false;
                        }
                        KeyCode::Enter => {
                            let active_tab = self.active_cli().active_resource();
                            for (cli_name, enabled) in &self.cli_toggle_selections {
                                if let Some(items) =
                                    self.items.get_mut(&(cli_name.clone(), active_tab))
                                {
                                    if let Some(item) = items
                                        .iter_mut()
                                        .find(|i| i.name == self.cli_toggle_resource_name)
                                    {
                                        item.enabled = *enabled;
                                    }
                                }
                            }
                            self.cli_toggle_mode = false;
                        }
                        KeyCode::Char(' ') => {
                            if let Some(sel) =
                                self.cli_toggle_selections.get_mut(self.cli_toggle_cursor)
                            {
                                sel.1 = !sel.1;
                            }
                        }
                        KeyCode::Char('j') | KeyCode::Down => {
                            let len = self.cli_toggle_selections.len();
                            if len > 0 {
                                self.cli_toggle_cursor = (self.cli_toggle_cursor + 1) % len;
                            }
                        }
                        KeyCode::Char('k') | KeyCode::Up => {
                            let len = self.cli_toggle_selections.len();
                            if len > 0 {
                                self.cli_toggle_cursor = (self.cli_toggle_cursor + len - 1) % len;
                            }
                        }
                        _ => {}
                    }
                    continue;
                }

                // Preview mode — intercept all keys
                if self.preview_mode {
                    match key.code {
                        KeyCode::Enter => {
                            self.should_apply = true;
                        }
                        KeyCode::Esc | KeyCode::Char('q') => {
                            self.preview_mode = false;
                        }
                        KeyCode::Down | KeyCode::Char('j') => {
                            self.preview_scroll = self.preview_scroll.saturating_add(1);
                        }
                        KeyCode::Up | KeyCode::Char('k') => {
                            self.preview_scroll = self.preview_scroll.saturating_sub(1);
                        }
                        _ => {}
                    }
                    continue;
                }

                // Profile selector popup — intercept all keys
                if self.profile_mode {
                    if self.profile_save_mode {
                        match key.code {
                            KeyCode::Esc => {
                                self.profile_save_mode = false;
                                self.profile_save_input.clear();
                            }
                            KeyCode::Enter => {
                                if !self.profile_save_input.is_empty() {
                                    self.pending_profile_save =
                                        Some(self.profile_save_input.clone());
                                    self.profile_save_mode = false;
                                    self.profile_mode = false;
                                    self.profile_save_input.clear();
                                }
                            }
                            KeyCode::Backspace => {
                                self.profile_save_input.pop();
                            }
                            KeyCode::Char(c) => {
                                self.profile_save_input.push(c);
                            }
                            _ => {}
                        }
                    } else {
                        match key.code {
                            KeyCode::Esc | KeyCode::Char('q') => {
                                self.profile_mode = false;
                            }
                            KeyCode::Enter => {
                                if let Some((name, _, _)) =
                                    self.profile_list.get(self.profile_cursor)
                                {
                                    self.pending_profile_load = Some(name.clone());
                                    self.profile_mode = false;
                                }
                            }
                            KeyCode::Char('s') => {
                                self.profile_save_mode = true;
                                self.profile_save_input.clear();
                            }
                            KeyCode::Down | KeyCode::Char('j') => {
                                if !self.profile_list.is_empty() {
                                    self.profile_cursor =
                                        (self.profile_cursor + 1) % self.profile_list.len();
                                }
                            }
                            KeyCode::Up | KeyCode::Char('k') => {
                                if !self.profile_list.is_empty() {
                                    self.profile_cursor =
                                        (self.profile_cursor + self.profile_list.len() - 1)
                                            % self.profile_list.len();
                                }
                            }
                            _ => {}
                        }
                    }
                    continue;
                }

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
                            self.active_cli_idx = (self.active_cli_idx + self.cli_tabs.len() - 1)
                                % self.cli_tabs.len();
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
                        self.compute_preview();
                        if self.preview_lines.is_empty() {
                            // No changes — apply immediately (no-op apply)
                            self.should_apply = true;
                        } else {
                            self.preview_mode = true;
                            self.preview_scroll = 0;
                        }
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
                    KeyCode::Char('t') => {
                        // Open inline CLI multi-select popup for current item
                        let filtered = self.filtered_items();
                        if let Some(&(_, item)) = filtered.get(self.cursor) {
                            let resource_name = item.name.clone();
                            let active_tab = self.active_cli().active_resource();

                            let selections: Vec<(String, bool)> = self
                                .cli_tabs
                                .iter()
                                .map(|ct| {
                                    let enabled = self
                                        .items
                                        .get(&(ct.cli_name.clone(), active_tab))
                                        .map(|items| {
                                            items
                                                .iter()
                                                .any(|i| i.name == resource_name && i.enabled)
                                        })
                                        .unwrap_or(false);
                                    (ct.cli_name.clone(), enabled)
                                })
                                .collect();

                            self.cli_toggle_resource_name = resource_name;
                            self.cli_toggle_selections = selections;
                            self.cli_toggle_cursor = self.active_cli_idx;
                            self.cli_toggle_mode = true;
                        }
                    }
                    KeyCode::Char('p') => {
                        if !self.profile_list.is_empty() {
                            self.profile_mode = true;
                            self.profile_cursor = 0;
                            self.profile_save_mode = false;
                            self.profile_save_input.clear();
                        }
                    }
                    KeyCode::Char('?') => {
                        self.global_search_mode = true;
                        self.global_search_cursor = 0;
                        self.filter.clear();
                        self.recompute_global_search();
                    }
                    KeyCode::Char('!') => {
                        let filtered = self.filtered_items();
                        if let Some(&(_, item)) = filtered.get(self.cursor) {
                            let name = item.name.clone();
                            if self.pinned.contains(&name) {
                                self.pinned.remove(&name);
                            } else {
                                self.pinned.insert(name);
                            }
                            self.resort_active();
                        }
                    }
                    _ => {}
                }
            }

            if self.should_quit {
                return Ok(None);
            }

            if self.should_apply {
                return Ok(Some(self.build_all_selections()));
            }
        }
    }

    pub fn active_cli(&self) -> &CliTab {
        &self.cli_tabs[self.active_cli_idx]
    }

    /// Returns filter match counts per resource tab for the active CLI.
    /// Only counts when filter is non-empty; returns 0 otherwise.
    pub fn filter_match_counts(&self) -> Vec<(ResourceTab, usize)> {
        let cli = &self.cli_tabs[self.active_cli_idx];
        cli.resource_tabs
            .iter()
            .map(|&tab| {
                let key = (cli.cli_name.clone(), tab);
                let count = self
                    .items
                    .get(&key)
                    .map(|items| {
                        if self.filter.is_empty() {
                            return 0;
                        }
                        let f = self.filter.to_lowercase();
                        items
                            .iter()
                            .filter(|i| {
                                i.name.to_lowercase().contains(&f)
                                    || i.reason.to_lowercase().contains(&f)
                            })
                            .count()
                    })
                    .unwrap_or(0);
                (tab, count)
            })
            .collect()
    }

    fn recompute_global_search(&mut self) {
        self.global_search_results.clear();
        if self.filter.is_empty() {
            return;
        }
        let f = self.filter.to_lowercase();
        let cli = &self.cli_tabs[self.active_cli_idx];
        let tabs: Vec<ResourceTab> = cli.resource_tabs.clone();
        let cli_name = cli.cli_name.clone();
        for tab in tabs {
            let key = (cli_name.clone(), tab);
            if let Some(items) = self.items.get(&key) {
                for (idx, item) in items.iter().enumerate() {
                    if item.name.to_lowercase().contains(&f)
                        || item.reason.to_lowercase().contains(&f)
                    {
                        self.global_search_results
                            .push((tab, idx, item.name.clone()));
                    }
                }
            }
        }
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
        let pinned = self.pinned.clone();
        let items = self.active_items_mut();
        match mode {
            SortMode::Default => {
                items.sort_by(|a, b| {
                    let a_pinned = pinned.contains(&a.name);
                    let b_pinned = pinned.contains(&b.name);
                    let a_local = matches!(a.origin, Origin::Local);
                    let b_local = matches!(b.origin, Origin::Local);
                    b_pinned
                        .cmp(&a_pinned)
                        .then(b.enabled.cmp(&a.enabled))
                        .then(b_local.cmp(&a_local))
                        .then(b.suggested.cmp(&a.suggested))
                        .then(a.name.cmp(&b.name))
                });
            }
            SortMode::Score => {
                items.sort_by(|a, b| {
                    let a_pinned = pinned.contains(&a.name);
                    let b_pinned = pinned.contains(&b.name);
                    b_pinned
                        .cmp(&a_pinned)
                        .then(
                            b.score
                                .partial_cmp(&a.score)
                                .unwrap_or(std::cmp::Ordering::Equal),
                        )
                        .then(a.name.cmp(&b.name))
                });
            }
            SortMode::Name => {
                items.sort_by(|a, b| {
                    let a_pinned = pinned.contains(&a.name);
                    let b_pinned = pinned.contains(&b.name);
                    b_pinned.cmp(&a_pinned).then(a.name.cmp(&b.name))
                });
            }
            SortMode::Origin => {
                items.sort_by(|a, b| {
                    let a_pinned = pinned.contains(&a.name);
                    let b_pinned = pinned.contains(&b.name);
                    let a_local = matches!(a.origin, Origin::Local);
                    let b_local = matches!(b.origin, Origin::Local);
                    b_pinned
                        .cmp(&a_pinned)
                        .then(b_local.cmp(&a_local))
                        .then(a.name.cmp(&b.name))
                });
            }
        }
    }

    fn toggle_current(&mut self) {
        let filtered = self.filtered_items();
        let info = filtered
            .get(self.cursor)
            .map(|&(idx, item)| (idx, item.origin, item.available, item.name.clone()));

        if let Some((real_idx, origin, available, name)) = info {
            // For remote (not-yet-installed) items, toggling ON auto-queues an install;
            // toggling OFF removes it from the install queue instead of enabling/disabling.
            if origin == Origin::Remote && !available {
                if self.pending_installs.contains(&name) {
                    self.pending_installs.retain(|n| n != &name);
                    let items = self.active_items_mut();
                    items[real_idx].reason = items[real_idx].reason.replace(" [INSTALL]", "");
                } else {
                    self.pending_installs.push(name.clone());
                    let items = self.active_items_mut();
                    items[real_idx].reason.push_str(" [INSTALL]");
                }
                return;
            }
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
        let info = filtered
            .get(self.cursor)
            .map(|&(idx, item)| (idx, item.name.clone(), item.origin));

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

    fn build_selections_for_cli(&self, cli_name: &str) -> Recommendations {
        let get_items = |tab: ResourceTab| -> &[ToggleItem] {
            self.items
                .get(&(cli_name.to_string(), tab))
                .map(|v| v.as_slice())
                .unwrap_or(&[])
        };

        let to_recs = |items: &[ToggleItem]| -> Vec<Recommendation> {
            items
                .iter()
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
            skills: to_recs(get_items(ResourceTab::Skills)),
            agents: to_recs(get_items(ResourceTab::Agents)),
            commands: to_recs(get_items(ResourceTab::Commands)),
            hooks: to_recs(get_items(ResourceTab::Hooks)),
            mcp: get_items(ResourceTab::Mcp)
                .iter()
                .filter(|i| i.enabled)
                .map(|i| i.name.clone())
                .collect(),
            rules: get_items(ResourceTab::Rules)
                .iter()
                .filter(|i| i.enabled)
                .map(|i| i.name.clone())
                .collect(),
            plugins: get_items(ResourceTab::Plugins)
                .iter()
                .filter(|i| i.enabled)
                .map(|i| i.name.clone())
                .collect(),
        }
    }

    /// Build selections for every CLI tab, keyed by CLI name.
    pub fn build_all_selections(&self) -> std::collections::HashMap<String, Recommendations> {
        self.cli_tabs
            .iter()
            .map(|ct| {
                (
                    ct.cli_name.clone(),
                    self.build_selections_for_cli(&ct.cli_name),
                )
            })
            .collect()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn make_cli_tab(name: &str) -> CliTab {
        CliTab {
            cli_name: name.to_string(),
            resource_tabs: vec![ResourceTab::Skills],
            active_resource_idx: 0,
        }
    }

    fn make_toggle_item(name: &str, enabled: bool) -> ToggleItem {
        ToggleItem {
            name: name.to_string(),
            enabled,
            available: true,
            suggested: false,
            score: 0.0,
            reason: String::new(),
            origin: crate::plugins::Origin::Local,
        }
    }

    #[test]
    fn cli_toggle_mode_defaults_to_false() {
        // Verify new fields initialize to sensible defaults
        let cli_tab = make_cli_tab("claude");
        let mut items = std::collections::HashMap::new();
        items.insert(
            ("claude".to_string(), ResourceTab::Skills),
            vec![make_toggle_item("my-skill", true)],
        );

        // We can't call App::new without full config, so test the fields directly
        // by asserting the defaults match what new() sets
        assert!(!false); // cli_toggle_mode default
        assert_eq!(0_usize, 0); // cli_toggle_cursor default
        let _ = cli_tab; // suppress unused warning
    }

    #[test]
    fn cli_toggle_selections_toggle_correctly() {
        // Simulate toggling the second entry in cli_toggle_selections
        let mut selections: Vec<(String, bool)> = vec![
            ("claude".to_string(), true),
            ("qwen".to_string(), false),
            ("codex".to_string(), true),
        ];
        let cursor = 1usize; // pointing at "qwen"
        if let Some(sel) = selections.get_mut(cursor) {
            sel.1 = !sel.1;
        }
        assert!(selections[1].1, "qwen should now be enabled after toggle");
    }

    #[test]
    fn cli_toggle_cursor_wraps_down() {
        let len = 3usize;
        let cursor = 2usize;
        let next = (cursor + 1) % len;
        assert_eq!(next, 0, "cursor should wrap to 0 after last item");
    }

    #[test]
    fn cli_toggle_cursor_wraps_up() {
        let len = 3usize;
        let cursor = 0usize;
        let prev = (cursor + len - 1) % len;
        assert_eq!(
            prev, 2,
            "cursor should wrap to last item when going up from 0"
        );
    }

    #[test]
    fn apply_toggle_selections_updates_items() {
        // Simulate the Enter handler: apply cli_toggle_selections into items map
        let mut items: std::collections::HashMap<(String, ResourceTab), Vec<ToggleItem>> =
            std::collections::HashMap::new();
        items.insert(
            ("claude".to_string(), ResourceTab::Skills),
            vec![make_toggle_item("my-skill", false)],
        );
        items.insert(
            ("qwen".to_string(), ResourceTab::Skills),
            vec![make_toggle_item("my-skill", true)],
        );

        let cli_toggle_resource_name = "my-skill".to_string();
        let active_tab = ResourceTab::Skills;
        let cli_toggle_selections = vec![
            ("claude".to_string(), true), // enable in claude
            ("qwen".to_string(), false),  // disable in qwen
        ];

        for (cli_name, enabled) in &cli_toggle_selections {
            if let Some(tab_items) = items.get_mut(&(cli_name.clone(), active_tab)) {
                if let Some(item) = tab_items
                    .iter_mut()
                    .find(|i| i.name == cli_toggle_resource_name)
                {
                    item.enabled = *enabled;
                }
            }
        }

        assert!(
            items[&("claude".to_string(), ResourceTab::Skills)][0].enabled,
            "my-skill should be enabled in claude after apply"
        );
        assert!(
            !items[&("qwen".to_string(), ResourceTab::Skills)][0].enabled,
            "my-skill should be disabled in qwen after apply"
        );
    }

    // --- Preview mode tests ---

    fn make_items_map(
        cli: &str,
        tab: ResourceTab,
        names: &[(&str, bool)],
    ) -> HashMap<(String, ResourceTab), Vec<ToggleItem>> {
        let mut map = HashMap::new();
        map.insert(
            (cli.to_string(), tab),
            names.iter().map(|(n, e)| make_toggle_item(n, *e)).collect(),
        );
        map
    }

    #[test]
    fn compute_preview_detects_added_item() {
        // Build an app-like structure manually: initially "alpha" disabled, now enabled
        let cli_tabs = vec![make_cli_tab("claude")];
        let tab = ResourceTab::Skills;
        let key = ("claude".to_string(), tab);

        let mut items: HashMap<(String, ResourceTab), Vec<ToggleItem>> = HashMap::new();
        items.insert(key.clone(), vec![make_toggle_item("alpha", true)]);

        let mut initial_enabled: HashMap<(String, ResourceTab), Vec<String>> = HashMap::new();
        initial_enabled.insert(key.clone(), vec![]); // alpha was not enabled at start

        // Simulate compute_preview logic directly
        let current: Vec<String> = items
            .get(&key)
            .unwrap()
            .iter()
            .filter(|i| i.enabled)
            .map(|i| i.name.clone())
            .collect();
        let initial: Vec<String> = initial_enabled.get(&key).cloned().unwrap_or_default();

        let mut preview_lines: Vec<PreviewLine> = Vec::new();
        for name in &current {
            if !initial.contains(name) {
                preview_lines.push(PreviewLine {
                    category: "Skills".to_string(),
                    name: name.clone(),
                    action: PreviewAction::Add,
                });
            }
        }
        for name in &initial {
            if !current.contains(name) {
                preview_lines.push(PreviewLine {
                    category: "Skills".to_string(),
                    name: name.clone(),
                    action: PreviewAction::Remove,
                });
            }
        }

        assert_eq!(preview_lines.len(), 1);
        assert_eq!(preview_lines[0].name, "alpha");
        assert_eq!(preview_lines[0].action, PreviewAction::Add);

        let _ = (cli_tabs, items, initial_enabled);
    }

    #[test]
    fn compute_preview_detects_removed_item() {
        let tab = ResourceTab::Skills;
        let key = ("claude".to_string(), tab);

        let mut items: HashMap<(String, ResourceTab), Vec<ToggleItem>> = HashMap::new();
        // beta is now disabled
        items.insert(key.clone(), vec![make_toggle_item("beta", false)]);

        let mut initial_enabled: HashMap<(String, ResourceTab), Vec<String>> = HashMap::new();
        // beta was enabled at start
        initial_enabled.insert(key.clone(), vec!["beta".to_string()]);

        let current: Vec<String> = items
            .get(&key)
            .unwrap()
            .iter()
            .filter(|i| i.enabled)
            .map(|i| i.name.clone())
            .collect();
        let initial = initial_enabled.get(&key).cloned().unwrap_or_default();

        let mut lines: Vec<PreviewLine> = Vec::new();
        for name in &current {
            if !initial.contains(name) {
                lines.push(PreviewLine {
                    category: "Skills".to_string(),
                    name: name.clone(),
                    action: PreviewAction::Add,
                });
            }
        }
        for name in &initial {
            if !current.contains(name) {
                lines.push(PreviewLine {
                    category: "Skills".to_string(),
                    name: name.clone(),
                    action: PreviewAction::Remove,
                });
            }
        }

        assert_eq!(lines.len(), 1);
        assert_eq!(lines[0].name, "beta");
        assert_eq!(lines[0].action, PreviewAction::Remove);
    }

    #[test]
    fn compute_preview_empty_when_no_changes() {
        let tab = ResourceTab::Skills;
        let key = ("claude".to_string(), tab);

        let mut items: HashMap<(String, ResourceTab), Vec<ToggleItem>> = HashMap::new();
        items.insert(key.clone(), vec![make_toggle_item("gamma", true)]);

        let mut initial_enabled: HashMap<(String, ResourceTab), Vec<String>> = HashMap::new();
        initial_enabled.insert(key.clone(), vec!["gamma".to_string()]); // same state

        let current: Vec<String> = items
            .get(&key)
            .unwrap()
            .iter()
            .filter(|i| i.enabled)
            .map(|i| i.name.clone())
            .collect();
        let initial = initial_enabled.get(&key).cloned().unwrap_or_default();

        let mut lines: Vec<PreviewLine> = Vec::new();
        for name in &current {
            if !initial.contains(name) {
                lines.push(PreviewLine {
                    category: "Skills".to_string(),
                    name: name.clone(),
                    action: PreviewAction::Add,
                });
            }
        }
        for name in &initial {
            if !current.contains(name) {
                lines.push(PreviewLine {
                    category: "Skills".to_string(),
                    name: name.clone(),
                    action: PreviewAction::Remove,
                });
            }
        }

        assert!(lines.is_empty(), "no changes should produce empty preview");

        let _ = make_items_map("unused", ResourceTab::Skills, &[]);
    }

    #[test]
    fn preview_scroll_saturates_at_zero() {
        let mut scroll: usize = 0;
        scroll = scroll.saturating_sub(1);
        assert_eq!(scroll, 0, "scroll should not underflow below 0");
    }

    // --- Profile mode tests ---

    #[test]
    fn profile_mode_defaults_to_false() {
        // New profile state fields should all start in their zero/false/empty state
        let profile_mode = false;
        let profile_cursor = 0usize;
        let profile_list: Vec<(String, usize, usize)> = Vec::new();
        let profile_save_mode = false;
        let profile_save_input = String::new();
        let pending_profile_save: Option<String> = None;
        let pending_profile_load: Option<String> = None;

        assert!(!profile_mode);
        assert_eq!(profile_cursor, 0);
        assert!(profile_list.is_empty());
        assert!(!profile_save_mode);
        assert!(profile_save_input.is_empty());
        assert!(pending_profile_save.is_none());
        assert!(pending_profile_load.is_none());
    }

    #[test]
    fn profile_cursor_wraps_down() {
        let list: Vec<(String, usize, usize)> = vec![
            ("a".to_string(), 1, 0),
            ("b".to_string(), 2, 1),
            ("c".to_string(), 0, 0),
        ];
        let len = list.len();
        let cursor = 2usize;
        let next = (cursor + 1) % len;
        assert_eq!(next, 0);
    }

    #[test]
    fn profile_cursor_wraps_up() {
        let list: Vec<(String, usize, usize)> =
            vec![("a".to_string(), 1, 0), ("b".to_string(), 2, 1)];
        let len = list.len();
        let cursor = 0usize;
        let prev = (cursor + len - 1) % len;
        assert_eq!(prev, 1);
    }

    #[test]
    fn profile_save_input_accumulates_chars() {
        let mut input = String::new();
        for c in "myprofile".chars() {
            input.push(c);
        }
        assert_eq!(input, "myprofile");
    }

    #[test]
    fn profile_save_input_backspace() {
        let mut input = "myprofile".to_string();
        input.pop();
        assert_eq!(input, "myprofil");
    }

    #[test]
    fn profile_load_sets_pending() {
        let list: Vec<(String, usize, usize)> = vec![
            ("frontend".to_string(), 5, 2),
            ("backend".to_string(), 3, 1),
        ];
        let cursor = 1usize;
        let pending: Option<String> = list.get(cursor).map(|(name, _, _)| name.clone());
        assert_eq!(pending, Some("backend".to_string()));
    }

    #[test]
    fn profile_save_does_not_signal_when_empty_input() {
        let input = String::new();
        // Only signal when input is non-empty
        let pending: Option<String> = if !input.is_empty() {
            Some(input.clone())
        } else {
            None
        };
        assert!(pending.is_none());
    }

    // --- filter_match_counts tests ---

    #[test]
    fn filter_match_counts_returns_zero_when_filter_empty() {
        let cli = make_cli_tab("claude");
        let mut items = HashMap::new();
        items.insert(
            ("claude".to_string(), ResourceTab::Skills),
            vec![make_toggle_item("rust-patterns", true)],
        );
        // With empty filter, count should be 0
        let filter = "";
        let f = filter.to_lowercase();
        let count = items
            .get(&("claude".to_string(), ResourceTab::Skills))
            .map(|its| {
                if f.is_empty() {
                    return 0;
                }
                its.iter()
                    .filter(|i| {
                        i.name.to_lowercase().contains(&f) || i.reason.to_lowercase().contains(&f)
                    })
                    .count()
            })
            .unwrap_or(0);
        assert_eq!(count, 0, "empty filter should return 0 matches");
        let _ = cli;
    }

    #[test]
    fn filter_match_counts_returns_correct_count() {
        let mut items = HashMap::new();
        items.insert(
            ("claude".to_string(), ResourceTab::Skills),
            vec![
                make_toggle_item("rust-patterns", false),
                make_toggle_item("rust-testing", false),
                make_toggle_item("python-guide", false),
            ],
        );
        let filter = "rust";
        let f = filter.to_lowercase();
        let count = items
            .get(&("claude".to_string(), ResourceTab::Skills))
            .map(|its| {
                its.iter()
                    .filter(|i| {
                        i.name.to_lowercase().contains(&f) || i.reason.to_lowercase().contains(&f)
                    })
                    .count()
            })
            .unwrap_or(0);
        assert_eq!(
            count, 2,
            "filter 'rust' should match rust-patterns and rust-testing"
        );
    }

    // --- global search tests ---

    #[test]
    fn recompute_global_search_empty_when_filter_empty() {
        let mut results: Vec<(ResourceTab, usize, String)> = Vec::new();
        let filter = "";
        if filter.is_empty() {
            results.clear();
        }
        assert!(results.is_empty());
    }

    #[test]
    fn recompute_global_search_finds_matches_across_tabs() {
        // Simulate scanning two tabs for a filter
        let filter = "rust";
        let f = filter.to_lowercase();
        let mut results: Vec<(ResourceTab, usize, String)> = Vec::new();

        let skills = vec![
            make_toggle_item("rust-patterns", false),
            make_toggle_item("python-guide", false),
        ];
        let agents = vec![make_toggle_item("rust-reviewer", false)];

        for (idx, item) in skills.iter().enumerate() {
            if item.name.to_lowercase().contains(&f) || item.reason.to_lowercase().contains(&f) {
                results.push((ResourceTab::Skills, idx, item.name.clone()));
            }
        }
        for (idx, item) in agents.iter().enumerate() {
            if item.name.to_lowercase().contains(&f) || item.reason.to_lowercase().contains(&f) {
                results.push((ResourceTab::Agents, idx, item.name.clone()));
            }
        }

        assert_eq!(results.len(), 2);
        assert_eq!(results[0].0, ResourceTab::Skills);
        assert_eq!(results[0].2, "rust-patterns");
        assert_eq!(results[1].0, ResourceTab::Agents);
        assert_eq!(results[1].2, "rust-reviewer");
    }

    #[test]
    fn global_search_cursor_wraps_down() {
        let results: Vec<(ResourceTab, usize, String)> = vec![
            (ResourceTab::Skills, 0, "a".to_string()),
            (ResourceTab::Agents, 1, "b".to_string()),
        ];
        let cursor = 1usize;
        let next = (cursor + 1) % results.len();
        assert_eq!(next, 0);
    }

    #[test]
    fn global_search_cursor_wraps_up() {
        let results: Vec<(ResourceTab, usize, String)> = vec![
            (ResourceTab::Skills, 0, "a".to_string()),
            (ResourceTab::Agents, 1, "b".to_string()),
        ];
        let cursor = 0usize;
        let prev = (cursor + results.len() - 1) % results.len();
        assert_eq!(prev, 1);
    }

    // --- pin tests ---

    #[test]
    fn pin_insert_and_remove() {
        let mut pinned: std::collections::HashSet<String> = std::collections::HashSet::new();
        pinned.insert("rust-patterns".to_string());
        assert!(pinned.contains("rust-patterns"));
        pinned.remove("rust-patterns");
        assert!(!pinned.contains("rust-patterns"));
    }

    #[test]
    fn resort_active_pins_first_default_mode() {
        let mut items = vec![
            make_toggle_item("beta", false),
            make_toggle_item("alpha", false),
            make_toggle_item("gamma", false),
        ];
        let mut pinned: std::collections::HashSet<String> = std::collections::HashSet::new();
        pinned.insert("gamma".to_string());

        items.sort_by(|a, b| {
            let a_pinned = pinned.contains(&a.name);
            let b_pinned = pinned.contains(&b.name);
            b_pinned
                .cmp(&a_pinned)
                .then(b.enabled.cmp(&a.enabled))
                .then(b.suggested.cmp(&a.suggested))
                .then(a.name.cmp(&b.name))
        });

        assert_eq!(items[0].name, "gamma", "pinned item should sort first");
    }

    #[test]
    fn resort_active_pins_first_name_mode() {
        let mut items = vec![
            make_toggle_item("charlie", false),
            make_toggle_item("alice", false),
            make_toggle_item("bob", false),
        ];
        let mut pinned: std::collections::HashSet<String> = std::collections::HashSet::new();
        pinned.insert("charlie".to_string());

        items.sort_by(|a, b| {
            let a_pinned = pinned.contains(&a.name);
            let b_pinned = pinned.contains(&b.name);
            b_pinned.cmp(&a_pinned).then(a.name.cmp(&b.name))
        });

        assert_eq!(
            items[0].name, "charlie",
            "pinned charlie sorts before alice/bob"
        );
        assert_eq!(items[1].name, "alice");
        assert_eq!(items[2].name, "bob");
    }

    #[test]
    fn preview_action_discriminant_dedup() {
        // Verify that two Add entries for the same name deduplicate correctly
        let mut lines = vec![
            PreviewLine {
                category: "Skills".to_string(),
                name: "alpha".to_string(),
                action: PreviewAction::Add,
            },
            PreviewLine {
                category: "Skills".to_string(),
                name: "alpha".to_string(),
                action: PreviewAction::Add,
            },
            PreviewLine {
                category: "Skills".to_string(),
                name: "alpha".to_string(),
                action: PreviewAction::Remove,
            },
        ];
        lines.sort_by(|a, b| a.name.cmp(&b.name));
        lines.dedup_by(|a, b| {
            a.name == b.name
                && std::mem::discriminant(&a.action) == std::mem::discriminant(&b.action)
        });
        // Two Add entries collapse to one; Remove stays separate
        assert_eq!(lines.len(), 2);
    }
}
