//! AI-powered recommendation refinement (optional, behind --smart flag)
//!
//! Multi-stage pipeline:
//! 1. Deterministic scanner produces fingerprint (always runs)
//! 2. AI analyzes fingerprint + CLAUDE.md/README.md for context
//! 3. Returns refined recommendations
//!
//! Provider priority: Ollama (local, free) > Claude API > OpenAI API

use anyhow::{bail, Context, Result};
use serde::{Deserialize, Serialize};

use crate::config::AiConfig;
use crate::matcher::Recommendations;
use crate::scanner::ProjectFingerprint;

#[derive(Debug, Serialize)]
struct AiRequest {
    fingerprint_summary: String,
    project_context: String,
    available_skills: Vec<String>,
    available_agents: Vec<String>,
    current_recommendations: Vec<String>,
}

#[derive(Debug, Deserialize)]
struct AiResponse {
    #[serde(default)]
    add_skills: Vec<String>,
    #[serde(default)]
    add_agents: Vec<String>,
    #[serde(default)]
    remove_skills: Vec<String>,
    #[serde(default)]
    reasoning: String,
}

/// Auto-detect the best available AI provider based on environment.
/// Returns (provider, model) or None if nothing available.
pub fn auto_detect_provider() -> Option<(&'static str, &'static str)> {
    // Priority: Ollama (local, free) > Claude API > OpenAI API
    if let Ok(output) = std::process::Command::new("curl")
        .args(["-s", "--max-time", "2", "http://localhost:11434/api/tags"])
        .output()
    {
        if output.status.success() {
            return Some(("ollama", "qwen3:8b"));
        }
    }

    if std::env::var("ANTHROPIC_API_KEY").is_ok() {
        return Some(("claude", "claude-haiku-4-5-20251001"));
    }

    if std::env::var("OPENAI_API_KEY").is_ok() {
        return Some(("openai", "gpt-4o-mini"));
    }

    None
}

/// Refine recommendations using AI
pub fn refine(
    config: &AiConfig,
    fingerprint: &ProjectFingerprint,
    recommendations: &Recommendations,
    skill_names: &[String],
    agent_names: &[String],
) -> Result<AiRefinement> {
    if !config.enabled {
        bail!("AI recommendations disabled. Use --smart flag or set ai.enabled=true");
    }

    // Build context from project files
    let project_context = read_project_context(&fingerprint.project_dir)?;

    let request = AiRequest {
        fingerprint_summary: format_fingerprint(fingerprint),
        project_context,
        available_skills: skill_names.to_vec(),
        available_agents: agent_names.to_vec(),
        current_recommendations: recommendations
            .skills
            .iter()
            .map(|r| r.name.clone())
            .collect(),
    };

    let prompt = build_prompt(&request);

    // Resolve provider: "auto" detects best available, otherwise use configured
    let (effective_provider, effective_model) = if config.provider == "auto" {
        match auto_detect_provider() {
            Some((p, m)) => (p.to_string(), m.to_string()),
            None => bail!("AI provider set to 'auto' but no provider available (no Ollama, ANTHROPIC_API_KEY, or OPENAI_API_KEY)"),
        }
    } else {
        (config.provider.clone(), config.model.clone())
    };

    // Try providers in order
    let response = match effective_provider.as_str() {
        "ollama" => query_ollama(&effective_model, &prompt, config.max_tokens).or_else(|_| {
            if let Some(fallback) = &config.fallback {
                match fallback.as_str() {
                    "claude" => query_claude_api(&prompt, config.max_tokens),
                    "openai" => query_openai_api(&prompt, config.max_tokens),
                    _ => bail!("Unknown fallback provider: {}", fallback),
                }
            } else {
                bail!("Ollama unavailable and no fallback configured")
            }
        }),
        "claude" => query_claude_api(&prompt, config.max_tokens),
        "openai" => query_openai_api(&prompt, config.max_tokens),
        "disabled" => bail!("AI provider disabled"),
        other => bail!("Unknown AI provider: {}", other),
    }?;

    Ok(AiRefinement {
        add_skills: response.add_skills,
        add_agents: response.add_agents,
        remove_skills: response.remove_skills,
        reasoning: response.reasoning,
    })
}

#[derive(Debug)]
pub struct AiRefinement {
    pub add_skills: Vec<String>,
    pub add_agents: Vec<String>,
    pub remove_skills: Vec<String>,
    pub reasoning: String,
}

fn read_project_context(project_dir: &std::path::Path) -> Result<String> {
    let mut context = String::new();

    // Read CLAUDE.md if exists
    let claude_md = project_dir.join("CLAUDE.md");
    if claude_md.exists() {
        let content =
            std::fs::read_to_string(&claude_md).with_context(|| "Failed to read CLAUDE.md")?;
        // Take first 2000 chars to keep prompt small
        context.push_str("CLAUDE.md:\n");
        context.push_str(&content[..content.len().min(2000)]);
        context.push('\n');
    }

    // Read README.md if exists
    let readme = project_dir.join("README.md");
    if readme.exists() {
        let content =
            std::fs::read_to_string(&readme).with_context(|| "Failed to read README.md")?;
        context.push_str("README.md:\n");
        context.push_str(&content[..content.len().min(1000)]);
        context.push('\n');
    }

    Ok(context)
}

fn format_fingerprint(fp: &ProjectFingerprint) -> String {
    let langs: Vec<String> = fp.languages.iter().map(|l| l.name.clone()).collect();
    let frameworks: Vec<String> = fp.frameworks.iter().map(|f| f.name.clone()).collect();
    let infra: Vec<String> = fp.infrastructure.iter().map(|i| i.name.clone()).collect();
    let dbs: Vec<String> = fp.databases.iter().map(|d| d.name.clone()).collect();

    format!(
        "Languages: {}. Frameworks: {}. Infrastructure: {}. Databases: {}.",
        if langs.is_empty() {
            "none".to_string()
        } else {
            langs.join(", ")
        },
        if frameworks.is_empty() {
            "none".to_string()
        } else {
            frameworks.join(", ")
        },
        if infra.is_empty() {
            "none".to_string()
        } else {
            infra.join(", ")
        },
        if dbs.is_empty() {
            "none".to_string()
        } else {
            dbs.join(", ")
        },
    )
}

fn build_prompt(request: &AiRequest) -> String {
    format!(
        r#"You are a development tools advisor. Given a project fingerprint and context, suggest which skills and agents to add or remove.

Project fingerprint: {}

Project context:
{}

Currently recommended skills: {}

Available skills (not yet recommended): {}
Available agents (not yet recommended): {}

Respond in JSON format only:
{{"add_skills": ["skill1", "skill2"], "add_agents": ["agent1"], "remove_skills": [], "reasoning": "brief explanation"}}

Only suggest skills/agents from the available lists. Be concise. Focus on what the scanner missed."#,
        request.fingerprint_summary,
        if request.project_context.is_empty() {
            "(no context files found)"
        } else {
            &request.project_context
        },
        request.current_recommendations.join(", "),
        request
            .available_skills
            .iter()
            .take(50)
            .cloned()
            .collect::<Vec<_>>()
            .join(", "),
        request
            .available_agents
            .iter()
            .take(30)
            .cloned()
            .collect::<Vec<_>>()
            .join(", "),
    )
}

fn query_ollama(model: &str, prompt: &str, _max_tokens: u32) -> Result<AiResponse> {
    let body = serde_json::json!({
        "model": model,
        "prompt": prompt,
        "stream": false,
        "format": "json",
    });

    let output = std::process::Command::new("curl")
        .args([
            "-s",
            "--max-time",
            "30",
            "-X",
            "POST",
            "http://localhost:11434/api/generate",
            "-H",
            "Content-Type: application/json",
            "-d",
            &body.to_string(),
        ])
        .output()
        .with_context(|| "Failed to call Ollama API")?;

    if !output.status.success() {
        bail!("Ollama API call failed (is Ollama running?)");
    }

    let response_text = String::from_utf8_lossy(&output.stdout);
    let ollama_response: serde_json::Value =
        serde_json::from_str(&response_text).with_context(|| "Failed to parse Ollama response")?;

    let generated = ollama_response
        .get("response")
        .and_then(|v| v.as_str())
        .unwrap_or("{}");

    let ai_response: AiResponse = serde_json::from_str(generated).unwrap_or(AiResponse {
        add_skills: vec![],
        add_agents: vec![],
        remove_skills: vec![],
        reasoning: "Failed to parse AI response".to_string(),
    });

    Ok(ai_response)
}

fn query_claude_api(prompt: &str, _max_tokens: u32) -> Result<AiResponse> {
    let api_key = std::env::var("ANTHROPIC_API_KEY")
        .with_context(|| "ANTHROPIC_API_KEY not set for Claude API")?;

    let body = serde_json::json!({
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 500,
        "messages": [{"role": "user", "content": prompt}],
    });

    let output = std::process::Command::new("curl")
        .args([
            "-s",
            "--max-time",
            "30",
            "-X",
            "POST",
            "https://api.anthropic.com/v1/messages",
            "-H",
            "Content-Type: application/json",
            "-H",
            &format!("x-api-key: {}", api_key),
            "-H",
            "anthropic-version: 2023-06-01",
            "-d",
            &body.to_string(),
        ])
        .output()
        .with_context(|| "Failed to call Claude API")?;

    let response_text = String::from_utf8_lossy(&output.stdout);
    let claude_response: serde_json::Value =
        serde_json::from_str(&response_text).with_context(|| "Failed to parse Claude response")?;

    let content = claude_response
        .get("content")
        .and_then(|v| v.as_array())
        .and_then(|arr| arr.first())
        .and_then(|v| v.get("text"))
        .and_then(|v| v.as_str())
        .unwrap_or("{}");

    let ai_response: AiResponse = serde_json::from_str(content).unwrap_or(AiResponse {
        add_skills: vec![],
        add_agents: vec![],
        remove_skills: vec![],
        reasoning: "Failed to parse Claude response".to_string(),
    });

    Ok(ai_response)
}

fn query_openai_api(prompt: &str, _max_tokens: u32) -> Result<AiResponse> {
    let api_key =
        std::env::var("OPENAI_API_KEY").with_context(|| "OPENAI_API_KEY not set for OpenAI API")?;

    let body = serde_json::json!({
        "model": "gpt-4o-mini",
        "max_tokens": 500,
        "messages": [{"role": "user", "content": prompt}],
        "response_format": {"type": "json_object"},
    });

    let output = std::process::Command::new("curl")
        .args([
            "-s",
            "--max-time",
            "30",
            "-X",
            "POST",
            "https://api.openai.com/v1/chat/completions",
            "-H",
            "Content-Type: application/json",
            "-H",
            &format!("Authorization: Bearer {}", api_key),
            "-d",
            &body.to_string(),
        ])
        .output()
        .with_context(|| "Failed to call OpenAI API")?;

    let response_text = String::from_utf8_lossy(&output.stdout);
    let openai_response: serde_json::Value =
        serde_json::from_str(&response_text).with_context(|| "Failed to parse OpenAI response")?;

    let content = openai_response
        .get("choices")
        .and_then(|v| v.as_array())
        .and_then(|arr| arr.first())
        .and_then(|v| v.get("message"))
        .and_then(|v| v.get("content"))
        .and_then(|v| v.as_str())
        .unwrap_or("{}");

    let ai_response: AiResponse = serde_json::from_str(content).unwrap_or(AiResponse {
        add_skills: vec![],
        add_agents: vec![],
        remove_skills: vec![],
        reasoning: "Failed to parse OpenAI response".to_string(),
    });

    Ok(ai_response)
}
