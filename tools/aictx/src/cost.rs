use crate::matcher::Recommendations;
use crate::symlinker::ProjectStatus;

const TOKENS_PER_SKILL: usize = 250;
const TOKENS_PER_AGENT: usize = 500;
const TOKENS_PER_COMMAND: usize = 200;
const TOKENS_PER_MCP: usize = 400;
const TOKENS_PER_RULE_LANG: usize = 600;
const TOKENS_PER_PLUGIN: usize = 300;

const GLOBAL_SKILLS: usize = 648;
const GLOBAL_AGENTS: usize = 192;
const GLOBAL_COMMANDS: usize = 60;
const GLOBAL_MCP: usize = 19;
const GLOBAL_RULE_LANGS: usize = 12;
const GLOBAL_PLUGINS: usize = 43;

pub fn estimate(status: &ProjectStatus) -> CostEstimate {
    let skills = status.skills.len() * TOKENS_PER_SKILL;
    let agents = status.agents.len() * TOKENS_PER_AGENT;
    let commands = status.commands.len() * TOKENS_PER_COMMAND;
    let mcp = status.mcp.len() * TOKENS_PER_MCP;
    let rules = status.rules.len() * TOKENS_PER_RULE_LANG;
    let plugins = status.plugins.len() * TOKENS_PER_PLUGIN;

    let project_total = skills + agents + commands + mcp + rules + plugins;
    let global_total = GLOBAL_SKILLS * TOKENS_PER_SKILL
        + GLOBAL_AGENTS * TOKENS_PER_AGENT
        + GLOBAL_COMMANDS * TOKENS_PER_COMMAND
        + GLOBAL_MCP * TOKENS_PER_MCP
        + GLOBAL_RULE_LANGS * TOKENS_PER_RULE_LANG
        + GLOBAL_PLUGINS * TOKENS_PER_PLUGIN;

    CostEstimate {
        skills_count: status.skills.len(),
        skills_tokens: skills,
        agents_count: status.agents.len(),
        agents_tokens: agents,
        commands_count: status.commands.len(),
        commands_tokens: commands,
        mcp_count: status.mcp.len(),
        mcp_tokens: mcp,
        rules_count: status.rules.len(),
        rules_tokens: rules,
        plugins_count: status.plugins.len(),
        plugins_tokens: plugins,
        project_total,
        global_total,
    }
}

pub struct CostEstimate {
    pub skills_count: usize,
    pub skills_tokens: usize,
    pub agents_count: usize,
    pub agents_tokens: usize,
    pub commands_count: usize,
    pub commands_tokens: usize,
    pub mcp_count: usize,
    pub mcp_tokens: usize,
    pub rules_count: usize,
    pub rules_tokens: usize,
    pub plugins_count: usize,
    pub plugins_tokens: usize,
    pub project_total: usize,
    pub global_total: usize,
}

pub fn print(status: &ProjectStatus) {
    let est = estimate(status);

    println!("Current project config:");
    println!(
        "  Skills ({:>3})     ~{:>6} tokens/msg",
        est.skills_count,
        format_tokens(est.skills_tokens)
    );
    println!(
        "  Agents ({:>3})     ~{:>6} tokens/msg",
        est.agents_count,
        format_tokens(est.agents_tokens)
    );
    println!(
        "  Commands ({:>2})    ~{:>6} tokens/msg",
        est.commands_count,
        format_tokens(est.commands_tokens)
    );
    println!(
        "  MCP ({:>2})         ~{:>6} tokens/msg",
        est.mcp_count,
        format_tokens(est.mcp_tokens)
    );
    println!(
        "  Rules ({:>2} langs)  ~{:>6} tokens/msg",
        est.rules_count,
        format_tokens(est.rules_tokens)
    );
    println!(
        "  Plugins ({:>2})     ~{:>6} tokens/msg",
        est.plugins_count,
        format_tokens(est.plugins_tokens)
    );
    println!("  {}", "-".repeat(35));
    println!(
        "  Total overhead  ~{} tokens/msg",
        format_tokens(est.project_total)
    );
    println!();
    println!(
        "  vs global:      ~{} tokens/msg",
        format_tokens(est.global_total)
    );

    if est.global_total > 0 {
        let savings_pct =
            ((est.global_total - est.project_total) as f64 / est.global_total as f64) * 100.0;
        println!(
            "  Savings:        {:.0}% (-{} tokens/msg)",
            savings_pct,
            format_tokens(est.global_total - est.project_total)
        );
    }
}

pub fn print_diff(current: &ProjectStatus, recommended: &Recommendations) {
    println!("Changes since last apply:");

    let recommended_skills = recommended.skill_names();
    let new_skills: Vec<&String> = recommended_skills
        .iter()
        .filter(|s| !current.skills.contains(s))
        .collect();

    let removed_skills: Vec<&String> = current
        .skills
        .iter()
        .filter(|s| !recommended_skills.contains(s))
        .collect();

    if !new_skills.is_empty() {
        println!("\n  + Recommended skills:");
        for s in &new_skills {
            println!("    + {}", s);
        }
    }

    if !removed_skills.is_empty() {
        println!("\n  - Consider removing:");
        for s in &removed_skills {
            println!("    - {}", s);
        }
    }

    if new_skills.is_empty() && removed_skills.is_empty() {
        println!("  No changes detected.");
    }
}

pub fn has_diff(current: &ProjectStatus, recommended: &Recommendations) -> bool {
    let rec_skills: Vec<&str> = recommended.skills.iter().map(|r| r.name.as_str()).collect();
    let rec_agents: Vec<&str> = recommended.agents.iter().map(|r| r.name.as_str()).collect();

    // Check if any recommended items are not active
    for name in &rec_skills {
        if !current.skills.contains(&name.to_string()) {
            return true;
        }
    }
    for name in &rec_agents {
        if !current.agents.contains(&name.to_string()) {
            return true;
        }
    }
    // Check if any active items are not recommended
    for name in &current.skills {
        if !rec_skills.contains(&name.as_str()) {
            return true;
        }
    }
    for name in &current.agents {
        if !rec_agents.contains(&name.as_str()) {
            return true;
        }
    }
    false
}

fn format_tokens(n: usize) -> String {
    if n >= 1_000_000 {
        format!("{:.1}m", n as f64 / 1_000_000.0)
    } else if n >= 1_000 {
        format!("{:.1}k", n as f64 / 1_000.0)
    } else {
        format!("{}", n)
    }
}
