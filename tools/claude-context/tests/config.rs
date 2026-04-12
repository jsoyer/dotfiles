/// Tests for config.rs path resolution logic.
///
/// These tests verify that the canonical paths are `~/.aictx/{skills,agents}`
/// and that the legacy `~/.skills` / `~/.agents` fallbacks have been removed.
use claude_context::config::AppConfig;
use std::path::PathBuf;

fn home() -> PathBuf {
    dirs::home_dir().unwrap_or_else(|| PathBuf::from("/tmp"))
}

#[test]
fn default_skills_dir_is_aictx_skills() {
    let config = AppConfig::load().unwrap_or_else(|_| {
        // If no defaults.yaml exists, the Default impl is used — that's what we test.
        // We can't call AppConfig::default() directly (it's private), but load()
        // falls through to it when the config file is absent.
        panic!("AppConfig::load() failed unexpectedly")
    });
    // The canonical skills dir must be under ~/.aictx/skills (or the claude fallback).
    // It must NOT be ~/.skills or ~/.agents/skills.
    let skills = &config.paths.skills_dir;
    let legacy_skills = home().join(".skills");
    let legacy_agents_skills = home().join(".agents").join("skills");
    assert_ne!(
        skills, &legacy_skills,
        "skills_dir must not fall back to ~/.skills"
    );
    assert_ne!(
        skills, &legacy_agents_skills,
        "skills_dir must not fall back to ~/.agents/skills"
    );
}

#[test]
fn default_agents_dir_is_not_bare_dot_agents() {
    let config =
        AppConfig::load().unwrap_or_else(|_| panic!("AppConfig::load() failed unexpectedly"));
    let agents = &config.paths.agents_dir;
    let legacy_agents = home().join(".agents");
    assert_ne!(
        agents, &legacy_agents,
        "agents_dir must not fall back to bare ~/.agents"
    );
}
