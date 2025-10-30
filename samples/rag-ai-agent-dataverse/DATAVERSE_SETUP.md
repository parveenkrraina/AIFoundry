# Dataverse Integration Guide

This guide explains how to set up and configure Dataverse integration with the RAG AI Agent.

## 🎯 Overview

The agent can now search both:
- **Microsoft 365 Content**: SharePoint, OneDrive (via Microsoft Graph API)
- **Dataverse Tables**: Business data stored in Dataverse tables

## 📋 Prerequisites

1. Azure AD App Registration (already configured for Graph API)
2. Power Platform environment with Dataverse
3. Appropriate permissions in Dataverse

## 🔧 Setup Steps

### Step 1: Get Your Dataverse Environment URL

1. Go to [Power Platform Admin Center](https://admin.powerplatform.microsoft.com/)
2. Select your environment
3. Copy the **Environment URL** (e.g., `https://your-org.crm.dynamics.com`)

### Step 2: Grant API Permissions to Your Azure AD App

1. Go to [Azure Portal - App Registrations](https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps)
2. Open your app registration (same one used for Graph API)
3. Go to **API permissions**
4. Click **Add a permission** → **APIs my organization uses**
5. Search for **Dynamics CRM** or **Common Data Service**
6. Select **Delegated permissions**
7. Add **user_impersonation** permission
8. Click **Add permissions**
9. **(Optional)** Grant admin consent if required

### Step 3: Configure Environment Variables

Update your `.env` file:

```env
# Enable Dataverse integration
ENABLE_DATAVERSE=true

# Your Dataverse environment URL
DATAVERSE_ENVIRONMENT_URL=https://your-org.crm.dynamics.com

# Use same app registration as Graph API (or create separate one)
DATAVERSE_CLIENT_ID=your_azure_ad_app_client_id
DATAVERSE_TENANT_ID=common
```

### Step 4: Customize Table Search (Optional)

Edit `dataverse_client.py` to specify which tables to search:

```python
# In the search_dataverse_tables function, customize table_names:
table_names = ['account', 'contact', 'opportunity', 'incident']
```

Or specify tables when calling:

```python
search_dataverse_tables(query, max_results=5, table_names=['account', 'contact'])
```

## 🎮 Usage

Once configured, the agent will automatically search Dataverse tables along with Microsoft 365 content:

```
You: What customers do we have?

🔍 Searching Microsoft 365 and Dataverse for: 'What customers do we have?'
✅ Successfully authenticated with Dataverse

📚 Retrieved Context:
💾 Dataverse Records:
[account] Contoso Ltd: Leading technology company
[account] Fabrikam Inc: Manufacturing partner
📄 SharePoint Content:
Customer_List.docx: Updated list of active customers
```

## 📊 Default Tables Searched

By default, the agent searches these Dataverse tables:
- **account** - Customer accounts
- **contact** - Contact records
- **annotation** - Notes and attachments

## 🔍 Customizing Search

### Search Specific Fields

Edit the `search_dataverse_tables` function to add field-specific filters:

```python
# Add OData filter for specific fields
params = {
    "$top": max_results,
    "$select": "name,emailaddress1,telephone1",
    "$filter": f"contains(name,'{query}') or contains(emailaddress1,'{query}')"
}
```

### Search Custom Tables

To search your custom tables:

```python
# Add your custom table logical names
table_names = ['cr123_customtable', 'cr123_anothertable']
```

## 🔐 Security & Permissions

- **User Impersonation**: The agent accesses Dataverse as the logged-in user
- **Row-Level Security**: Users only see records they have permission to access
- **Business Units**: Security rules are respected
- **Audit Logs**: All API calls are logged in Dataverse

## ⚙️ Troubleshooting

### Issue: "Could not authenticate with Dataverse"

**Solutions:**
1. Verify `DATAVERSE_ENVIRONMENT_URL` is correct
2. Check that user_impersonation permission is granted
3. Ensure you're logged in with correct account: `az login`
4. Try device code authentication: `GRAPH_AUTH_METHOD=device_code`

### Issue: "Could not search [table]"

**Solutions:**
1. Check table logical name is correct (use Power Apps maker portal)
2. Verify user has read permissions on the table
3. Check table has records that match your query

### Issue: "No relevant records found"

**Solutions:**
1. Verify data exists in Dataverse tables
2. Check field names in the search query
3. Add custom filters for your table schema

## 🚀 Advanced Configuration

### Search with FetchXML

For complex queries, you can use FetchXML:

```python
def search_with_fetchxml(query):
    token = get_dataverse_token()
    
    fetchxml = f"""
    <fetch top="5">
      <entity name="account">
        <attribute name="name" />
        <attribute name="description" />
        <filter>
          <condition attribute="name" operator="like" value="%{query}%" />
        </filter>
      </entity>
    </fetch>
    """
    
    url = f"{DATAVERSE_ENVIRONMENT_URL}/api/data/v9.2/accounts?fetchXml={fetchxml}"
    # ... rest of implementation
```

### Use Dataverse Search API

For full-text search across multiple tables:

```python
url = f"{DATAVERSE_ENVIRONMENT_URL}/api/data/v9.2/search"
body = {
    "search": query,
    "entities": ["account", "contact", "incident"],
    "top": 10
}
```

## 📚 Additional Resources

- [Dataverse Web API Documentation](https://learn.microsoft.com/power-apps/developer/data-platform/webapi/overview)
- [Query Data using Web API](https://learn.microsoft.com/power-apps/developer/data-platform/webapi/query-data-web-api)
- [Authenticate with Dataverse](https://learn.microsoft.com/power-apps/developer/data-platform/authenticate-oauth)
- [Dataverse Security](https://learn.microsoft.com/power-apps/developer/data-platform/security-concepts)

## 🔄 Disabling Dataverse

To use only Microsoft Graph API without Dataverse:

```env
ENABLE_DATAVERSE=false
```

The agent will continue to work with SharePoint and OneDrive search only.
