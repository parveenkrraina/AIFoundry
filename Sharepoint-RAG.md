# SharePoint RAG Implementation Guide

**A Step-by-Step Guide**

This guide will help you build a simple Retrieval-Augmented Generation (RAG) application that connects to SharePoint, indexes documents, and answers questions using Azure AI services.

---

## 📋 Prerequisites

Before starting, ensure you have:

1. **Python 3.8+** installed on your system
2. **Visual Studio Code** or any code editor
3. **Azure Account** with access to:
   - Azure AI Search
   - Azure OpenAI Service
   - SharePoint Online
4. **Azure AD App Registration** with:
   - Client ID
   - Client Secret
   - Tenant ID
   - SharePoint permissions (Sites.Read.All)

---

## 🎯 What You'll Build

A console application that:
- Connects to your SharePoint site
- Fetches and indexes documents (PDF, DOCX, TXT)
- Uses Azure AI Search for document retrieval
- Answers questions using Azure OpenAI (GPT-4)

---

## 📁 Step 1: Create Project Structure

Create a new folder for your project and set up the following structure:

```
sharepoint-rag-simple/
│
├── app.py                      # Main application file
├── rag_query.py               # RAG query handler
├── indexer.py                 # Document indexer
├── sharepoint_connector.py    # SharePoint connector
├── .env                       # Environment variables (DO NOT commit to Git!)
├── requirements.txt           # Python dependencies
└── README.md                  # Project documentation
```

**Create the folder:**

```bash
mkdir sharepoint-rag-simple
cd sharepoint-rag-simple
```

---

## 📦 Step 2: Install Required Packages

### 2.1 Create `requirements.txt`

Create a file named `requirements.txt` and add the following content:

```txt
azure-search-documents==11.6.0
openai==1.54.4
python-dotenv==1.0.0
rich==13.7.0
msal==1.31.0
requests==2.32.3
pypdf==5.1.0
```

### 2.2 Install Dependencies

Run the following command in your terminal:

```bash
pip install -r requirements.txt
```

---

## 🔐 Step 3: Configure Environment Variables

### 3.1 Create `.env` File

Create a file named `.env` in your project root and add the following (replace placeholders with your actual values):

```env
# Azure AI Search Configuration
AZURE_SEARCH_ENDPOINT=https://YOUR-SEARCH-SERVICE.search.windows.net
AZURE_SEARCH_KEY=YOUR-SEARCH-ADMIN-KEY
AZURE_SEARCH_INDEX_NAME=sharepoint-docs

# Azure OpenAI Configuration
AZURE_OPENAI_ENDPOINT=https://YOUR-OPENAI-RESOURCE.openai.azure.com/
AZURE_OPENAI_KEY=YOUR-OPENAI-KEY

# Model Deployment Name
MODEL_DEPLOYMENT_NAME=gpt-4

# SharePoint Configuration
AZURE_TENANT_ID=YOUR-TENANT-ID
AZURE_CLIENT_ID=YOUR-CLIENT-ID
AZURE_CLIENT_SECRET=YOUR-CLIENT-SECRET
SHAREPOINT_SITE_ID=YOUR-SITE-ID
```

### 3.2 How to Get These Values

**Azure AI Search:**
1. Go to Azure Portal → Your Search Service
2. Copy the URL (Endpoint)
3. Go to Keys → Copy Primary Admin Key

**Azure OpenAI:**
1. Go to Azure Portal → Your OpenAI Resource
2. Copy the Endpoint URL
3. Go to Keys and Endpoint → Copy KEY 1
4. Go to Model Deployments → Note your GPT-4 deployment name

**SharePoint Site ID:**
1. Go to your SharePoint site
2. Use Microsoft Graph Explorer: `https://graph.microsoft.com/v1.0/sites/{hostname}:{site-path}`
3. Example: `https://graph.microsoft.com/v1.0/sites/contoso.sharepoint.com:/sites/TeamSite`

**Azure AD App Registration:**
1. Go to Azure Portal → Azure Active Directory → App Registrations
2. Copy Application (client) ID
3. Copy Directory (tenant) ID
4. Go to Certificates & Secrets → Create new client secret → Copy the value

---

## 💻 Step 4: Create SharePoint Connector

### 4.1 Create `sharepoint_connector.py`

Create a new file named `sharepoint_connector.py` and add the following code:

```python
"""
SharePoint connector - fetches documents from SharePoint.
"""
import os
from typing import List, Dict, Optional
from io import BytesIO
import requests
from msal import ConfidentialClientApplication
from pypdf import PdfReader


class SharePointConnector:
    """Simple SharePoint connector."""
    
    def __init__(self, tenant_id: str, client_id: str, client_secret: str, site_id: str):
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.site_id = site_id
        self.graph_base = "https://graph.microsoft.com/v1.0"
        
        # Initialize MSAL
        self.app = ConfidentialClientApplication(
            client_id,
            authority=f"https://login.microsoftonline.com/{tenant_id}",
            client_credential=client_secret
        )
    
    def _get_token(self) -> str:
        """Get access token."""
        result = self.app.acquire_token_for_client(
            scopes=["https://graph.microsoft.com/.default"]
        )
        if "access_token" in result:
            return result["access_token"]
        raise Exception(f"Failed to get token: {result.get('error_description')}")
    
    def list_documents(self, top: int = 50) -> List[Dict]:
        """List documents from SharePoint."""
        token = self._get_token()
        headers = {"Authorization": f"Bearer {token}"}
        
        url = f"{self.graph_base}/sites/{self.site_id}/drive/root/children"
        params = {"$top": top}
        
        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            items = response.json().get('value', [])
            
            documents = []
            for item in items:
                if 'file' in item:
                    documents.append({
                        'id': item['id'],
                        'name': item['name'],
                        'url': item.get('webUrl', ''),
                        'drive_id': item.get('parentReference', {}).get('driveId', ''),
                        'mime_type': item.get('file', {}).get('mimeType', '')
                    })
            
            return documents
            
        except Exception as e:
            print(f"Error listing documents: {e}")
            return []
    
    def get_document_content(self, drive_id: str, item_id: str) -> Optional[str]:
        """Download and extract document content."""
        token = self._get_token()
        headers = {"Authorization": f"Bearer {token}"}
        
        content_url = f"{self.graph_base}/drives/{drive_id}/items/{item_id}/content"
        
        try:
            response = requests.get(content_url, headers=headers)
            response.raise_for_status()
            
            content_type = response.headers.get('Content-Type', '')
            
            # Handle text content
            if any(ct in content_type.lower() for ct in ['text', 'json', 'xml', 'html']):
                return response.text
            
            # Handle PDF files
            if 'pdf' in content_type.lower():
                return self._extract_pdf_text(response.content)
            
            return None
            
        except Exception as e:
            print(f"Error downloading content: {e}")
            return None
    
    def _extract_pdf_text(self, pdf_content: bytes) -> Optional[str]:
        """Extract text from PDF."""
        try:
            pdf_file = BytesIO(pdf_content)
            reader = PdfReader(pdf_file)
            
            text = []
            max_pages = min(10, len(reader.pages))  # Limit pages
            for page_num in range(max_pages):
                page = reader.pages[page_num]
                text.append(page.extract_text())
            
            return '\n\n'.join(text)
            
        except Exception as e:
            print(f"Could not extract PDF text: {e}")
            return None
```

**What this code does:**
- Connects to SharePoint using Microsoft Graph API
- Authenticates using Azure AD credentials
- Lists documents from SharePoint site
- Downloads and extracts text from PDF files
- Supports text files and PDFs

---

## 🔍 Step 5: Create Document Indexer

### 5.1 Create `indexer.py`

Create a new file named `indexer.py` and add the following code:

```python
"""
Simple document indexer for Azure AI Search.
"""
from typing import List, Dict
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SimpleField,
    SearchableField,
    SearchFieldDataType
)


class SimpleIndexer:
    """Simple document indexer without chunking or embeddings."""
    
    def __init__(self, search_endpoint: str, search_key: str, index_name: str):
        self.endpoint = search_endpoint
        self.credential = AzureKeyCredential(search_key)
        self.index_name = index_name
        
        self.index_client = SearchIndexClient(
            endpoint=self.endpoint,
            credential=self.credential
        )
        
        self.search_client = SearchClient(
            endpoint=self.endpoint,
            index_name=self.index_name,
            credential=self.credential
        )
    
    def create_index(self):
        """Create search index with simple schema."""
        fields = [
            SimpleField(
                name="id",
                type=SearchFieldDataType.String,
                key=True
            ),
            SearchableField(
                name="content",
                type=SearchFieldDataType.String,
                searchable=True
            ),
            SearchableField(
                name="document_name",
                type=SearchFieldDataType.String,
                searchable=True,
                filterable=True
            ),
            SimpleField(
                name="document_url",
                type=SearchFieldDataType.String
            )
        ]
        
        index = SearchIndex(name=self.index_name, fields=fields)
        
        try:
            self.index_client.create_or_update_index(index)
            print(f"✓ Index '{self.index_name}' created/updated successfully")
        except Exception as e:
            print(f"Error creating index: {e}")
            raise
    
    def index_documents(self, documents: List[Dict]):
        """Index documents without chunking."""
        if not documents:
            print("No documents to index")
            return
        
        # Prepare documents for indexing
        search_docs = []
        for doc in documents:
            # Truncate content to avoid size limits (5000 chars)
            content = doc.get('content', '')[:5000]
            
            search_docs.append({
                'id': doc['id'],
                'content': content,
                'document_name': doc['name'],
                'document_url': doc.get('url', '')
            })
        
        # Upload to Azure Search
        try:
            result = self.search_client.upload_documents(documents=search_docs)
            success_count = sum(1 for r in result if r.succeeded)
            print(f"✓ Indexed {success_count}/{len(search_docs)} documents")
        except Exception as e:
            print(f"Error indexing documents: {e}")
            raise
    
    def delete_all_documents(self):
        """Delete all documents from index."""
        try:
            # This is a placeholder - implement based on your needs
            print("Delete all documents not implemented")
        except Exception as e:
            print(f"Error deleting documents: {e}")
```

**What this code does:**
- Creates an Azure AI Search index with 4 fields (id, content, document_name, document_url)
- Uploads documents to the search index
- Truncates large documents to 5000 characters
- No chunking or vector embeddings (simple keyword search)

---

## 🤖 Step 6: Create RAG Query Handler

### 6.1 Create `rag_query.py`

Create a new file named `rag_query.py` and add the following code:

```python
"""
RAG Query Handler - Simple implementation without vector embeddings.
"""
from typing import Tuple, List, Dict
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from openai import AzureOpenAI


class RAGQuery:
    """Simple RAG query handler with keyword search."""
    
    def __init__(
        self,
        search_endpoint: str,
        search_key: str,
        index_name: str,
        openai_endpoint: str,
        openai_key: str,
        model_deployment: str
    ):
        # Initialize Azure Search client
        self.search_client = SearchClient(
            endpoint=search_endpoint,
            index_name=index_name,
            credential=AzureKeyCredential(search_key)
        )
        
        # Initialize Azure OpenAI client
        self.openai_client = AzureOpenAI(
            azure_endpoint=openai_endpoint,
            api_key=openai_key,
            api_version="2024-02-15-preview"
        )
        
        self.model_deployment = model_deployment
    
    def _search(self, query: str, top: int = 3) -> List[Dict]:
        """Search for relevant documents."""
        try:
            results = self.search_client.search(
                search_text=query,
                top=top,
                select=["content", "document_name", "document_url"]
            )
            
            documents = []
            for result in results:
                documents.append({
                    'content': result.get('content', ''),
                    'name': result.get('document_name', 'Unknown'),
                    'url': result.get('document_url', '')
                })
            
            return documents
            
        except Exception as e:
            print(f"Search error: {e}")
            return []
    
    def _generate_answer(self, query: str, context: str) -> str:
        """Generate answer using Azure OpenAI."""
        system_prompt = """You are a helpful assistant that answers questions based on the provided context.
        If the context doesn't contain relevant information, say so politely.
        Be concise and accurate in your responses."""
        
        user_prompt = f"""Context:
{context}

Question: {query}

Answer:"""
        
        try:
            response = self.openai_client.chat.completions.create(
                model=self.model_deployment,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=500
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"OpenAI error: {e}")
            return "Sorry, I couldn't generate an answer at this time."
    
    def ask(self, question: str) -> Dict:
        """Ask a question and get an answer."""
        # Search for relevant documents
        documents = self._search(question, top=3)
        
        if not documents:
            return {
                'answer': "I couldn't find any relevant documents to answer your question.",
                'sources': []
            }
        
        # Combine document content as context
        context = "\n\n".join([
            f"Document: {doc['name']}\n{doc['content'][:1000]}"
            for doc in documents
        ])
        
        # Generate answer
        answer = self._generate_answer(question, context)
        
        # Prepare sources
        sources = [
            {'name': doc['name'], 'url': doc['url']}
            for doc in documents
        ]
        
        return {
            'answer': answer,
            'sources': sources
        }
    
    def query(self, question: str) -> Tuple[str, List[Dict]]:
        """Query and return answer with sources (backward compatibility)."""
        result = self.ask(question)
        return result['answer'], result['sources']
```

**What this code does:**
- Searches Azure AI Search for relevant documents using keywords
- Retrieves top 3 matching documents
- Combines document content as context
- Uses Azure OpenAI (GPT-4) to generate answers
- Returns answer with source citations

---

## 🖥️ Step 7: Create Main Application

### 7.1 Create `app.py`

Create a new file named `app.py` and add the following code:

```python
"""
Simple SharePoint RAG Console - Minimal implementation
"""
import os
import sys
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.prompt import Prompt
from rich.progress import Progress, SpinnerColumn, TextColumn

from rag_query import RAGQuery
from indexer import SimpleIndexer
from sharepoint_connector import SharePointConnector


console = Console()


def load_config():
    """Load configuration from .env file."""
    load_dotenv()
    
    config = {
        'search_endpoint': os.getenv('AZURE_SEARCH_ENDPOINT'),
        'search_key': os.getenv('AZURE_SEARCH_KEY'),
        'search_index': os.getenv('AZURE_SEARCH_INDEX_NAME', 'sharepoint-docs'),
        'azure_openai_endpoint': os.getenv('AZURE_OPENAI_ENDPOINT'),
        'azure_openai_key': os.getenv('AZURE_OPENAI_KEY'),
        'model_deployment': os.getenv('MODEL_DEPLOYMENT_NAME', 'gpt-4')
    }
    
    # Validate required fields
    required = ['search_endpoint', 'search_key', 'azure_openai_endpoint', 'azure_openai_key']
    missing = [k for k in required if not config.get(k)]
    
    if missing:
        console.print(f"[red]❌ Missing required environment variables: {', '.join(missing)}[/red]")
        console.print("\n[yellow]Please check your .env file.[/yellow]")
        sys.exit(1)
    
    return config


def display_welcome():
    """Display welcome message."""
    welcome_text = """
# SharePoint AI Console

Ask questions about your SharePoint documents using AI.

**Commands:**
- Type **`index`** to fetch and index documents from SharePoint
- Type your question to get AI-powered answers
- Type **`help`** to see this message
- Type **`exit`** or **`quit`** to exit
    """
    console.print(Panel(Markdown(welcome_text), title="Welcome", border_style="blue"))


def display_answer(result: dict):
    """Display answer with sources."""
    # Display answer
    console.print("\n[bold green]📝 Answer:[/bold green]")
    console.print(Panel(result['answer'], border_style="green"))
    
    # Display sources
    if result.get('sources'):
        console.print("\n[bold blue]📚 Sources:[/bold blue]")
        for i, source in enumerate(result['sources'], 1):
            console.print(f"  {i}. [cyan]{source['name']}[/cyan]")
            if source.get('url'):
                console.print(f"     [dim]{source['url']}[/dim]")


def index_documents(config: dict):
    """Index documents from SharePoint."""
    console.print("\n[bold cyan]📥 Indexing Documents from SharePoint[/bold cyan]\n")
    
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Connecting to SharePoint...", total=None)
            
            # Initialize SharePoint connector
            sp = SharePointConnector(
                tenant_id=os.getenv("AZURE_TENANT_ID"),
                client_id=os.getenv("AZURE_CLIENT_ID"),
                client_secret=os.getenv("AZURE_CLIENT_SECRET"),
                site_id=os.getenv("SHAREPOINT_SITE_ID")
            )
            
            # Fetch documents
            progress.update(task, description="Fetching documents...")
            docs = sp.list_documents(top=20)
            
            if not docs:
                console.print("[yellow]⚠️  No documents found.[/yellow]\n")
                return
            
            console.print(f"[green]✓ Found {len(docs)} documents[/green]")
            
            # Download content
            progress.update(task, description="Downloading content...")
            documents = []
            for doc in docs:
                content = sp.get_document_content(doc['drive_id'], doc['id'])
                if content:
                    documents.append({
                        'id': doc['id'],
                        'name': doc['name'],
                        'content': content,
                        'url': doc['url']
                    })
            
            console.print(f"[green]✓ Downloaded {len(documents)} documents[/green]")
            
            # Create indexer
            progress.update(task, description="Creating search index...")
            indexer = SimpleIndexer(
                search_endpoint=config['search_endpoint'],
                search_key=config['search_key'],
                index_name=config['search_index']
            )
            
            indexer.create_index()
            
            # Index documents
            progress.update(task, description="Indexing documents...")
            indexer.index_documents(documents)
        
        console.print(f"[bold green]✅ Successfully indexed {len(documents)} documents![/bold green]\n")
        
    except Exception as e:
        console.print(f"[red]❌ Error during indexing: {e}[/red]\n")


def main():
    """Main console loop."""
    console.clear()
    display_welcome()
    
    # Load configuration
    config = load_config()
    
    # Initialize RAG query handler
    console.print("\n[cyan]🔄 Initializing...[/cyan]")
    rag = RAGQuery(
        search_endpoint=config['search_endpoint'],
        search_key=config['search_key'],
        index_name=config['search_index'],
        openai_endpoint=config['azure_openai_endpoint'],
        openai_key=config['azure_openai_key'],
        model_deployment=config['model_deployment']
    )
    
    console.print("[bold green]✅ Ready![/bold green]")
    console.print(f"Search Index: {config['search_index']}\n")
    
    # Main loop
    while True:
        try:
            question = Prompt.ask("\n[bold cyan]Your question[/bold cyan]").strip()
            
            if not question:
                continue
            
            # Handle commands
            if question.lower() in ['exit', 'quit', 'q']:
                console.print("[yellow]👋 Goodbye![/yellow]")
                break
            
            elif question.lower() == 'help':
                display_welcome()
            
            elif question.lower() == 'index':
                index_documents(config)
            
            else:
                # Ask question using RAG
                result = rag.ask(question)
                display_answer(result)
        
        except KeyboardInterrupt:
            console.print("\n[yellow]👋 Goodbye![/yellow]")
            break
        except Exception as e:
            console.print(f"[red]❌ Error: {e}[/red]")


if __name__ == "__main__":
    main()
```

**What this code does:**
- Loads configuration from `.env` file
- Displays welcome message with available commands
- Handles three commands:
  - `index` - Fetches and indexes documents from SharePoint
  - `help` - Shows help message
  - `exit/quit` - Exits the application
- Processes questions and displays AI-generated answers with sources

---

## ▶️ Step 8: Run the Application

### 8.1 First Time Setup

Run the application for the first time:

```bash
python app.py
```

### 8.2 Index Documents

When the application starts, type:

```
index
```

This will:
1. Connect to your SharePoint site
2. Fetch up to 20 documents
3. Download and extract content
4. Create search index in Azure AI Search
5. Upload documents to the index

### 8.3 Ask Questions

After indexing, you can ask questions:

```
Your question: What are the company policies?
```

```
Your question: Where should I go in Dubai?
```

```
Your question: Tell me about the project timeline
```

### 8.4 Exit the Application

Type `exit` or `quit` to close the application.

---

## 🧪 Step 9: Testing

### 9.1 Test Checklist

- [ ] Application starts without errors
- [ ] Environment variables are loaded correctly
- [ ] `index` command connects to SharePoint
- [ ] Documents are fetched and indexed successfully
- [ ] Questions return relevant answers
- [ ] Source citations are displayed
- [ ] `help` command shows available commands
- [ ] `exit` command closes the application

### 9.2 Common Issues and Solutions

**Issue 1: Authentication Failed**
```
Error: Failed to get token: invalid_client
```
**Solution:** Verify your Azure AD credentials (Tenant ID, Client ID, Client Secret) in `.env` file

**Issue 2: No Documents Found**
```
⚠️  No documents found.
```
**Solution:** 
- Check SharePoint Site ID is correct
- Verify Azure AD app has Sites.Read.All permission
- Ensure documents exist in SharePoint site root

**Issue 3: Search Index Not Found**
```
Error: Index 'sharepoint-docs' not found
```
**Solution:** Run the `index` command first to create the index

**Issue 4: OpenAI API Error**
```
Error: The API deployment for this resource does not exist
```
**Solution:** Verify your Azure OpenAI deployment name in `.env` file

---

## 🎓 Learning Exercises

### Exercise 1: Add Document Count
Modify `app.py` to display the total number of indexed documents at startup.

**Hint:** Use Azure Search client's `get_document_count()` method

### Exercise 2: Add File Type Filter
Modify `sharepoint_connector.py` to filter documents by file type (e.g., only PDFs).

**Hint:** Check `mime_type` field in `list_documents()` method

### Exercise 3: Improve Answer Quality
Modify `rag_query.py` to include more context from documents.

**Hint:** Increase the `top` parameter in `_search()` method and content length in context

### Exercise 4: Add Document Preview
Modify `display_answer()` to show a preview of the source document content.

**Hint:** Add content snippet to sources dictionary

---

## 📚 Additional Resources

**Azure Documentation:**
- [Azure AI Search Documentation](https://learn.microsoft.com/azure/search/)
- [Azure OpenAI Service Documentation](https://learn.microsoft.com/azure/ai-services/openai/)
- [Microsoft Graph API Documentation](https://learn.microsoft.com/graph/)

**Python Libraries:**
- [azure-search-documents](https://pypi.org/project/azure-search-documents/)
- [openai](https://pypi.org/project/openai/)
- [msal](https://pypi.org/project/msal/)
- [pypdf](https://pypi.org/project/pypdf/)

**RAG Concepts:**
- [Retrieval-Augmented Generation (RAG)](https://learn.microsoft.com/azure/search/retrieval-augmented-generation-overview)
- [What is RAG?](https://aws.amazon.com/what-is/retrieval-augmented-generation/)

---

## 🔒 Security Best Practices

1. **Never commit `.env` file to Git**
   - Add `.env` to `.gitignore`
   - Use environment variables in production

2. **Rotate credentials regularly**
   - Change client secrets every 90 days
   - Use Azure Key Vault for production

3. **Use least privilege principle**
   - Grant only required permissions to Azure AD app
   - Use read-only keys when possible

4. **Protect sensitive data**
   - Don't log credentials
   - Sanitize error messages

---

## 📝 Assignment Submission Checklist

Before submitting your project:

- [ ] Code runs without errors
- [ ] All files are present (app.py, rag_query.py, indexer.py, sharepoint_connector.py, requirements.txt)
- [ ] `.env` file is NOT included (create `.env.example` with placeholder values instead)
- [ ] README.md documents your implementation
- [ ] Screenshots showing:
  - Application startup
  - Index command execution
  - Question answering with sources
- [ ] Code is properly commented
- [ ] No hardcoded credentials in source code

---

## 🎯 Grading Rubric

| Component | Points | Criteria |
|-----------|--------|----------|
| SharePoint Connection | 20 | Successfully connects and fetches documents |
| Document Indexing | 20 | Creates index and uploads documents to Azure Search |
| RAG Implementation | 25 | Retrieves relevant documents and generates answers |
| Code Quality | 15 | Clean, well-commented, follows best practices |
| Error Handling | 10 | Gracefully handles errors with meaningful messages |
| Documentation | 10 | Clear README with setup instructions |
| **Total** | **100** | |

---

## 🤝 Support

If you encounter issues:

1. Check the **Common Issues and Solutions** section
2. Review Azure Portal for service health
3. Verify all environment variables are set correctly
4. Check Azure AD app permissions
5. Contact your instructor for assistance

---

## 🚀 Next Steps

Once you complete this project, consider:

1. **Add Vector Search**: Implement embeddings for semantic search
2. **Add Document Chunking**: Split large documents into smaller chunks
3. **Add Conversation History**: Store and use chat history for context
4. **Build a Web Interface**: Create a Flask/FastAPI web app
5. **Add Multi-language Support**: Support documents in multiple languages

---

**Good luck with your implementation! 🎉**

---

*Last Updated: October 28, 2025*
