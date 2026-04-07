use crate::config::CliEntry;

/// Check if a CLI tool is installed by running its detection command
pub fn is_installed(cli: &CliEntry) -> bool {
    match &cli.detect {
        None => true, // Always present (e.g., claude)
        Some(cmd) => std::process::Command::new("sh")
            .args(["-c", cmd])
            .stdout(std::process::Stdio::null())
            .stderr(std::process::Stdio::null())
            .status()
            .map(|s| s.success())
            .unwrap_or(false),
    }
}

/// Get a display string of all detected CLIs
pub fn detected_summary(clis: &[&CliEntry]) -> String {
    clis.iter()
        .map(|c| c.name.as_str())
        .collect::<Vec<_>>()
        .join(", ")
}
