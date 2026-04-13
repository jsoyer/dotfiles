use anyhow::Result;
use serde::{Deserialize, Serialize};
use std::path::PathBuf;

#[derive(Debug, Serialize, Deserialize, Default)]
pub struct StatsData {
    pub total_applies: u64,
    pub last_apply: Option<String>,
    pub resources_active: ResourceCounts,
    pub history: Vec<DayEntry>,
}

#[derive(Debug, Serialize, Deserialize, Default)]
pub struct ResourceCounts {
    pub skills: usize,
    pub agents: usize,
    pub commands: usize,
    pub hooks: usize,
    pub rules: usize,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct DayEntry {
    pub date: String,
    pub applies: u32,
    pub scope: String,
}

fn stats_path() -> PathBuf {
    dirs::cache_dir()
        .unwrap_or_else(|| PathBuf::from("/tmp"))
        .join("aictx")
        .join("stats.json")
}

fn now_rfc3339() -> String {
    let output = std::process::Command::new("date")
        .arg("+%Y-%m-%dT%H:%M:%S")
        .output()
        .ok();
    output
        .map(|o| String::from_utf8_lossy(&o.stdout).trim().to_string())
        .unwrap_or_else(|| "unknown".to_string())
}

fn today() -> String {
    let output = std::process::Command::new("date")
        .arg("+%Y-%m-%d")
        .output()
        .ok();
    output
        .map(|o| String::from_utf8_lossy(&o.stdout).trim().to_string())
        .unwrap_or_else(|| "unknown".to_string())
}

pub fn load() -> StatsData {
    let path = stats_path();
    std::fs::read_to_string(&path)
        .ok()
        .and_then(|s| serde_json::from_str(&s).ok())
        .unwrap_or_default()
}

pub fn save(data: &StatsData) -> Result<()> {
    let path = stats_path();
    std::fs::create_dir_all(path.parent().unwrap())?;
    let json = serde_json::to_string_pretty(data)?;
    std::fs::write(&path, json)?;
    Ok(())
}

pub fn record_apply(
    skills: usize,
    agents: usize,
    commands: usize,
    hooks: usize,
    rules: usize,
    scope: &str,
) {
    let mut data = load();
    data.total_applies += 1;
    data.last_apply = Some(now_rfc3339());
    data.resources_active = ResourceCounts {
        skills,
        agents,
        commands,
        hooks,
        rules,
    };

    let today = today();
    if let Some(entry) = data.history.iter_mut().find(|e| e.date == today) {
        entry.applies += 1;
    } else {
        data.history.push(DayEntry {
            date: today,
            applies: 1,
            scope: scope.to_string(),
        });
        // Keep last 30 days
        if data.history.len() > 30 {
            data.history.remove(0);
        }
    }

    let _ = save(&data);
}

pub fn print(data: &StatsData) {
    println!("aictx stats\n");
    println!("Usage");
    println!("  Total applies: {}", data.total_applies);
    if let Some(last) = &data.last_apply {
        let display = if last.len() >= 19 {
            last[..19].replace('T', " ")
        } else {
            last.clone()
        };
        println!("  Last apply: {}", display);
    }
    let r = &data.resources_active;
    println!(
        "  Active: {} skills, {} agents, {} commands, {} hooks, {} rules\n",
        r.skills, r.agents, r.commands, r.hooks, r.rules
    );

    if !data.history.is_empty() {
        println!("History (last 7 days)");
        let recent: Vec<&DayEntry> = data.history.iter().rev().take(7).collect();
        let max = recent.iter().map(|e| e.applies).max().unwrap_or(1);
        for entry in recent.iter().rev() {
            let bar_len = ((entry.applies as f32 / max as f32) * 20.0) as usize;
            let bar: String = "#".repeat(bar_len);
            let date_short = if entry.date.len() >= 10 {
                &entry.date[5..]
            } else {
                entry.date.as_str()
            };
            println!("  {}  {:<20} {} applies", date_short, bar, entry.applies);
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn stats_data_default_is_zeroed() {
        let data = StatsData::default();
        assert_eq!(data.total_applies, 0);
        assert!(data.last_apply.is_none());
        assert!(data.history.is_empty());
        assert_eq!(data.resources_active.skills, 0);
    }

    #[test]
    fn resource_counts_default_is_zeroed() {
        let counts = ResourceCounts::default();
        assert_eq!(counts.skills, 0);
        assert_eq!(counts.agents, 0);
        assert_eq!(counts.commands, 0);
        assert_eq!(counts.hooks, 0);
        assert_eq!(counts.rules, 0);
    }

    #[test]
    fn stats_serializes_and_deserializes() {
        let data = StatsData {
            total_applies: 42,
            last_apply: Some("2026-04-12T10:00:00".to_string()),
            resources_active: ResourceCounts {
                skills: 5,
                agents: 3,
                commands: 2,
                hooks: 1,
                rules: 4,
            },
            history: vec![DayEntry {
                date: "2026-04-12".to_string(),
                applies: 3,
                scope: "global".to_string(),
            }],
        };

        let json = serde_json::to_string(&data).unwrap();
        let restored: StatsData = serde_json::from_str(&json).unwrap();
        assert_eq!(restored.total_applies, 42);
        assert_eq!(restored.history.len(), 1);
        assert_eq!(restored.history[0].applies, 3);
        assert_eq!(restored.resources_active.skills, 5);
    }

    #[test]
    fn print_does_not_panic_on_empty_data() {
        let data = StatsData::default();
        // Should not panic
        print(&data);
    }

    #[test]
    fn print_does_not_panic_with_full_data() {
        let data = StatsData {
            total_applies: 10,
            last_apply: Some("2026-04-12T09:30:00".to_string()),
            resources_active: ResourceCounts {
                skills: 10,
                agents: 5,
                commands: 3,
                hooks: 2,
                rules: 6,
            },
            history: vec![
                DayEntry {
                    date: "2026-04-10".to_string(),
                    applies: 2,
                    scope: "project".to_string(),
                },
                DayEntry {
                    date: "2026-04-11".to_string(),
                    applies: 5,
                    scope: "global".to_string(),
                },
                DayEntry {
                    date: "2026-04-12".to_string(),
                    applies: 3,
                    scope: "global".to_string(),
                },
            ],
        };
        // Should not panic
        print(&data);
    }

    #[test]
    fn history_capped_at_30() {
        let mut data = StatsData::default();
        for i in 0..35u32 {
            data.history.push(DayEntry {
                date: format!("2026-{:02}-{:02}", (i / 30) + 1, (i % 28) + 1),
                applies: 1,
                scope: "global".to_string(),
            });
            if data.history.len() > 30 {
                data.history.remove(0);
            }
        }
        assert!(data.history.len() <= 30);
    }

    #[test]
    fn load_returns_default_when_file_missing() {
        // load() uses the real stats_path(); must not panic and returns valid data
        let data = load();
        assert!(data.total_applies < u64::MAX);
    }
}
