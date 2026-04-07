use anyhow::Result;

use crate::indexer::{Index, ResourceEntry};
use crate::scanner::ProjectFingerprint;

#[derive(Debug, Clone)]
pub struct Recommendations {
    pub skills: Vec<Recommendation>,
    pub agents: Vec<Recommendation>,
    pub commands: Vec<Recommendation>,
    pub mcp: Vec<String>,
    pub rules: Vec<String>,
    pub plugins: Vec<String>,
}

#[derive(Debug, Clone)]
pub struct Recommendation {
    pub name: String,
    pub score: f32,
    pub reason: String,
    pub source: RecommendSource,
}

#[derive(Debug, Clone, PartialEq)]
pub enum RecommendSource {
    Base,
    Scanner,
    Ai,
}

pub fn recommend(
    fingerprint: &ProjectFingerprint,
    index: &Index,
    _smart: bool,
) -> Result<Recommendations> {
    let project_tags = fingerprint.all_tags();
    let project_langs = fingerprint.language_names();

    let skills = score_resources(&index.skills, &project_tags, &project_langs);
    let agents = score_resources(&index.agents, &project_tags, &project_langs);
    let commands = score_resources(&index.commands, &project_tags, &project_langs);

    let rules = project_langs
        .iter()
        .filter(|l| {
            // Map language names to rule directory names
            let _rule_name = match l.as_str() {
                "go" => "golang",
                _ => l.as_str(),
            };
            // Check if rule directory exists
            true // Will be validated during symlink creation
        })
        .cloned()
        .collect();

    let mcp = recommend_mcp(fingerprint);
    let plugins = recommend_plugins(fingerprint);

    Ok(Recommendations {
        skills,
        agents,
        commands,
        mcp,
        rules,
        plugins,
    })
}

fn score_resources(
    resources: &[ResourceEntry],
    project_tags: &[String],
    project_langs: &[String],
) -> Vec<Recommendation> {
    let mut scored: Vec<Recommendation> = resources
        .iter()
        .filter_map(|resource| {
            let (score, reason) = compute_score(resource, project_tags, project_langs);
            if score >= resource.match_rules.min_confidence {
                Some(Recommendation {
                    name: resource.name.clone(),
                    score,
                    reason,
                    source: RecommendSource::Scanner,
                })
            } else {
                None
            }
        })
        .collect();

    scored.sort_by(|a, b| b.score.partial_cmp(&a.score).unwrap());
    scored
}

fn compute_score(
    resource: &ResourceEntry,
    project_tags: &[String],
    project_langs: &[String],
) -> (f32, String) {
    let mut score = 0.0f32;
    let mut reasons = Vec::new();

    // Language match (highest weight)
    for lang in &resource.match_rules.languages {
        if project_langs.contains(lang) {
            score += 0.4;
            reasons.push(format!("lang:{}", lang));
        }
    }

    // Tag match
    for tag in &resource.match_rules.tags {
        if project_tags.contains(tag) {
            score += 0.3;
            reasons.push(format!("tag:{}", tag));
        }
    }

    // Dep match
    for dep in &resource.match_rules.deps {
        if project_tags.iter().any(|t| t.contains(dep.as_str())) {
            score += 0.2;
            reasons.push(format!("dep:{}", dep));
        }
    }

    // Cap at 1.0
    score = score.min(1.0);

    let reason = if reasons.is_empty() {
        "inferred".to_string()
    } else {
        reasons.join(", ")
    };

    (score, reason)
}

fn recommend_mcp(fingerprint: &ProjectFingerprint) -> Vec<String> {
    let mut mcp = Vec::new();
    let tags = fingerprint.all_tags();

    if tags.iter().any(|t| matches!(t.as_str(), "playwright" | "cypress")) {
        mcp.push("playwright".to_string());
    }

    if tags.iter().any(|t| t.contains("aws")) {
        mcp.push("aws-serverless".to_string());
    }

    // sequential-thinking for complex projects
    if fingerprint.languages.len() > 2 || fingerprint.frameworks.len() > 3 {
        mcp.push("sequential-thinking".to_string());
    }

    mcp
}

fn recommend_plugins(fingerprint: &ProjectFingerprint) -> Vec<String> {
    let mut plugins = Vec::new();
    let tags = fingerprint.all_tags();

    if tags.contains(&"rust".to_string()) {
        plugins.push("rust-skills@rust-skills".to_string());
    }

    plugins
}

impl Recommendations {
    pub fn skill_names(&self) -> Vec<String> {
        self.skills.iter().map(|r| r.name.clone()).collect()
    }

    pub fn agent_names(&self) -> Vec<String> {
        self.agents.iter().map(|r| r.name.clone()).collect()
    }

    pub fn command_names(&self) -> Vec<String> {
        self.commands.iter().map(|r| r.name.clone()).collect()
    }
}
