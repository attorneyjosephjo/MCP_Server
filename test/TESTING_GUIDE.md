# MCP Server Testing Guide

Complete guide for testing both self-hosted (remote) and local MCP servers.

---

## ⚠️ MOST IMPORTANT: Verify You Receive Actual Document Text

**A test is ONLY successful if you receive REAL document content, not just status messages!**

### ✅ Success = Actual Text Content
```
"content": "For Educational Use Only\nSAFE: Simple Agreement for Future Equity...\n\nThis amendments and waivers clause..."
```

### ❌ Failure = Just Status Messages
```
"status": "success", "message": "Search completed"
```

**If you don't see paragraphs of legal document text in your response, the test has FAILED even if you get HTTP 200!**

---

## Table of Contents

1. [Testing Self-Hosted MCP Server](#testing-self-hosted-mcp-server)
2. [Testing Local MCP Server](#testing-local-mcp-server)
3. [Testing Methods](#testing-methods)
4. [Expected Responses](#expected-responses)
5. [Troubleshooting](#troubleshooting)

---

## Testing Self-Hosted MCP Server

Self-hosted MCP servers are deployed to remote servers (e.g., via Coolify) and accessible via HTTPS.

### Prerequisites

- Server deployed and running
- Domain configured with HTTPS (e.g., `https://startuplawrag.thejolawfirm.uk`)
- Access to terminal with curl or HTTP client

### Test 1: Health Check

Test if the server is running and accessible.

```bash
curl https://startuplawrag.thejolawfirm.uk/health
```

**Expected Response:**
```json
{
  "status": "healthy",
  "service": "LegalDocumentRAGServer",
  "version": "1.0.0"
}
```

**What This Tests:**
- ✅ Server is running
- ✅ Domain/SSL configured correctly
- ✅ Basic HTTP connectivity

---

### Test 2: Server Info

Check server information and available endpoints.

```bash
curl https://startuplawrag.thejolawfirm.uk/
```

**Expected Response:**
```json
{
  "service": "Legal RAG MCP Server",
  "status": "running",
  "description": "FastMCP server for legal document search and retrieval",
  "endpoints": {
    "health": "/health",
    "mcp": "Use an MCP client to connect to this server"
  }
}
```

**What This Tests:**
- ✅ Server metadata accessible
- ✅ Endpoint information correct

---

### Test 3: Initialize MCP Session

Start an MCP protocol session and get session ID.

```bash
curl -i -X POST https://startuplawrag.thejolawfirm.uk/mcp \
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

**Expected Response Headers:**
```
HTTP/1.1 200 OK
Content-Type: text/event-stream
Mcp-Session-Id: <your-session-id>
```

**Expected Response Body:**
```
event: message
data: {"jsonrpc":"2.0","id":1,"result":{"protocolVersion":"2024-11-05","capabilities":{"experimental":{},"prompts":{"listChanged":false},"resources":{"subscribe":false,"listChanged":false},"tools":{"listChanged":false}},"serverInfo":{"name":"LegalDocumentRAGServer","version":"1.12.2"}}}
```

**Important:** Save the `Mcp-Session-Id` from headers for subsequent requests!

**What This Tests:**
- ✅ MCP protocol endpoint accessible
- ✅ Session initialization working
- ✅ Server capabilities reported

---

### Test 4: Send Initialized Notification

After initialization, send the initialized notification.

```bash
# Replace with your session ID from Test 3
SESSION_ID="4abcfa25cde14c60930b70e7e1b674f0"

curl -X POST https://startuplawrag.thejolawfirm.uk/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "Mcp-Session-Id: $SESSION_ID" \
  -d '{
    "jsonrpc": "2.0",
    "method": "notifications/initialized"
  }'
```

**Expected Response:** Empty (no error)

**What This Tests:**
- ✅ Session ready for tool calls

---

### Test 5: List Available Tools

Get all available MCP tools.

```bash
curl -X POST https://startuplawrag.thejolawfirm.uk/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "Mcp-Session-Id: $SESSION_ID" \
  -d '{
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/list"
  }'
```

**Expected Response:**
```
event: message
data: {"jsonrpc":"2.0","id":2,"result":{"tools":[{"name":"semantic_search_legal_documents","description":"...","inputSchema":{...}},{"name":"browse_legal_documents_by_type",...},{...}]}}
```

**What This Tests:**
- ✅ Tool listing working
- ✅ All 4 tools registered
- ✅ Tool schemas available

---

### Test 6: Call Semantic Search Tool

Test the semantic search functionality.

```bash
curl -X POST https://startuplawrag.thejolawfirm.uk/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "Mcp-Session-Id: $SESSION_ID" \
  -d '{
    "jsonrpc": "2.0",
    "id": 3,
    "method": "tools/call",
    "params": {
      "name": "semantic_search_legal_documents",
      "arguments": {
        "query": "SAFE agreement",
        "top_k": 2
      }
    }
  }' --max-time 15
```

**Expected Response:**
```
event: message
data: {"jsonrpc":"2.0","id":3,"result":{"content":[{"type":"text","text":"{\n  \"query\": \"SAFE agreement\",\n  \"document_type\": null,\n  \"total_results\": 2,\n  \"results\": [...document data...]\n}"}],"isError":false}}
```

**What This Tests:**
- ✅ OpenAI embeddings working
- ✅ Supabase vector search working
- ✅ Cohere reranking working
- ✅ Full pipeline functional
- ✅ Response time reasonable (~5-10 seconds)

**⚠️ CRITICAL VERIFICATION - Must Receive Actual Document Text:**

The test is **ONLY successful** if you receive **real document content** in the response. Look for:

✅ **Actual legal document text** like:
```json
{
  "content": "For Educational Use Only\nSAFE: Simple Agreement for Future Equity...\nThis amendments and waivers clause provides...",
  "metadata": {
    "doc_name": "SAFE Simple Agreement for Future Equity (Seed-Stage Startup).pdf",
    "doc_type": "file",
    "main_category": "startuplaw",
    "jurisdiction": "united_states_federal"
  },
  "similarity": 0.528486308039871,
  "relevance_score": 0.767847
}
```

❌ **NOT just status messages** like:
```json
{
  "status": "success",
  "message": "Search completed"
}
```

**What You Should See:**
1. **Document content** - Paragraphs of actual legal text (not just metadata)
2. **Document metadata** - File name, category, jurisdiction
3. **Relevance scores** - Similarity and relevance scores showing ranking
4. **Multiple results** - Array of 2+ documents (based on top_k parameter)

**If you only get success messages without actual document text, the test has FAILED!**

---

### Test 7: Test Other Tools

**Browse by Type:**
```bash
curl -X POST https://startuplawrag.thejolawfirm.uk/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "Mcp-Session-Id: $SESSION_ID" \
  -d '{
    "jsonrpc": "2.0",
    "id": 4,
    "method": "tools/call",
    "params": {
      "name": "browse_legal_documents_by_type",
      "arguments": {
        "document_type": "agreement",
        "limit": 5
      }
    }
  }' --max-time 10
```

**List All Documents:**
```bash
curl -X POST https://startuplawrag.thejolawfirm.uk/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "Mcp-Session-Id: $SESSION_ID" \
  -d '{
    "jsonrpc": "2.0",
    "id": 5,
    "method": "tools/call",
    "params": {
      "name": "list_all_legal_documents",
      "arguments": {
        "limit": 3,
        "include_content": false
      }
    }
  }' --max-time 10
```

---

## Testing Local MCP Server

Local MCP servers run on your development machine (localhost) for testing and development.

### Prerequisites

- Python 3.10+ installed
- Dependencies installed (`pip install -e .` or `uv sync`)
- Environment variables configured in `.env` file
- Port 3000 available

---

### Starting Local Server

#### Option 1: HTTP Mode (for testing with HTTP clients)

```bash
cd "c:\Users\joong\OneDrive\Documents\Coding\MCP Sever\MCP_Server"
python legal_rag_server.py --http
```

**Expected Output:**
```
INFO - Starting Legal RAG Server in HTTP mode
INFO - Server will be accessible at http://0.0.0.0:3000
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:3000
```

#### Option 2: Stdio Mode (for local Claude Desktop)

```bash
python legal_rag_server.py
```

**Expected Output:**
```
INFO - Starting Legal RAG Server in stdio mode (local use)
```

---

### Test 1: Local Health Check

```bash
curl http://localhost:3000/health
```

**Expected Response:**
```json
{
  "status": "healthy",
  "service": "LegalDocumentRAGServer",
  "version": "1.0.0"
}
```

**What This Tests:**
- ✅ Server running locally
- ✅ Port 3000 accessible

---

### Test 2: Local Server Info

```bash
curl http://localhost:3000/
```

**Expected Response:**
```json
{
  "service": "Legal RAG MCP Server",
  "status": "running",
  "description": "FastMCP server for legal document search and retrieval",
  "endpoints": {
    "health": "/health",
    "mcp": "Use an MCP client to connect to this server"
  }
}
```

---

### Test 3: Initialize Local MCP Session

```bash
curl -i -X POST http://localhost:3000/mcp \
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
        "name": "local-test",
        "version": "1.0.0"
      }
    }
  }'
```

**Save the `Mcp-Session-Id` from response headers!**

---

### Test 4: Local Tool Testing

Use the same commands as self-hosted, but replace:
- `https://startuplawrag.thejolawfirm.uk` → `http://localhost:3000`

**Example:**
```bash
SESSION_ID="your-local-session-id"

curl -X POST http://localhost:3000/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "Mcp-Session-Id: $SESSION_ID" \
  -d '{"jsonrpc":"2.0","method":"notifications/initialized"}'

curl -X POST http://localhost:3000/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "Mcp-Session-Id: $SESSION_ID" \
  -d '{
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/call",
    "params": {
      "name": "semantic_search_legal_documents",
      "arguments": {
        "query": "incorporation",
        "top_k": 3
      }
    }
  }' --max-time 15
```

---

## Testing Methods

### Method 1: Command Line (curl)

**Pros:**
- ✅ Fast and simple
- ✅ Available on all platforms
- ✅ Good for automated testing

**Cons:**
- ❌ Manual session management
- ❌ Hard to read JSON responses

**Use Cases:**
- Quick health checks
- CI/CD pipelines
- Debugging

---

### Method 2: Python Script

Create `test_mcp_client.py`:

```python
import requests
import json

class MCPClient:
    def __init__(self, base_url):
        self.base_url = base_url
        self.session_id = None
        self.request_id = 0

    def initialize(self):
        """Initialize MCP session"""
        response = requests.post(
            f"{self.base_url}/mcp",
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream"
            },
            json={
                "jsonrpc": "2.0",
                "id": self._next_id(),
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "python-test", "version": "1.0.0"}
                }
            }
        )
        self.session_id = response.headers.get("Mcp-Session-Id")
        print(f"Session ID: {self.session_id}")

        # Send initialized notification
        requests.post(
            f"{self.base_url}/mcp",
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
                "Mcp-Session-Id": self.session_id
            },
            json={
                "jsonrpc": "2.0",
                "method": "notifications/initialized"
            }
        )

    def _next_id(self):
        self.request_id += 1
        return self.request_id

    def list_tools(self):
        """List available tools"""
        response = requests.post(
            f"{self.base_url}/mcp",
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
                "Mcp-Session-Id": self.session_id
            },
            json={
                "jsonrpc": "2.0",
                "id": self._next_id(),
                "method": "tools/list"
            }
        )
        return response.text

    def call_tool(self, tool_name, arguments):
        """Call a tool"""
        response = requests.post(
            f"{self.base_url}/mcp",
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
                "Mcp-Session-Id": self.session_id
            },
            json={
                "jsonrpc": "2.0",
                "id": self._next_id(),
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments
                }
            },
            timeout=30
        )
        return response.text

# Usage
if __name__ == "__main__":
    # Test self-hosted
    client = MCPClient("https://startuplawrag.thejolawfirm.uk")

    # Or test local
    # client = MCPClient("http://localhost:3000")

    client.initialize()

    # List tools
    print("\n=== Available Tools ===")
    print(client.list_tools())

    # Call semantic search
    print("\n=== Semantic Search ===")
    result = client.call_tool(
        "semantic_search_legal_documents",
        {"query": "SAFE agreement", "top_k": 2}
    )
    print(result)
```

**Run:**
```bash
python test_mcp_client.py
```

---

### Method 3: Using Existing Test Suite

Run the comprehensive test suite:

```bash
cd "c:\Users\joong\OneDrive\Documents\Coding\MCP Sever\MCP_Server"
pytest test_legal_rag.py -v
```

**What This Tests:**
- ✅ All utility functions
- ✅ All core business logic
- ✅ Error handling
- ✅ Integration tests

---

### Method 4: Using MCP Inspector

For visual/interactive testing, use the MCP Inspector:

```bash
# Install MCP Inspector globally
npx @modelcontextprotocol/inspector

# Then open in browser and connect to your server
```

---

## Expected Responses

### Successful Health Check
```json
{
  "status": "healthy",
  "service": "LegalDocumentRAGServer",
  "version": "1.0.0"
}
```

### Successful Tool Call (WITH ACTUAL DOCUMENT TEXT) ✅

**This is what SUCCESS looks like:**

```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "{\n  \"query\": \"SAFE agreement\",\n  \"document_type\": null,\n  \"total_results\": 2,\n  \"results\": [\n    {\n      \"id\": 7186,\n      \"content\": \"For Educational Use Only\\nSAFE: Simple Agreement for Future Equity...\\n\\nTypically, most agreements contain a clause requiring all amendments and waivers to be in writing and be signed by all parties to the agreement...\\n\\nThis amendments and waivers clause provides an option between requiring the SAFE holder's consent, or alternatively if the SAFE is part of a series, the consent of the Requisite Holders...\",\n      \"metadata\": {\n        \"doc_name\": \"SAFE Simple Agreement for Future Equity (Seed-Stage Startup).pdf\",\n        \"doc_type\": \"file\",\n        \"main_category\": \"startuplaw\",\n        \"sub_category\": \"financing_instruments\",\n        \"jurisdiction\": \"united_states_federal\",\n        \"legaldocument_type\": \"standard_documents_clauses\"\n      },\n      \"similarity\": 0.528486,\n      \"relevance_score\": 0.767847\n    },\n    {\n      \"id\": 7189,\n      \"content\": \"For Educational Use Only\\nSAFE: Simple Agreement for Future Equity...\\n\\nDrafting Note: Severability\\nThe purpose of the severability clause is to clarify that, if one or more terms or provisions are held to be invalid, illegal, or unenforceable, the parties intend the SAFE to survive...\\n\\nMarket Stand-Off Agreement. The Holder hereby agrees that it will not, without the prior written consent of the managing underwriter...\",\n      \"metadata\": {\n        \"doc_name\": \"SAFE Simple Agreement for Future Equity (Seed-Stage Startup).pdf\",\n        \"doc_type\": \"file\",\n        \"main_category\": \"startuplaw\",\n        \"sub_category\": \"financing_instruments\",\n        \"jurisdiction\": \"united_states_federal\"\n      },\n      \"similarity\": 0.515234,\n      \"relevance_score\": 0.712453\n    }\n  ]\n}"
      }
    ],
    "isError": false
  }
}
```

**Key indicators of SUCCESS:**
1. ✅ `"content"` field contains PARAGRAPHS of actual legal text
2. ✅ Multiple documents returned (array with 2+ items)
3. ✅ Each document has `metadata` with file name, category, jurisdiction
4. ✅ Each document has `similarity` and `relevance_score` numbers
5. ✅ Text is readable and makes sense (about SAFE agreements)
6. ✅ `"isError": false`

---

### Failed Tool Call (NO DOCUMENT TEXT) ❌

**This is what FAILURE looks like (even if HTTP 200):**

```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "{\"status\": \"success\", \"message\": \"Search completed\", \"results\": []}"
      }
    ],
    "isError": false
  }
}
```

**This is a FAILURE because:**
- ❌ No actual document content/text
- ❌ Just status messages
- ❌ Empty results array
- ❌ Cannot verify data pipeline is working

### Error Response (Invalid Tool)
```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "error": {
    "code": -32602,
    "message": "Tool not found: invalid_tool_name"
  }
}
```

### Error Response (Missing Session)
```json
{
  "jsonrpc": "2.0",
  "id": "server-error",
  "error": {
    "code": -32600,
    "message": "Bad Request: Missing session ID"
  }
}
```

---

## Troubleshooting

### Problem: Connection Refused

**Symptoms:**
```
curl: (7) Failed to connect to localhost port 3000: Connection refused
```

**Solutions:**
1. Check if server is running: `ps aux | grep legal_rag_server` (Linux/Mac) or Task Manager (Windows)
2. Verify port 3000 is not in use: `netstat -ano | findstr :3000` (Windows)
3. Start the server: `python legal_rag_server.py --http`

---

### Problem: SSL Certificate Error

**Symptoms:**
```
curl: (60) SSL certificate problem: unable to get local issuer certificate
```

**Solutions:**
1. For testing only, skip verification: `curl -k https://...`
2. For production, check SSL certificate: `openssl s_client -connect your-domain.com:443`
3. Verify Let's Encrypt certificate is valid in Coolify

---

### Problem: Timeout on Tool Calls

**Symptoms:**
```
curl: (28) Operation timed out after 10000 milliseconds
```

**Solutions:**
1. Increase timeout: `curl --max-time 30 ...`
2. Check server logs for errors
3. Verify database connectivity (Supabase)
4. Test individual components (OpenAI, Cohere)

---

### Problem: Database Timeout

**Response:**
```json
{
  "error": true,
  "error_type": "list_error",
  "message": "canceling statement due to statement timeout"
}
```

**Solutions:**
1. Check Supabase connection: `curl http://your-supabase-url:8000`
2. Verify `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` in environment
3. Check database performance/indexes
4. Increase Supabase timeout settings

---

### Problem: Session ID Missing

**Response:**
```json
{
  "error": {
    "code": -32600,
    "message": "Bad Request: Missing session ID"
  }
}
```

**Solutions:**
1. Make sure you called `initialize` first
2. Extract `Mcp-Session-Id` from response headers
3. Include session ID in all subsequent requests: `-H "Mcp-Session-Id: your-id"`

---

### Problem: Invalid JSON-RPC Format

**Response:**
```json
{
  "error": {
    "code": -32600,
    "message": "Invalid Request"
  }
}
```

**Solutions:**
1. Verify JSON syntax is valid
2. Check `jsonrpc: "2.0"` is present
3. Ensure `method` field is correct
4. Validate request structure matches examples

---

## Performance Benchmarks

### Expected Response Times (Self-Hosted):

| Operation | Expected Time |
|-----------|---------------|
| Health Check | < 100ms |
| Initialize Session | < 500ms |
| List Tools | < 200ms |
| Semantic Search | 5-10 seconds |
| Browse by Type | 1-3 seconds |
| Get by ID | < 1 second |
| List All | 2-5 seconds |

### Expected Response Times (Local):

| Operation | Expected Time |
|-----------|---------------|
| Health Check | < 50ms |
| Initialize Session | < 200ms |
| List Tools | < 100ms |
| Semantic Search | 4-8 seconds |
| Browse by Type | 1-2 seconds |
| Get by ID | < 500ms |
| List All | 1-3 seconds |

---

## Testing Checklist

### Self-Hosted Server Testing

- [ ] Health endpoint returns 200 OK
- [ ] Server info endpoint accessible
- [ ] MCP session initialization successful
- [ ] Session ID received in headers
- [ ] Tools list returns all 4 tools
- [ ] Semantic search returns results (5-10s)
- [ ] Browse by type works for all types
- [ ] Get by ID retrieves document
- [ ] List all returns paginated results
- [ ] Error handling works (invalid inputs)

### Local Server Testing

- [ ] Server starts without errors
- [ ] Port 3000 is listening
- [ ] Environment variables loaded
- [ ] Health endpoint returns 200 OK
- [ ] MCP protocol responds correctly
- [ ] All tools functional
- [ ] Performance within benchmarks
- [ ] Logs showing detailed timing

---

## Quick Test Scripts

### Test Self-Hosted (Bash)

Save as `test_selfhosted.sh`:

```bash
#!/bin/bash

BASE_URL="https://startuplawrag.thejolawfirm.uk"

echo "=== Testing Self-Hosted MCP Server ==="

echo -e "\n1. Health Check:"
curl -s "$BASE_URL/health" | jq

echo -e "\n2. Initialize Session:"
RESPONSE=$(curl -si -X POST "$BASE_URL/mcp" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}')

SESSION_ID=$(echo "$RESPONSE" | grep -i "Mcp-Session-Id:" | awk '{print $2}' | tr -d '\r')
echo "Session ID: $SESSION_ID"

echo -e "\n3. Send Initialized:"
curl -s -X POST "$BASE_URL/mcp" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "Mcp-Session-Id: $SESSION_ID" \
  -d '{"jsonrpc":"2.0","method":"notifications/initialized"}'

echo -e "\n4. List Tools:"
curl -s -X POST "$BASE_URL/mcp" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "Mcp-Session-Id: $SESSION_ID" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/list"}'

echo -e "\n5. Call Semantic Search:"
curl -s -X POST "$BASE_URL/mcp" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "Mcp-Session-Id: $SESSION_ID" \
  -d '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"semantic_search_legal_documents","arguments":{"query":"incorporation","top_k":2}}}' \
  --max-time 15

echo -e "\n=== Test Complete ==="
```

Run: `bash test_selfhosted.sh`

---

### Test Local (PowerShell)

Save as `test_local.ps1`:

```powershell
$BASE_URL = "http://localhost:3000"

Write-Host "=== Testing Local MCP Server ===" -ForegroundColor Green

Write-Host "`n1. Health Check:" -ForegroundColor Yellow
Invoke-RestMethod -Uri "$BASE_URL/health" | ConvertTo-Json

Write-Host "`n2. Initialize Session:" -ForegroundColor Yellow
$initResponse = Invoke-WebRequest -Uri "$BASE_URL/mcp" -Method Post `
    -Headers @{
        "Content-Type" = "application/json"
        "Accept" = "application/json, text/event-stream"
    } `
    -Body '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}'

$SESSION_ID = $initResponse.Headers["Mcp-Session-Id"][0]
Write-Host "Session ID: $SESSION_ID"

Write-Host "`n3. Send Initialized:" -ForegroundColor Yellow
Invoke-WebRequest -Uri "$BASE_URL/mcp" -Method Post `
    -Headers @{
        "Content-Type" = "application/json"
        "Accept" = "application/json, text/event-stream"
        "Mcp-Session-Id" = $SESSION_ID
    } `
    -Body '{"jsonrpc":"2.0","method":"notifications/initialized"}' | Out-Null

Write-Host "`n4. List Tools:" -ForegroundColor Yellow
Invoke-RestMethod -Uri "$BASE_URL/mcp" -Method Post `
    -Headers @{
        "Content-Type" = "application/json"
        "Accept" = "application/json, text/event-stream"
        "Mcp-Session-Id" = $SESSION_ID
    } `
    -Body '{"jsonrpc":"2.0","id":2,"method":"tools/list"}'

Write-Host "`n5. Call Semantic Search:" -ForegroundColor Yellow
Invoke-RestMethod -Uri "$BASE_URL/mcp" -Method Post `
    -Headers @{
        "Content-Type" = "application/json"
        "Accept" = "application/json, text/event-stream"
        "Mcp-Session-Id" = $SESSION_ID
    } `
    -Body '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"semantic_search_legal_documents","arguments":{"query":"incorporation","top_k":2}}}' `
    -TimeoutSec 15

Write-Host "`n=== Test Complete ===" -ForegroundColor Green
```

Run: `powershell -ExecutionPolicy Bypass -File test_local.ps1`

---

## Summary

| Aspect | Self-Hosted | Local |
|--------|-------------|-------|
| **URL** | `https://your-domain.com` | `http://localhost:3000` |
| **SSL** | Required (HTTPS) | Not required (HTTP) |
| **Session** | Required | Required |
| **Startup** | Automatic (Coolify) | Manual (`python legal_rag_server.py --http`) |
| **Logs** | Coolify dashboard | Terminal/file |
| **Use Case** | Production, Claude Desktop, n8n | Development, debugging |

---

**Last Updated:** December 10, 2025
**Version:** 1.0
**Author:** MCP Server Testing Documentation
