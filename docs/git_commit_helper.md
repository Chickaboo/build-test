# Git Commit Helper

A smart Git commit wrapper that streamlines the commit process with automatic formatting retry, flexible message composition, and consistent behavior across platforms.

## Overview

This tool provides a single, predictable command that new contributors can use instead of remembering to run formatters manually. It handles staging, committing, and automatic format-retry workflows while staying fast and avoiding feature creep.

## Installation

1. Place `commit.py` in your project root (alongside your `.git` folder)
2. Make it executable (Unix/macOS): `chmod +x commit.py`
3. Optionally create a `format_project.py` script for automatic formatting

## Basic Usage

### Quick Start Examples

```bash
# Commit with a message
python commit.py -m "Add user authentication"

# Stage all changes and commit interactively (default behavior)
python commit.py --all

# Commit with auto-generated timestamp instead
python commit.py --all --auto-timestamp

# Amend the last commit (opens editor)
python commit.py --amend

# Preview what would happen without committing
python commit.py --dry-run --all -m "Preview changes"
```

## Command-Line Options

### Message Options

| Option | Description |
|--------|-------------|
| `-m MESSAGE` | Specify commit message directly |
| `--auto-timestamp` | Generate timestamp message instead of opening editor |

### Staging Options

| Option | Description |
|--------|-------------|
| `--all` | Stage all changes (tracked + untracked) before committing |

### Amend Options

| Option | Description |
|--------|-------------|
| `--amend` | Amend the previous commit |
| `--no-edit` | With `--amend`, keep the existing commit message |

### Formatting Options

| Option | Description |
|--------|-------------|
| `--no-format` | Skip automatic formatting retry on commit failure |

### Utility Options

| Option | Description |
|--------|-------------|
| `--dry-run` | Show what actions would be taken without executing them |

## Commit Message Behaviour

The script determines commit messages using this priority:

1. **Direct message**: `-m "Your message"` - Uses the provided message
2. **Interactive editor**: Default behavior when no `-m` is provided - Opens your preferred editor
3. **Amend with editor**: `--amend` (without `--no-edit`) - Opens editor with previous message
4. **Auto-timestamp**: `--auto-timestamp` - Generates timestamp-based message

### Interactive Editor Selection

The script finds your editor using this priority:

1. `GIT_EDITOR` environment variable
2. `EDITOR` environment variable
3. `VISUAL` environment variable
4. Platform defaults:
   - **Windows**: `notepad`
   - **Linux/macOS**: `nano`, `vim`, `vi`, or `emacs` (whichever is found first)

### Setting Your Preferred Editor

```bash
# Set for Git specifically
git config --global core.editor "code --wait"  # VS Code
git config --global core.editor "vim"          # Vim

# Or set environment variables
export EDITOR="nano"
export GIT_EDITOR="code --wait"
```

## Automatic Formatting Integration

When a commit fails and `--no-format` is not specified:

1. The script looks for `format_project.py` in the same directory
2. If found, it runs: `python format_project.py`
3. Re-stages modified tracked files and any new files
4. Retries the commit once

### Creating format_project.py

Example formatting script:

```python
#!/usr/bin/env python3
"""Project formatter - customize for your needs."""
import subprocess
import sys

def main():
    # Example: Run black, isort, and other formatters
    commands = [
        ["black", "."],
        ["isort", "."],
        ["autopep8", "--in-place", "--recursive", "."],
    ]

    for cmd in commands:
        try:
            subprocess.run(cmd, check=True)
            print(f"✓ {' '.join(cmd)}")
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            print(f"⚠ {' '.join(cmd)}: {e}")
            # Continue with other formatters

    return 0

if __name__ == "__main__":
    sys.exit(main())
```

## Common Workflows

### New Contributor Workflow
```bash
# Make changes, then:
python commit.py --all
# Opens editor with staged file list for context (default behavior)
```

### Quick Development Commits
```bash
# For small, obvious changes:
python commit.py --all -m "Fix typo in README"

# For work-in-progress with timestamp:
python commit.py --all --auto-timestamp
```

### Code Review Preparation
```bash
# Stage specific files manually, then:
git add src/important_file.py
python commit.py -m "Refactor authentication logic"

# Or stage everything and commit interactively (default):
python commit.py --all
```

### Fixing the Last Commit
```bash
# Amend with new message:
python commit.py --amend

# Amend without changing message:
python commit.py --amend --no-edit

# Add forgotten files to last commit:
git add forgotten_file.py
python commit.py --amend --no-edit
```

## Interactive Editor Features

When using the interactive editor, you'll see:

```
# Please enter the commit message for your changes.
# Lines starting with "#" will be ignored, and an empty message
# aborts the commit.
#
# Changes to be committed:
#	modified:   src/auth.py
#	modified:   tests/test_auth.py
#	modified:   README.md
#	... and 5 more files
```

- Lines starting with `#` are comments and will be ignored
- Empty messages abort the commit
- The staged files are listed for reference
- Save and close the editor to proceed with the commit

## Error Handling

### Exit Codes
- `0`: Success
- `1`: Commit failed (after formatting retry if enabled)
- `127`: Missing dependency (git or Python tools not found)

### Common Scenarios

**Nothing staged to commit:**
```
→ Attempting first commit: git commit -m "Your message"
Nothing to commit (clean working tree).

You have changes that aren't staged for commit:

  Modified files (not staged):
    src/auth.py
    tests/test_auth.py

  Untracked files:
    new_feature.py

To stage and commit these changes, use:
  python commit.py --all                    # Stage all changes and commit

Or stage files individually:
  git add <file>                            # Stage specific files
  python commit.py                          # Commit staged files
```

**Formatting helps fix the commit:**
```
→ Attempting first commit: git commit -m "Add feature"
Commit failed (exit 1).
First commit failed; running formatters then retrying once...
→ Formatting project: python format_project.py
→ Restaging modified tracked files: git add -u
→ Attempting second commit: git commit -m "Add feature"
Commit hash: abc123def456
Done.
```

**Editor cancelled:**
```
Opening editor for commit message...
Editor failed or was cancelled.
Commit cancelled: no message provided.
```

## Integration Tips

### PowerShell Alias (Windows)
```powershell
# Add to your PowerShell profile
function gc { python commit.py $args }
function gca { python commit.py --all $args }
function gci { python commit.py $args }
function gct { python commit.py --auto-timestamp $args }
```

### Bash Alias (Unix/macOS)
```bash
# Add to ~/.bashrc or ~/.zshrc
alias gc='python commit.py'
alias gca='python commit.py --all'
alias gci='python commit.py'
alias gct='python commit.py --auto-timestamp'
```

### Git Alias
```bash
# Add a Git alias
git config --global alias.smart-commit '!python commit.py'

# Usage: git smart-commit --all -m "Fix bug"
```

## Troubleshooting

### Editor Won't Open
- Check that your editor is installed and in PATH
- Try setting `EDITOR` environment variable explicitly
- Use `--dry-run` to test without committing

### Formatting Script Issues
- Ensure `format_project.py` is executable
- Test it independently: `python format_project.py`
- Use `--no-format` to skip formatting if it's causing problems

### Git Repository Issues
- Ensure you're in a Git repository
- The script will find the repo root automatically
- Check that `git` is installed and in PATH

## Philosophy

This script intentionally:

- **Stays simple**: No push/pull/test orchestration
- **Fails fast**: Clear error messages and exit codes
- **Respects workflow**: Pre-commit hooks still run normally
- **Provides consistency**: Same command works for everyone
- **Enables automation**: Scriptable with clear behavior

It's designed to be the "one command" new contributors need to know, while staying powerful enough for experienced developers.

## Advanced Examples

### Team Onboarding
```bash
# New team member workflow:
git clone <repository>
cd <repository>

# Make changes, then always:
python commit.py --all --interactive
```

### CI/CD Integration
```bash
# Automated commits with validation:
python commit.py --all --auto-timestamp

# Or with custom message:
python commit.py --all -m "Automated update: $(date)"

# Preview mode for CI checks:
python commit.py --dry-run --all -m "CI test commit"
```

### Custom Formatting Workflows
```bash
# Skip formatting for urgent fixes:
python commit.py --no-format -m "URGENT: fix production issue"

# Test formatting without committing:
python format_project.py && echo "Formatting successful"
```
