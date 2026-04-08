use anyhow::{bail, Context, Result};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::path::PathBuf;

use crate::config::AppConfig;
use crate::matcher::{RecommendSource, Recommendation, Recommendations};
use crate::symlinker::ProjectStatus;

#[derive(Debug, Serialize, Deserialize)]
pub struct Profile {
    pub name: String,
    pub description: Option<String>,
    #[serde(default)]
    pub scope: Option<String>,
    pub skills: Vec<String>,
    pub agents: Vec<String>,
    pub commands: Vec<String>,
    pub mcp: Vec<String>,
    pub rules: Vec<String>,
    pub plugins: Vec<String>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ProjectMap {
    pub projects: HashMap<String, String>,
}

pub struct ProfileManager {
    profiles_dir: PathBuf,
    project_map_path: PathBuf,
}

impl ProfileManager {
    pub fn new(config: &AppConfig) -> Result<Self> {
        let profiles_dir = config.paths.profiles_dir.clone();
        let project_map_path = config.paths.config_dir.join("project-map.yaml");

        std::fs::create_dir_all(&profiles_dir)?;

        Ok(Self {
            profiles_dir,
            project_map_path,
        })
    }

    pub fn load(&self, name: &str) -> Result<Recommendations> {
        let path = self.profiles_dir.join(format!("{}.yaml", name));
        if !path.exists() {
            // Try in _generated/
            let gen_path = self.profiles_dir.join("_generated").join(format!("{}.yaml", name));
            if !gen_path.exists() {
                bail!("Profile '{}' not found", name);
            }
            return self.load_from_path(&gen_path);
        }
        self.load_from_path(&path)
    }

    /// Load profile with its scope metadata.
    pub fn load_with_scope(&self, name: &str) -> Result<(Recommendations, Option<String>)> {
        let path = self.profiles_dir.join(format!("{}.yaml", name));
        let path = if path.exists() {
            path
        } else {
            let gen_path = self.profiles_dir.join("_generated").join(format!("{}.yaml", name));
            if !gen_path.exists() {
                bail!("Profile '{}' not found", name);
            }
            gen_path
        };
        let content = std::fs::read_to_string(&path)
            .with_context(|| format!("Failed to read {}", path.display()))?;
        let profile: Profile = serde_yaml::from_str(&content)?;
        let scope = profile.scope.clone();
        let recs = self.profile_to_recommendations(&profile);
        Ok((recs, scope))
    }

    fn profile_to_recommendations(&self, profile: &Profile) -> Recommendations {
        Recommendations {
            skills: profile
                .skills
                .iter()
                .map(|name| Recommendation {
                    name: name.clone(),
                    score: 1.0,
                    reason: "profile".to_string(),
                    source: RecommendSource::Base,
                })
                .collect(),
            agents: profile
                .agents
                .iter()
                .map(|name| Recommendation {
                    name: name.clone(),
                    score: 1.0,
                    reason: "profile".to_string(),
                    source: RecommendSource::Base,
                })
                .collect(),
            commands: profile
                .commands
                .iter()
                .map(|name| Recommendation {
                    name: name.clone(),
                    score: 1.0,
                    reason: "profile".to_string(),
                    source: RecommendSource::Base,
                })
                .collect(),
            mcp: profile.mcp.clone(),
            rules: profile.rules.clone(),
            plugins: profile.plugins.clone(),
        }
    }

    fn load_from_path(&self, path: &PathBuf) -> Result<Recommendations> {
        let content = std::fs::read_to_string(path)
            .with_context(|| format!("Failed to read {}", path.display()))?;
        let profile: Profile = serde_yaml::from_str(&content)?;

        Ok(Recommendations {
            skills: profile
                .skills
                .iter()
                .map(|name| Recommendation {
                    name: name.clone(),
                    score: 1.0,
                    reason: "profile".to_string(),
                    source: RecommendSource::Base,
                })
                .collect(),
            agents: profile
                .agents
                .iter()
                .map(|name| Recommendation {
                    name: name.clone(),
                    score: 1.0,
                    reason: "profile".to_string(),
                    source: RecommendSource::Base,
                })
                .collect(),
            commands: profile
                .commands
                .iter()
                .map(|name| Recommendation {
                    name: name.clone(),
                    score: 1.0,
                    reason: "profile".to_string(),
                    source: RecommendSource::Base,
                })
                .collect(),
            mcp: profile.mcp,
            rules: profile.rules,
            plugins: profile.plugins,
        })
    }

    pub fn save(&self, name: &str, status: &ProjectStatus) -> Result<()> {
        let profile = Profile {
            name: name.to_string(),
            description: None,
            scope: Some(status.scope.to_string()),
            skills: status.skills.clone(),
            agents: status.agents.clone(),
            commands: status.commands.clone(),
            mcp: status.mcp.clone(),
            rules: status.rules.clone(),
            plugins: status.plugins.clone(),
        };

        let yaml = serde_yaml::to_string(&profile)?;
        let path = self.profiles_dir.join(format!("{}.yaml", name));
        std::fs::write(&path, &yaml)?;

        // Update project map
        let project_dir = std::env::current_dir()?;
        self.update_project_map(&project_dir.to_string_lossy(), name)?;

        Ok(())
    }

    pub fn list(&self) -> Result<()> {
        println!("Profiles:");

        // Manual profiles
        if let Ok(entries) = std::fs::read_dir(&self.profiles_dir) {
            for entry in entries.filter_map(|e| e.ok()) {
                let path = entry.path();
                if path.extension().map_or(false, |e| e == "yaml") && path.is_file() {
                    let name = path.file_stem().unwrap().to_string_lossy();
                    println!("  {}", name);
                }
            }
        }

        // Generated profiles
        let gen_dir = self.profiles_dir.join("_generated");
        if gen_dir.exists() {
            println!("\nGenerated:");
            if let Ok(entries) = std::fs::read_dir(&gen_dir) {
                for entry in entries.filter_map(|e| e.ok()) {
                    let path = entry.path();
                    if path.extension().map_or(false, |e| e == "yaml") {
                        let name = path.file_stem().unwrap().to_string_lossy();
                        println!("  {}", name);
                    }
                }
            }
        }

        Ok(())
    }

    pub fn export(&self, name: &str) -> Result<String> {
        let path = self.profiles_dir.join(format!("{}.yaml", name));
        if !path.exists() {
            bail!("Profile '{}' not found", name);
        }
        std::fs::read_to_string(&path).with_context(|| "Failed to read profile")
    }

    pub fn import(&self, file: &str) -> Result<()> {
        let content = std::fs::read_to_string(file)?;
        let profile: Profile = serde_yaml::from_str(&content)?;
        let path = self.profiles_dir.join(format!("{}.yaml", profile.name));
        std::fs::write(&path, &content)?;
        Ok(())
    }

    fn update_project_map(&self, project_path: &str, profile_name: &str) -> Result<()> {
        let mut map = if self.project_map_path.exists() {
            let content = std::fs::read_to_string(&self.project_map_path)?;
            serde_yaml::from_str::<ProjectMap>(&content).unwrap_or(ProjectMap {
                projects: HashMap::new(),
            })
        } else {
            ProjectMap {
                projects: HashMap::new(),
            }
        };

        map.projects
            .insert(project_path.to_string(), profile_name.to_string());

        let yaml = serde_yaml::to_string(&map)?;
        std::fs::write(&self.project_map_path, yaml)?;

        Ok(())
    }

}
