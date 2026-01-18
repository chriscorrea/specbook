# Get Started with Specbook

This guide will help you install and run Specbook in just a few minutes.

## What You'll Need

Before you start, make sure you have:

- **Python 3.11 or newer** - Check your version by running `python --version`
- **uv** - A fast Python package installer. [Get it here](https://docs.astral.sh/uv/)

## Installation

Install Specbook from the command line:

```bash
uv tool install specbook --from git+https://github.com/chriscorrea/specbook.git
```

This adds the `specbook` command to your terminal. You can use it from any folder.

## Your First SDD Project

Specbook works best with projects that have a `specs/` folder. Here's what a typical project might look like:

```
my-project/
├── specs/
│   ├── 001-user-login/
│   │   ├── spec.md
│   │   └── tasks.md
│   └── 002-dashboard/
│       └── spec.md
└── src/
    └── ... your code ...
```

## Starting the Server

Open your terminal, go to your project folder, and run:

```bash
specbook
```

That's it! Your browser will open to `http://localhost:7732` where you can view and edit spec documents.

## Next Steps

- Create a `specs/` folder in your project or get started with [spec-kit](https://speckit.org/) 
- Add your first specification
- Run `specbook` to see it in action

---

[← Back to Documentation](index.md)
