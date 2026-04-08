use anyhow::Result;
use std::path::{Path, PathBuf};

use crate::symlinker::is_project_dir;

#[derive(Debug, Clone, Copy, PartialEq, Eq, clap::ValueEnum)]
pub enum Scope {
    Global,
    Project,
    UserProject,
}

impl std::fmt::Display for Scope {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Scope::Global => write!(f, "global"),
            Scope::Project => write!(f, "project"),
            Scope::UserProject => write!(f, "user-project"),
        }
    }
}

#[derive(Debug, Clone)]
pub struct ResolvedScope {
    pub scope: Scope,
    /// The base directory for this scope (home for global, project root for project,
    /// ~/.claude/projects/<hash>/ for user-project)
    pub target_dir: PathBuf,
    /// The project root directory (None for global when CWD is not in a project)
    #[allow(dead_code)]
    pub project_root: Option<PathBuf>,
    /// Whether this scope supports symlink-based resources (skills, agents, commands, rules)
    pub supports_symlinks: bool,
}

/// Resolve scope from CWD and optional explicit override.
///
/// Auto-detection: project dir → Project, otherwise → Global.
/// Explicit `--scope` always wins.
pub fn resolve(cwd: &Path, explicit: Option<Scope>) -> Result<ResolvedScope> {
    let home = dirs::home_dir().unwrap_or_else(|| PathBuf::from("/tmp"));
    let project_root = find_project_root(cwd);

    let scope = match explicit {
        Some(s) => s,
        None => {
            if project_root.is_some() {
                Scope::Project
            } else {
                Scope::Global
            }
        }
    };

    match scope {
        Scope::Global => Ok(ResolvedScope {
            scope,
            target_dir: home,
            project_root,
            supports_symlinks: true,
        }),
        Scope::Project => {
            let root = project_root
                .as_ref()
                .ok_or_else(|| anyhow::anyhow!(
                    "No project detected in {}. Cannot use --scope project outside a project directory.",
                    cwd.display()
                ))?;
            Ok(ResolvedScope {
                scope,
                target_dir: root.clone(),
                project_root: Some(root.clone()),
                supports_symlinks: true,
            })
        }
        Scope::UserProject => {
            let root = project_root
                .as_ref()
                .ok_or_else(|| anyhow::anyhow!(
                    "No project detected in {}. Cannot use --scope user-project outside a project directory.",
                    cwd.display()
                ))?;
            let hash = path_hash(root);
            let user_project_dir = home.join(".claude").join("projects").join(&hash);
            Ok(ResolvedScope {
                scope,
                target_dir: user_project_dir,
                project_root: Some(root.clone()),
                supports_symlinks: false,
            })
        }
    }
}

/// Walk up from `start` to find the nearest project root.
/// Stops at home directory.
pub fn find_project_root(start: &Path) -> Option<PathBuf> {
    let home = dirs::home_dir().unwrap_or_default();
    let mut dir = start.to_path_buf();

    loop {
        if is_project_dir(&dir) {
            return Some(dir);
        }
        if dir == home || !dir.pop() {
            return None;
        }
    }
}

/// Derive the Claude Code project path hash.
/// `/home/foo/bar` → `-home-foo-bar`
pub fn path_hash(project_root: &Path) -> String {
    project_root.to_string_lossy().replace('/', "-")
}

/// Convert a Scope to its string form for matching against CliEntry.scopes
pub fn scope_str(scope: Scope) -> &'static str {
    match scope {
        Scope::Global => "global",
        Scope::Project => "project",
        Scope::UserProject => "user-project",
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn path_hash_converts_slashes() {
        let path = Path::new("/home/jeromesoyer/Documents/Github/jsoyer/dotfiles");
        assert_eq!(
            path_hash(path),
            "-home-jeromesoyer-Documents-Github-jsoyer-dotfiles"
        );
    }

    #[test]
    fn path_hash_root() {
        let path = Path::new("/");
        assert_eq!(path_hash(path), "-");
    }

    #[test]
    fn scope_display() {
        assert_eq!(format!("{}", Scope::Global), "global");
        assert_eq!(format!("{}", Scope::Project), "project");
        assert_eq!(format!("{}", Scope::UserProject), "user-project");
    }

    #[test]
    fn resolve_global_when_no_project() {
        let tmp = std::env::temp_dir().join("cctx-test-scope-noproj");
        let _ = std::fs::create_dir_all(&tmp);
        let resolved = resolve(&tmp, None).unwrap();
        assert_eq!(resolved.scope, Scope::Global);
        assert!(resolved.project_root.is_none());
        assert!(resolved.supports_symlinks);
        let _ = std::fs::remove_dir_all(&tmp);
    }

    #[test]
    fn resolve_project_when_git_present() {
        let tmp = std::env::temp_dir().join("cctx-test-scope-proj");
        let _ = std::fs::create_dir_all(tmp.join(".git"));
        let resolved = resolve(&tmp, None).unwrap();
        assert_eq!(resolved.scope, Scope::Project);
        assert_eq!(resolved.project_root.unwrap(), tmp);
        assert!(resolved.supports_symlinks);
        let _ = std::fs::remove_dir_all(&tmp);
    }

    #[test]
    fn resolve_user_project_no_symlinks() {
        let tmp = std::env::temp_dir().join("cctx-test-scope-userproj");
        let _ = std::fs::create_dir_all(tmp.join(".git"));
        let resolved = resolve(&tmp, Some(Scope::UserProject)).unwrap();
        assert_eq!(resolved.scope, Scope::UserProject);
        assert!(!resolved.supports_symlinks);
        let hash = path_hash(&tmp);
        assert!(resolved.target_dir.to_string_lossy().contains(&hash));
        let _ = std::fs::remove_dir_all(&tmp);
    }

    #[test]
    fn resolve_project_fails_outside_project() {
        let tmp = std::env::temp_dir().join("cctx-test-scope-fail");
        let _ = std::fs::create_dir_all(&tmp);
        let result = resolve(&tmp, Some(Scope::Project));
        assert!(result.is_err());
        let _ = std::fs::remove_dir_all(&tmp);
    }
}
