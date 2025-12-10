# Claude Code CLI - Team Usage Guide

> **Purpose**: This guide will help team members install and use Claude Code CLI with our custom slash commands for development workflows.

## 📋 Table of Contents

1. [What is Claude Code CLI?](#what-is-claude-code-cli)
2. [Installation](#installation)
3. [Getting Started](#getting-started)
4. [Available Slash Commands](#available-slash-commands)
5. [Usage Examples](#usage-examples)
6. [Best Practices](#best-practices)
7. [Troubleshooting](#troubleshooting)

---

## What is Claude Code CLI?

**Claude Code CLI** is a terminal-based interface for Claude that provides:

- 🖥️ **Terminal Interface**: Chat with Claude directly from your command line
- ⚡ **Slash Commands**: Custom commands for common development tasks
- 🔄 **Context Awareness**: Claude can read and modify files in your project
- 🎯 **Workflow Automation**: Automate repetitive development tasks

### Difference from Claude Desktop

| Feature | Claude Desktop (GUI) | Claude Code CLI (Terminal) |
|---------|---------------------|---------------------------|
| Interface | Desktop application | Terminal/Command line |
| Slash Commands | ❌ No | ✅ Yes |
| MCP Tools | ✅ Yes | ❌ No |
| File Access | Limited | Full project access |
| Use Case | General chat, MCP tools | Development workflows |

**When to use Claude Code CLI:**
- Running builds and tests
- Creating features with specs
- Managing GitHub issues and projects
- Making commits with detailed messages
- Publishing features to GitHub

**When to use Claude Desktop:**
- Searching legal documents (MCP tools)
- General conversation
- Quick questions

---

## Installation

### Prerequisites

- ✅ **Node.js** v18 or higher ([Download here](https://nodejs.org/))
- ✅ **npm** (comes with Node.js)
- ✅ **Git** installed and configured
- ✅ **Claude API key** (get from [claude.ai](https://claude.ai))

Check versions:
```bash
node --version  # Should be v18.0.0 or higher
npm --version   # Should be 9.0.0 or higher
git --version   # Any recent version
```

### Step 1: Install Claude Code CLI

Open PowerShell or Command Prompt and run:

```bash
npm install -g @anthropic-ai/claude-code
```

Verify installation:
```bash
claude --version
```

You should see the version number (e.g., `1.0.0` or similar).

### Step 2: Configure API Key

Set up your Claude API key:

```bash
# Option 1: Set environment variable (temporary - for current session)
set ANTHROPIC_API_KEY=your-api-key-here

# Option 2: Set permanently (Windows)
setx ANTHROPIC_API_KEY "your-api-key-here"
```

> **Getting your API key**:
> 1. Go to [claude.ai](https://claude.ai)
> 2. Sign in
> 3. Go to API settings
> 4. Generate a new API key
> 5. Copy and save it securely

### Step 3: Verify Setup

Test that everything works:

```bash
# Navigate to any project directory
cd "C:\Users\YOUR_USERNAME\Documents\MyProject"

# Start Claude Code CLI
claude
```

You should see:
```
Claude Code CLI
Type /help for available commands
Type 'exit' to quit

>
```

If you see this, you're ready to go! Type `exit` to quit for now.

---

## Getting Started

### Starting Claude Code CLI

1. **Open PowerShell or Command Prompt**

2. **Navigate to your project directory:**
   ```bash
   cd "C:\Users\YOUR_USERNAME\Documents\MCP Sever\MCP_Server"
   ```

3. **Start Claude:**
   ```bash
   claude
   ```

4. **You'll see the prompt:**
   ```
   >
   ```

Now you can:
- Type regular messages to chat with Claude
- Type `/` to see available slash commands
- Type `exit` to quit

### Basic Commands

| Command | Description |
|---------|-------------|
| `exit` | Exit Claude Code CLI |
| `/help` | Show available commands |
| `/` | Show list of slash commands |
| `clear` | Clear the terminal screen |

---

## Available Slash Commands

Our project has **5 custom slash commands** in `.claude/commands/`:

### 1. `/check-build`
**Run lint, typecheck and build**

**What it does:**
- Runs `npm run lint` to check code style
- Runs `npm run typecheck` to check TypeScript types
- Runs `npm run build` to build the project
- Resolves any issues found

**When to use:**
- Before committing code
- After making changes
- To verify everything still works

**Example:**
```bash
> /check-build
```

Claude will automatically run all checks and report any issues.

---

### 2. `/checkpoint`
**Create a comprehensive checkpoint commit**

**What it does:**
- Analyzes all changes with `git status` and `git diff`
- Stages ALL files (tracked and untracked)
- Creates a detailed commit message following project conventions
- Includes co-author attribution for Claude

**When to use:**
- When you want to save progress
- After completing a feature or fix
- Before switching to another task

**Example:**
```bash
> /checkpoint
```

Claude will:
1. Show you what changed
2. Create a descriptive commit message
3. Commit everything with proper formatting

**Commit message format:**
```
feat: add user authentication system

- Implemented JWT-based authentication
- Added login/logout endpoints
- Created middleware for protected routes
- Updated database schema with users table

🤖 Generated with Claude Code
Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

---

### 3. `/create-feature`
**Create a new feature with requirements and implementation plan**

**What it does:**
- Creates a new folder in `/specs/{feature-name}/`
- Generates three files:
  - `requirements.md` - What the feature does and why
  - `implementation-plan.md` - Step-by-step tasks broken into phases
  - `action-required.md` - Manual steps that need human action

**When to use:**
- Starting a new feature
- Planning a large change
- Need to break work into phases

**Example conversation:**
```bash
> /create-feature

Claude: What feature would you like to create?

> Add user profile management with avatar upload

Claude: [Creates specs/user-profile-management/ folder with all files]
```

**Generated structure:**
```
specs/user-profile-management/
├── requirements.md           # Feature description and acceptance criteria
├── implementation-plan.md    # Phases and tasks with checkboxes
└── action-required.md        # Manual steps (API keys, account setup, etc.)
```

**Implementation plan example:**
```markdown
# Implementation Plan: User Profile Management

## Phase 1: Database Setup
- [ ] Create users table with profile fields
- [ ] Add avatar_url column
- [ ] Create migration script

## Phase 2: Backend API
- [ ] Create GET /api/profile endpoint
- [ ] Create PUT /api/profile endpoint
- [ ] Add avatar upload endpoint with S3 integration

## Phase 3: Frontend UI
- [ ] Create profile page component
- [ ] Add avatar upload widget
- [ ] Implement form validation
```

---

### 4. `/continue-feature`
**Continue implementing the next task for a GitHub-published feature**

**What it does:**
- Finds the next unchecked task in your feature
- Updates GitHub issue to "In Progress"
- Implements the task
- Commits the changes
- Updates GitHub with completion status
- Marks task as complete

**Prerequisites:**
- Feature must be published to GitHub (using `/publish-to-github`)
- GitHub CLI (`gh`) must be installed and authenticated
- Feature folder must be attached to conversation

**When to use:**
- Working through a feature step-by-step
- Want automated GitHub updates
- Following a published implementation plan

**Example:**
```bash
# First, drag the feature folder into the terminal or chat

> /continue-feature

Claude: 📋 Next Task: Create users table with profile fields

Phase: 1 - Database Setup
Issue: #123
Task: 1 of 3

Proceeding with implementation...

[Claude implements the task]

✅ Task complete!
GitHub Updates: ✅
Commit: abc123def

Ready to continue? Drop the feature folder again and say "continue"
```

---

### 5. `/publish-to-github`
**Publish a feature from /specs to GitHub Issues and Projects**

**What it does:**
- Creates an Epic issue with full requirements
- Creates Phase issues (one per phase) with task checklists
- Creates a GitHub Project board to track progress
- Links everything together
- Generates `github.md` with all references

**Prerequisites:**
- Feature must exist in `/specs/` folder (created with `/create-feature`)
- GitHub CLI (`gh`) must be installed and authenticated
- Must be in a git repository

**When to use:**
- After creating feature specs
- Ready to start implementation
- Want to track progress on GitHub

**Example:**
```bash
# First, make sure you're in the project directory with /specs folder

> /publish-to-github

Claude: Which feature would you like to publish?

> user-profile-management

Claude: Publishing "User Profile Management" to GitHub...

Feature "User Profile Management" published to GitHub!

Epic: https://github.com/yourorg/yourrepo/issues/123
Project: https://github.com/users/yourorg/projects/5
Phases created: 3
Total tasks: 12

The github.md file has been created at specs/user-profile-management/github.md

To continue implementing, use /continue-feature
```

**What gets created on GitHub:**

1. **Epic Issue (#123)**
   - Contains full requirements
   - Links to all phase issues
   - Labeled: `epic`, `feature/user-profile-management`

2. **Phase Issues (#124, #125, #126)**
   - Phase 1: Database Setup (3 tasks)
   - Phase 2: Backend API (5 tasks)
   - Phase 3: Frontend UI (4 tasks)
   - Each with full task checklist

3. **GitHub Project Board**
   - Columns: Todo, In Progress, Done
   - All issues added
   - Linked to repository

4. **github.md file**
   ```markdown
   # GitHub References

   - Epic: #123
   - Project: #5
   - Phase 1: #124
   - Phase 2: #125
   - Phase 3: #126
   ```

---

## Usage Examples

### Example 1: Quick Code Check Before Commit

```bash
> /check-build

Claude: Running lint, typecheck, and build...

✅ Lint: Passed
✅ TypeCheck: Passed
✅ Build: Successful

No issues found! Ready to commit.
```

### Example 2: Making a Checkpoint Commit

```bash
> /checkpoint

Claude: Analyzing changes...

Files changed:
- src/components/UserProfile.tsx (modified)
- src/api/profile.ts (new)
- src/types/user.ts (modified)

Creating commit...

✅ Commit created: feat: add user profile component

Summary:
- Created UserProfile component with avatar display
- Added profile API endpoints
- Updated user type definitions

🤖 Generated with Claude Code
Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

### Example 3: End-to-End Feature Development

```bash
# Step 1: Create feature spec
> /create-feature

Claude: What feature would you like to create?

> Add email notifications for user actions

Claude: ✅ Feature specification created at specs/email-notifications/

Next steps:
1. Review action-required.md for manual tasks
2. Run /publish-to-github to create GitHub issues
3. Use /continue-feature to start implementing

# Step 2: Publish to GitHub
> /publish-to-github

Claude: Which feature?

> email-notifications

Claude: ✅ Published! Epic: #150, Phases: 3, Tasks: 15

# Step 3: Implement tasks one by one
> /continue-feature

Claude: 📋 Next Task: Set up email service provider account

[Claude guides you through implementation]

> /continue-feature

Claude: 📋 Next Task: Create email templates

[Continue until all tasks complete]
```

---

## Best Practices

### Using Slash Commands Effectively

✅ **DO:**
- Use `/check-build` before every commit
- Use `/checkpoint` when you complete a logical chunk of work
- Use `/create-feature` for new features, even small ones (helps with planning)
- Use `/publish-to-github` to track work publicly on GitHub
- Use `/continue-feature` for step-by-step implementation

❌ **DON'T:**
- Don't use `/checkpoint` for every tiny change (group related changes)
- Don't skip `/check-build` - catch errors early
- Don't create features without specs for complex work
- Don't manually update GitHub when using `/continue-feature` (it handles it)

### Git Workflow

When using Claude Code CLI:

1. **Before starting work:**
   ```bash
   git checkout -b feature/my-feature
   ```

2. **During work:**
   ```bash
   # Make changes, then:
   > /check-build
   > /checkpoint
   ```

3. **After task completion:**
   ```bash
   git push origin feature/my-feature
   # Create PR on GitHub
   ```

### Feature Development Workflow

**Recommended flow for new features:**

```
1. Plan
   └─> /create-feature

2. Publish
   └─> /publish-to-github

3. Implement (repeat)
   └─> /continue-feature
   └─> /check-build
   └─> (automatic commit by /continue-feature)

4. Review & Merge
   └─> Create PR on GitHub
   └─> Code review
   └─> Merge
```

---

## Troubleshooting

### Issue: "Command not found: claude"

**Cause:** Claude Code CLI not installed or not in PATH

**Solution:**
```bash
# Reinstall globally
npm install -g @anthropic-ai/claude-code

# Check installation
claude --version

# If still not found, check PATH includes npm global bin
npm config get prefix
# Add this path to your system PATH environment variable
```

### Issue: "API key not configured"

**Cause:** `ANTHROPIC_API_KEY` environment variable not set

**Solution:**
```bash
# Set permanently
setx ANTHROPIC_API_KEY "your-api-key-here"

# Close and reopen your terminal

# Verify
echo %ANTHROPIC_API_KEY%
```

### Issue: Slash commands don't appear

**Cause:** Not running Claude in a project directory with `.claude/commands/`

**Solution:**
```bash
# Make sure you're in the project directory
cd "C:\Users\YOUR_USERNAME\Documents\MCP Sever\MCP_Server"

# Verify .claude/commands/ exists
dir .claude\commands

# Start Claude
claude

# Type / to see commands
> /
```

### Issue: `/publish-to-github` fails with "gh not found"

**Cause:** GitHub CLI not installed

**Solution:**
1. Install GitHub CLI: [cli.github.com](https://cli.github.com/)
2. Authenticate: `gh auth login`
3. Add project scopes: `gh auth refresh -s project,read:project`
4. Try again

### Issue: `/check-build` fails with "script not found"

**Cause:** Project doesn't have npm scripts defined

**Solution:**
Ensure `package.json` has these scripts:
```json
{
  "scripts": {
    "lint": "eslint .",
    "typecheck": "tsc --noEmit",
    "build": "npm run lint && npm run typecheck"
  }
}
```

### Issue: Claude Code CLI is slow or hangs

**Cause:** Large project files or API rate limits

**Solution:**
1. Check internet connection
2. Verify API key has credits at [claude.ai](https://claude.ai)
3. Add `.claudeignore` file to exclude large files:
   ```
   node_modules/
   dist/
   build/
   *.log
   .git/
   ```

---

## Advanced Tips

### Creating Custom Slash Commands

You can create your own slash commands!

1. **Create a new `.md` file in `.claude/commands/`:**
   ```bash
   # Example: .claude/commands/deploy.md
   ```

2. **Add frontmatter and instructions:**
   ```markdown
   ---
   description: Deploy to production
   ---

   Please deploy the application to production:

   1. Run the build command
   2. Run tests
   3. Deploy to Vercel using `vercel --prod`
   4. Verify deployment is live
   5. Report the deployment URL
   ```

3. **Use it:**
   ```bash
   > /deploy
   ```

### Combining Commands

You can chain commands in conversation:

```bash
> First run /check-build, then /checkpoint with message "Complete user auth"

Claude will:
1. Run build checks
2. If passed, create commit
3. Use your custom message
```

### Using with Git Hooks

Add to `.git/hooks/pre-commit`:
```bash
#!/bin/sh
# Auto-run checks before commit
npm run lint && npm run typecheck
```

---

## Getting Help

### In-CLI Help

```bash
> /help
# Shows available commands and usage

> help
# Shows Claude's general help
```

### Resources

- 📚 [Claude Code Documentation](https://docs.anthropic.com/claude-code)
- 💬 Team Slack channel: `#dev-claude-cli`
- 🐛 Report issues: Contact your team lead
- 📖 This guide: `CLAUDE_CLI_GUIDE.md`

### Common Questions

**Q: Can I use Claude Code CLI and Claude Desktop at the same time?**
A: Yes! They serve different purposes. Use CLI for development, Desktop for MCP tools.

**Q: Do slash commands work in Claude Desktop?**
A: No, slash commands only work in Claude Code CLI (terminal).

**Q: How much does Claude Code CLI cost?**
A: Uses your Claude API credits. Each command uses tokens based on context.

**Q: Can I create my own slash commands?**
A: Yes! Add `.md` files to `.claude/commands/` directory.

**Q: What if a command fails partway through?**
A: Claude will report the error and you can retry or fix manually.

---

## Quick Reference Card

### Essential Commands

| Command | Usage | Purpose |
|---------|-------|---------|
| `claude` | Start CLI | Begin session |
| `/check-build` | Before commit | Run tests |
| `/checkpoint` | After changes | Create commit |
| `/create-feature` | Start feature | Create specs |
| `/publish-to-github` | After specs | Create issues |
| `/continue-feature` | Implement | Do next task |
| `exit` | End session | Close CLI |

### Typical Workflow

```
1. claude                    # Start
2. /create-feature          # Plan feature
3. /publish-to-github       # Create issues
4. /continue-feature        # Implement task 1
5. /continue-feature        # Implement task 2
6. ...                      # Repeat
7. exit                     # Done
```

---

**Questions?** Contact your team lead or check the team wiki.

**Last Updated**: December 10, 2025
