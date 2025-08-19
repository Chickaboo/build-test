# Code Formatting Guide

This document explains how to format code in the GambitPairing project.

## Quick Start

### Using the Python Script (#1)

Run the formatting script directly with:

```bash
python3 {{git root}}/format_project.py
```

Or make it executable and run directly:

```bash
chmod +x format_project.py
./format_project.py
```

### Manual Execution

If you prefer to run the formatting script manually:

```bash
python3 format_project.py --target src/gambitpairing
```

## What Gets Formatted

The formatting script processes all Python files in the `src/gambitpairing` directory and applies:

- **Code style formatting**
- **Import sorting**

## Requirements

- everything + dev dependencies in pyproject.toml


## Troubleshooting


### Permission Denied (Unix/Linux/macOS)

```bash
chmod +x format.py
```

### Python Not Found

Make sure Python 3 is installed and available in your PATH:

```bash
python3 --version
```

## IDE Integration

### VS Code

Add this to your VS Code settings to run formatting automatically:

```json
{
  "python.formatting.provider": "black",
  "editor.formatOnSave": true,
  "python.sortImports.args": ["--profile", "black"]
}
```

### PyCharm

1. Go to Settings → Tools → External Tools
2. Add a new tool with:
   - Program: `python3`
   - Arguments: `$ProjectFileDir$/format.py`
   - Working directory: `$ProjectFileDir$`

## Pre-commit Hook (Optional)

## Best Practices

1. **Format before committing** - Always run the formatter before pushing code
2. **Team consistency** - All team members should use the same formatting configuration
3. **Editor configuration** - Set up your editor to format on save for immediate feedback

## Getting Help

If you encounter issues with formatting:

1. Check that all dependencies are installed
2. Verify you're in the correct directory
3. Examine the output of the formatting script for error messages
4. Consult the documentation for the specific formatting tools being used
