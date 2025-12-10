# Deploying Legal RAG MCP Server to Coolify

This guide covers deploying your Legal RAG MCP server to Coolify for remote access.

## Prerequisites

- Coolify instance set up and running
- GitHub repository with your code
- Supabase project with legal documents table
- OpenAI API key
- Cohere API key

## Deployment Options

### Option 1: Nixpacks (Recommended for Quick Setup)

Nixpacks will auto-detect your Python project and handle setup automatically.

**Coolify Configuration:**
- **Build Pack**: Nixpacks
- **Port**: 3000
- **Start Command**: `uv run legal_rag_server.py --sse`

### Option 2: Dockerfile (Recommended for Production)

Use the included Dockerfile for more control and optimized builds.

**Coolify Configuration:**
- **Build Pack**: Dockerfile
- **Port**: 3000
- **Dockerfile Path**: `./Dockerfile` (default)

## Step-by-Step Coolify Setup

### 1. Create New Application

1. Log into your Coolify dashboard
2. Click **+ New Resource** > **Application**
3. Select your Git repository
4. Choose the branch to deploy (e.g., `main`)

### 2. Configure Build Settings

**For Dockerfile (Recommended):**
- Build Pack: **Dockerfile**
- Dockerfile: `./Dockerfile`
- Port: **3000**

**For Nixpacks:**
- Build Pack: **Nixpacks**
- Port: **3000**
- Start Command: `uv run legal_rag_server.py --sse`

### 3. Environment Variables

Add these environment variables in Coolify's Environment tab:

```env
# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key_here

# AI API Keys
OPENAI_API_KEY=sk-your-openai-api-key
COHERE_API_KEY=your-cohere-api-key

# Legal RAG Configuration
LEGAL_RAG_TABLE_NAME=n8n_law_startuplaw
LEGAL_RAG_MATCH_FUNCTION=match_n8n_law_startuplaw
LEGAL_RAG_TOP_K=10
```

**Security Note:** Never commit these values to your repository. Always set them in Coolify's environment configuration.

### 4. Deploy

1. Click **Deploy** button
2. Monitor the build logs
3. Once deployed, note your application URL (e.g., `https://legal-rag.your-coolify-domain.com`)

### 5. Test Deployment

Test your deployment with curl:

```bash
curl https://legal-rag.your-coolify-domain.com/health
```

You should see a health check response.

## Configure Claude Desktop for Remote Access

After deployment, update your Claude Desktop configuration to connect to the remote server.

**Location:**
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

**Configuration:**

```json
{
  "mcpServers": {
    "legal-rag": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/client-sse",
        "https://legal-rag.your-coolify-domain.com"
      ]
    }
  }
}
```

Replace `https://legal-rag.your-coolify-domain.com` with your actual Coolify app URL.

**Restart Claude Desktop** after updating the configuration.

## Local Development vs Remote Access

### Local Mode (stdio transport)

For local development, run without the `--sse` flag:

```bash
uv run legal_rag_server.py
```

Configure Claude Desktop:

```json
{
  "mcpServers": {
    "legal-rag": {
      "command": "uv",
      "args": ["run", "legal_rag_server.py"],
      "cwd": "/path/to/MCP_Server"
    }
  }
}
```

### Remote Mode (SSE transport)

For remote access via Coolify, the server automatically runs with `--sse` flag.

Configure Claude Desktop as shown in section 5 above.

## Benefits of Remote Deployment

- Access from any machine with Claude Desktop
- Always running (no need to start locally)
- Environment variables secured in Coolify
- Easy updates via git push
- Can share with team members
- Automatic SSL/TLS via Coolify

## Troubleshooting

### Build Fails

**Problem:** Build fails with dependency errors

**Solution:** Ensure `uv.lock` file is committed to your repository. Run `uv lock` locally first.

### Server Not Responding

**Problem:** Application deployed but not responding

**Solution:**
1. Check Coolify logs for errors
2. Verify environment variables are set correctly
3. Check if port 3000 is exposed correctly
4. Verify Supabase credentials and table names

### Claude Desktop Can't Connect

**Problem:** Claude Desktop shows connection errors

**Solution:**
1. Test the URL in a browser or with curl
2. Ensure the URL in config is correct (no trailing slash)
3. Check Coolify application is running
4. Restart Claude Desktop after config changes

### Authentication Errors

**Problem:** API returns authentication errors

**Solution:**
1. Verify `SUPABASE_SERVICE_ROLE_KEY` is set correctly
2. Check Supabase project URL matches your project
3. Ensure API keys (OpenAI, Cohere) are valid

## Updating Your Deployment

To update your deployment:

1. Push changes to your Git repository
2. Coolify will auto-deploy (if auto-deploy is enabled)
3. Or manually click **Deploy** in Coolify dashboard

## Monitoring

Coolify provides:
- **Logs**: Real-time application logs
- **Metrics**: CPU, memory, network usage
- **Health Checks**: Automatic monitoring via healthcheck endpoint

## Security Considerations

1. **Always use HTTPS** - Coolify provides this automatically
2. **Keep API keys secure** - Use Coolify's environment variables, never commit to Git
3. **Use service role key** - Required for Supabase database access
4. **Regular updates** - Keep dependencies updated with `uv lock --upgrade`
5. **Monitor logs** - Check for unauthorized access attempts

## Cost Optimization

- Use Nixpacks for faster builds (smaller Docker context)
- Enable Coolify's build cache
- Consider reducing `LEGAL_RAG_TOP_K` if API costs are high
- Monitor API usage (OpenAI embeddings, Cohere reranking)

## Next Steps

After successful deployment:

1. Test all MCP tools from Claude Desktop
2. Monitor logs for any errors
3. Set up monitoring/alerting if needed
4. Share access URL with team members
5. Document any custom configurations

## Support

For issues:
- Check Coolify logs first
- Verify environment variables
- Test Supabase connection separately
- Check API key validity
- Review MCP server logs
