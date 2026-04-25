//! Resource discovery, caching, and management.
//!
//! Fetches resource listings (skills, agents, commands, plugins) from configured
//! sources (GitHub repos, web catalogs, awesome lists), caches locally, and
//! provides search/install/download.

use anyhow::{bail, Context, Result};
use serde::{Deserialize, Serialize};
use std::path::{Path, PathBuf};
use std::time::{Duration, SystemTime};

#[allow(unused_imports)]
use crate::{debug_log, verbose};

// ── Enums ───────────────────────────────────────────────────────────────

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum ResourceType {
    Skill,
    Agent,
    Command,
    Hook,
    Plugin,
}

impl std::fmt::Display for ResourceType {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            ResourceType::Skill => write!(f, "skill"),
            ResourceType::Agent => write!(f, "agent"),
            ResourceType::Command => write!(f, "command"),
            ResourceType::Hook => write!(f, "hook"),
            ResourceType::Plugin => write!(f, "plugin"),
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Origin {
    Local,
    Remote,
}

impl std::fmt::Display for Origin {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Origin::Local => write!(f, "L"),
            Origin::Remote => write!(f, "R"),
        }
    }
}

// ── Source config (parsed from sources.yaml) ────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SourcesConfig {
    #[serde(default)]
    pub sources: Vec<PluginSource>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PluginSource {
    pub name: String,
    #[serde(rename = "type")]
    pub source_type: SourceType,
    pub repo: Option<String>,
    pub url: Option<String>,
    #[serde(default = "default_refresh")]
    pub refresh: String,
    #[serde(default = "default_resources")]
    pub resources: Vec<ResourceType>,
}

fn default_refresh() -> String {
    "24h".to_string()
}

fn default_resources() -> Vec<ResourceType> {
    vec![ResourceType::Plugin]
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "kebab-case")]
pub enum SourceType {
    GithubMarketplace,
    GithubRepo,
    WebCatalog,
    AwesomeList,
}

impl SourcesConfig {
    pub fn load(config_dir: &Path) -> Result<Self> {
        let path = config_dir.join("sources.yaml");
        if !path.exists() {
            return Ok(Self { sources: vec![] });
        }
        let content = std::fs::read_to_string(&path)
            .with_context(|| format!("Failed to read {}", path.display()))?;
        serde_yaml::from_str(&content).with_context(|| "Failed to parse sources.yaml")
    }
}

// ── Remote resource entry ───────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RemoteResource {
    pub name: String,
    pub description: String,
    pub author: String,
    pub source_name: String,
    pub tags: Vec<String>,
    pub install_id: String,
    #[serde(default = "default_resource_type")]
    pub resource_type: ResourceType,
    /// URL to fetch the actual content from (for download/install)
    #[serde(default)]
    pub download_url: String,
    /// GitHub star count for the source repo (populated when available)
    #[serde(default)]
    pub stars: Option<u32>,
    /// ISO-8601 timestamp of last update (populated when available)
    #[serde(default)]
    pub updated_at: Option<String>,
}

fn default_resource_type() -> ResourceType {
    ResourceType::Plugin
}

// ── Cache ────────────────────────────────────────────────────────────────

pub struct PluginCache {
    cache_dir: PathBuf,
    ttl: Duration,
}

impl PluginCache {
    pub fn new(config_dir: &Path) -> Self {
        Self {
            cache_dir: config_dir.join("plugin-cache"),
            ttl: Duration::from_secs(24 * 3600),
        }
    }

    fn cache_path(&self, source_name: &str) -> PathBuf {
        self.cache_dir.join(format!("{}.json", source_name))
    }

    pub fn is_fresh(&self, source_name: &str) -> bool {
        let path = self.cache_path(source_name);
        if !path.exists() {
            return false;
        }
        path.metadata()
            .and_then(|m| m.modified())
            .map(|mtime| {
                SystemTime::now()
                    .duration_since(mtime)
                    .unwrap_or(Duration::MAX)
                    < self.ttl
            })
            .unwrap_or(false)
    }

    pub fn read(&self, source_name: &str) -> Result<Vec<RemoteResource>> {
        let path = self.cache_path(source_name);
        if !path.exists() {
            return Ok(vec![]);
        }
        let content = std::fs::read_to_string(&path)?;
        serde_json::from_str(&content).with_context(|| "Failed to parse resource cache")
    }

    pub fn write(&self, source_name: &str, entries: &[RemoteResource]) -> Result<()> {
        std::fs::create_dir_all(&self.cache_dir)?;
        let json = serde_json::to_string_pretty(entries)?;
        std::fs::write(self.cache_path(source_name), json)?;
        Ok(())
    }
}

// ── Plugin Manager ──────────────────────────────────────────────────────

pub struct PluginManager {
    sources: Vec<PluginSource>,
    cache: PluginCache,
}

impl PluginManager {
    pub fn new(config_dir: &Path) -> Result<Self> {
        let sources_config = SourcesConfig::load(config_dir)?;
        Ok(Self {
            sources: sources_config.sources,
            cache: PluginCache::new(config_dir),
        })
    }

    /// Return the list of configured sources.
    pub fn list_sources(&self) -> &[PluginSource] {
        &self.sources
    }

    /// Refresh stale source caches (rate-limited: 1s between fetches).
    pub fn refresh(&self) -> Result<()> {
        let mut first = true;
        for source in &self.sources {
            if self.cache.is_fresh(&source.name) {
                verbose!("Cache fresh for source: {}", source.name);
                continue;
            }
            verbose!(
                "Fetching source: {} ({:?})",
                source.name,
                source.source_type
            );
            eprintln!("  Fetching {}...", source.name);
            // Rate limit: wait 1s between fetches to avoid spamming APIs
            if !first {
                std::thread::sleep(std::time::Duration::from_secs(1));
            }
            first = false;
            match fetch_source(source) {
                Ok(entries) => {
                    self.cache.write(&source.name, &entries)?;
                    let mut counts = std::collections::HashMap::new();
                    for e in &entries {
                        *counts.entry(e.resource_type).or_insert(0usize) += 1;
                    }
                    let summary: Vec<String> = counts
                        .iter()
                        .map(|(t, c)| format!("{} {}s", c, t))
                        .collect();
                    eprintln!("Refreshed {} ({})", source.name, summary.join(", "));
                }
                Err(e) => {
                    eprintln!("Warning: failed to fetch {}: {}", source.name, e);
                }
            }
        }
        Ok(())
    }

    /// Return all cached resources across all sources.
    pub fn all_available(&self) -> Result<Vec<RemoteResource>> {
        let mut all = Vec::new();
        for source in &self.sources {
            if let Ok(entries) = self.cache.read(&source.name) {
                all.extend(entries);
            }
        }
        Ok(all)
    }

    /// Fuzzy search by name, description, or tags, with optional sorting.
    ///
    /// `sort` values: `"stars"` (default), `"name"`, `"updated"`, `""` (cache order).
    pub fn search(&self, query: &str, sort: &str) -> Result<Vec<RemoteResource>> {
        let query_lower = query.to_lowercase();
        let all = self.all_available()?;
        let mut results: Vec<RemoteResource> = all
            .into_iter()
            .filter(|e| {
                e.name.to_lowercase().contains(&query_lower)
                    || e.description.to_lowercase().contains(&query_lower)
                    || e.tags
                        .iter()
                        .any(|t| t.to_lowercase().contains(&query_lower))
            })
            .collect();

        match sort {
            "stars" => results.sort_by(|a, b| b.stars.unwrap_or(0).cmp(&a.stars.unwrap_or(0))),
            "name" => results.sort_by(|a, b| a.name.cmp(&b.name)),
            "updated" => results.sort_by(|a, b| b.updated_at.cmp(&a.updated_at)),
            _ => {} // default: preserve cache order
        }

        Ok(results)
    }

    /// Download and install a remote resource to the appropriate local dir.
    pub fn install(
        &self,
        resource: &RemoteResource,
        skills_dir: &Path,
        agents_dir: &Path,
        commands_dir: &Path,
    ) -> Result<()> {
        verbose!(
            "Installing {} ({}) from {}",
            resource.name,
            resource.resource_type,
            resource.source_name
        );
        debug_log!("Download URL: {}", resource.download_url);
        if resource.download_url.is_empty() {
            bail!("No download URL for '{}'. Cannot install.", resource.name);
        }

        let output = std::process::Command::new("curl")
            .args(["-s", "--max-time", "30", "-f", &resource.download_url])
            .output()
            .with_context(|| format!("Failed to download {}", resource.download_url))?;

        if !output.status.success() {
            bail!("Download failed for '{}' (HTTP error)", resource.name);
        }

        let content = String::from_utf8_lossy(&output.stdout);

        match resource.resource_type {
            ResourceType::Skill => {
                let skill_dir = skills_dir.join(&resource.install_id);
                std::fs::create_dir_all(&skill_dir)?;
                std::fs::write(skill_dir.join("SKILL.md"), content.as_ref())?;
                println!(
                    "Installed skill '{}' to {}",
                    resource.name,
                    skill_dir.display()
                );
                println!("  Run `aictx apply` or save/apply a profile to activate it.");
            }
            ResourceType::Agent => {
                std::fs::create_dir_all(agents_dir)?;
                let path = agents_dir.join(format!("{}.md", resource.install_id));
                std::fs::write(&path, content.as_ref())?;
                println!("Installed agent '{}' to {}", resource.name, path.display());
                println!("  Run `aictx apply` or save/apply a profile to activate it.");
            }
            ResourceType::Command => {
                std::fs::create_dir_all(commands_dir)?;
                let path = commands_dir.join(format!("{}.md", resource.install_id));
                std::fs::write(&path, content.as_ref())?;
                println!(
                    "Installed command '{}' to {}",
                    resource.name,
                    path.display()
                );
                println!("  Run `aictx apply` or save/apply a profile to activate it.");
            }
            ResourceType::Hook => {
                println!(
                    "Hook '{}' — hooks are managed via symlinks; place the .sh file in your hooks source dir and run `aictx apply`.",
                    resource.name
                );
            }
            ResourceType::Plugin => {
                println!(
                    "Plugin '{}' — enable via settings.json (no file download needed)",
                    resource.name
                );
            }
        }

        Ok(())
    }

    /// Update all installed remote resources by re-downloading them.
    pub fn update_installed(
        &self,
        skills_dir: &Path,
        agents_dir: &Path,
        commands_dir: &Path,
    ) -> Result<usize> {
        let all = self.all_available()?;
        let mut updated = 0;

        for resource in &all {
            if resource.download_url.is_empty() {
                continue;
            }

            let exists = match resource.resource_type {
                ResourceType::Skill => skills_dir.join(&resource.install_id).exists(),
                ResourceType::Agent => agents_dir
                    .join(format!("{}.md", resource.install_id))
                    .exists(),
                ResourceType::Command => commands_dir
                    .join(format!("{}.md", resource.install_id))
                    .exists(),
                ResourceType::Hook => false,
                ResourceType::Plugin => false,
            };

            if exists {
                match self.install(resource, skills_dir, agents_dir, commands_dir) {
                    Ok(()) => updated += 1,
                    Err(e) => eprintln!("Failed to update '{}': {}", resource.name, e),
                }
                // Rate limit between downloads
                std::thread::sleep(std::time::Duration::from_millis(500));
            }
        }

        Ok(updated)
    }

    /// Uninstall a previously downloaded resource from local dirs.
    pub fn uninstall(
        &self,
        name: &str,
        resource_type: ResourceType,
        skills_dir: &Path,
        agents_dir: &Path,
        commands_dir: &Path,
    ) -> Result<()> {
        match resource_type {
            ResourceType::Skill => {
                let skill_dir = skills_dir.join(name);
                if skill_dir.exists() {
                    std::fs::remove_dir_all(&skill_dir)?;
                    println!("Uninstalled skill '{}'", name);
                    println!("  Note: Run `aictx reset` or re-apply your desired profile to remove active symlinks.");
                } else {
                    bail!("Skill '{}' not found in {}", name, skills_dir.display());
                }
            }
            ResourceType::Agent => {
                let path = agents_dir.join(format!("{}.md", name));
                if path.exists() {
                    std::fs::remove_file(&path)?;
                    println!("Uninstalled agent '{}'", name);
                    println!("  Note: Run `aictx reset` or re-apply your desired profile to remove active symlinks.");
                } else {
                    bail!("Agent '{}' not found in {}", name, agents_dir.display());
                }
            }
            ResourceType::Command => {
                let path = commands_dir.join(format!("{}.md", name));
                if path.exists() {
                    std::fs::remove_file(&path)?;
                    println!("Uninstalled command '{}'", name);
                    println!("  Note: Run `aictx reset` or re-apply your desired profile to remove active symlinks.");
                } else {
                    bail!("Command '{}' not found in {}", name, commands_dir.display());
                }
            }
            ResourceType::Hook => {
                println!(
                    "Hook '{}' — remove the .sh symlink from your CLI hooks dir or run `aictx reset` to clear all symlinks.",
                    name
                );
            }
            ResourceType::Plugin => {
                println!(
                    "Plugin '{}' — disable via settings.json or `aictx plugin disable-all`",
                    name
                );
            }
        }
        Ok(())
    }
}

/// Add a new source to sources.yaml.
pub fn add_source(
    config_dir: &Path,
    name: &str,
    url: &str,
    resource_types: &[ResourceType],
) -> Result<()> {
    let path = config_dir.join("sources.yaml");

    let mut config = if path.exists() {
        SourcesConfig::load(config_dir)?
    } else {
        SourcesConfig { sources: vec![] }
    };

    // Check for duplicate name
    if config.sources.iter().any(|s| s.name == name) {
        bail!("Source '{}' already exists", name);
    }

    // Auto-detect source type from URL
    let (source_type, repo, source_url) = if url.contains("github.com/") {
        let repo = url
            .trim_end_matches('/')
            .rsplit("github.com/")
            .next()
            .unwrap_or(url)
            .to_string();
        (SourceType::GithubRepo, Some(repo), None)
    } else {
        (SourceType::WebCatalog, None, Some(url.to_string()))
    };

    config.sources.push(PluginSource {
        name: name.to_string(),
        source_type,
        repo,
        url: source_url,
        refresh: "24h".to_string(),
        resources: resource_types.to_vec(),
    });

    let yaml = serde_yaml::to_string(&config)?;
    std::fs::write(&path, yaml)?;
    println!("Added source '{}' to {}", name, path.display());
    Ok(())
}

// ── Fetch implementations ───────────────────────────────────────────────

/// Fetch the star count for a GitHub repo (owner/repo).  Returns None on any
/// network or parse failure so callers degrade gracefully.
fn fetch_repo_stars(repo: &str) -> Option<u32> {
    let url = format!("https://api.github.com/repos/{}", repo);
    let output = std::process::Command::new("curl")
        .args([
            "-s",
            "--max-time",
            "3",
            "-H",
            "Accept: application/vnd.github.v3+json",
            &url,
        ])
        .output()
        .ok()?;
    let json: serde_json::Value = serde_json::from_slice(&output.stdout).ok()?;
    json.get("stargazers_count")?.as_u64().map(|n| n as u32)
}

fn fetch_source(source: &PluginSource) -> Result<Vec<RemoteResource>> {
    match source.source_type {
        SourceType::GithubRepo | SourceType::GithubMarketplace => fetch_github_repo(source),
        SourceType::AwesomeList => fetch_awesome_list(source),
        SourceType::WebCatalog => fetch_web_catalog(source),
    }
}

fn fetch_github_repo(source: &PluginSource) -> Result<Vec<RemoteResource>> {
    let repo = source.repo.as_deref().unwrap_or_default();
    if repo.is_empty() {
        return Ok(vec![]);
    }

    // Fetch star count once per repo — applied to all resources from this source.
    let repo_stars = fetch_repo_stars(repo);

    /// Annotate all entries with the repo star count (if not already set).
    fn annotate_stars(mut entries: Vec<RemoteResource>, stars: Option<u32>) -> Vec<RemoteResource> {
        if let Some(s) = stars {
            for e in &mut entries {
                if e.stars.is_none() {
                    e.stars = Some(s);
                }
            }
        }
        entries
    }

    // Try fetching a resources.json manifest from the repo
    let url = format!(
        "https://raw.githubusercontent.com/{}/main/resources.json",
        repo
    );
    let output = std::process::Command::new("curl")
        .args(["-s", "--max-time", "5", "-f", &url])
        .output()
        .with_context(|| format!("Failed to fetch {}", url))?;

    if output.status.success() {
        let text = String::from_utf8_lossy(&output.stdout);
        if let Ok(entries) = serde_json::from_str::<Vec<RemoteResource>>(&text) {
            return Ok(annotate_stars(entries, repo_stars));
        }
    }

    // Fallback: try plugins.json
    let url = format!(
        "https://raw.githubusercontent.com/{}/main/plugins.json",
        repo
    );
    let output = std::process::Command::new("curl")
        .args(["-s", "--max-time", "5", "-f", &url])
        .output()?;

    if output.status.success() {
        let text = String::from_utf8_lossy(&output.stdout);
        if let Ok(entries) = serde_json::from_str::<Vec<RemoteResource>>(&text) {
            return Ok(annotate_stars(entries, repo_stars));
        }
    }

    // Final fallback: fetch README.md and parse
    let readme_url = format!("https://raw.githubusercontent.com/{}/main/README.md", repo);
    let output = std::process::Command::new("curl")
        .args(["-s", "--max-time", "5", "-f", &readme_url])
        .output()?;

    if output.status.success() {
        let text = String::from_utf8_lossy(&output.stdout);
        let entries = parse_markdown_resources(&text, &source.name, &source.resources);
        return Ok(annotate_stars(entries, repo_stars));
    }

    Ok(vec![])
}

fn fetch_awesome_list(source: &PluginSource) -> Result<Vec<RemoteResource>> {
    let repo = source.repo.as_deref().unwrap_or_default();
    if repo.is_empty() {
        return Ok(vec![]);
    }

    let url = format!("https://raw.githubusercontent.com/{}/main/README.md", repo);
    let output = std::process::Command::new("curl")
        .args(["-s", "--max-time", "5", "-f", &url])
        .output()?;

    if output.status.success() {
        let text = String::from_utf8_lossy(&output.stdout);
        return Ok(parse_markdown_resources(
            &text,
            &source.name,
            &source.resources,
        ));
    }

    Ok(vec![])
}

fn fetch_web_catalog(source: &PluginSource) -> Result<Vec<RemoteResource>> {
    let url = source.url.as_deref().unwrap_or_default();
    if url.is_empty() {
        return Ok(vec![]);
    }

    let api_url = format!("{}/api/plugins", url.trim_end_matches('/'));
    let output = std::process::Command::new("curl")
        .args(["-s", "--max-time", "5", "-f", &api_url])
        .output()?;

    if output.status.success() {
        let text = String::from_utf8_lossy(&output.stdout);
        if let Ok(entries) = serde_json::from_str::<Vec<RemoteResource>>(&text) {
            return Ok(entries);
        }
    }

    Ok(vec![])
}

/// Parse markdown for resource entries.
/// Uses the source's `resources` field to tag entries with the appropriate type.
fn parse_markdown_resources(
    markdown: &str,
    source_name: &str,
    resource_types: &[ResourceType],
) -> Vec<RemoteResource> {
    let mut entries = Vec::new();
    let default_type = resource_types
        .first()
        .copied()
        .unwrap_or(ResourceType::Plugin);
    let mut current_type = default_type;

    for line in markdown.lines() {
        let trimmed = line.trim();

        // Detect section headers to infer resource type
        let lower = trimmed.to_lowercase();
        if lower.starts_with('#') {
            if lower.contains("skill") && resource_types.contains(&ResourceType::Skill) {
                current_type = ResourceType::Skill;
            } else if lower.contains("agent") && resource_types.contains(&ResourceType::Agent) {
                current_type = ResourceType::Agent;
            } else if lower.contains("command") && resource_types.contains(&ResourceType::Command) {
                current_type = ResourceType::Command;
            } else if lower.contains("plugin") && resource_types.contains(&ResourceType::Plugin) {
                current_type = ResourceType::Plugin;
            }
            continue;
        }

        // Match: - [Name](url) - Description
        if let Some(rest) = trimmed.strip_prefix("- [") {
            if let Some(bracket_end) = rest.find("](") {
                let name = &rest[..bracket_end];
                let url_start = bracket_end + 2;
                let url_end = rest[url_start..].find(')').map(|i| url_start + i);

                let download_url = url_end
                    .map(|end| rest[url_start..end].to_string())
                    .unwrap_or_default();

                let after_url = url_end.map(|end| &rest[end + 1..]).unwrap_or("");
                let description = after_url
                    .trim()
                    .trim_start_matches('-')
                    .trim_start_matches(':')
                    .trim()
                    .to_string();

                if !name.is_empty() {
                    entries.push(RemoteResource {
                        name: name.to_string(),
                        description,
                        author: String::new(),
                        source_name: source_name.to_string(),
                        tags: vec![],
                        install_id: name.to_lowercase().replace(' ', "-"),
                        resource_type: current_type,
                        download_url,
                        stars: None,
                        updated_at: None,
                    });
                }
            }
        }
    }

    entries
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn sources_config_empty_when_missing() {
        let tmp = std::env::temp_dir().join("cctx-test-plugins-nosrc");
        let _ = std::fs::create_dir_all(&tmp);
        let config = SourcesConfig::load(&tmp).unwrap();
        assert!(config.sources.is_empty());
        let _ = std::fs::remove_dir_all(&tmp);
    }

    #[test]
    fn cache_read_write_roundtrip() {
        let tmp = std::env::temp_dir().join("cctx-test-plugins-cache2");
        let _ = std::fs::remove_dir_all(&tmp);
        let _ = std::fs::create_dir_all(&tmp);
        let cache = PluginCache::new(&tmp);

        let entries = vec![RemoteResource {
            name: "test-plugin".to_string(),
            description: "A test".to_string(),
            author: "tester".to_string(),
            source_name: "test-src".to_string(),
            tags: vec!["rust".to_string()],
            install_id: "test-plugin".to_string(),
            resource_type: ResourceType::Skill,
            download_url: String::new(),
            stars: None,
            updated_at: None,
        }];

        cache.write("test-src", &entries).unwrap();
        assert!(cache.is_fresh("test-src"));

        let loaded = cache.read("test-src").unwrap();
        assert_eq!(loaded.len(), 1);
        assert_eq!(loaded[0].name, "test-plugin");
        assert_eq!(loaded[0].resource_type, ResourceType::Skill);

        let _ = std::fs::remove_dir_all(&tmp);
    }

    #[test]
    fn cache_not_fresh_when_missing() {
        let tmp = std::env::temp_dir().join("cctx-test-plugins-notfresh2");
        let _ = std::fs::create_dir_all(&tmp);
        let cache = PluginCache::new(&tmp);
        assert!(!cache.is_fresh("nonexistent"));
        let _ = std::fs::remove_dir_all(&tmp);
    }

    #[test]
    fn parse_markdown_extracts_typed_entries() {
        let md = r#"
# Skills

- [Code Formatter](https://example.com/formatter.md) - Formats your code
- [Linter](https://example.com/linter.md) - Lints your code

# Agents

- [Reviewer](https://example.com/reviewer.md) - Reviews PRs

# Plugins

- [Theme](https://example.com) - Color theme
"#;
        let types = vec![
            ResourceType::Skill,
            ResourceType::Agent,
            ResourceType::Plugin,
        ];
        let entries = parse_markdown_resources(md, "test", &types);
        assert_eq!(entries.len(), 4);
        assert_eq!(entries[0].resource_type, ResourceType::Skill);
        assert_eq!(entries[1].resource_type, ResourceType::Skill);
        assert_eq!(entries[2].resource_type, ResourceType::Agent);
        assert_eq!(entries[3].resource_type, ResourceType::Plugin);
    }

    #[test]
    fn search_filters_by_name() {
        let tmp = std::env::temp_dir().join("cctx-test-plugins-search2");
        let _ = std::fs::remove_dir_all(&tmp);
        let _ = std::fs::create_dir_all(&tmp);

        let sources_yaml = r#"sources:
  - name: test
    type: github-repo
    repo: example/test
    resources: [skill, plugin]
"#;
        std::fs::write(tmp.join("sources.yaml"), sources_yaml).unwrap();

        let cache_dir = tmp.join("plugin-cache");
        std::fs::create_dir_all(&cache_dir).unwrap();
        let entries = vec![
            RemoteResource {
                name: "rust-analyzer".to_string(),
                description: "Rust language server".to_string(),
                author: "ra".to_string(),
                source_name: "test".to_string(),
                tags: vec!["rust".to_string()],
                install_id: "rust-analyzer".to_string(),
                resource_type: ResourceType::Skill,
                download_url: String::new(),
                stars: None,
                updated_at: None,
            },
            RemoteResource {
                name: "prettier".to_string(),
                description: "Code formatter".to_string(),
                author: "pr".to_string(),
                source_name: "test".to_string(),
                tags: vec!["js".to_string()],
                install_id: "prettier".to_string(),
                resource_type: ResourceType::Plugin,
                download_url: String::new(),
                stars: None,
                updated_at: None,
            },
        ];
        let json = serde_json::to_string(&entries).unwrap();
        std::fs::write(cache_dir.join("test.json"), json).unwrap();

        let pm = PluginManager::new(&tmp).unwrap();
        let results = pm.search("rust", "").unwrap();
        assert_eq!(results.len(), 1);
        assert_eq!(results[0].name, "rust-analyzer");

        let _ = std::fs::remove_dir_all(&tmp);
    }

    #[test]
    fn default_resources_is_plugin() {
        let yaml = r#"sources:
  - name: test
    type: github-repo
    repo: foo/bar
"#;
        let config: SourcesConfig = serde_yaml::from_str(yaml).unwrap();
        assert_eq!(config.sources[0].resources, vec![ResourceType::Plugin]);
    }
}
