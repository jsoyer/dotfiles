use anyhow::Result;
use serde::Deserialize;
use std::collections::HashMap;
use std::path::{Path, PathBuf};
use walkdir::WalkDir;

/// External patterns loaded from patterns.yaml
#[derive(Debug, Deserialize)]
#[allow(dead_code)]
pub struct PatternsConfig {
    #[serde(default)]
    pub languages: Vec<PatternEntry>,
    #[serde(default)]
    pub frameworks: Vec<FrameworkEntry>,
    #[serde(default)]
    pub infrastructure: Vec<PatternEntry>,
    #[serde(default)]
    pub databases: Vec<DepEntry>,
    #[serde(default)]
    pub tools: Vec<PatternEntry>,
    #[serde(default)]
    pub ci: Vec<PatternEntry>,
}

#[derive(Debug, Deserialize)]
pub struct PatternEntry {
    pub name: String,
    #[serde(default)]
    pub extensions: Vec<String>,
    #[serde(default)]
    pub config_files: Vec<String>,
}

#[derive(Debug, Deserialize)]
pub struct FrameworkEntry {
    pub name: String,
    #[serde(default)]
    pub config_files: Vec<String>,
    #[serde(default)]
    pub deps: Vec<String>,
}

#[derive(Debug, Deserialize)]
#[allow(dead_code)]
pub struct DepEntry {
    pub name: String,
    #[serde(default)]
    pub deps: Vec<String>,
}

impl PatternsConfig {
    pub fn load() -> Self {
        let config_dir = crate::config::AppConfig::config_dir();
        let path = config_dir.join("patterns.yaml");
        if path.exists() {
            if let Ok(content) = std::fs::read_to_string(&path) {
                if let Ok(config) = serde_yaml::from_str(&content) {
                    return config;
                }
            }
        }
        // Fallback to empty (use built-in detection)
        Self {
            languages: vec![],
            frameworks: vec![],
            infrastructure: vec![],
            databases: vec![],
            tools: vec![],
            ci: vec![],
        }
    }

    pub fn has_languages(&self) -> bool {
        !self.languages.is_empty()
    }
}

#[derive(Debug, Clone)]
pub struct Workspace {
    pub name: String,
    pub path: PathBuf,
    pub languages: Vec<String>,
}

#[derive(Debug, Clone)]
pub struct ProjectFingerprint {
    pub languages: Vec<Detection>,
    pub frameworks: Vec<Detection>,
    pub infrastructure: Vec<Detection>,
    pub databases: Vec<Detection>,
    pub tools: Vec<Detection>,
    pub ci: Vec<Detection>,
    pub file_counts: HashMap<String, usize>,
    pub project_dir: PathBuf,
    pub workspaces: Vec<Workspace>,
}

#[derive(Debug, Clone)]
pub struct Detection {
    pub name: String,
    pub confidence: f32,
    pub signals: Vec<String>,
}

pub struct Scanner;

impl Scanner {
    pub fn scan(project_dir: &Path) -> Result<ProjectFingerprint> {
        let patterns = PatternsConfig::load();
        let file_counts = Self::count_extensions(project_dir);
        let config_files = Self::detect_config_files(project_dir);
        let deps = Self::detect_dependencies(project_dir);

        // Use patterns.yaml if available, otherwise fall back to built-in detection
        let languages = if patterns.has_languages() {
            Self::detect_languages_from_patterns(&patterns.languages, &file_counts, &config_files)
        } else {
            Self::detect_languages(&file_counts, &config_files)
        };

        let frameworks = if !patterns.frameworks.is_empty() {
            Self::detect_frameworks_from_patterns(&patterns.frameworks, &config_files, &deps)
        } else {
            Self::detect_frameworks(&config_files, &deps)
        };

        let infrastructure = Self::detect_infrastructure(&config_files);
        let databases = Self::detect_databases(&config_files, &deps);
        let tools = Self::detect_tools(&config_files);
        let ci = Self::detect_ci(&config_files);

        let workspaces = Self::detect_workspaces(project_dir, &config_files);

        Ok(ProjectFingerprint {
            languages,
            frameworks,
            infrastructure,
            databases,
            tools,
            ci,
            file_counts,
            project_dir: project_dir.to_path_buf(),
            workspaces,
        })
    }

    fn count_extensions(dir: &Path) -> HashMap<String, usize> {
        let mut counts = HashMap::new();
        for entry in WalkDir::new(dir)
            .max_depth(6)
            .into_iter()
            .filter_entry(|e| {
                let name = e.file_name().to_string_lossy();
                !name.starts_with('.')
                    && name != "node_modules"
                    && name != "target"
                    && name != "dist"
                    && name != "build"
                    && name != "__pycache__"
                    && name != "vendor"
                    && name != ".git"
            })
            .filter_map(|e| e.ok())
        {
            if entry.file_type().is_file() {
                if let Some(ext) = entry.path().extension() {
                    *counts.entry(ext.to_string_lossy().to_string()).or_insert(0) += 1;
                }
            }
        }
        counts
    }

    fn detect_config_files(dir: &Path) -> Vec<String> {
        let candidates = [
            "tsconfig.json",
            "package.json",
            "Cargo.toml",
            "Cargo.lock",
            "go.mod",
            "go.sum",
            "pyproject.toml",
            "setup.py",
            "requirements.txt",
            "Pipfile",
            "Gemfile",
            "composer.json",
            "pom.xml",
            "build.gradle",
            "build.gradle.kts",
            "CMakeLists.txt",
            "Makefile",
            "next.config.js",
            "next.config.mjs",
            "next.config.ts",
            "vite.config.ts",
            "vite.config.js",
            "nuxt.config.ts",
            "svelte.config.js",
            "angular.json",
            "vue.config.js",
            "tailwind.config.js",
            "tailwind.config.ts",
            "postcss.config.js",
            "Dockerfile",
            "docker-compose.yml",
            "docker-compose.yaml",
            "terraform.tf",
            "main.tf",
            "kubernetes.yaml",
            ".eslintrc.js",
            ".eslintrc.json",
            "eslint.config.js",
            "biome.json",
            "prettier.config.js",
            ".prettierrc",
            "jest.config.js",
            "jest.config.ts",
            "vitest.config.ts",
            "playwright.config.ts",
            "cypress.config.ts",
            ".github/workflows",
            ".gitlab-ci.yml",
            "Jenkinsfile",
            "prisma/schema.prisma",
            "drizzle.config.ts",
            "CLAUDE.md",
            ".claude/settings.json",
            "Brewfile",
            "Aptfile",
            "Dnffile",
            "nx.json",
            "turbo.json",
            "pnpm-workspace.yaml",
            "lerna.json",
            "rush.json",
        ];

        candidates
            .iter()
            .filter(|f| {
                let path = dir.join(f);
                path.exists() || path.is_dir()
            })
            .map(|f| f.to_string())
            .collect()
    }

    fn detect_dependencies(dir: &Path) -> HashMap<String, Vec<String>> {
        let mut deps = HashMap::new();

        // package.json
        let pkg_path = dir.join("package.json");
        if pkg_path.exists() {
            if let Ok(content) = std::fs::read_to_string(&pkg_path) {
                if let Ok(json) = serde_json::from_str::<serde_json::Value>(&content) {
                    let mut npm_deps = Vec::new();
                    for section in ["dependencies", "devDependencies"] {
                        if let Some(obj) = json.get(section).and_then(|v| v.as_object()) {
                            npm_deps.extend(obj.keys().cloned());
                        }
                    }
                    deps.insert("npm".to_string(), npm_deps);
                }
            }
        }

        // Cargo.toml
        let cargo_path = dir.join("Cargo.toml");
        if cargo_path.exists() {
            if let Ok(content) = std::fs::read_to_string(&cargo_path) {
                let mut cargo_deps = Vec::new();
                let mut in_deps = false;
                for line in content.lines() {
                    if line.starts_with("[dependencies]") || line.starts_with("[dev-dependencies]")
                    {
                        in_deps = true;
                        continue;
                    }
                    if line.starts_with('[') {
                        in_deps = false;
                    }
                    if in_deps {
                        if let Some(name) = line.split('=').next() {
                            let name = name.trim();
                            if !name.is_empty() && !name.starts_with('#') {
                                cargo_deps.push(name.to_string());
                            }
                        }
                    }
                }
                deps.insert("cargo".to_string(), cargo_deps);
            }
        }

        // pyproject.toml / requirements.txt
        let req_path = dir.join("requirements.txt");
        if req_path.exists() {
            if let Ok(content) = std::fs::read_to_string(&req_path) {
                let py_deps: Vec<String> = content
                    .lines()
                    .filter(|l| !l.starts_with('#') && !l.trim().is_empty())
                    .map(|l| {
                        l.split(['=', '>', '<', '~', '!', ';', '['])
                            .next()
                            .unwrap_or("")
                            .trim()
                            .to_string()
                    })
                    .filter(|s| !s.is_empty())
                    .collect();
                deps.insert("pip".to_string(), py_deps);
            }
        }

        // go.mod
        let gomod_path = dir.join("go.mod");
        if gomod_path.exists() {
            if let Ok(content) = std::fs::read_to_string(&gomod_path) {
                let go_deps: Vec<String> = content
                    .lines()
                    .filter(|l| l.starts_with('\t') && !l.contains("//"))
                    .map(|l| l.trim().split_whitespace().next().unwrap_or("").to_string())
                    .filter(|s| !s.is_empty())
                    .collect();
                deps.insert("go".to_string(), go_deps);
            }
        }

        deps
    }

    fn detect_languages(
        file_counts: &HashMap<String, usize>,
        config_files: &[String],
    ) -> Vec<Detection> {
        let mut langs = Vec::new();

        let lang_map: &[(&str, &[&str], &[&str])] = &[
            ("typescript", &["ts", "tsx"], &["tsconfig.json"]),
            (
                "javascript",
                &["js", "jsx", "mjs", "cjs"],
                &["package.json"],
            ),
            ("rust", &["rs"], &["Cargo.toml"]),
            ("go", &["go"], &["go.mod"]),
            (
                "python",
                &["py"],
                &["pyproject.toml", "setup.py", "requirements.txt"],
            ),
            ("java", &["java"], &["pom.xml", "build.gradle"]),
            ("kotlin", &["kt", "kts"], &["build.gradle.kts"]),
            ("swift", &["swift"], &[]),
            (
                "cpp",
                &["cpp", "cc", "cxx", "hpp", "h"],
                &["CMakeLists.txt"],
            ),
            ("csharp", &["cs"], &[]),
            ("ruby", &["rb"], &["Gemfile"]),
            ("php", &["php"], &["composer.json"]),
            ("lua", &["lua"], &[]),
            ("shell", &["sh", "bash", "zsh"], &["Brewfile"]),
            ("nix", &["nix"], &[]),
            ("elixir", &["ex", "exs"], &[]),
            ("dart", &["dart"], &[]),
        ];

        for (name, exts, configs) in lang_map {
            let file_count: usize = exts.iter().map(|e| file_counts.get(*e).unwrap_or(&0)).sum();
            let has_config = configs
                .iter()
                .any(|c| config_files.contains(&c.to_string()));

            if file_count > 0 || has_config {
                let confidence = if file_count > 20 && has_config {
                    1.0
                } else if file_count > 5 {
                    0.9
                } else if has_config {
                    0.8
                } else if file_count > 0 {
                    0.5
                } else {
                    0.3
                };

                let mut signals = Vec::new();
                if file_count > 0 {
                    signals.push(format!("{} files ({})", exts.join("/"), file_count));
                }
                for c in configs
                    .iter()
                    .filter(|c| config_files.contains(&c.to_string()))
                {
                    signals.push(c.to_string());
                }

                langs.push(Detection {
                    name: name.to_string(),
                    confidence,
                    signals,
                });
            }
        }

        langs.sort_by(|a, b| b.confidence.partial_cmp(&a.confidence).unwrap());
        langs
    }

    fn detect_frameworks(
        config_files: &[String],
        deps: &HashMap<String, Vec<String>>,
    ) -> Vec<Detection> {
        let mut frameworks = Vec::new();
        let npm_deps = deps.get("npm").cloned().unwrap_or_default();

        let framework_map: &[(&str, &[&str], &[&str])] = &[
            (
                "nextjs",
                &["next.config.js", "next.config.mjs", "next.config.ts"],
                &["next"],
            ),
            ("react", &[], &["react", "react-dom"]),
            ("vue", &["vue.config.js", "nuxt.config.ts"], &["vue"]),
            ("angular", &["angular.json"], &["@angular/core"]),
            ("svelte", &["svelte.config.js"], &["svelte"]),
            ("express", &[], &["express"]),
            ("fastify", &[], &["fastify"]),
            ("nestjs", &[], &["@nestjs/core"]),
            ("django", &[], &[]),
            ("flask", &[], &[]),
            ("axum", &[], &[]),
            ("actix", &[], &[]),
            ("spring", &[], &[]),
            ("rails", &["Gemfile"], &[]),
            ("laravel", &["composer.json"], &[]),
            (
                "tailwind",
                &["tailwind.config.js", "tailwind.config.ts"],
                &["tailwindcss"],
            ),
            (
                "prisma",
                &["prisma/schema.prisma"],
                &["@prisma/client", "prisma"],
            ),
            ("drizzle", &["drizzle.config.ts"], &["drizzle-orm"]),
        ];

        for (name, configs, dep_names) in framework_map {
            let has_config = configs
                .iter()
                .any(|c| config_files.contains(&c.to_string()));
            let has_dep = dep_names.iter().any(|d| npm_deps.contains(&d.to_string()));

            if has_config || has_dep {
                let confidence = if has_config && has_dep {
                    0.95
                } else if has_config {
                    0.85
                } else {
                    0.75
                };

                let mut signals = Vec::new();
                for c in configs
                    .iter()
                    .filter(|c| config_files.contains(&c.to_string()))
                {
                    signals.push(c.to_string());
                }
                for d in dep_names
                    .iter()
                    .filter(|d| npm_deps.contains(&d.to_string()))
                {
                    signals.push(format!("dep: {}", d));
                }

                frameworks.push(Detection {
                    name: name.to_string(),
                    confidence,
                    signals,
                });
            }
        }

        frameworks.sort_by(|a, b| b.confidence.partial_cmp(&a.confidence).unwrap());
        frameworks
    }

    fn detect_infrastructure(config_files: &[String]) -> Vec<Detection> {
        let mut infra = Vec::new();

        let infra_map: &[(&str, &[&str])] = &[
            (
                "docker",
                &["Dockerfile", "docker-compose.yml", "docker-compose.yaml"],
            ),
            ("terraform", &["terraform.tf", "main.tf"]),
            ("kubernetes", &["kubernetes.yaml"]),
        ];

        for (name, configs) in infra_map {
            let matches: Vec<String> = configs
                .iter()
                .filter(|c| config_files.contains(&c.to_string()))
                .map(|c| c.to_string())
                .collect();

            if !matches.is_empty() {
                infra.push(Detection {
                    name: name.to_string(),
                    confidence: 0.9,
                    signals: matches,
                });
            }
        }

        infra
    }

    fn detect_databases(
        config_files: &[String],
        deps: &HashMap<String, Vec<String>>,
    ) -> Vec<Detection> {
        let mut dbs = Vec::new();
        let npm_deps = deps.get("npm").cloned().unwrap_or_default();

        if config_files.contains(&"prisma/schema.prisma".to_string()) {
            dbs.push(Detection {
                name: "postgresql".to_string(),
                confidence: 0.8,
                signals: vec!["prisma/schema.prisma".to_string()],
            });
        }

        let db_deps: &[(&str, &[&str])] = &[
            ("postgresql", &["pg", "postgres", "typeorm", "knex"]),
            ("mysql", &["mysql2", "mysql"]),
            ("mongodb", &["mongodb", "mongoose"]),
            ("redis", &["redis", "ioredis"]),
            ("sqlite", &["better-sqlite3", "sqlite3"]),
        ];

        for (name, dep_names) in db_deps {
            let matches: Vec<String> = dep_names
                .iter()
                .filter(|d| npm_deps.contains(&d.to_string()))
                .map(|d| format!("dep: {}", d))
                .collect();

            if !matches.is_empty() && !dbs.iter().any(|d| d.name == *name) {
                dbs.push(Detection {
                    name: name.to_string(),
                    confidence: 0.75,
                    signals: matches,
                });
            }
        }

        dbs
    }

    fn detect_tools(config_files: &[String]) -> Vec<Detection> {
        let mut tools = Vec::new();

        let tool_map: &[(&str, &[&str])] = &[
            (
                "eslint",
                &[".eslintrc.js", ".eslintrc.json", "eslint.config.js"],
            ),
            ("biome", &["biome.json"]),
            ("prettier", &["prettier.config.js", ".prettierrc"]),
            ("jest", &["jest.config.js", "jest.config.ts"]),
            ("vitest", &["vitest.config.ts"]),
            ("playwright", &["playwright.config.ts"]),
            ("cypress", &["cypress.config.ts"]),
        ];

        for (name, configs) in tool_map {
            let matches: Vec<String> = configs
                .iter()
                .filter(|c| config_files.contains(&c.to_string()))
                .map(|c| c.to_string())
                .collect();

            if !matches.is_empty() {
                tools.push(Detection {
                    name: name.to_string(),
                    confidence: 1.0,
                    signals: matches,
                });
            }
        }

        tools
    }

    fn detect_ci(config_files: &[String]) -> Vec<Detection> {
        let mut ci = Vec::new();

        if config_files.contains(&".github/workflows".to_string()) {
            ci.push(Detection {
                name: "github-actions".to_string(),
                confidence: 1.0,
                signals: vec![".github/workflows/".to_string()],
            });
        }
        if config_files.contains(&".gitlab-ci.yml".to_string()) {
            ci.push(Detection {
                name: "gitlab-ci".to_string(),
                confidence: 1.0,
                signals: vec![".gitlab-ci.yml".to_string()],
            });
        }
        if config_files.contains(&"Jenkinsfile".to_string()) {
            ci.push(Detection {
                name: "jenkins".to_string(),
                confidence: 1.0,
                signals: vec!["Jenkinsfile".to_string()],
            });
        }

        ci
    }

    // ── Monorepo workspace detection ──────────────────────────────

    fn detect_workspaces(cwd: &Path, config_files: &[String]) -> Vec<Workspace> {
        let mut workspaces = Vec::new();

        // pnpm-workspace.yaml
        if config_files.contains(&"pnpm-workspace.yaml".to_string()) {
            if let Ok(content) = std::fs::read_to_string(cwd.join("pnpm-workspace.yaml")) {
                for line in content.lines() {
                    let trimmed = line
                        .trim()
                        .trim_start_matches("- ")
                        .trim_matches('\'')
                        .trim_matches('"');
                    if trimmed.contains('*') {
                        let base = trimmed.trim_end_matches("/*").trim_end_matches("/**");
                        let base_path = cwd.join(base);
                        if base_path.is_dir() {
                            if let Ok(entries) = std::fs::read_dir(&base_path) {
                                for entry in entries.filter_map(|e| e.ok()) {
                                    if entry.path().is_dir() {
                                        let name = format!(
                                            "{}/{}",
                                            base,
                                            entry.file_name().to_string_lossy()
                                        );
                                        let langs = Self::detect_workspace_languages(&entry.path());
                                        workspaces.push(Workspace {
                                            name,
                                            path: entry.path(),
                                            languages: langs,
                                        });
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        // package.json workspaces (only if pnpm-workspace.yaml didn't produce results)
        if workspaces.is_empty() && config_files.contains(&"package.json".to_string()) {
            if let Ok(content) = std::fs::read_to_string(cwd.join("package.json")) {
                if let Ok(json) = serde_json::from_str::<serde_json::Value>(&content) {
                    if let Some(ws) = json.get("workspaces") {
                        let patterns: Vec<String> = match ws {
                            serde_json::Value::Array(arr) => arr
                                .iter()
                                .filter_map(|v| v.as_str().map(String::from))
                                .collect(),
                            serde_json::Value::Object(obj) => obj
                                .get("packages")
                                .and_then(|p| p.as_array())
                                .map(|arr| {
                                    arr.iter()
                                        .filter_map(|v| v.as_str().map(String::from))
                                        .collect()
                                })
                                .unwrap_or_default(),
                            _ => vec![],
                        };
                        for pattern in patterns {
                            let base = pattern.trim_end_matches("/*").trim_end_matches("/**");
                            let base_path = cwd.join(base);
                            if base_path.is_dir() {
                                if let Ok(entries) = std::fs::read_dir(&base_path) {
                                    for entry in entries.filter_map(|e| e.ok()) {
                                        if entry.path().is_dir() {
                                            let name = format!(
                                                "{}/{}",
                                                base,
                                                entry.file_name().to_string_lossy()
                                            );
                                            let langs =
                                                Self::detect_workspace_languages(&entry.path());
                                            workspaces.push(Workspace {
                                                name,
                                                path: entry.path(),
                                                languages: langs,
                                            });
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        // nx.json — projects are typically in apps/, libs/, packages/
        if workspaces.is_empty() && config_files.contains(&"nx.json".to_string()) {
            for dir in ["apps", "libs", "packages"] {
                let base = cwd.join(dir);
                if base.is_dir() {
                    if let Ok(entries) = std::fs::read_dir(&base) {
                        for entry in entries.filter_map(|e| e.ok()) {
                            if entry.path().is_dir() {
                                let name =
                                    format!("{}/{}", dir, entry.file_name().to_string_lossy());
                                let langs = Self::detect_workspace_languages(&entry.path());
                                workspaces.push(Workspace {
                                    name,
                                    path: entry.path(),
                                    languages: langs,
                                });
                            }
                        }
                    }
                }
            }
        }

        workspaces
    }

    fn detect_workspace_languages(path: &Path) -> Vec<String> {
        let mut langs = Vec::new();
        if path.join("tsconfig.json").exists() || path.join("package.json").exists() {
            langs.push("typescript".to_string());
        }
        if path.join("Cargo.toml").exists() {
            langs.push("rust".to_string());
        }
        if path.join("go.mod").exists() {
            langs.push("go".to_string());
        }
        if path.join("pyproject.toml").exists() || path.join("setup.py").exists() {
            langs.push("python".to_string());
        }
        if path.join("pubspec.yaml").exists() {
            langs.push("dart".to_string());
        }
        langs
    }

    // ── Pattern-based detection (from patterns.yaml) ──────────────

    fn detect_languages_from_patterns(
        patterns: &[PatternEntry],
        file_counts: &HashMap<String, usize>,
        config_files: &[String],
    ) -> Vec<Detection> {
        let mut langs = Vec::new();

        for pattern in patterns {
            let file_count: usize = pattern
                .extensions
                .iter()
                .map(|e| file_counts.get(e.as_str()).unwrap_or(&0))
                .sum();
            let has_config = pattern
                .config_files
                .iter()
                .any(|c| config_files.contains(c));

            if file_count > 0 || has_config {
                let confidence = if file_count > 20 && has_config {
                    1.0
                } else if file_count > 5 {
                    0.9
                } else if has_config {
                    0.8
                } else if file_count > 0 {
                    0.5
                } else {
                    0.3
                };

                let mut signals = Vec::new();
                if file_count > 0 {
                    signals.push(format!(
                        "{} files ({})",
                        pattern.extensions.join("/"),
                        file_count
                    ));
                }
                for c in pattern
                    .config_files
                    .iter()
                    .filter(|c| config_files.contains(c))
                {
                    signals.push(c.to_string());
                }

                langs.push(Detection {
                    name: pattern.name.clone(),
                    confidence,
                    signals,
                });
            }
        }

        langs.sort_by(|a, b| b.confidence.partial_cmp(&a.confidence).unwrap());
        langs
    }

    fn detect_frameworks_from_patterns(
        patterns: &[FrameworkEntry],
        config_files: &[String],
        deps: &HashMap<String, Vec<String>>,
    ) -> Vec<Detection> {
        let mut frameworks = Vec::new();
        let all_deps: Vec<String> = deps.values().flatten().cloned().collect();

        for pattern in patterns {
            let has_config = pattern
                .config_files
                .iter()
                .any(|c| config_files.contains(c));
            let has_dep = pattern.deps.iter().any(|d| all_deps.contains(d));

            if has_config || has_dep {
                let confidence = if has_config && has_dep {
                    0.95
                } else if has_config {
                    0.85
                } else {
                    0.75
                };

                let mut signals = Vec::new();
                for c in pattern
                    .config_files
                    .iter()
                    .filter(|c| config_files.contains(c))
                {
                    signals.push(c.to_string());
                }
                for d in pattern.deps.iter().filter(|d| all_deps.contains(d)) {
                    signals.push(format!("dep: {}", d));
                }

                frameworks.push(Detection {
                    name: pattern.name.clone(),
                    confidence,
                    signals,
                });
            }
        }

        frameworks.sort_by(|a, b| b.confidence.partial_cmp(&a.confidence).unwrap());
        frameworks
    }
}

impl ProjectFingerprint {
    pub fn is_empty(&self) -> bool {
        self.languages.is_empty() && self.frameworks.is_empty() && self.infrastructure.is_empty()
    }

    pub fn print(&self) {
        println!("Project: {}", self.project_dir.display());
        println!();

        if !self.languages.is_empty() {
            println!("Languages:");
            for d in &self.languages {
                println!(
                    "  {:<16} {:.0}%  [{}]",
                    d.name,
                    d.confidence * 100.0,
                    d.signals.join(", ")
                );
            }
        }

        if !self.frameworks.is_empty() {
            println!("\nFrameworks:");
            for d in &self.frameworks {
                println!(
                    "  {:<16} {:.0}%  [{}]",
                    d.name,
                    d.confidence * 100.0,
                    d.signals.join(", ")
                );
            }
        }

        if !self.infrastructure.is_empty() {
            println!("\nInfrastructure:");
            for d in &self.infrastructure {
                println!("  {:<16} [{}]", d.name, d.signals.join(", "));
            }
        }

        if !self.databases.is_empty() {
            println!("\nDatabases:");
            for d in &self.databases {
                println!("  {:<16} [{}]", d.name, d.signals.join(", "));
            }
        }

        if !self.tools.is_empty() {
            println!("\nTools:");
            for d in &self.tools {
                println!("  {:<16} [{}]", d.name, d.signals.join(", "));
            }
        }

        if !self.ci.is_empty() {
            println!("\nCI/CD:");
            for d in &self.ci {
                println!("  {:<16} [{}]", d.name, d.signals.join(", "));
            }
        }

        if !self.workspaces.is_empty() {
            println!("\nMonorepo ({} workspaces)", self.workspaces.len());
            for ws in &self.workspaces {
                println!("  {:<30} {}", ws.name, ws.languages.join(", "));
            }
        }

        let total_files: usize = self.file_counts.values().sum();
        println!("\nTotal files scanned: {}", total_files);
    }

    pub fn language_names(&self) -> Vec<String> {
        self.languages.iter().map(|l| l.name.clone()).collect()
    }

    pub fn all_tags(&self) -> Vec<String> {
        let mut tags: Vec<String> = Vec::new();
        for d in &self.languages {
            tags.push(d.name.clone());
        }
        for d in &self.frameworks {
            tags.push(d.name.clone());
        }
        for d in &self.infrastructure {
            tags.push(d.name.clone());
        }
        for d in &self.databases {
            tags.push(d.name.clone());
        }
        for d in &self.tools {
            tags.push(d.name.clone());
        }
        for d in &self.ci {
            tags.push(d.name.clone());
        }
        tags
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;
    use std::path::PathBuf;

    fn temp_dir(name: &str) -> PathBuf {
        let dir = std::env::temp_dir().join(format!("aictx-scanner-test-{}", name));
        let _ = fs::create_dir_all(&dir);
        dir
    }

    fn cleanup(dir: &PathBuf) {
        let _ = fs::remove_dir_all(dir);
    }

    #[test]
    fn detects_monorepo_config_files_nx() {
        let dir = temp_dir("mono-nx");
        fs::write(dir.join("nx.json"), "{}").unwrap();
        let fp = Scanner::scan(&dir).unwrap();
        assert!(fp.workspaces.is_empty());
        cleanup(&dir);
    }

    #[test]
    fn detects_monorepo_config_files_turbo() {
        let dir = temp_dir("mono-turbo");
        fs::write(dir.join("turbo.json"), "{}").unwrap();
        let fp = Scanner::scan(&dir).unwrap();
        assert!(fp.workspaces.is_empty());
        cleanup(&dir);
    }

    #[test]
    fn detects_monorepo_config_files_lerna() {
        let dir = temp_dir("mono-lerna");
        fs::write(dir.join("lerna.json"), "{}").unwrap();
        let fp = Scanner::scan(&dir).unwrap();
        assert!(fp.workspaces.is_empty());
        cleanup(&dir);
    }

    #[test]
    fn detects_monorepo_config_files_rush() {
        let dir = temp_dir("mono-rush");
        fs::write(dir.join("rush.json"), "{}").unwrap();
        let fp = Scanner::scan(&dir).unwrap();
        assert!(fp.workspaces.is_empty());
        cleanup(&dir);
    }

    #[test]
    fn detects_pnpm_workspaces() {
        let dir = temp_dir("pnpm-ws");
        fs::create_dir_all(dir.join("packages/app-a")).unwrap();
        fs::create_dir_all(dir.join("packages/lib-b")).unwrap();
        fs::write(dir.join("packages/app-a/package.json"), r#"{"name":"app-a"}"#).unwrap();
        fs::write(dir.join("packages/lib-b/tsconfig.json"), "{}").unwrap();
        fs::write(
            dir.join("pnpm-workspace.yaml"),
            "packages:\n  - 'packages/*'\n",
        )
        .unwrap();
        let fp = Scanner::scan(&dir).unwrap();
        assert!(!fp.workspaces.is_empty(), "Expected workspaces to be detected");
        let names: Vec<&str> = fp.workspaces.iter().map(|w| w.name.as_str()).collect();
        assert!(names.iter().any(|n| n.contains("app-a")), "got: {:?}", names);
        assert!(names.iter().any(|n| n.contains("lib-b")), "got: {:?}", names);
        cleanup(&dir);
    }

    #[test]
    fn pnpm_workspace_detects_languages() {
        let dir = temp_dir("pnpm-ws-langs");
        fs::create_dir_all(dir.join("packages/ts-pkg")).unwrap();
        fs::write(dir.join("packages/ts-pkg/tsconfig.json"), "{}").unwrap();
        fs::create_dir_all(dir.join("packages/rust-pkg")).unwrap();
        fs::write(
            dir.join("packages/rust-pkg/Cargo.toml"),
            "[package]\nname=\"rust-pkg\"\nversion=\"0.1.0\"\n",
        )
        .unwrap();
        fs::write(
            dir.join("pnpm-workspace.yaml"),
            "packages:\n  - 'packages/*'\n",
        )
        .unwrap();
        let fp = Scanner::scan(&dir).unwrap();
        let ts_pkg = fp
            .workspaces
            .iter()
            .find(|w| w.name.contains("ts-pkg"))
            .expect("ts-pkg not found");
        assert!(ts_pkg.languages.contains(&"typescript".to_string()));
        let rust_pkg = fp
            .workspaces
            .iter()
            .find(|w| w.name.contains("rust-pkg"))
            .expect("rust-pkg not found");
        assert!(rust_pkg.languages.contains(&"rust".to_string()));
        cleanup(&dir);
    }

    #[test]
    fn detects_package_json_workspaces() {
        let dir = temp_dir("pkg-json-ws");
        fs::create_dir_all(dir.join("apps/web")).unwrap();
        fs::create_dir_all(dir.join("apps/api")).unwrap();
        fs::write(dir.join("apps/web/package.json"), r#"{"name":"web"}"#).unwrap();
        fs::write(dir.join("apps/api/package.json"), r#"{"name":"api"}"#).unwrap();
        fs::write(
            dir.join("package.json"),
            r#"{"name":"root","workspaces":["apps/*"]}"#,
        )
        .unwrap();
        let fp = Scanner::scan(&dir).unwrap();
        assert!(!fp.workspaces.is_empty(), "Expected workspaces from package.json");
        let names: Vec<&str> = fp.workspaces.iter().map(|w| w.name.as_str()).collect();
        assert!(names.iter().any(|n| n.contains("web")), "got: {:?}", names);
        assert!(names.iter().any(|n| n.contains("api")), "got: {:?}", names);
        cleanup(&dir);
    }

    #[test]
    fn detects_nx_workspaces() {
        let dir = temp_dir("nx-ws");
        fs::create_dir_all(dir.join("apps/frontend")).unwrap();
        fs::create_dir_all(dir.join("libs/shared")).unwrap();
        fs::write(dir.join("apps/frontend/package.json"), r#"{"name":"frontend"}"#).unwrap();
        fs::write(dir.join("libs/shared/tsconfig.json"), "{}").unwrap();
        fs::write(dir.join("nx.json"), r#"{"version":2}"#).unwrap();
        let fp = Scanner::scan(&dir).unwrap();
        assert!(!fp.workspaces.is_empty(), "Expected nx workspaces");
        let names: Vec<&str> = fp.workspaces.iter().map(|w| w.name.as_str()).collect();
        assert!(names.iter().any(|n| n.contains("frontend")), "got: {:?}", names);
        assert!(names.iter().any(|n| n.contains("shared")), "got: {:?}", names);
        cleanup(&dir);
    }

    #[test]
    fn workspace_struct_fields() {
        let ws = Workspace {
            name: "packages/my-pkg".to_string(),
            path: PathBuf::from("/tmp/my-pkg"),
            languages: vec!["typescript".to_string()],
        };
        assert_eq!(ws.name, "packages/my-pkg");
        assert_eq!(ws.languages, vec!["typescript".to_string()]);
    }

    #[test]
    fn no_workspaces_for_plain_rust_project() {
        let dir = temp_dir("plain-rust");
        fs::write(
            dir.join("Cargo.toml"),
            "[package]\nname=\"plain\"\nversion=\"0.1.0\"\n",
        )
        .unwrap();
        let fp = Scanner::scan(&dir).unwrap();
        assert!(fp.workspaces.is_empty());
        cleanup(&dir);
    }
}
