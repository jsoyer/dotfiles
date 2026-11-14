//! Preserve user settings and record only the changes owned by aictx.
use anyhow::{bail, Context, Result};
use serde::{Deserialize, Serialize};
use serde_json::{Map, Value};
use std::collections::BTreeMap;
use std::fs::{self, File, OpenOptions};
use std::io::Write;
use std::path::{Path, PathBuf};

#[derive(Default, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct Ownership {
    version: u32,
    groups: BTreeMap<String, Group>,
}

#[derive(Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct Group {
    existed: bool,
    entries: BTreeMap<String, Original>,
}

#[derive(Serialize, Deserialize)]
enum Original {
    Absent,
    Present(Value),
}

fn sidecar(path: &Path, suffix: &str) -> PathBuf {
    let name = path
        .file_name()
        .expect("settings filename")
        .to_string_lossy();
    path.with_file_name(format!(".{name}.aictx-{suffix}"))
}

fn regular_file(path: &Path) -> Result<bool> {
    match fs::symlink_metadata(path) {
        Ok(metadata) if metadata.is_file() => Ok(true),
        Ok(_) => bail!(
            "Refusing to replace a symlink or non-regular file: {}",
            path.display()
        ),
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => Ok(false),
        Err(error) => Err(error).with_context(|| format!("Cannot inspect {}", path.display())),
    }
}

fn read_object(path: &Path) -> Result<Map<String, Value>> {
    if !regular_file(path)? {
        return Ok(Map::new());
    }
    let raw = fs::read(path).with_context(|| format!("Cannot read {}", path.display()))?;
    serde_json::from_slice(&raw).with_context(|| {
        format!(
            "Invalid JSON object in {}; file left unchanged",
            path.display()
        )
    })
}

fn read_ownership(path: &Path) -> Result<Ownership> {
    let owner = sidecar(path, "state.json");
    if !regular_file(&owner)? {
        return Ok(Ownership {
            version: 1,
            ..Ownership::default()
        });
    }
    let state: Ownership = serde_json::from_slice(&fs::read(&owner)?).with_context(|| {
        format!(
            "Invalid aictx ownership file {}; settings left unchanged",
            owner.display()
        )
    })?;
    if state.version != 1
        || state
            .groups
            .keys()
            .any(|key| key != "enabledPlugins" && key != "enabledMcpServers")
    {
        bail!(
            "Unsupported aictx ownership data in {}; settings left unchanged",
            owner.display()
        );
    }
    Ok(state)
}

fn lock(path: &Path) -> Result<File> {
    let parent = path.parent().context("Settings need a parent directory")?;
    fs::create_dir_all(parent)?;
    let target = sidecar(path, "lock");
    regular_file(&target)?;
    let mut options = OpenOptions::new();
    options.read(true).write(true).create(true).truncate(false);
    #[cfg(unix)]
    {
        use std::os::unix::fs::OpenOptionsExt;
        options.mode(0o600);
    }
    let file = options
        .open(&target)
        .with_context(|| format!("Cannot open {}", target.display()))?;
    file.lock()
        .with_context(|| format!("Cannot lock {}", target.display()))?;
    Ok(file)
}

fn atomic_write(path: &Path, content: &[u8]) -> Result<()> {
    regular_file(path)?;
    let parent = path.parent().context("Settings need a parent directory")?;
    let mut temporary = tempfile::Builder::new()
        .prefix(".aictx-")
        .tempfile_in(parent)?;
    // NamedTempFile is private from creation; never widen temporary permissions.
    temporary.write_all(content)?;
    temporary.as_file().sync_all()?;
    temporary
        .persist(path)
        .map_err(|error| error.error)
        .with_context(|| {
            format!(
                "Cannot replace {}; previous file left unchanged",
                path.display()
            )
        })?;
    Ok(())
}

fn backup(path: &Path) -> Result<()> {
    let target = sidecar(path, "backup");
    if !regular_file(path)? || regular_file(&target)? {
        return Ok(());
    }
    // The caller holds the per-file lock. Keep the first exact copy permanently.
    atomic_write(&target, &fs::read(path)?)
}

fn restore_owned(settings: &mut Map<String, Value>, state: &Ownership) {
    for (key, group) in &state.groups {
        let Some(Value::Object(entries)) = settings.get_mut(key) else {
            continue; // A user replacement of the whole value also stays intact.
        };
        for (name, original) in &group.entries {
            if entries.get(name) != Some(&Value::Bool(true)) {
                continue; // Preserve any user edit made after aictx applied it.
            }
            match original {
                Original::Absent => {
                    entries.remove(name);
                }
                Original::Present(value) => {
                    entries.insert(name.clone(), value.clone());
                }
            }
        }
        if entries.is_empty() && !group.existed {
            settings.remove(key);
        }
    }
}

pub fn merge(path: &Path, mcp: &[String], plugins: &[String]) -> Result<()> {
    let _lock = lock(path)?;
    let mut settings = read_object(path)?;
    let previous = settings.clone();
    let state = read_ownership(path)?;
    restore_owned(&mut settings, &state);
    let mut next = Ownership {
        version: 1,
        ..Ownership::default()
    };
    for (key, selected) in [("enabledMcpServers", mcp), ("enabledPlugins", plugins)] {
        if selected.is_empty() {
            continue;
        }
        let existed = settings.contains_key(key);
        let entries = settings
            .entry(key)
            .or_insert_with(|| Value::Object(Map::new()))
            .as_object_mut()
            .with_context(|| {
                format!(
                    "Expected an object for {key} in {}; file left unchanged",
                    path.display()
                )
            })?;
        let mut owned = BTreeMap::new();
        for name in selected {
            if entries.get(name) == Some(&Value::Bool(true)) {
                continue; // Already enabled by the user: do not claim ownership.
            }
            let original = match entries.insert(name.clone(), Value::Bool(true)) {
                Some(value) => Original::Present(value),
                None => Original::Absent,
            };
            owned.insert(name.clone(), original);
        }
        if !owned.is_empty() {
            next.groups.insert(
                key.to_string(),
                Group {
                    existed,
                    entries: owned,
                },
            );
        }
    }
    let owner = sidecar(path, "state.json");
    let had_owner = owner.exists();
    if settings != previous {
        backup(path)?;
    }
    // Save provenance before touching settings; never lose the original values.
    if !next.groups.is_empty() || owner.exists() {
        atomic_write(&owner, &serde_json::to_vec_pretty(&next)?)?;
    }
    if settings != previous {
        if let Err(error) = atomic_write(path, &serde_json::to_vec_pretty(&settings)?) {
            if had_owner {
                atomic_write(&owner, &serde_json::to_vec_pretty(&state)?)?;
            } else if owner.exists() {
                fs::remove_file(&owner)?;
            }
            return Err(error);
        }
    }
    Ok(())
}

pub fn reset(path: &Path) -> Result<()> {
    if !path.exists() && !sidecar(path, "state.json").exists() {
        return Ok(());
    }
    let _lock = lock(path)?;
    let mut settings = read_object(path)?;
    let previous = settings.clone();
    let state = read_ownership(path)?;
    restore_owned(&mut settings, &state);
    if settings != previous {
        backup(path)?;
        if settings.is_empty() {
            fs::remove_file(path)?;
        } else {
            atomic_write(path, &serde_json::to_vec_pretty(&settings)?)?;
        }
    }
    let owner = sidecar(path, "state.json");
    if owner.exists() {
        fs::remove_file(owner)?;
    }
    Ok(())
}

pub fn set_plugins_enabled(path: &Path, enabled: bool) -> Result<()> {
    if !path.exists() {
        return Ok(());
    }
    let _lock = lock(path)?;
    let mut settings = read_object(path)?;
    let previous = settings.clone();
    if let Some(Value::Object(plugins)) = settings.get_mut("enabledPlugins") {
        for value in plugins.values_mut() {
            *value = Value::Bool(enabled);
        }
    }
    if settings != previous {
        backup(path)?;
        atomic_write(path, &serde_json::to_vec_pretty(&settings)?)?;
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;
    use std::sync::{Arc, Barrier};

    fn selected(names: &[&str]) -> Vec<String> {
        names.iter().map(|name| name.to_string()).collect()
    }

    fn fixture(value: Value) -> (tempfile::TempDir, PathBuf) {
        let directory = tempfile::tempdir().unwrap();
        let path = directory.path().join("settings.local.json");
        fs::write(&path, serde_json::to_vec_pretty(&value).unwrap()).unwrap();
        (directory, path)
    }

    fn contents(path: &Path) -> Value {
        serde_json::from_slice(&fs::read(path).unwrap()).unwrap()
    }

    #[test]
    fn reset_keeps_legacy_settings_without_provenance_byte_for_byte() {
        let (_directory, path) = fixture(
            json!({"permissions":{"allow":["Bash(git status)"]},"enabledPlugins":{"personal":true}}),
        );
        let before = fs::read(&path).unwrap();
        reset(&path).unwrap();
        assert_eq!(fs::read(&path).unwrap(), before);
    }

    #[test]
    fn apply_and_reset_preserve_personal_entries_and_restore_previous_values() {
        let original = json!({
            "permissions": {"deny": ["Bash(rm *)"]},
            "enabledPlugins": {"personal": true, "selected": false, "null-value": null},
            "enabledMcpServers": {"own-server": true}
        });
        let (_directory, path) = fixture(original.clone());
        merge(
            &path,
            &selected(&["new-server"]),
            &selected(&["personal", "selected", "null-value", "new-plugin"]),
        )
        .unwrap();
        let applied = contents(&path);
        assert_eq!(applied["enabledPlugins"]["personal"], true);
        assert_eq!(applied["enabledPlugins"]["selected"], true);
        assert_eq!(applied["enabledMcpServers"]["own-server"], true);
        reset(&path).unwrap();
        assert_eq!(contents(&path), original);
    }

    #[test]
    fn repeated_apply_retains_original_ownership_and_deselection_is_selective() {
        let original = json!({"personal": "kept", "enabledPlugins": {"mine": true, "off": false}});
        let (_directory, path) = fixture(original.clone());
        for _ in 0..3 {
            merge(&path, &[], &selected(&["off", "first"])).unwrap();
        }
        merge(&path, &[], &selected(&["second"])).unwrap();
        assert_eq!(
            contents(&path)["enabledPlugins"],
            json!({"mine":true,"off":false,"second":true})
        );
        reset(&path).unwrap();
        assert_eq!(contents(&path), original);
    }

    #[test]
    fn empty_selection_restores_previously_managed_entries() {
        let (_directory, path) = fixture(json!({"personal": true}));
        merge(&path, &selected(&["server"]), &selected(&["plugin"])).unwrap();
        merge(&path, &[], &[]).unwrap();
        assert_eq!(contents(&path), json!({"personal":true}));
    }

    #[test]
    fn reset_preserves_user_changes_made_after_apply() {
        let (_directory, path) = fixture(json!({"personal": true}));
        merge(&path, &[], &selected(&["managed"])).unwrap();
        let mut changed = contents(&path);
        changed["enabledPlugins"]["managed"] = json!(false);
        changed["enabledPlugins"]["added-by-user"] = json!(true);
        fs::write(&path, serde_json::to_vec(&changed).unwrap()).unwrap();
        reset(&path).unwrap();
        assert_eq!(contents(&path), changed);
    }

    #[test]
    fn reset_removes_only_files_created_entirely_from_owned_entries() {
        let directory = tempfile::tempdir().unwrap();
        let path = directory.path().join("settings.json");
        merge(&path, &[], &selected(&["managed"])).unwrap();
        reset(&path).unwrap();
        assert!(!path.exists());
        assert!(!sidecar(&path, "state.json").exists());
    }

    #[test]
    fn malformed_json_is_never_replaced_by_apply_reset_or_toggles() {
        for raw in ["{broken", "[]", "null", "\"not an object\""] {
            let directory = tempfile::tempdir().unwrap();
            let path = directory.path().join("settings.json");
            fs::write(&path, raw).unwrap();
            assert!(merge(&path, &[], &selected(&["plugin"])).is_err());
            assert!(reset(&path).is_err());
            assert!(set_plugins_enabled(&path, false).is_err());
            assert_eq!(fs::read_to_string(&path).unwrap(), raw);
            assert!(!sidecar(&path, "state.json").exists());
        }
    }

    #[test]
    fn invalid_group_or_provenance_preserves_the_existing_file() {
        let (_directory, path) = fixture(json!({"enabledPlugins":["personal"]}));
        let before = fs::read(&path).unwrap();
        assert!(merge(&path, &[], &selected(&["plugin"])).is_err());
        assert_eq!(fs::read(&path).unwrap(), before);
        fs::write(sidecar(&path, "state.json"), b"{broken").unwrap();
        assert!(reset(&path).is_err());
        assert_eq!(fs::read(&path).unwrap(), before);
    }

    #[test]
    fn backup_keeps_the_first_exact_user_file_and_private_permissions() {
        let (_directory, path) = fixture(json!({"personal":"original"}));
        let before = fs::read(&path).unwrap();
        merge(&path, &[], &selected(&["first"])).unwrap();
        merge(&path, &[], &selected(&["second"])).unwrap();
        let saved = sidecar(&path, "backup");
        assert_eq!(fs::read(&saved).unwrap(), before);
        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt;
            for file in [&path, &saved, &sidecar(&path, "state.json")] {
                assert_eq!(
                    fs::metadata(file).unwrap().permissions().mode() & 0o777,
                    0o600
                );
            }
        }
    }

    #[test]
    fn concurrent_writers_keep_personal_data_and_a_consistent_ledger() {
        let (_directory, path) = fixture(json!({"personal":true}));
        let barrier = Arc::new(Barrier::new(4));
        let threads: Vec<_> = (0..4)
            .map(|number| {
                let path = path.clone();
                let barrier = barrier.clone();
                std::thread::spawn(move || {
                    barrier.wait();
                    for _ in 0..8 {
                        merge(&path, &[], &selected(&[&format!("plugin-{number}")])).unwrap();
                    }
                })
            })
            .collect();
        for thread in threads {
            thread.join().unwrap();
        }
        assert_eq!(
            contents(&path)["enabledPlugins"].as_object().unwrap().len(),
            1
        );
        reset(&path).unwrap();
        assert_eq!(contents(&path), json!({"personal":true}));
        assert!(!fs::read_dir(path.parent().unwrap())
            .unwrap()
            .any(|entry| entry
                .unwrap()
                .file_name()
                .to_string_lossy()
                .starts_with(".aictx-")));
    }

    #[cfg(unix)]
    #[test]
    fn settings_symlinks_and_their_targets_are_untouched() {
        let (directory, path) = fixture(json!({"personal":true}));
        let link = directory.path().join("settings.json");
        std::os::unix::fs::symlink(&path, &link).unwrap();
        assert!(merge(&link, &[], &selected(&["plugin"])).is_err());
        assert!(reset(&link).is_err());
        assert_eq!(contents(&path), json!({"personal":true}));
        assert!(link.is_symlink());
    }

    #[test]
    fn reset_through_symlinker_preserves_user_settings_in_every_scope() {
        use crate::config::{AiConfig, AppConfig, BaseConfig, CliEntry, PathsConfig};
        use crate::scope::{ResolvedScope, Scope};
        for scope in [Scope::Global, Scope::Project, Scope::UserProject] {
            let directory = tempfile::tempdir().unwrap();
            let root = directory.path();
            let config = AppConfig {
                base: BaseConfig {
                    skills: vec![],
                    agents: vec![],
                    commands: vec![],
                    mcp: vec![],
                    rules: vec![],
                    plugins: vec![],
                    theme: String::new(),
                },
                ai: AiConfig {
                    enabled: false,
                    provider: String::new(),
                    model: String::new(),
                    fallback: None,
                    max_tokens: 0,
                    cache_ttl: String::new(),
                },
                paths: PathsConfig {
                    skills_dir: root.join("source/skills"),
                    agents_dir: root.join("source/agents"),
                    commands_dir: root.join("source/commands"),
                    hooks_dir: root.join("source/hooks"),
                    rules_dir: root.join("source/rules"),
                    config_dir: root.join("config"),
                    profiles_dir: root.join("profiles"),
                },
                cli_registry: vec![CliEntry {
                    name: "claude".into(),
                    config_dir: root.to_path_buf(),
                    project_dir: ".claude".into(),
                    supports: vec!["plugins".into()],
                    scopes: vec!["global".into(), "project".into(), "user-project".into()],
                    detect: None,
                }],
            };
            let target = if scope == Scope::Project {
                root.join(".claude")
            } else {
                root.to_path_buf()
            };
            fs::create_dir_all(&target).unwrap();
            let name = if scope == Scope::UserProject {
                "settings.json"
            } else {
                "settings.local.json"
            };
            let path = target.join(name);
            fs::write(&path, b"{\"personal\":true}").unwrap();
            merge(&path, &[], &selected(&["managed"])).unwrap();
            let resolved = ResolvedScope {
                scope,
                target_dir: root.to_path_buf(),
                project_root: None,
                supports_symlinks: false,
            };
            crate::symlinker::reset(&config, &resolved).unwrap();
            assert_eq!(contents(&path), json!({"personal":true}));
        }
    }
}
