# Poetry 2.0 Upgrade Guide

This document outlines the changes needed to upgrade the `tom-lt` project from Poetry 1.x to Poetry 2.0.

## Installation

First, upgrade Poetry to version 2.0:

```bash
# Using pipx (recommended)
pipx upgrade poetry

# Using pip
pip install --upgrade poetry

# Verify version
poetry --version
```

## Changes Made

### 1. Updated `pyproject.toml`

The following changes were made to ensure Poetry 2.0 compatibility:

#### Dependency Version Constraints
- **Python version**: Updated upper bound from `<3.12` to `<3.13` to support Python 3.12
- **tomtoolkit**: Changed from `>=2.15` to `>=2.15,<3.0` for better version pinning
- **suds-py3**: Changed from `~1.4` to `^1.4.5` (more explicit caret constraint)
- **lxml**: Updated from `>=5.2,<5.4` to `>=5.2,<6.0` for broader compatibility
- **flake8**: Updated from `>=7.0,<7.2` to `>=7.0,<8.0`

#### Build System
- **poetry-core**: Updated minimum version from `>=1.0.0` to `>=1.8.0`
- **poetry-dynamic-versioning**: Added minimum version constraint `>=1.0.0`

#### Dynamic Versioning
- Added explicit `files` configuration for version substitution
- Fixed typo: "manditory" → "mandatory"

### 2. Lock File Regeneration

The old `poetry.lock` file has been removed and will need to be regenerated:

```bash
poetry lock
```

## Migration Steps

1. **Backup your current environment** (optional but recommended):
   ```bash
   poetry export -f requirements.txt --output requirements-backup.txt
   ```

2. **Update Poetry** (if not already done):
   ```bash
   pipx upgrade poetry
   ```

3. **Navigate to the project directory**:
   ```bash
   cd tom_lt
   ```

4. **Generate new lock file**:
   ```bash
   poetry lock
   ```

5. **Install dependencies**:
   ```bash
   poetry install
   ```

6. **Verify installation**:
   ```bash
   poetry run python -c "import tom_lt; print(tom_lt.__version__)"
   ```

## Key Poetry 2.0 Features

- **Improved dependency resolution**: Faster and more reliable
- **Better plugin system**: Enhanced extensibility
- **Performance improvements**: Faster lock file generation and installation
- **Enhanced security**: Better handling of dependencies and sources
- **Python 3.12 support**: Full compatibility with the latest Python version

## Troubleshooting

### Common Issues

1. **Lock file conflicts**:
   ```bash
   rm poetry.lock
   poetry lock
   ```

2. **Cache issues**:
   ```bash
   poetry cache clear --all .
   poetry install
   ```

3. **Virtual environment issues**:
   ```bash
   poetry env remove python
   poetry install
   ```

### Version Conflicts

If you encounter dependency conflicts, try:

1. **Update all dependencies**:
   ```bash
   poetry update
   ```

2. **Check for outdated packages**:
   ```bash
   poetry show --outdated
   ```

3. **Resolve specific conflicts** by adjusting version constraints in `pyproject.toml`

## Verification

After upgrading, verify everything works:

```bash
# Check Poetry version
poetry --version

# Verify dependencies
poetry check

# Run tests (if available)
poetry run python -m pytest

# Check linting
poetry run flake8 tom_lt
```

## Additional Resources

- [Poetry 2.0 Release Notes](https://python-poetry.org/blog/announcing-poetry-2.0.0/)
- [Poetry Documentation](https://python-poetry.org/docs/)
- [Migration Guide](https://python-poetry.org/docs/master/faq/#what-do-i-need-to-know-when-migrating-from-poetry-1x-to-poetry-20)

## Support

If you encounter issues during the upgrade:

1. Check the [Poetry GitHub Issues](https://github.com/python-poetry/poetry/issues)
2. Consult the [Poetry Discord](https://discord.gg/awxPgve)
3. Review the project's existing CI/CD configuration for any Poetry-specific settings