# 🏥 UMLS Natural Language Interface

A three-tier architecture for providing natural language access to the Unified Medical Language System (UMLS) database.

## 🌟 Quick Start: Using the EC2 Instance

The UMLS server is deployed on an EC2 instance at `52.43.228.165`. To use it:

1. Ensure you are on the Geneial VPN
2. Make sure the EC2 instance is running (costs ~50c/hour)
3. The UMLS server starts automatically when the instance is on
4. The server shuts down automatically at midnight ET every night

To manually start the server on EC2:
```sh
ssh -i "umls-server.pem" ec2-user@ec2-52-43-228-165.us-west-2.compute.amazonaws.com
cd umls-server/umls_api
uvicorn app:app --host 0.0.0.0 --port 8000
```

Example API usage:
```sh
# Search for terms
curl "http://52.43.228.165:8000/terms?search=cancer&ontology=HPO"

# Response format:
{
  "results": [
    {
      "code": "HP:0002896",
      "term": "Liver cancer",
      "description": "A primary or metastatic malignant neoplasm that affects the liver."
    }
  ]
}
```

## 🏗 Architecture

The system consists of three main components:

1. **UMLS API** (Port 8000): A FastAPI application that directly queries the UMLS database
2. **MCP Server** (Port 8001): A middleware layer that maps natural language intents to API endpoints
3. **LLM Integration** (Port 8002): A service that interfaces with an LLM (like OpenAI) and processes queries

### Workflow

1. User sends a natural language query to the LLM Integration (port 8002)
2. LLM service processes the query and identifies the intent
3. LLM service sends a structured request to the MCP server (port 8001)
4. MCP server maps the intent to the correct UMLS API endpoint (port 8000)
5. MCP server gets the data and returns it to the LLM service
6. LLM service formats the result into natural language
7. User receives a human-readable response

## 🌐 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/terms?search={term}&ontology={ontology}` | Search for a term (Default: `HPO`) |
| `GET`  | `/cuis?query={term}` | Search for CUIs matching a given term |
| `GET`  | `/cuis/{cui}` | Get details about a specific CUI |
| `GET`  | `/cuis/{cui}/relations` | Get hierarchical relations (parents, children, ancestors) of a CUI |
| `GET`  | `/cuis/{cui}/depth` | Get depth of a CUI in the hierarchy |
| `GET`  | `/cuis/{cui}/ancestors` | Retrieve all ancestors of a CUI |
| `GET`  | `/ontologies/{source}/{code}/cui` | Map an ontology term (HPO, SNOMED, etc.) to a CUI |
| `GET`  | `/cuis/{cui1}/{cui2}/lca` | Get the lowest common ancestor (LCA) of two CUIs |
| `GET`  | `/cuis/{cui1}/{cui2}/similarity/wu-palmer` | Compute Wu-Palmer similarity between two CUIs |
| `GET`  | `/cuis/{cui}/hpo` | Retrieve HPO code from CUI |


### Endpoint Descriptions

#### Search for Terms
`GET /terms?search={term}&ontology={ontology}`
- Searches for a term in the specified ontology (default: `HPO`).

#### Search for CUIs by Term
`GET /cuis?query={term}`
- Finds CUIs that match a given search term.

#### Get CUI Information
`GET /cuis/{cui}`
- Fetches details about a given CUI, including name and description.

#### Get Hierarchical Relations
`GET /cuis/{cui}/relations`
- Retrieves hierarchical relations for a CUI, including parents, children, and ancestors.

#### Get Depth of a CUI
`GET /cuis/{cui}/depth`
- Determines the depth of a CUI within the hierarchy.

#### Retrieve Ancestors of a CUI
`GET /cuis/{cui}/ancestors`
- Retrieves all ancestor CUIs of a given CUI.

#### Map Ontology Term to CUI
`GET /ontologies/{source}/{code}/cui`
- Maps an ontology term (e.g., HPO, SNOMED) to a corresponding CUI.

#### Find Lowest Common Ancestor (LCA)
`GET /cuis/{cui1}/{cui2}/lca`
- Finds the lowest common ancestor of two CUIs.

#### Compute Wu-Palmer Similarity
`GET /cuis/{cui1}/{cui2}/similarity/wu-palmer`
- Computes Wu-Palmer similarity between two CUIs based on hierarchical depth.

#### Find HPO from CUI term
`GET /cuis/{cui1}/hpo`
- Retrieves the HPO term and its corresponding code associated with a given CUI.

## 📦 Installation

### Prerequisites

- Python 3.8+
- MySQL/MariaDB with UMLS data
- OpenAI API key (for LLM integration)

### Local Setup

1. Clone the repository:
   ```sh
   git clone <repository-url>
   cd umls-server
   ```

2. Set up the UMLS API:
   ```sh
   cd umls_api
   cp .env.example .env
   # Edit .env with your database credentials:
   # DB_HOST=your-db-host
   # DB_USER=your-db-user
   # DB_PASSWORD=your-db-password
   # DB_NAME=your-db-name
   pip install -r requirements.txt
   ```

3. Set up the MCP Server:
   ```sh
   cd ../mcp-server
   cp .env.example .env
   # Edit .env with your API key and UMLS API URL
   pip install -r requirements.txt
   ```

4. Set up the LLM Integration:
   ```sh
   cd ../llm-integration
   cp .env.example .env
   # Edit .env with your API key, MCP server URL, and OpenAI API key
   pip install -r requirements.txt
   ```

### Running the Services

1. Start the UMLS API:
   ```sh
   cd umls_api
   uvicorn app:app --host 0.0.0.0 --port 8000
   ```

2. Start the MCP Server:
   ```sh
   cd mcp-server
   uvicorn mcp_app:app --host 0.0.0.0 --port 8001
   ```

3. Start the LLM Integration:
   ```sh
   cd llm-integration
   uvicorn app:app --host 0.0.0.0 --port 8002
   ```

For long-running processes on EC2, use:
```sh
nohup uvicorn app:app --host 0.0.0.0 --port 8000 > umls_api.log 2>&1 &
```

### Setting up as Systemd Services (Linux)

1. Create systemd service files for each component:

   **umls-api.service**:
   ```ini
   [Unit]
   Description=UMLS API Service
   After=network.target

   [Service]
   User=your_user
   WorkingDirectory=/path/to/umls_api
   ExecStart=/path/to/venv/bin/uvicorn app:app --host 0.0.0.0 --port 8000
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```

   **mcp-server.service**:
   ```ini
   [Unit]
   Description=UMLS MCP Server
   After=network.target

   [Service]
   User=your_user
   WorkingDirectory=/path/to/mcp-server
   ExecStart=/path/to/venv/bin/uvicorn mcp_app:app --host 0.0.0.0 --port 8001
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```

   **llm-integration.service**:
   ```ini
   [Unit]
   Description=UMLS LLM Integration
   After=network.target

   [Service]
   User=your_user
   WorkingDirectory=/path/to/llm-integration
   ExecStart=/path/to/venv/bin/uvicorn app:app --host 0.0.0.0 --port 8002
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```

2. Install and enable the services:
   ```sh
   sudo cp umls-api.service /etc/systemd/system/
   sudo cp mcp-server.service /etc/systemd/system/
   sudo cp llm-integration.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable umls-api mcp-server llm-integration
   sudo systemctl start umls-api mcp-server llm-integration
   ```

## 🔒 Security Considerations

- All services use API key authentication
- The LLM Integration requires an OpenAI API key
- Consider using HTTPS in production
- Restrict access to the services using a VPN or firewall
- Make sure port 8000 is open in your EC2 Security Group

## 🛠 Troubleshooting

- **API not accessible?** Make sure EC2 is on and port 8000 is open in your EC2 Security Group
- **No results found?** Ensure your ontology (`HPO`, `NCI`, etc.) is correct
- **API stops when logging out?** Use the `nohup` command shown above

## 🤝 Contributing

1. Fork the repo & create a new branch (`feature-name`)
2. Commit changes (`git commit -m "Added feature"`)
3. Push & open a pull request

## 📜 License

MIT License

---

🚀 Now you're ready to query UMLS with natural language!

