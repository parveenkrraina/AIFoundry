# Dataverse RAG Agent

A streamlined Retrieval-Augmented Generation (RAG) agent that queries Microsoft Dataverse (only) and uses Azure OpenAI to formulate answers. No Microsoft 365 (SharePoint/OneDrive/OneNote) and no Azure AI Search indexing — just Dataverse APIs plus metadata-driven aggregates.

## What you can do

- Ask natural questions and get answers grounded in Dataverse records.
- Run generic aggregates over any table using OData $apply: sum, avg, count — with optional year filters.
- Resolve correct collection endpoints dynamically from Dataverse metadata (no hardcoding).

Examples:
- "count records from account in 2024"
- "sum totalamount from opportunity in 2023"
- "show records from cr5cd_sales"
- "total sales for 2024"

## Prerequisites

- Python 3.8+
- An Azure AD app registration
  - Delegated permission: Dynamics CRM (Common Data Service) → user_impersonation
  - Authentication → Allow public client flows = Yes (for interactive browser/device code)
- A Dataverse environment URL (e.g., https://your-org.crm.dynamics.com)
- Azure OpenAI (endpoint + API key) for answer generation

## Setup (Windows PowerShell shown)

1) Install dependencies

```powershell
cd E:\ai-foundry\mcpDemo\rag-ai-agent-dataverse
pip install -r agent/requirements.txt
```

2) Create and edit your .env

```powershell
Copy-Item .env.example .env
```

Edit `.env` and set at minimum:

```properties
# Dataverse
ENABLE_DATAVERSE=true
DATAVERSE_ENVIRONMENT_URL=https://your-org.crm.dynamics.com
DATAVERSE_CLIENT_ID=<your AAD app client id>
DATAVERSE_TENANT_ID=common  # or your tenant id
GRAPH_AUTH_METHOD=interactive  # interactive | device_code | default

# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://<your-openai>.openai.azure.com/
AZURE_OPENAI_API_KEY=<key>
AGENT_MODEL=gpt-4o  # or your deployment name
API_VERSION=2024-02-15-preview

# Keep SharePoint/Azure Search OFF for clean Dataverse-only
ENABLE_SHAREPOINT=false
ENABLE_AZURE_SEARCH=false
```

3) Run

Interactive mode:

```powershell
cd agent
python main.py
```

One-shot question:

```powershell
cd agent
python main.py "count records from account in 2024"
```

## How it works

- Uses azure-identity (interactive/device code/default) to get an access token for Dataverse.
- For each detected table, resolves the correct EntitySetName via metadata.
- If your prompt implies an aggregate (sum/avg/count), it issues a server-side OData $apply query with an optional year filter. Year scoping prioritizes domain date fields (e.g., orderdate) and falls back to createdon.
- Returns a compact, human-readable summary or aggregate, then Azure OpenAI drafts the answer.

## Tips

- Use logical table names (e.g., account, contact, opportunity, cr5cd_sales).
- Include a year in your question to scope results (e.g., 2024).
- For custom totals like unitprice × quantity, prefer a Dataverse calculated column (e.g., linetotal) so generic sum works out of the box.

## Troubleshooting

- 401/permission errors: ensure your AAD app has Dynamics CRM → user_impersonation (delegated), and admin consent if required.
- 404 table not found: verify the logical name, not the display name.
- Empty results: confirm the table contains data for the period asked.
- Auth method: switch GRAPH_AUTH_METHOD between interactive and device_code if needed.

## Project structure

```
rag-ai-agent-dataverse/
  agent/
    main.py              # CLI entry point
    dataverse_client.py  # Dataverse-only retrieval and aggregates
    openai_client.py     # Azure OpenAI wrapper
    requirements.txt
  .env.example
  README.md
```

```powershell
cd agent
python dataverse_client.py
```

This will:
1. Authenticate with Microsoft Graph
2. Display your user information
3. Perform a test search

### Test OpenAI Client

```powershell
cd agent
python openai_client.py
```

## 🎛️ Azure AI Foundry Agent Features

The solution uses Azure OpenAI Service (part of Azure AI Foundry) with:
- **Direct API Access**: Uses endpoint and API key for simple, reliable authentication
- **Model Selection**: Configure any deployed model (GPT-4, GPT-4o, GPT-3.5-turbo)
- **Customizable System Prompts**: Define agent behavior and responsibilities
- **Temperature Control**: Adjust creativity vs. consistency
- **Token Limits**: Control response length

### How It Works

1. **Context Retrieval**: Searches Microsoft 365 via Graph API
2. **Prompt Construction**: Combines context with user query
3. **AI Generation**: Sends to Azure OpenAI with system instructions
4. **Response Delivery**: Returns context-aware answer to user

## 🐛 Troubleshooting

### Common Issues

1. **Import errors for `requests` or `dotenv`:**
   - Run: `pip install -r agent/requirements.txt`

2. **Authentication errors with Microsoft Graph:**
   - Ensure your Azure AD app is properly configured
   - Verify `GRAPH_CLIENT_ID` is correct in `.env`
   - Check that API permissions are granted (and admin consent if required)
   - Try running `az login` if using default authentication
   - Make sure "Allow public client flows" is enabled in app registration

3. **Azure AI Foundry errors:**
   - Verify you're using the correct endpoint URL (should end with `.openai.azure.com/`)
   - Check that the API key is valid and not expired
   - Ensure the deployment name in `AGENT_MODEL` matches your actual deployment
   - Verify the model is deployed and running in Azure AI Foundry
   - Try regenerating the API key if authentication fails

4. **No context retrieved:**
   - **Microsoft 365:**
     - Verify you have content in SharePoint/OneDrive
     - Check that you're logged in with the correct Microsoft 365 account
     - Ensure the search query matches content in your Microsoft 365 environment
     - Test with simple queries like "document" or "file"
     - Check Graph API permissions are granted
   
   - **Dataverse:**
     - Verify `ENABLE_DATAVERSE=true` in `.env`
     - Check that `DATAVERSE_ENVIRONMENT_URL` is correct
     - Ensure Dataverse tables have data matching your query
     - Verify Dynamics CRM API permission (`user_impersonation`) is granted
     - Check that table names in code match your Dataverse schema

5. **Browser doesn't open for authentication:**
   - Try changing to device code flow: `GRAPH_AUTH_METHOD=device_code`
   - Or use default credential after `az login`

6. **Dataverse authentication errors:**
   - Ensure the same Azure AD app is used for both Graph and Dataverse
   - Grant `user_impersonation` permission for Dynamics CRM API
   - Verify user has access to the Dataverse environment
   - See [DATAVERSE_SETUP.md](./DATAVERSE_SETUP.md) for detailed troubleshooting

## 🎯 Best Practices

1. **Security:**
   - Never commit `.env` file to version control
   - Use least-privilege principle for Graph API permissions
   - For production, use Managed Identity instead of app registration
   - Regularly review and rotate client secrets (if using client credentials)
   - Store sensitive configuration in Azure Key Vault

2. **Performance:**
   - Limit the number of search results (`max_results` parameter)
   - Cache frequently accessed content
   - Use appropriate timeout values
   - Consider implementing pagination for large result sets

3. **User Experience:**
   - Provide clear authentication instructions to users
   - Handle authentication errors gracefully
   - Show which content sources are being searched
   - Respect user permissions - never try to access content they can't see

## 📚 Additional Resources

### General Documentation
- [Azure AI Foundry Documentation](https://learn.microsoft.com/azure/ai-studio/)
- [Azure AI Foundry Agents Documentation](https://learn.microsoft.com/azure/ai-studio/how-to/develop/agents)
- [RAG Pattern Best Practices](https://learn.microsoft.com/azure/architecture/ai-ml/guide/rag/rag-solution-design-and-evaluation-guide)

### Microsoft Graph API
- [Microsoft Graph API Documentation](https://learn.microsoft.com/graph/)
- [Microsoft Graph Python SDK](https://learn.microsoft.com/graph/sdks/sdks-overview)
- [Graph API Search Endpoint](https://learn.microsoft.com/graph/api/resources/search-api-overview)

### Microsoft Dataverse
- [Dataverse Web API Documentation](https://learn.microsoft.com/power-apps/developer/data-platform/webapi/overview)
- [Query Data using Web API](https://learn.microsoft.com/power-apps/developer/data-platform/webapi/query-data-web-api)
- [Authenticate with Dataverse](https://learn.microsoft.com/power-apps/developer/data-platform/authenticate-oauth)
- [Dataverse Security Concepts](https://learn.microsoft.com/power-apps/developer/data-platform/security-concepts)
- **[📘 DATAVERSE_SETUP.md](./DATAVERSE_SETUP.md)** - Complete setup guide in this repo

### Authentication
- [Azure AD App Registration Guide](https://learn.microsoft.com/azure/active-directory/develop/quickstart-register-app)
- [Azure Identity & Authentication](https://learn.microsoft.com/python/api/overview/azure/identity-readme)

## 🤝 Contributing

Feel free to customize this solution for your specific use case. Consider:
- Adding semantic search capabilities to Graph queries
- Implementing caching for frequently accessed content
- Integrating additional Microsoft 365 services (Teams, Planner, etc.)
- Extending Dataverse integration with custom entities and relationships
- Adding support for file attachments and binary content retrieval
- Implementing conversation history and multi-turn context
- Implementing conversation history and multi-turn dialogues
- Adding more Microsoft 365 data sources (Teams, Planner, etc.)
- Deploying as an Azure Function or Container App
- Creating a web UI with Streamlit or Flask
- Adding function calling capabilities to the agent
- Integrating with Microsoft Teams as a bot
- Adding email search capabilities
- Implementing caching for better performance

## 🚀 Advanced: Deploying to Azure

### Deploy as Azure Function
```powershell
# Create function app
func init --worker-runtime python
func new --name RagAgent --template "HTTP trigger"

# Deploy
func azure functionapp publish <your-function-app-name>
```

### Deploy as Container App
```powershell
# Build container
docker build -t rag-agent .

# Push to Azure Container Registry
az acr build --registry <your-acr> --image rag-agent:latest .

# Deploy to Container Apps
az containerapp create --name rag-agent --resource-group <rg> --image <your-acr>.azurecr.io/rag-agent:latest
```

## 📝 License

This is a sample project for educational purposes.

---

**Built with Azure AI Foundry & Microsoft Graph API** 🚀

## 🔑 Key Benefits of This Architecture

### Using Microsoft Graph API with User Authentication

1. **Personalized Access**: Each user sees only their own content and what they have permissions to access
2. **No Token Management**: Uses interactive authentication - no need to manage bearer tokens
3. **Secure by Default**: Leverages Microsoft identity platform security
4. **Rich Content Access**: Access to SharePoint, OneDrive, OneNote, and more
5. **Real-time Data**: Always queries the latest content from Microsoft 365
6. **Compliance**: Respects organizational data governance and DLP policies

### Using Azure AI Foundry Agents

1. **Managed Infrastructure**: No need to manage complex agent frameworks manually
2. **Built-in Agent Framework**: Structured approach to building AI agents
3. **Easy Integration**: Seamless integration with other Azure AI services
4. **Thread Management**: Automatic conversation context handling
5. **Scalability**: Enterprise-grade scalability and reliability
6. **Security**: Leverages Azure identity and access management
7. **Simple Authentication**: Just endpoint and API key - no complex setup

## 🔐 Security Considerations

- **Delegated Permissions**: The app uses delegated permissions, meaning it can only access what the logged-in user can access
- **No Elevation**: The app cannot elevate privileges or access content the user doesn't have permissions to
- **Audit Logs**: All Graph API calls are logged in Azure AD audit logs
- **Conditional Access**: Respects organizational conditional access policies
- **MFA Support**: Fully supports multi-factor authentication requirements

## 🌐 Extending to Other Microsoft 365 Services

You can easily extend this solution to search other Microsoft 365 services:

```python
# Add to dataverse_client.py

# Search Emails
def search_emails(query, max_results=5):
    graph_client = get_graph_client()
    messages = graph_client.me.messages.get(
        search=query,
        top=max_results
    )
    # Process messages...

# Search Teams Messages  
def search_teams_messages(query, max_results=5):
    graph_client = get_graph_client()
    # Search across user's teams
    # Process results...

# Search Calendar Events
def search_calendar_events(query, max_results=5):
    graph_client = get_graph_client()
    events = graph_client.me.events.get()
    # Process events...
```

Remember to add the corresponding permissions to your Azure AD app!
