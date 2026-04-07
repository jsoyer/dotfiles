use anyhow::{Context, Result};
use std::path::Path;

/// Token estimation: ~4 chars per token
const CHARS_PER_TOKEN: usize = 4;

/// Sections that are typically verbose and can be trimmed
const VERBOSE_PATTERNS: &[&str] = &[
    "## Auto-Update",
    "## Auto-Healing",
    "## Notifications",
    "## Heartbeat",
    "## Fleet Monitoring",
    "## Post-Apply Validation",
    "## ntfy Setup",
    "## Timers & Activation",
    "## Status Tracking",
    "## Configuration\n\n**Enable/disable**",
];

/// Sections that duplicate what's in the code
const CODE_DUPLICATE_PATTERNS: &[&str] = &[
    "<!-- rtk-instructions",
    "## RTK Commands by Workflow",
    "## Token Savings Overview",
    "## RTK (Rust Token Killer) - Token-Optimized Commands",
];

pub struct TrimReport {
    pub file_path: String,
    pub original_lines: usize,
    pub original_tokens: usize,
    pub suggestions: Vec<TrimSuggestion>,
    pub estimated_savings: usize,
}

pub struct TrimSuggestion {
    pub section: String,
    pub start_line: usize,
    pub end_line: usize,
    pub reason: String,
    pub token_savings: usize,
}

pub fn analyze(file_path: &str) -> Result<TrimReport> {
    let path = Path::new(file_path);
    let content = std::fs::read_to_string(path)
        .with_context(|| format!("Failed to read {}", file_path))?;

    let lines: Vec<&str> = content.lines().collect();
    let original_lines = lines.len();
    let original_tokens = content.len() / CHARS_PER_TOKEN;

    let mut suggestions = Vec::new();

    // Check for verbose sections
    for pattern in VERBOSE_PATTERNS {
        if let Some(start) = find_section_start(&lines, pattern) {
            let end = find_section_end(&lines, start);
            let section_content: String = lines[start..end].join("\n");
            let token_savings = section_content.len() / CHARS_PER_TOKEN;

            if token_savings > 50 {
                suggestions.push(TrimSuggestion {
                    section: lines[start].trim_start_matches('#').trim().to_string(),
                    start_line: start + 1,
                    end_line: end,
                    reason: "Verbose internal details (findable in code)".to_string(),
                    token_savings,
                });
            }
        }
    }

    // Check for code-duplicate sections
    for pattern in CODE_DUPLICATE_PATTERNS {
        if let Some(start) = find_pattern_start(&lines, pattern) {
            let end = find_rtk_block_end(&lines, start);
            let section_content: String = lines[start..end].join("\n");
            let token_savings = section_content.len() / CHARS_PER_TOKEN;

            if token_savings > 30 {
                suggestions.push(TrimSuggestion {
                    section: lines[start].trim_start_matches('#').trim().to_string(),
                    start_line: start + 1,
                    end_line: end,
                    reason: "Duplicated content (available in global config or code)".to_string(),
                    token_savings,
                });
            }
        }
    }

    // Check for long code blocks (>20 lines)
    let mut in_code_block = false;
    let mut code_block_start = 0;
    for (i, line) in lines.iter().enumerate() {
        if line.starts_with("```") {
            if in_code_block {
                let block_len = i - code_block_start;
                if block_len > 20 {
                    let section_content: String = lines[code_block_start..=i].join("\n");
                    suggestions.push(TrimSuggestion {
                        section: format!("Code block at line {}", code_block_start + 1),
                        start_line: code_block_start + 1,
                        end_line: i + 1,
                        reason: format!("Long code block ({} lines) — consider summarizing", block_len),
                        token_savings: section_content.len() / CHARS_PER_TOKEN,
                    });
                }
                in_code_block = false;
            } else {
                in_code_block = true;
                code_block_start = i;
            }
        }
    }

    // Check total file size
    if original_tokens > 3000 {
        suggestions.push(TrimSuggestion {
            section: "File size".to_string(),
            start_line: 0,
            end_line: 0,
            reason: format!(
                "File is ~{} tokens ({} lines). Target: <1500 tokens for optimal context usage.",
                original_tokens, original_lines
            ),
            token_savings: 0,
        });
    }

    let estimated_savings: usize = suggestions.iter().map(|s| s.token_savings).sum();

    Ok(TrimReport {
        file_path: file_path.to_string(),
        original_lines,
        original_tokens,
        suggestions,
        estimated_savings,
    })
}

pub fn auto_trim(file_path: &str) -> Result<()> {
    let path = Path::new(file_path);
    let content = std::fs::read_to_string(path)?;

    // Create backup
    let backup_path = format!("{}.backup", file_path);
    std::fs::write(&backup_path, &content)
        .with_context(|| format!("Failed to create backup at {}", backup_path))?;
    println!("Backup created: {}", backup_path);

    let mut lines: Vec<String> = content.lines().map(String::from).collect();
    let mut removed_sections = 0;

    // Remove RTK instruction blocks
    let mut i = 0;
    while i < lines.len() {
        if lines[i].contains("<!-- rtk-instructions") {
            let start = i;
            while i < lines.len() && !lines[i].contains("<!-- /rtk-instructions") {
                i += 1;
            }
            if i < lines.len() {
                i += 1; // include closing comment
            }
            lines.drain(start..i.min(lines.len()));
            i = start;
            removed_sections += 1;
            continue;
        }
        i += 1;
    }

    // Remove verbose sections by pattern
    for pattern in VERBOSE_PATTERNS {
        let line_refs: Vec<&str> = lines.iter().map(|s| s.as_str()).collect();
        if let Some(start) = find_section_start(&line_refs, pattern) {
            let end = find_section_end(&line_refs, start);
            if end > start {
                lines.drain(start..end);
                removed_sections += 1;
            }
        }
    }

    let new_content = lines.join("\n");
    std::fs::write(path, &new_content)?;

    let new_tokens = new_content.len() / CHARS_PER_TOKEN;
    let old_tokens = content.len() / CHARS_PER_TOKEN;
    println!(
        "Trimmed: {} -> {} tokens ({} sections removed, saved ~{} tokens)",
        old_tokens,
        new_tokens,
        removed_sections,
        old_tokens.saturating_sub(new_tokens)
    );

    Ok(())
}

impl TrimReport {
    pub fn print(&self) {
        println!("Trim analysis: {}\n", self.file_path);
        println!("  Size: {} lines, ~{} tokens\n", self.original_lines, self.original_tokens);

        if self.suggestions.is_empty() {
            println!("  No trim suggestions — file looks lean.");
            return;
        }

        println!("  Suggestions:\n");
        for (i, s) in self.suggestions.iter().enumerate() {
            let line_info = if s.start_line > 0 {
                format!("(lines {}-{})", s.start_line, s.end_line)
            } else {
                String::new()
            };
            println!(
                "  {}. {} {}",
                i + 1,
                s.section,
                line_info
            );
            println!("     Reason: {}", s.reason);
            if s.token_savings > 0 {
                println!("     Savings: ~{} tokens", s.token_savings);
            }
            println!();
        }

        println!(
            "  Estimated total savings: ~{} tokens ({:.0}% of file)",
            self.estimated_savings,
            (self.estimated_savings as f64 / self.original_tokens.max(1) as f64) * 100.0
        );
        println!("\n  Run `cctx trim --auto` to apply with backup.");
    }
}

fn find_section_start(lines: &[&str], pattern: &str) -> Option<usize> {
    lines.iter().position(|line| line.contains(pattern))
}

fn find_pattern_start(lines: &[&str], pattern: &str) -> Option<usize> {
    lines.iter().position(|line| line.contains(pattern))
}

fn find_section_end(lines: &[&str], start: usize) -> usize {
    let heading_level = lines[start].chars().take_while(|c| *c == '#').count();
    if heading_level == 0 {
        return (start + 1).min(lines.len());
    }

    for i in (start + 1)..lines.len() {
        let level = lines[i].chars().take_while(|c| *c == '#').count();
        if level > 0 && level <= heading_level {
            return i;
        }
    }

    lines.len()
}

fn find_rtk_block_end(lines: &[&str], start: usize) -> usize {
    for i in start..lines.len() {
        if lines[i].contains("<!-- /rtk-instructions") {
            return (i + 1).min(lines.len());
        }
    }
    find_section_end(lines, start)
}
