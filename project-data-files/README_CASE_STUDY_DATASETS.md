# Contoso AI Foundry Case Study Datasets

This folder contains synthetic but realistic datasets for the Azure AI Foundry end-to-end lab.

## Files
- ProductCatalog_v2.csv — Product master with pricing, warranty, status, timestamps
- WarrantyRecords_v2.csv — Warranty registrations with computed expiry and status
- Customers.csv — Customer master (segment, consent, geography)
- SupportTickets.csv — Operational tickets with SLA and resolution notes
- ProductReviews.csv — Reviews with rating-to-sentiment mapping
- ProductInventory.csv — Regional inventory by warehouse
- api_samples.json — Example payloads for MCP/API testing

## Suggested Storage
- CSVs → Azure Blob (Data Lake) or Azure SQL (staged tables)
- JSON → Blob for API test connector

## Suggested Indexing (Azure AI Search)
- Index PDFs + selected columns from CSVs (ProductName, Category, ShortDescription, ResolutionNote, ReviewText)

## Foreign Keys
- Customers.CustomerID ↔ SupportTickets.CustomerID, ProductReviews.CustomerID
- ProductCatalog_v2.ProductID ↔ WarrantyRecords_v2.ProductID, SupportTickets.ProductID, ProductReviews.ProductID

