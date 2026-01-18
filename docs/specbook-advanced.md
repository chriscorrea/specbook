# Advanced Usage

This guide introduces features and configuration options for experienced Specbook users.

## Server Configuration

### Custom Port

By default, Specbook runs on port 7732. You can change this:

```bash
# Start on a different port
specbook -p 8080

# Or with the serve command
specbook serve -p 8080

# Stop a server on a custom port
specbook stop -p 8080
```

Note that can run Specbook for different projects simultaneously by assigning different ports for each project.

```bash
# One project's documentation is available on default port
cd ~/projects/first-project
specbook

# Another project's documentation is available on port 8080
cd ~/projects/another-project
specbook -p 8080
```

## Working with Specifications

### Specification Structure

A well-organized spec folder looks something like this:

```
specs/
├── 001-user-auth/
│   ├── spec.md          # main specification
│   ├── plan.md          # implementation plan
│   ├── tasks.md         # task list
│   └── research.md      # research notes
├── 002-dashboard/
│   └── spec.md
└── 003-reporting/
    ├── spec.md
    └── plan.md
```

### Naming Conventions

Specbook recognizes these standard document types:

| Filename | Purpose |
|----------|---------|
| `spec.md` | Feature specification with requirements |
| `plan.md` | Technical implementation plan |
| `tasks.md` | Detailed task breakdown |
| `research.md` | Background research and decisions |
| `data-model.md` | Data structures and relationships |
| `quickstart.md` | Testing and validation scenarios |

You can add other markdown files too - Specbook will display them alongside the standard documents.

### Document Status

Specbook infers each document's status through optional YAML frontmatter:

```markdown
---
status: implementing
---

# My Feature Spec
...
```

Available statuses:
- `draft` 
- `in-review`
- `approved`
- `implementing`
- `complete`

## Inline Editing

The following keyboard shortcuts are available in edit mode:
- `Cmd/Ctrl + S` - Save changes
- `Cmd/Ctrl + B` - Bold selected text
- `Cmd/Ctrl + I` - Italicize selected text
- `Escape` - Cancel editing

---

[← Back to Get Started](get-started.md)
