use anyhow::Result;

use crate::ai;
use crate::config::AiConfig;
use crate::indexer::{Index, ResourceEntry};
use crate::scanner::ProjectFingerprint;

#[derive(Debug, Clone, Default)]
pub struct Recommendations {
    pub skills: Vec<Recommendation>,
    pub agents: Vec<Recommendation>,
    pub commands: Vec<Recommendation>,
    pub hooks: Vec<Recommendation>,
    pub mcp: Vec<String>,
    pub rules: Vec<String>,
    pub plugins: Vec<String>,
}

#[derive(Debug, Clone)]
pub struct Recommendation {
    pub name: String,
    pub score: f32,
    pub reason: String,
    #[allow(dead_code)]
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
    smart: bool,
    ai_config: &AiConfig,
) -> Result<Recommendations> {
    let project_tags = fingerprint.all_tags();
    let project_langs = fingerprint.language_names();

    let skills = score_resources(&index.skills, &project_tags, &project_langs);
    let agents = score_resources(&index.agents, &project_tags, &project_langs);
    let commands = score_resources(&index.commands, &project_tags, &project_langs);

    let rules = project_langs
        .iter()
        .filter(|l| {
            let _rule_name = match l.as_str() {
                "go" => "golang",
                _ => l.as_str(),
            };
            true // Will be validated during symlink creation
        })
        .cloned()
        .collect();

    let mcp = recommend_mcp(fingerprint);
    let plugins = recommend_plugins(fingerprint);

    let mut recs = Recommendations {
        skills,
        agents,
        commands,
        hooks: vec![],
        mcp,
        rules,
        plugins,
    };

    // AI refinement when --smart flag is active and AI is enabled
    if smart && ai_config.enabled {
        let skill_names: Vec<String> = index.skills.iter().map(|s| s.name.clone()).collect();
        let agent_names: Vec<String> = index.agents.iter().map(|a| a.name.clone()).collect();
        match ai::refine(ai_config, fingerprint, &recs, &skill_names, &agent_names) {
            Ok(refinement) => apply_refinement(&mut recs, &refinement),
            Err(e) => eprintln!("AI refinement failed, using scanner results: {}", e),
        }
    }

    Ok(recs)
}

fn apply_refinement(recs: &mut Recommendations, refinement: &ai::AiRefinement) {
    for name in &refinement.add_skills {
        if !recs.skills.iter().any(|r| &r.name == name) {
            recs.skills.push(Recommendation {
                name: name.clone(),
                score: 0.7,
                reason: format!("AI: {}", refinement.reasoning),
                source: RecommendSource::Ai,
            });
        }
    }
    for name in &refinement.add_agents {
        if !recs.agents.iter().any(|r| &r.name == name) {
            recs.agents.push(Recommendation {
                name: name.clone(),
                score: 0.7,
                reason: format!("AI: {}", refinement.reasoning),
                source: RecommendSource::Ai,
            });
        }
    }
    recs.skills
        .retain(|r| !refinement.remove_skills.contains(&r.name));
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
        "auto-detected".to_string()
    } else {
        reasons.join(", ")
    };

    (score, reason)
}

fn recommend_mcp(fingerprint: &ProjectFingerprint) -> Vec<String> {
    let mut mcp = Vec::new();
    let tags = fingerprint.all_tags();

    if tags
        .iter()
        .any(|t| matches!(t.as_str(), "playwright" | "cypress"))
    {
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

    pub fn hook_names(&self) -> Vec<String> {
        self.hooks.iter().map(|r| r.name.clone()).collect()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn recommendations_hook_names_returns_names() {
        let recs = Recommendations {
            skills: vec![],
            agents: vec![],
            commands: vec![],
            hooks: vec![Recommendation {
                name: "check-test-exists".to_string(),
                score: 0.9,
                reason: "test".to_string(),
                source: RecommendSource::Scanner,
            }],
            mcp: vec![],
            rules: vec![],
            plugins: vec![],
        };
        assert_eq!(recs.hook_names(), vec!["check-test-exists"]);
    }

    #[test]
    fn recommendations_hook_names_empty_when_no_hooks() {
        let recs = Recommendations {
            skills: vec![],
            agents: vec![],
            commands: vec![],
            hooks: vec![],
            mcp: vec![],
            rules: vec![],
            plugins: vec![],
        };
        assert!(recs.hook_names().is_empty());
    }
}
