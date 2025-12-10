# Legal RAG MCP Server - Team Setup Guide

> **Purpose**: This guide will help team members set up the Legal RAG MCP Server on their local machines to access our legal document database through Claude Desktop.

## 📋 Table of Contents

1. [What is This?](#what-is-this)
2. [Prerequisites](#prerequisites)
3. [Installation Steps](#installation-steps)
4. [Configuration](#configuration)
5. [Testing the Setup](#testing-the-setup)
6. [Using with Claude Desktop](#using-with-claude-desktop)
7. [Available Tools](#available-tools)
8. [Troubleshooting](#troubleshooting)
9. [Best Practices](#best-practices)

---

## What is This?

The Legal RAG MCP Server provides AI-powered semantic search for our legal document database. It integrates with Claude Desktop, allowing you to:

- 🔍 Search legal documents using natural language
- 📚 Browse documents by type (agreements, practice guides, clauses)
- 🎯 Get highly relevant results with AI reranking
- ⚡ Fast vector similarity search powered by Supabase

**Tech Stack:**
- **Vector Database**: Supabase with pgvector
- **Embeddings**: OpenAI text-embedding-3-small (1536 dimensions)
- **Reranking**: Cohere rerank-v3.5
- **Protocol**: Model Context Protocol (MCP)

---

## Prerequisites

Before you begin, ensure you have:

### Required Software

- ✅ **Windows 10/11** (this guide is Windows-specific)
- ✅ **Python 3.10 - 3.13** installed ([Download here](https://www.python.org/downloads/))
  - ⚠️ **Do NOT use Python 3.14** - some dependencies don't support it yet
  - Check version: `python --version`
- ✅ **uv** package manager installed ([Installation guide](https://docs.astral.sh/uv/))
  - Check if installed: `uv --version`
  - Install if needed: `powershell -c "irm https://astral.sh/uv/install.ps1 | iex"`
- ✅ **Claude Desktop for Windows** ([Download here](https://claude.ai/download))

### Required API Keys

You'll need API keys from your team lead or system administrator:

- 🔑 `SUPABASE_URL` - Our Supabase instance URL
- 🔑 `SUPABASE_SERVICE_ROLE_KEY` - Supabase service role key
- 🔑 `OPENAI_API_KEY` - OpenAI API key for embeddings
- 🔑 `COHERE_API_KEY` - Cohere API key for reranking

> **Note**: Contact your team lead to get these API keys. Do NOT share these keys publicly or commit them to version control.

---

## Installation Steps

### Step 1: Clone the Repository

```bash
# Clone the repository (or download the ZIP and extract it)
cd C:\Users\YOUR_USERNAME\Documents
git clone [REPOSITORY_URL]
cd "MCP Sever\MCP_Server"
```

> Replace `[REPOSITORY_URL]` with the actual repository URL provided by your team lead.

### Step 2: Verify Directory Structure

Your directory should look like this:

```
MCP_Server/
├── legal_rag_server.py
├── legal_rag_utils.py
├── pyproject.toml
├── .env.example
└── test_mcp_search.py
```

### Step 3: Install Dependencies

The dependencies will be automatically installed by `uv` when you run the server, but you can pre-install them:

```bash
# Navigate to the project directory
cd "C:\Users\YOUR_USERNAME\Documents\MCP Sever\MCP_Server"

# Sync dependencies (optional - uv will do this automatically)
uv sync
```

---

## Configuration

### Step 1: Get Your API Keys

Contact your team lead to receive:
1. Supabase URL and Service Role Key
2. OpenAI API Key
3. Cohere API Key

### Step 2: Configure Claude Desktop

**Important**: You'll configure the API keys directly in Claude Desktop's configuration file. Do NOT create a `.env` file - the keys will be passed through Claude Desktop.

1. **Open the Claude Desktop config file:**
   - Press `Windows + R`
   - Type: `%APPDATA%\Claude`
   - Press Enter
   - Open `claude_desktop_config.json` in a text editor (Notepad, VS Code, etc.)

2. **Add the MCP server configuration:**

Replace the entire contents with this (update the paths and API keys):

```json
{
  "mcpServers": {
    "legal-rag-server": {
      "command": "uv",
      "args": [
        "--directory",
        "C:\\Users\\YOUR_USERNAME\\Documents\\MCP Sever\\MCP_Server",
        "run",
        "--python",
        "3.13",
        "legal_rag_server.py"
      ],
      "env": {
        "SUPABASE_URL": "YOUR_SUPABASE_URL_HERE",
        "SUPABASE_SERVICE_ROLE_KEY": "YOUR_SUPABASE_KEY_HERE",
        "OPENAI_API_KEY": "YOUR_OPENAI_KEY_HERE",
        "COHERE_API_KEY": "YOUR_COHERE_KEY_HERE"
      }
    }
  }
}
```

3. **Update the configuration:**
   - Replace `YOUR_USERNAME` with your actual Windows username
   - Replace all `YOUR_*_HERE` placeholders with the actual API keys
   - Ensure all backslashes are doubled (`\\`) in Windows paths
   - Save the file

**Example with real paths:**
```json
{
  "mcpServers": {
    "legal-rag-server": {
      "command": "uv",
      "args": [
        "--directory",
        "C:\\Users\\jsmith\\Documents\\MCP Sever\\MCP_Server",
        "run",
        "--python",
        "3.13",
        "legal_rag_server.py"
      ],
      "env": {
        "SUPABASE_URL": "http://185.28.22.212:8000",
        "SUPABASE_SERVICE_ROLE_KEY": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "OPENAI_API_KEY": "sk-proj-...",
        "COHERE_API_KEY": "dOuDhVGel..."
      }
    }
  }
}
```

4. **Adjust Python version if needed:**
   - If you have Python 3.10, 3.11, or 3.12, update the `"3.13"` to your version
   - Check your version: `python --version`

---

## Testing the Setup

### Step 1: Test Without Claude Desktop (Optional)

Before connecting to Claude Desktop, verify the server works:

1. **Open PowerShell or Command Prompt**

2. **Navigate to the project directory:**
   ```bash
   cd "C:\Users\YOUR_USERNAME\Documents\MCP Sever\MCP_Server"
   ```

3. **Create a temporary `.env` file for testing:**
   ```bash
   # Copy the example file
   copy .env.example .env

   # Open .env in notepad and add your API keys
   notepad .env
   ```

4. **Add your API keys to `.env`:**
   ```env
   SUPABASE_URL=YOUR_SUPABASE_URL_HERE
   SUPABASE_SERVICE_ROLE_KEY=YOUR_SUPABASE_KEY_HERE
   OPENAI_API_KEY=YOUR_OPENAI_KEY_HERE
   COHERE_API_KEY=YOUR_COHERE_KEY_HERE
   ```

5. **Run the test script:**
   ```bash
   python test_mcp_search.py
   ```

6. **Expected output:**
   ```
   ============================================================
   MCP Server Search Tool Test
   ============================================================
   Query: What are the key terms in a SAFE agreement?

   [PASS] Search completed within expected time!
   Total Time: ~6 seconds
   Results: 10 documents
   ```

7. **Delete the `.env` file after testing** (Claude Desktop uses its own config):
   ```bash
   del .env
   ```

### Step 2: Connect to Claude Desktop

1. **Close Claude Desktop completely** if it's running
   - Right-click the Claude Desktop icon in the system tray
   - Click "Quit"
   - Or use Task Manager to ensure it's closed

2. **Restart Claude Desktop**

3. **Verify the connection:**
   - Look for the 🔌 **MCP server icon** in the chat interface
   - You should see **"legal-rag-server"** listed as connected
   - The status should show as **"Connected"** or show tool counts

4. **Test with a simple query:**

Type in Claude Desktop:
```
Search for documents about SAFE agreements
```

If everything is working, Claude will use the MCP server to search and return results!

---

## Using with Claude Desktop

Once connected, Claude Desktop has access to 4 powerful tools:

### 1. Semantic Search

**What it does**: Search legal documents using natural language

**Example queries:**
```
Search for SAFE agreement best practices

Find documents about Series A funding rounds

What are the key terms in a Delaware C-corp incorporation?

Show me employee stock option plan templates
```

**Parameters:**
- Query (required): Your search question
- Number of results (optional): Default 10, max 100
- Document type filter (optional): "practice_guide", "agreement", or "clause"

### 2. Browse by Type

**What it does**: Browse documents filtered by category

**Example queries:**
```
Show me all legal agreement templates

List practice guides available

Browse all contract clauses
```

**Document types:**
- **practice_guide**: Step-by-step guides and how-to documents
- **agreement**: Full legal agreement templates
- **clause**: Individual contract clauses and provisions

### 3. Get Document by ID

**What it does**: Retrieve a specific document when you have its ID

**Example:**
```
Get document with ID 550e8400-e29b-41d4-a716-446655440000
```

### 4. List All Documents

**What it does**: Browse all documents with pagination

**Example queries:**
```
List the first 20 legal documents

Show all documents with full content
```

---

## Available Tools

When you type in Claude Desktop, Claude can automatically use these MCP tools:

| Tool | Description | Use Case |
|------|-------------|----------|
| `semantic_search_legal_documents` | AI-powered semantic search | "Find documents about X" |
| `browse_legal_documents_by_type` | Browse by category | "Show me all agreements" |
| `get_legal_document_by_id` | Get specific document | "Get document ID: xxx" |
| `list_all_legal_documents` | List all with pagination | "List all documents" |

**Performance:**
- Average search time: **6-8 seconds**
- Breakdown:
  - OpenAI embeddings: ~2 seconds
  - Supabase vector search: ~2 seconds
  - Cohere reranking: ~2 seconds

---

## Troubleshooting

### Issue: "No result received from client-side tool execution"

**Cause**: Server failed to start or API keys are missing

**Solution:**
1. Check that API keys are correctly configured in `claude_desktop_config.json`
2. Verify the directory path is correct
3. Check the server logs at: `C:\Users\YOUR_USERNAME\Documents\MCP Sever\MCP_Server\legal_rag_server.log`
4. Restart Claude Desktop

### Issue: "Server disconnected" or "Failed to spawn"

**Cause**: Python not found or wrong version

**Solution:**
1. Verify Python is installed: `python --version`
2. Ensure Python 3.10-3.13 (NOT 3.14)
3. Update the `--python` version in the config to match your installed version
4. Verify the directory path uses double backslashes: `C:\\Users\\...`

### Issue: MCP server icon not showing

**Cause**: Config file not loaded or has syntax errors

**Solution:**
1. Open `claude_desktop_config.json` in a JSON validator ([jsonlint.com](https://jsonlint.com))
2. Verify all quotes are present and commas are correct
3. Ensure file is saved in the correct location: `%APPDATA%\Claude`
4. Restart Claude Desktop completely

### Issue: Search takes too long or times out

**Cause**: Network issues or API rate limits

**Solution:**
1. Check internet connection
2. Verify API keys are valid and have credits:
   - OpenAI: Check at [platform.openai.com](https://platform.openai.com)
   - Cohere: Check at [dashboard.cohere.com](https://dashboard.cohere.com)
3. Contact team lead if Supabase is down

### Issue: "pydantic-core build failure" or Rust errors

**Cause**: Using Python 3.14 which doesn't have pre-built wheels

**Solution:**
1. Downgrade to Python 3.13 or 3.12
2. Update the `--python` version in `claude_desktop_config.json`
3. Restart Claude Desktop

### Check Server Logs

If issues persist, check the logs:

```bash
# Open the log file
notepad "C:\Users\YOUR_USERNAME\Documents\MCP Sever\MCP_Server\legal_rag_server.log"
```

Look for error messages with timestamps. Share these with your team lead if you need help.

---

## Best Practices

### Security

- ✅ **NEVER commit API keys to version control**
- ✅ **NEVER share API keys in chat, email, or documentation**
- ✅ Keep your `claude_desktop_config.json` file secure
- ✅ Use only the API keys provided by your team lead
- ✅ Report any suspected key leaks immediately

### Usage

- ✅ Use specific queries for better results ("SAFE agreement valuation cap" vs "SAFE")
- ✅ Filter by document type when you know what you're looking for
- ✅ Start with fewer results (10) for faster responses
- ✅ Use natural language - the AI understands context

### Performance

- ✅ Expect 6-8 seconds per search query
- ✅ Longer queries (>100 words) may take slightly longer
- ✅ Subsequent similar queries may be faster due to caching

### Maintenance

- ✅ Check for updates regularly (notify team lead of issues)
- ✅ Keep Python and dependencies up to date
- ✅ Clear logs periodically if they grow large
- ✅ Report any errors or slow performance to the team

---

## Getting Help

If you encounter issues not covered in this guide:

1. **Check the logs** at `legal_rag_server.log`
2. **Search existing team documentation** (Notion, Confluence, etc.)
3. **Contact your team lead** with:
   - Description of the issue
   - Error messages from logs
   - Steps you've already tried
   - Screenshots if applicable

---

## Appendix: Configuration Reference

### Minimum Configuration (Claude Desktop)

```json
{
  "mcpServers": {
    "legal-rag-server": {
      "command": "uv",
      "args": [
        "--directory",
        "C:\\Users\\YOUR_USERNAME\\Documents\\MCP Sever\\MCP_Server",
        "run",
        "--python",
        "3.13",
        "legal_rag_server.py"
      ],
      "env": {
        "SUPABASE_URL": "http://185.28.22.212:8000",
        "SUPABASE_SERVICE_ROLE_KEY": "eyJhbGci...",
        "OPENAI_API_KEY": "sk-proj-...",
        "COHERE_API_KEY": "dOuDhVGel..."
      }
    }
  }
}
```

### Environment Variables Reference

| Variable | Purpose | Example |
|----------|---------|---------|
| `SUPABASE_URL` | Supabase instance URL | `http://185.28.22.212:8000` |
| `SUPABASE_SERVICE_ROLE_KEY` | Authentication key | `eyJhbGci...` |
| `OPENAI_API_KEY` | Generate embeddings | `sk-proj-...` |
| `COHERE_API_KEY` | Rerank results | `dOuDhVGel...` |

### Optional Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `LEGAL_RAG_TABLE_NAME` | `n8n_law_startuplaw` | Database table name |
| `LEGAL_RAG_MATCH_FUNCTION` | `match_n8n_law_startuplaw` | Vector search function |
| `LEGAL_RAG_TOP_K` | `10` | Default results |
| `LEGAL_RAG_MATCH_THRESHOLD` | `0.5` | Similarity threshold (0.0-1.0) |

---

## Version History

- **v1.0** (2025-12-10): Initial team setup guide
  - Windows installation instructions
  - Claude Desktop integration
  - Troubleshooting guide

---

**Questions?** Contact your team lead or check the team wiki for updates.

**Last Updated**: December 10, 2025
