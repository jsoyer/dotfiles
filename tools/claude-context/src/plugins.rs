//! Plugin discovery, caching, and management.
//!
//! Fetches plugin listings from configured sources (GitHub repos, web catalogs,
//! awesome lists), caches locally, and provides search/install/uninstall.

use anyhow::{Context, Result};
use serde::{Deserialize, Serialize};
use std::path::{Path, PathBuf};
use std::time::{Duration, SystemTime};

// ── Source config (parsed from sources.yaml) ────────────────────────────

#[derive(Debug, Clone, Deserialize)]
pub struct SourcesConfig {
    #[serde(default)]
    pub sources: Vec<PluginSource>,
}

#[derive(Debug, Clone, Deserialize)]
pub struct PluginSource {
    pub name: String,
    #[serde(rename = "type")]
    pub source_type: SourceType,
    pub repo: Option<String>,
    pub url: Option<String>,
    #[serde(default = "default_refresh")]
    pub refresh: String,
}

fn default_refresh() -> String {
    "24h".to_string()
}

#[derive(Debug, Clone, Deserialize, PartialEq)]
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

// ── Plugin entry (a discovered plugin) ──────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PluginEntry {
    pub name: String,
    pub description: String,
    pub author: String,
    pub source_name: String,
    pub tags: Vec<String>,
    pub install_id: String,
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

    pub fn read(&self, source_name: &str) -> Result<Vec<PluginEntry>> {
        let path = self.cache_path(source_name);
        if !path.exists() {
            return Ok(vec![]);
        }
        let content = std::fs::read_to_string(&path)?;
        serde_json::from_str(&content).with_context(|| "Failed to parse plugin cache")
    }

    pub fn write(&self, source_name: &str, entries: &[PluginEntry]) -> Result<()> {
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

    /// Refresh stale source caches.
    pub fn refresh(&self) -> Result<()> {
        for source in &self.sources {
            if self.cache.is_fresh(&source.name) {
                continue;
            }
            let entries = fetch_source(source);
            match entries {
                Ok(entries) => {
                    self.cache.write(&source.name, &entries)?;
                    eprintln!("Refreshed {} ({} plugins)", source.name, entries.len());
                }
                Err(e) => {
                    eprintln!("Warning: failed to fetch {}: {}", source.name, e);
                }
            }
        }
        Ok(())
    }

    /// Return all cached plugins across all sources.
    pub fn all_available(&self) -> Result<Vec<PluginEntry>> {
        let mut all = Vec::new();
        for source in &self.sources {
            if let Ok(entries) = self.cache.read(&source.name) {
                all.extend(entries);
            }
        }
        Ok(all)
    }

    /// Fuzzy search by name, description, or tags.
    pub fn search(&self, query: &str) -> Result<Vec<PluginEntry>> {
        let query_lower = query.to_lowercase();
        let all = self.all_available()?;
        Ok(all
            .into_iter()
            .filter(|e| {
                e.name.to_lowercase().contains(&query_lower)
                    || e.description.to_lowercase().contains(&query_lower)
                    || e.tags.iter().any(|t| t.to_lowercase().contains(&query_lower))
            })
            .collect())
    }

    /// List configured sources.
    pub fn sources(&self) -> &[PluginSource] {
        &self.sources
    }
}

// ── Fetch implementations ───────────────────────────────────────────────

fn fetch_source(source: &PluginSource) -> Result<Vec<PluginEntry>> {
    match source.source_type {
        SourceType::GithubRepo | SourceType::GithubMarketplace => {
            fetch_github_repo(source)
        }
        SourceType::AwesomeList => fetch_awesome_list(source),
        SourceType::WebCatalog => fetch_web_catalog(source),
    }
}

fn fetch_github_repo(source: &PluginSource) -> Result<Vec<PluginEntry>> {
    let repo = source
        .repo
        .as_deref()
        .unwrap_or_default();
    if repo.is_empty() {
        return Ok(vec![]);
    }

    // Try fetching a plugins.json manifest from the repo
    let url = format!(
        "https://raw.githubusercontent.com/{}/main/plugins.json",
        repo
    );
    let output = std::process::Command::new("curl")
        .args(["-s", "--max-time", "15", "-f", &url])
        .output()
        .with_context(|| format!("Failed to fetch {}", url))?;

    if output.status.success() {
        let text = String::from_utf8_lossy(&output.stdout);
        if let Ok(entries) = serde_json::from_str::<Vec<PluginEntry>>(&text) {
            return Ok(entries);
        }
    }

    // Fallback: fetch README.md and parse plugin-like entries
    let readme_url = format!(
        "https://raw.githubusercontent.com/{}/main/README.md",
        repo
    );
    let output = std::process::Command::new("curl")
        .args(["-s", "--max-time", "15", "-f", &readme_url])
        .output()?;

    if output.status.success() {
        let text = String::from_utf8_lossy(&output.stdout);
        return Ok(parse_markdown_plugins(&text, &source.name));
    }

    Ok(vec![])
}

fn fetch_awesome_list(source: &PluginSource) -> Result<Vec<PluginEntry>> {
    let repo = source.repo.as_deref().unwrap_or_default();
    if repo.is_empty() {
        return Ok(vec![]);
    }

    let url = format!(
        "https://raw.githubusercontent.com/{}/main/README.md",
        repo
    );
    let output = std::process::Command::new("curl")
        .args(["-s", "--max-time", "15", "-f", &url])
        .output()?;

    if output.status.success() {
        let text = String::from_utf8_lossy(&output.stdout);
        return Ok(parse_markdown_plugins(&text, &source.name));
    }

    Ok(vec![])
}

fn fetch_web_catalog(source: &PluginSource) -> Result<Vec<PluginEntry>> {
    let url = source.url.as_deref().unwrap_or_default();
    if url.is_empty() {
        return Ok(vec![]);
    }

    // Try JSON API endpoint
    let api_url = format!("{}/api/plugins", url.trim_end_matches('/'));
    let output = std::process::Command::new("curl")
        .args(["-s", "--max-time", "15", "-f", &api_url])
        .output()?;

    if output.status.success() {
        let text = String::from_utf8_lossy(&output.stdout);
        if let Ok(entries) = serde_json::from_str::<Vec<PluginEntry>>(&text) {
            return Ok(entries);
        }
    }

    Ok(vec![])
}

/// Parse markdown for plugin-like entries (lines matching `- [name](url) - description`).
fn parse_markdown_plugins(markdown: &str, source_name: &str) -> Vec<PluginEntry> {
    let mut entries = Vec::new();

    for line in markdown.lines() {
        let trimmed = line.trim();
        // Match: - [Name](url) - Description  or  - **Name** - Description
        if let Some(rest) = trimmed.strip_prefix("- [") {
            if let Some(bracket_end) = rest.find("](") {
                let name = &rest[..bracket_end];
                let after_url = rest[bracket_end + 2..]
                    .find(')')
                    .map(|i| &rest[bracket_end + 2 + i + 1..])
                    .unwrap_or("");
                let description = after_url
                    .trim()
                    .trim_start_matches('-')
                    .trim_start_matches(':')
                    .trim()
                    .to_string();

                if !name.is_empty() {
                    entries.push(PluginEntry {
                        name: name.to_string(),
                        description,
                        author: String::new(),
                        source_name: source_name.to_string(),
                        tags: vec![],
                        install_id: name.to_lowercase().replace(' ', "-"),
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
        let tmp = std::env::temp_dir().join("cctx-test-plugins-cache");
        let _ = std::fs::remove_dir_all(&tmp);
        let _ = std::fs::create_dir_all(&tmp);
        let cache = PluginCache::new(&tmp);

        let entries = vec![PluginEntry {
            name: "test-plugin".to_string(),
            description: "A test".to_string(),
            author: "tester".to_string(),
            source_name: "test-src".to_string(),
            tags: vec!["rust".to_string()],
            install_id: "test-plugin".to_string(),
        }];

        cache.write("test-src", &entries).unwrap();
        assert!(cache.is_fresh("test-src"));

        let loaded = cache.read("test-src").unwrap();
        assert_eq!(loaded.len(), 1);
        assert_eq!(loaded[0].name, "test-plugin");

        let _ = std::fs::remove_dir_all(&tmp);
    }

    #[test]
    fn cache_not_fresh_when_missing() {
        let tmp = std::env::temp_dir().join("cctx-test-plugins-notfresh");
        let _ = std::fs::create_dir_all(&tmp);
        let cache = PluginCache::new(&tmp);
        assert!(!cache.is_fresh("nonexistent"));
        let _ = std::fs::remove_dir_all(&tmp);
    }

    #[test]
    fn parse_markdown_extracts_entries() {
        let md = r#"
# Awesome Plugins

- [Code Formatter](https://example.com) - Formats your code
- [Linter](https://example.com) - Lints your code
- Not a plugin line
"#;
        let entries = parse_markdown_plugins(md, "test");
        assert_eq!(entries.len(), 2);
        assert_eq!(entries[0].name, "Code Formatter");
        assert_eq!(entries[1].name, "Linter");
    }

    #[test]
    fn search_filters_by_name() {
        let tmp = std::env::temp_dir().join("cctx-test-plugins-search");
        let _ = std::fs::remove_dir_all(&tmp);
        let _ = std::fs::create_dir_all(&tmp);

        // Write sources.yaml with a source named "test"
        let sources_yaml = r#"sources:
  - name: test
    type: github-repo
    repo: example/test
"#;
        std::fs::write(tmp.join("sources.yaml"), sources_yaml).unwrap();

        // Write cache data for the "test" source
        let entries = vec![
            PluginEntry {
                name: "rust-analyzer".to_string(),
                description: "Rust language server".to_string(),
                author: "ra".to_string(),
                source_name: "test".to_string(),
                tags: vec!["rust".to_string()],
                install_id: "rust-analyzer".to_string(),
            },
            PluginEntry {
                name: "prettier".to_string(),
                description: "Code formatter".to_string(),
                author: "pr".to_string(),
                source_name: "test".to_string(),
                tags: vec!["js".to_string()],
                install_id: "prettier".to_string(),
            },
        ];

        // Write directly to the cache dir that PluginManager will use
        let cache_dir = tmp.join("plugin-cache");
        std::fs::create_dir_all(&cache_dir).unwrap();
        let json = serde_json::to_string(&entries).unwrap();
        std::fs::write(cache_dir.join("test.json"), json).unwrap();

        let pm = PluginManager::new(&tmp).unwrap();
        let results = pm.search("rust").unwrap();
        assert_eq!(results.len(), 1);
        assert_eq!(results[0].name, "rust-analyzer");

        let _ = std::fs::remove_dir_all(&tmp);
    }
}
