# 🏥 UMLS Natural Language Interface

A two-tier architecture for providing natural language access to the Unified Medical Language System (UMLS) database through Claude Desktop using the Model Context Protocol (MCP).

## 🚀 Quick Setup Guide

**Want to get started fast? Follow these steps:**

1. **Prerequisites**: Install Python 3.8+, Conda, and Claude Desktop

2. **Clone and Setup Environment**:
   ```bash
   git clone <repository-url>
   cd umls-server
   conda create -n umls-server python=3.11
   conda activate umls-server
   pip install -r requirements.txt
   ```

3. **Configure Database** (in `umls_api/.env`):
   ```env
   DB_HOST=your-db-host
   DB_USER=your-db-user  
   DB_PASSWORD=your-db-password
   DB_NAME=your-db-name
   ```

4. **Start UMLS API**:
   ```bash
   cd umls_api
   uvicorn app:app --host 0.0.0.0 --port 8000
   ```

5. **Configure Claude Desktop**:
   - Copy `claude_desktop_config.json` to your Claude config directory
   - Update the Python path: `conda info --envs` to find your environment path
   - Update the project path to your actual directory
   - Restart Claude Desktop

6. **Test**: Ask Claude "Search for diabetes in the HPO ontology"

✅ **Done!** You can now query UMLS through natural language in Claude Desktop.

## 🌟 Quick Start: Using Claude Desktop

The UMLS server consists of two components:
1. **UMLS API** (Port 8000): Direct database access
2. **MCP Server**: Claude Desktop integration via stdio

### For Claude Desktop Integration

1. Set up the conda environment and dependencies:
   ```sh
   conda create -n umls-server python=3.11
   conda activate umls-server
   pip install -r requirements.txt
   ```

2. Start the UMLS API:
   ```sh
   cd umls_api
   uvicorn app:app --host 0.0.0.0 --port 8000
   ```

3. Configure Claude Desktop with the provided `claude_desktop_config.json` (update paths):
   ```json
   {
     "mcpServers": {
       "umls-server": {
         "command": "/path/to/conda/envs/umls-server/bin/python",
         "args": [
           "/path/to/umls-server/mcp-server/umls_mcp_server.py"
         ],
         "env": {
           "UMLS_API_URL": "http://localhost:8000"
         }
       }
     }
   }
   ```

4. Restart Claude Desktop and start using natural language to query UMLS!

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

The system consists of two main components:

1. **UMLS API** (Port 8000): A FastAPI application that directly queries the UMLS database
2. **MCP Server**: A Model Context Protocol server that integrates with Claude Desktop via stdio

### Workflow

1. User sends a natural language query through Claude Desktop
2. Claude Desktop communicates with the MCP server via the MCP protocol
3. MCP server processes the request and calls the appropriate UMLS API endpoint (port 8000)
4. MCP server returns structured data to Claude Desktop
5. Claude Desktop formats the result into natural language
6. User receives a human-readable response

## 🔧 MCP Server Tools

The MCP server provides these tools to Claude Desktop:

| Tool | Description |
|------|-------------|
| `search_terms` | Search for medical terms in UMLS database by ontology |
| `search_cui` | Search for CUIs (Concept Unique Identifiers) by term |
| `get_cui_info` | Get detailed information about a specific CUI |
| `get_cui_ancestors` | Get all ancestor CUIs in the hierarchy |
| `get_cui_depth` | Get the depth of a CUI in the hierarchical structure |
| `find_lowest_common_ancestor` | Find the lowest common ancestor (LCA) of two CUIs |
| `wu_palmer_similarity` | Compute Wu-Palmer similarity between two CUIs |
| `get_hpo_term` | Get HPO (Human Phenotype Ontology) term and code from a CUI |

## 🌐 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/terms?search={term}&ontology={ontology}` | Search for a term (Default: `HPO`) |
| `GET`  | `/cuis?query={term}` | Search for CUIs matching a given term |
| `GET`  | `/cuis/{cui}` | Get details about a specific CUI |
| `GET`  | `/cuis/{cui}/depth` | Get depth of a CUI in the hierarchy |
| `GET`  | `/cuis/{cui}/ancestors` | Retrieve all ancestors of a CUI |
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

#### Get Depth of a CUI
`GET /cuis/{cui}/depth`
- Determines the depth of a CUI within the hierarchy.

#### Retrieve Ancestors of a CUI
`GET /cuis/{cui}/ancestors`
- Retrieves all ancestor CUIs of a given CUI.

#### Find Lowest Common Ancestor (LCA)
`GET /cuis/{cui1}/{cui2}/lca`
- Finds the lowest common ancestor of two CUIs.

#### Compute Wu-Palmer Similarity
`GET /cuis/{cui1}/{cui2}/similarity/wu-palmer`
- Computes Wu-Palmer similarity between two CUIs based on hierarchical depth.

#### Find HPO from CUI term
`GET /cuis/{cui}/hpo`
- Retrieves the HPO term and its corresponding code associated with a given CUI.

## 📦 Installation

### Prerequisites

- Python 3.8+
- Conda (recommended for environment management)
- MySQL/MariaDB with UMLS data
- Claude Desktop (for MCP integration)

### Local Setup

1. Clone the repository:
   ```sh
   git clone <repository-url>
   cd umls-server
   ```

2. Create and activate conda environment:
   ```sh
   conda create -n umls-server python=3.11
   conda activate umls-server
   ```

3. Install dependencies:
   ```sh
   pip install -r requirements.txt
   ```

4. Set up the UMLS API:
   ```sh
   cd umls_api
   cp .env.example .env
   # Edit .env with your database credentials:
   # DB_HOST=your-db-host
   # DB_USER=your-db-user
   # DB_PASSWORD=your-db-password
   # DB_NAME=your-db-name
   ```

5. Configure Claude Desktop:
   ```sh
   # Copy the sample configuration
   cp claude_desktop_config.json /path/to/claude/config/
   # Edit the configuration with your actual paths
   ```

### Running the Services

1. Start the UMLS API:
   ```sh
   conda activate umls-server
   cd umls_api
   uvicorn app:app --host 0.0.0.0 --port 8000
   ```

2. The MCP Server runs automatically when Claude Desktop starts (no manual startup required).

For long-running processes on EC2, use:
```sh
nohup uvicorn app:app --host 0.0.0.0 --port 8000 > umls_api.log 2>&1 &
```

### Setting up as Systemd Service (Linux)

Create systemd service files for the UMLS API:

**umls-api.service**:
```ini
[Unit]
Description=UMLS API Service
After=network.target

[Service]
User=your_user
WorkingDirectory=/path/to/umls_api
ExecStart=/path/to/conda/envs/umls-server/bin/uvicorn app:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

Install and enable the service:
```sh
sudo cp umls-api.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable umls-api
sudo systemctl start umls-api
```

## 🔒 Security Considerations

- The UMLS API should be secured appropriately
- Consider using HTTPS in production
- Restrict access to the services using a VPN or firewall
- Make sure port 8000 is open in your EC2 Security Group for API access
- The MCP server runs locally and communicates with Claude Desktop via stdio

## 🛠 Troubleshooting

### UMLS API Issues
- **API not accessible?** Make sure the conda environment is activated and port 8000 is open
- **No results found?** Ensure your ontology (`HPO`, `NCI`, etc.) is correct
- **API stops when logging out?** Use the `nohup` command shown above

### Claude Desktop Integration Issues
- **Tools not showing up?** Check the Claude Desktop configuration file paths
- **MCP server errors?** Ensure the conda environment path is correct in the configuration
- **Permission errors?** Make sure the MCP server script is executable

### Environment Issues
- **Import errors?** Ensure you've activated the conda environment and installed all dependencies
- **API connection errors?** Check that the UMLS API is running on port 8000

## 🤝 Contributing

1. Fork the repo & create a new branch (`feature-name`)
2. Commit changes (`git commit -m "Added feature"`)
3. Push & open a pull request

## 📜 License

MIT License

---

🚀 Now you're ready to query UMLS with natural language through Claude Desktop!

