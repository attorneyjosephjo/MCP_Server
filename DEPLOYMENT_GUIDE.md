# Guide: Deploying MCP Server (Remote & Local) and Connecting to Claude Desktop & n8n

## Overview

This guide walks you through:
1. **Remote Deployment:** Deploying MCP server via Coolify with Docker (production)
2. **Local Deployment:** Running MCP server locally for development
3. **Integration:** Connecting both to Claude Desktop and n8n workflows

## Prerequisites

### For Remote Deployment (Coolify):
- Coolify instance running
- Docker installed on your server
- Domain name configured (e.g., `your-domain.com`)
- MCP server code ready with Dockerfile

### For Local Deployment:
- Python 3.10+ installed
- Git repository cloned locally
- Environment variables configured in `.env` file

---

## Part 1: Deploy MCP Server via Coolify

### Step 1: Prepare Your Dockerfile

Ensure your `Dockerfile` is configured for HTTP transport:

```dockerfile
FROM python:3.13-slim

WORKDIR /app

# Copy project files
COPY pyproject.toml ./
COPY legal_rag_server.py ./
COPY legal_rag_utils.py ./
COPY .env ./

# Install dependencies
RUN pip install --no-cache-dir -e .

# Set environment variables
ENV PORT=3000
ENV HOST=0.0.0.0

# Expose port
EXPOSE 3000

# Health check - test if port 3000 is listening
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD python -c "import socket; s=socket.socket(); s.settimeout(5); s.connect(('localhost', 3000)); s.close()"

# Run server in HTTP mode
CMD ["python", "legal_rag_server.py", "--http"]
```

### Step 2: Configure Coolify Application

1. **Create New Application** in Coolify
2. **Source:** Connect your Git repository or upload files
3. **Build Pack:** Dockerfile
4. **Port:** 3000 (must match your Dockerfile EXPOSE and ENV PORT)

### Step 3: Configure Domain with HTTPS

**Important:** Coolify requires HTTPS for custom domains.

1. Go to **Domains** section in your Coolify app
2. Add your domain: `your-domain.com`
3. Coolify will automatically:
   - Configure SSL certificate (Let's Encrypt)
   - Set up reverse proxy
   - Enable HTTPS

**Result:** Your MCP server will be accessible at:
- Base URL: `https://your-domain.com`
- Health Check: `https://your-domain.com/health`
- MCP Endpoint: `https://your-domain.com/mcp`

### Step 4: Set Environment Variables in Coolify

In Coolify, add your environment variables:

```bash
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key-here
OPENAI_API_KEY=sk-proj-your-key-here
COHERE_API_KEY=your-cohere-key-here
PORT=3000
HOST=0.0.0.0
```

### Step 5: Deploy

1. Click **Deploy** button in Coolify
2. Monitor deployment logs
3. Wait for health check to pass
4. Verify deployment success

### Step 6: Verify Deployment

Test your endpoints:

```bash
# Health check
curl https://your-domain.com/health

# Expected response:
# {"status":"healthy","service":"LegalDocumentRAGServer","version":"1.0.0"}

# Root endpoint
curl https://your-domain.com/

# Expected response:
# {"service":"Legal RAG MCP Server","status":"running",...}
```

---

## Part 1B: Local Development Deployment

For local development and testing, you can run the MCP server directly on your machine.

### Step 1: Install Dependencies

```bash
cd "C:\Users\joong\OneDrive\Documents\Coding\MCP Sever\MCP_Server"

# Using pip
pip install -e .

# Or using uv (recommended)
uv sync
```

### Step 2: Configure Environment Variables

Create or verify your `.env` file:

```bash
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key-here
OPENAI_API_KEY=sk-proj-your-openai-key-here
COHERE_API_KEY=your-cohere-key-here
```

### Step 3: Run Server Locally

**For Claude Desktop (stdio mode):**
```bash
python legal_rag_server.py
```

**For HTTP testing (browser/curl):**
```bash
python legal_rag_server.py --http
```

Server will run on `http://localhost:3000`

### Step 4: Verify Local Server

```bash
# Test health check
curl http://localhost:3000/health

# Expected response:
# {"status":"healthy","service":"LegalDocumentRAGServer","version":"1.0.0"}
```

---

## Part 2: Connect to Claude Desktop

Claude Desktop can connect to both remote (Coolify-deployed) and local MCP servers.

### Step 1: Locate Claude Desktop Config

**Config file location:**
- **Windows:** `C:\Users\YourUsername\AppData\Roaming\Claude\claude_desktop_config.json`
- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Linux:** `~/.config/Claude/claude_desktop_config.json`

### Step 2: Add MCP Server Configuration

You can configure Claude Desktop to connect to either a remote server OR a local server (or both).

#### Option A: Remote Server (Coolify/Production)

For remote servers deployed via Coolify with HTTPS:

```json
{
  "mcpServers": {
    "startuplegal-rag-server-remote": {
      "type": "http",
      "url": "https://your-domain.com/mcp"
    }
  }
}
```

**Key Points:**
- ✅ `type` must be `"http"` (not "sse" or "stdio")
- ✅ `url` must include `/mcp` path
- ✅ `url` must use `https://` (not http://)
- ✅ No `command` or `args` needed for remote servers
- ✅ No `env` variables needed (server handles them internally)

---

#### Option B: Local Server (Development)

For local servers running on your development machine:

```json
{
  "mcpServers": {
    "legal-rag-server-local": {
      "command": "uv",
      "args": [
        "--directory",
        "C:\\Users\\joong\\OneDrive\\Documents\\Coding\\MCP Sever\\MCP_Server",
        "run",
        "--python",
        "3.13",
        "legal_rag_server.py"
      ],
      "env": {
        "SUPABASE_URL": "https://your-project.supabase.co",
        "SUPABASE_SERVICE_ROLE_KEY": "your-service-role-key-here",
        "OPENAI_API_KEY": "sk-proj-your-openai-key-here",
        "COHERE_API_KEY": "your-cohere-key-here"
      }
    }
  }
}
```

**Key Points:**
- ✅ `command` runs `uv` (or `python` if not using uv)
- ✅ `args` specifies the working directory with `--directory` flag
- ✅ `args` specifies Python version with `--python 3.13`
- ✅ `env` section **REQUIRED** - contains all API keys and credentials
- ✅ Server runs in stdio mode (not HTTP)
- ✅ Working directory must be absolute path

**Important:** According to the official MCP guide, the `env` section is **required** for local servers to pass environment variables from Claude Desktop to your MCP server process.

---

#### Option C: Both Remote and Local (Recommended for Development)

You can have both configurations simultaneously:

```json
{
  "mcpServers": {
    "legal-rag-server-remote": {
      "type": "http",
      "url": "https://your-domain.com/mcp"
    },
    "legal-rag-server-local": {
      "command": "uv",
      "args": [
        "--directory",
        "C:\\Users\\joong\\OneDrive\\Documents\\Coding\\MCP Sever\\MCP_Server",
        "run",
        "--python",
        "3.13",
        "legal_rag_server.py"
      ],
      "env": {
        "SUPABASE_URL": "https://your-project.supabase.co",
        "SUPABASE_SERVICE_ROLE_KEY": "your-service-role-key-here",
        "OPENAI_API_KEY": "sk-proj-your-openai-key-here",
        "COHERE_API_KEY": "your-cohere-key-here"
      }
    }
  }
}
```

This allows you to:
- ✅ Test against production (remote)
- ✅ Debug with local changes
- ✅ Switch between servers easily in Claude Desktop

### Step 3: Restart Claude Desktop

1. Completely close Claude Desktop
2. Reopen the application
3. Wait for it to fully load

### Step 4: Verify Connection

In Claude Desktop, check the **Connectors** section:
- Your server should appear as "Connected"
- Status should show as "Custom" connector

### Step 5: Test the Tools

Try asking Claude:
```
Search for SAFE agreements in the legal documents
```

Claude should use the `semantic_search_legal_documents` tool and return results from your MCP server.

---

## Part 3: Connect to n8n

### Step 1: Add MCP Client Node

1. Open your n8n workflow
2. Add a new node
3. Search for **"MCP Client"**
4. Add the node to your workflow

### Step 2: Configure MCP Client Node

Fill in the parameters:

| Parameter | Value |
|-----------|-------|
| **Endpoint** | `https://your-domain.com/mcp` |
| **Server Transport** | `HTTP Streamable` |
| **Authentication** | `None` |
| **Tools to Include** | `All` |

**Important Notes:**
- ✅ Endpoint must include `/mcp` path
- ✅ Must use `https://` protocol
- ✅ Server Transport must be "HTTP Streamable"
- ✅ Authentication should be "None" (unless you've added auth to your MCP server)

### Step 3: Configure Tool Call

After configuring connection, you can call specific tools:

**Example: Semantic Search**

1. **Resource:** `Tool`
2. **Operation:** `Call Tool`
3. **Tool Name:** `semantic_search_legal_documents`
4. **Arguments:**
   ```json
   {
     "query": "SAFE agreement",
     "top_k": 5,
     "document_type": null
   }
   ```

### Step 4: Test the Connection

1. Click **"Execute step"** button
2. If successful, you'll see tool results in the OUTPUT panel
3. If error, check:
   - Endpoint URL is correct with `/mcp`
   - Server is running (check health endpoint)
   - Coolify deployment is active

---

## Part 4: Available MCP Tools

Your deployed MCP server exposes 4 tools:

### 1. semantic_search_legal_documents
Search legal documents using natural language.

**Arguments:**
- `query` (string, required): Search query
- `top_k` (integer, optional, default: 10): Number of results
- `document_type` (string, optional): Filter by type ("practice_guide", "agreement", "clause")

**Example:**
```json
{
  "query": "How to structure a SAFE agreement?",
  "top_k": 5
}
```

### 2. browse_legal_documents_by_type
Browse documents filtered by category.

**Arguments:**
- `document_type` (string, required): "practice_guide", "agreement", or "clause"
- `limit` (integer, optional, default: 20): Results per page
- `offset` (integer, optional, default: 0): Pagination offset

**Example:**
```json
{
  "document_type": "agreement",
  "limit": 10,
  "offset": 0
}
```

### 3. get_legal_document_by_id
Retrieve specific document by UUID.

**Arguments:**
- `document_id` (string, required): Document UUID

**Example:**
```json
{
  "document_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### 4. list_all_legal_documents
List all documents with pagination.

**Arguments:**
- `limit` (integer, optional, default: 50): Results per page
- `offset` (integer, optional, default: 0): Pagination offset
- `include_content` (boolean, optional, default: false): Include full content

**Example:**
```json
{
  "limit": 20,
  "offset": 0,
  "include_content": false
}
```

---

## Part 5: Troubleshooting

### Issue: "Could not connect to MCP server"

**Solutions:**
1. Verify endpoint URL includes `/mcp`: `https://your-domain.com/mcp`
2. Check server is running: `curl https://your-domain.com/health`
3. Verify HTTPS is enabled (not HTTP)
4. Check Coolify deployment logs for errors

### Issue: "Invalid URL" in n8n

**Solutions:**
1. Make sure you're using `https://` not `http://`
2. Verify Server Transport is set to "HTTP Streamable"
3. Try removing and re-adding the MCP Client node
4. Update n8n to latest version

### Issue: Claude Desktop shows "Disconnected"

**Solutions:**
1. Check config file syntax is valid JSON
2. Verify `type` is `"http"` not "sse"
3. Restart Claude Desktop completely
4. Check server health endpoint is accessible

### Issue: "Session ID required" errors

**Solutions:**
1. This is normal - MCP protocol handles sessions automatically
2. Make sure you're calling `initialize` first (clients do this automatically)
3. For manual testing, save session ID from headers: `Mcp-Session-Id`

### Issue: Database timeout errors

**Solutions:**
1. Check Supabase connection and credentials
2. Verify `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` are correct
3. Check if Supabase database is accessible from Coolify server
4. Review database query performance and indexes

---

## Part 6: Endpoint Summary

### Your MCP Server Endpoints:

| Endpoint | Purpose | HTTP Method |
|----------|---------|-------------|
| `https://your-domain.com/` | Server info | GET |
| `https://your-domain.com/health` | Health check | GET |
| `https://your-domain.com/mcp` | MCP protocol | POST |

### Correct URLs for Connections:

| Client | Endpoint URL | Notes |
|--------|-------------|-------|
| **Claude Desktop** | `https://your-domain.com/mcp` | Must use `type: "http"` |
| **n8n MCP Client** | `https://your-domain.com/mcp` | Must use "HTTP Streamable" |
| **Custom clients** | `https://your-domain.com/mcp` | Use JSON-RPC 2.0 format |

---

## Part 7: Security Best Practices

### 1. Environment Variables
- ✅ Store API keys in Coolify environment variables
- ✅ Never commit `.env` files to Git
- ✅ Rotate API keys regularly

### 2. HTTPS Only
- ✅ Always use HTTPS (Coolify handles this automatically)
- ✅ Let's Encrypt SSL certificates auto-renew via Coolify

### 3. Access Control
- ⚠️ Consider adding authentication to your MCP server for production
- ⚠️ Implement rate limiting if exposing publicly
- ⚠️ Monitor API usage and costs (OpenAI, Cohere)

### 4. Monitoring
- ✅ Check Coolify deployment logs regularly
- ✅ Monitor health endpoint: `https://your-domain.com/health`
- ✅ Set up alerts for deployment failures

---

## Quick Reference Card

```
🚀 DEPLOYMENT
├─ Coolify: Docker + Port 3000
├─ Domain: HTTPS required
└─ Health: /health endpoint

🔌 CLAUDE DESKTOP
├─ Config: claude_desktop_config.json
├─ Type: "http"
└─ URL: https://domain.com/mcp

🔧 N8N
├─ Node: MCP Client
├─ Transport: HTTP Streamable
└─ Endpoint: https://domain.com/mcp

🛠️ TOOLS
├─ semantic_search_legal_documents
├─ browse_legal_documents_by_type
├─ get_legal_document_by_id
└─ list_all_legal_documents
```

---

## Testing Your MCP Server

### Test 1: Health Check
```bash
curl https://your-domain.com/health
```

Expected response:
```json
{
  "status": "healthy",
  "service": "LegalDocumentRAGServer",
  "version": "1.0.0"
}
```

### Test 2: Initialize MCP Session
```bash
curl -i -X POST https://your-domain.com/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
      "protocolVersion": "2024-11-05",
      "capabilities": {},
      "clientInfo": {
        "name": "test-client",
        "version": "1.0.0"
      }
    }
  }'
```

Look for `Mcp-Session-Id` in response headers.

### Test 3: List Tools
```bash
# Save session ID from previous step
SESSION_ID="your-session-id-here"

curl -X POST https://your-domain.com/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "Mcp-Session-Id: $SESSION_ID" \
  -d '{"jsonrpc":"2.0","method":"notifications/initialized"}'

curl -X POST https://your-domain.com/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "Mcp-Session-Id: $SESSION_ID" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/list"}'
```

### Test 4: Call a Tool
```bash
curl -X POST https://your-domain.com/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "Mcp-Session-Id: $SESSION_ID" \
  -d '{
    "jsonrpc":"2.0",
    "id":3,
    "method":"tools/call",
    "params":{
      "name":"semantic_search_legal_documents",
      "arguments":{
        "query":"SAFE agreement",
        "top_k":2
      }
    }
  }'
```

---

## Next Steps

1. ✅ Monitor your deployment in Coolify
2. ✅ Test all 4 MCP tools in both Claude and n8n
3. ✅ Set up monitoring/alerting for production use
4. ✅ Consider adding authentication for public endpoints
5. ✅ Document your specific use cases and workflows

---

## Troubleshooting Commands

```bash
# Check if server is accessible
curl -I https://your-domain.com/health

# Test MCP protocol endpoint
curl -X POST https://your-domain.com/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}'

# Check Coolify deployment logs
# (Access via Coolify web interface → Your App → Logs)

# Verify SSL certificate
openssl s_client -connect your-domain.com:443 -servername your-domain.com
```

---

## Common Configuration Mistakes

❌ **WRONG - Using HTTP instead of HTTPS**
```json
{
  "type": "http",
  "url": "http://your-domain.com/mcp"
}
```

✅ **CORRECT - Using HTTPS**
```json
{
  "type": "http",
  "url": "https://your-domain.com/mcp"
}
```

---

❌ **WRONG - Missing /mcp path**
```json
{
  "type": "http",
  "url": "https://your-domain.com"
}
```

✅ **CORRECT - Including /mcp path**
```json
{
  "type": "http",
  "url": "https://your-domain.com/mcp"
}
```

---

❌ **WRONG - Using SSE type for HTTP server**
```json
{
  "type": "sse",
  "url": "https://your-domain.com/mcp"
}
```

✅ **CORRECT - Using HTTP type**
```json
{
  "type": "http",
  "url": "https://your-domain.com/mcp"
}
```

---

## FAQ

**Q: Can I use HTTP instead of HTTPS?**
A: No. Coolify requires HTTPS for custom domains, and it's best practice for security.

**Q: Do I need to open any ports on my server?**
A: No. Coolify handles the reverse proxy and port mapping automatically.

**Q: Can I connect multiple clients to the same MCP server?**
A: Yes. Both Claude Desktop and n8n can connect to the same MCP server simultaneously.

**Q: How do I update my MCP server?**
A: Push changes to your Git repository and redeploy in Coolify, or manually rebuild the Docker image.

**Q: Can I add authentication to my MCP server?**
A: Yes. You can add API key authentication or OAuth to your MCP server code. Update the `Authentication` field in n8n and add headers to Claude Desktop config.

**Q: What's the difference between the /mcp endpoint and /health endpoint?**
A: `/health` is for monitoring server status (simple HTTP GET). `/mcp` is the MCP protocol endpoint for tool calls (JSON-RPC over HTTP POST).

---

## Support Resources

- **MCP Documentation:** https://modelcontextprotocol.io/
- **FastMCP Documentation:** https://gofastmcp.com/
- **Coolify Documentation:** https://coolify.io/docs
- **n8n MCP Client:** https://docs.n8n.io/integrations/builtin/cluster-nodes/sub-nodes/n8n-nodes-langchain.mcpclient/
- **Claude Desktop:** https://claude.ai/

---

## Deployment Comparison: Remote vs Local

### Configuration Summary

| Aspect | Remote (Coolify) | Local (Development) |
|--------|------------------|---------------------|
| **Config Type** | `"type": "http"` | `"command": "uv"` or `"python"` |
| **URL/Path** | `https://domain.com/mcp` | Not used (stdio) |
| **Environment Variables** | Managed in Coolify | Required in `env` section |
| **SSL/HTTPS** | Required (auto via Let's Encrypt) | Not needed (localhost) |
| **Domain** | Custom domain required | Not needed |
| **Startup** | Automatic (Coolify restarts) | Manual or via Claude Desktop |
| **Logs** | Coolify dashboard | Terminal or file |
| **Use Case** | Production, sharing with team, public access | Development, debugging, testing |
| **Performance** | Subject to network latency | Fast (local) |
| **Updates** | Git push + redeploy | Edit files directly |

---

### Complete `claude_desktop_config.json` Example

**Full working configuration with both remote and local servers:**

```json
{
  "mcpServers": {
    "legal-rag-server-remote": {
      "type": "http",
      "url": "https://your-domain.com/mcp"
    },
    "legal-rag-server-local": {
      "command": "uv",
      "args": [
        "--directory",
        "C:\\Users\\joong\\OneDrive\\Documents\\Coding\\MCP Sever\\MCP_Server",
        "run",
        "--python",
        "3.13",
        "legal_rag_server.py"
      ],
      "env": {
        "SUPABASE_URL": "https://your-project.supabase.co",
        "SUPABASE_SERVICE_ROLE_KEY": "your-service-role-key-here",
        "OPENAI_API_KEY": "sk-proj-your-actual-openai-key-here",
        "COHERE_API_KEY": "your-actual-cohere-key-here"
      }
    }
  }
}
```

**File Location:**
- Windows: `C:\Users\YourUsername\AppData\Roaming\Claude\claude_desktop_config.json`
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Linux: `~/.config/Claude/claude_desktop_config.json`

---

### When to Use Which Configuration

**Use Remote (Coolify) When:**
- ✅ Deploying to production
- ✅ Sharing with team members
- ✅ Need 24/7 availability
- ✅ Want automatic restarts and scaling
- ✅ Using from multiple machines
- ✅ Integrating with n8n workflows

**Use Local When:**
- ✅ Developing new features
- ✅ Debugging issues
- ✅ Testing changes before deployment
- ✅ Working offline
- ✅ Need fast iteration cycles
- ✅ Running experiments

**Use Both When:**
- ✅ Active development with production deployment
- ✅ Need to compare local changes vs production
- ✅ Testing migrations or updates
- ✅ A/B testing different configurations

---

**Last Updated:** December 10, 2025
**Author:** Deployment guide for Legal RAG MCP Server
**Version:** 2.0
