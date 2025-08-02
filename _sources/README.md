# LLM-ETI JupyterBook

This directory contains the JupyterBook version of "What can LLMs tell us about the ETI?"

## Prerequisites

- Python 3.13+
- [uv](https://github.com/astral-sh/uv) (will be auto-installed if missing)

## Quick Start

```bash
# Install dependencies with uv
make install

# Run test simulations (uses gpt-4o-mini only)
make test-data

# Generate figures and tables
make figures tables

# Build the book
make book

# Serve locally
make serve
```

## Full Pipeline

To run the complete analysis (warning: expensive API calls!):

```bash
# Set your OpenAI API key
export OPENAI_API_KEY=your-key-here

# Run full simulations
make data

# Build everything
make all
```

## Structure

- `intro.md` - Introduction and abstract
- `methods.md` - Methodology description
- `results/` - Analysis results chapters
- `scripts/` - Python scripts for simulations and figure generation
- `data/` - Generated simulation data (not in git)
- `figures/` - Generated figures (not in git)
- `tables/` - Generated LaTeX tables (not in git)

## CI/CD

The GitHub Actions workflow will:
1. Run test simulations with gpt-4o-mini
2. Generate figures and tables
3. Build the JupyterBook
4. Deploy to GitHub Pages (on main branch)

## Customization

Edit `_config.yml` to change book metadata, and `_toc.yml` to modify the table of contents.