# Develop Generative AI Solutions in Azure AI Foundry

The exercises in this repo provide a hands-on path to build intelligent, low-latency apps on Microsoft Azure using proven patterns for AI agents, RAG, and observability.

## Overview
This repository contains practical exercises and samples showing how to:
- Build AI agents and chat apps with Azure AI Foundry and Azure OpenAI
- Implement Retrieval-Augmented Generation (RAG) with fast contextual lookups
- Persist chat history, user context, and vectors in Azure Cosmos DB (with vector search)
- Trace, evaluate, and optimize AI workloads end to end
- Apply Azure-ready deployment and reliability practices

## Prerequisites
- Azure subscription
- Visual Studio Code with:
    - AI Foundry for VS Code: https://marketplace.visualstudio.com/items?itemName=TeamsDevApp.vscode-ai-foundry
    - Azure Cosmos DB: https://marketplace.visualstudio.com/items?itemName=ms-azuretools.vscode-cosmosdb
- Optional (recommended for local dev): Azure Cosmos DB Emulator (SQL API) and Docker
- Basic knowledge of Python/C#/JavaScript and Azure fundamentals

## What You’ll Learn
- AI agent and chat app patterns on Azure
- RAG design and semantic retrieval with vector search
- Managing conversation history and user/tenant isolation
- Evaluation, tracing, and diagnostics for AI apps
- Azure-focused deployment and reliability best practices

## Repository Structure
```
/data              # Supported data files
/samples           # Reference code samples
```

## Getting Started
1. Clone the repository.
2. Install the required VS Code extensions and sign in to Azure.
3. For local dev, start the Cosmos DB Emulator (Docker or desktop):
     - Endpoint: https://localhost:8081/
     - Get the master key from the emulator UI/docs
4. Configure environment variables for your app (example):
     ```
     COSMOS_ENDPOINT=https://localhost:8081/
     COSMOS_KEY=<your-emulator-or-account-key>
     COSMOS_DB_NAME=<db-name>
     COSMOS_CONTAINER=<container-name>
     ```
5. Navigate to /exercises and follow the labs in order.

## Key Technologies
- Azure OpenAI Service — Advanced language models
- Azure Cosmos DB — Low-latency storage for chat history, user profiles, and low-cost, scalable vector search
- Azure AI Services — Prebuilt AI capabilities
- Azure Functions — Serverless compute for AI workloads
- Azure Logic Apps — Integration and orchestration

## Data and Storage with Azure Cosmos DB
- Model to minimize cross-partition queries and joins.
- Embed related data when fetched together; reference when items get large or update patterns differ (max 2 MB per item).
- Prefer Hierarchical Partition Keys (HPK) to overcome the 20 GB logical partition limit and enable targeted multi-partition queries; ensure even data distribution to prevent hotspots.
- Choose high-cardinality partition keys aligned with query patterns (e.g., userId, tenantId, deviceId). Avoid low-cardinality keys (e.g., status, country).
- SDK best practices:
    - Use the latest SDK, async APIs, preferred regions, and connection retries
    - Reuse a singleton CosmosClient
    - Handle 429 (Request Rate Too Large) with retry-after logic
    - Log and review the SDK diagnostic string on high latency or unexpected status codes
    - Monitor and tune Request Units (RUs) based on workload

## Local Development
- Use the Azure Cosmos DB VS Code extension to browse, query, and manage data locally and in Azure.
- Use the Cosmos DB Emulator for cost-free local testing (SQL API). Update app connection strings to emulator endpoints when running locally.

## Recommended Scenarios Covered
- Multi-user AI assistants with memory and user/tenant isolation
- Chat interfaces with conversation history
- Semantic search using vector embeddings
- Real-time recommendations
- RAG implementation with fast contextual lookups

## Additional Resources
- Azure AI Foundry: https://learn.microsoft.com/azure/ai-foundry/
- Cosmos DB Well-Architected Guidance: https://learn.microsoft.com/azure/well-architected/service-guides/cosmos-db
- Cosmos DB Emulator: https://learn.microsoft.com/azure/cosmos-db/emulator

## Contributing
Contributions are welcome. Follow Azure development best practices in PRs.

## License
[Specify your license here]
