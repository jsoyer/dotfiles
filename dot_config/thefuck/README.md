# The Fuck Configuration

Command correction tool that fixes mistakes in shell commands.

## Files

- `settings.py` — Configuration (mostly defaults)
- `rules/` — Custom correction rules directory (empty)

## Details

- **Tool**: The Fuck
- **Platform**: Linux, macOS
- **Purpose**: Auto-correct shell command typos
- **Theme**: N/A (CLI tool)

## Configuration

Current settings are mostly defaults:
- All rules enabled
- 3-second wait for slow commands
- Requires confirmation before applying fix
- History alterations enabled
- 3 close matches suggested

## Usage

```bash
fuck                    # Correct last command
thefuck --alias        # Show available aliases
TF_HISTORY=50 fuck     # Use custom history depth
```

## Key Features

- Suggests multiple corrections
- Learns from git, Python, apt, npm, etc.
- No colors flag support
- History-aware correction
- Can repeat corrections

## Dependencies

- Python 3.4+
- Shell integration (bash, zsh, fish)

## Customization

Add custom rules to `rules/` directory:
- Create Python files with correction functions
- Rules can use subprocess for advanced matching
