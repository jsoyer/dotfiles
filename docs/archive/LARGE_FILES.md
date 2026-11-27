# Large Tracked Files

Audit command:

```bash
git ls-tree -r -l HEAD | sort -k4 -nr | awk '{printf "%10.2f MB  %s\n", $4/1024/1024, $5}' | head -30
```

Largest tracked files at the latest audit:

| Size | Path | Decision |
| --- | --- | --- |
| 3.67 MB | `dot_config/zellij/plugins/zjstatus.wasm` | Keep for runtime, provenance/checksum in `docs/PROVENANCE.md`. Candidate for external download script later. |
| 2.47 MB | `dot_aictx/skills/react-native-best-practices/references/images/view-hierarchy-flattening.png` | Keep as vendored skill reference content. Candidate for pruning if repo size becomes an issue. |
| 1.00 MB | `dot_config/zellij/plugins/zellij-datetime.wasm` | Keep for runtime, provenance/checksum in `docs/PROVENANCE.md`. Candidate for external download script later. |
| 0.64 MB | `dot_aictx/skills/react-native-best-practices/references/images/bundle-treemap-source-map-explorer.png` | Keep as vendored skill reference content. |
| 0.59 MB | `dot_aictx/skills/react-native-best-practices/references/images/expo-atlas-treemap.png` | Keep as vendored skill reference content. |

Notes:

- Rust `target/` artifacts are no longer tracked.
- The remaining large files are either runtime plugin binaries or vendored skill reference assets.
- If the repository becomes too large, the best next cleanup is externalizing Zellij WASM downloads with pinned checksums, then reviewing image-heavy `dot_aictx` skills.
