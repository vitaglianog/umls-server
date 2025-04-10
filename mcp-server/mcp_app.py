from fastapi import FastAPI, HTTPException, Depends, Header
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import httpx
import os
from dotenv import load_dotenv
import logging
import json

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="UMLS MCP Server", description="Middleware for UMLS API")

# Configuration
UMLS_API_URL = os.getenv("UMLS_API_URL", "http://localhost:8000")
API_KEY = os.getenv("API_KEY", "default_key")

# Intent definitions
INTENT_MAPPINGS = {
    "search_terms": {
        "endpoint": "/terms",
        "method": "GET",
        "params": ["search", "ontology"]
    },
    "get_cui_info": {
        "endpoint": "/cuis/{cui}",
        "method": "GET",
        "params": ["cui"]
    },
    "search_cui": {
        "endpoint": "/cuis",
        "method": "GET",
        "params": ["query"]
    },
    "get_ancestors": {
        "endpoint": "/cuis/{cui}/ancestors",
        "method": "GET",
        "params": ["cui"]
    },
    "get_depth": {
        "endpoint": "/cuis/{cui}/depth",
        "method": "GET",
        "params": ["cui"]
    },
    "get_relations": {
        "endpoint": "/cuis/{cui}/relations",
        "method": "GET",
        "params": ["cui"]
    },
    "get_cui_from_ontology": {
        "endpoint": "/ontologies/{source}/{code}/cui",
        "method": "GET",
        "params": ["source", "code"]
    },
    "find_lca": {
        "endpoint": "/cuis/{cui1}/{cui2}/lca",
        "method": "GET",
        "params": ["cui1", "cui2"]
    },
    "wu_palmer_similarity": {
        "endpoint": "/cuis/{cui1}/{cui2}/similarity/wu-palmer",
        "method": "GET",
        "params": ["cui1", "cui2"]
    }
}

# Models
class IntentRequest(BaseModel):
    intent: str
    parameters: Dict[str, Any]

class IntentResponse(BaseModel):
    result: Any
    status: str = "success"
    message: Optional[str] = None

# Authentication
async def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return x_api_key

# Helper functions
def format_url(endpoint: str, params: Dict[str, Any]) -> str:
    """Format URL with parameters."""
    try:
        return endpoint.format(**params)
    except KeyError as e:
        raise HTTPException(status_code=400, detail=f"Missing required parameter: {e}")

async def call_umls_api(endpoint: str, method: str, params: Dict[str, Any]) -> Any:
    """Call the UMLS API with the given parameters."""
    url = f"{UMLS_API_URL}{endpoint}"
    
    logger.info(f"Calling UMLS API: {url} with params: {params}")
    
    async with httpx.AsyncClient() as client:
        try:
            if method == "GET":
                response = await client.get(url, params=params, timeout=10.0)
            else:
                raise HTTPException(status_code=405, detail=f"Method {method} not supported")
            
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error: {e}, Response: {e.response.text}")
            raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
        except httpx.RequestError as e:
            logger.error(f"Request error: {e}")
            raise HTTPException(status_code=500, detail=f"Error connecting to UMLS API: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

# Routes
@app.post("/process_intent", response_model=IntentResponse)
async def process_intent(request: IntentRequest, api_key: str = Depends(verify_api_key)):
    """Process an intent and map it to the appropriate UMLS API endpoint."""
    intent = request.intent
    params = request.parameters
    
    logger.info(f"Processing intent: {intent} with parameters: {params}")
    
    if intent not in INTENT_MAPPINGS:
        raise HTTPException(status_code=400, detail=f"Unknown intent: {intent}")
    
    intent_config = INTENT_MAPPINGS[intent]
    endpoint = intent_config["endpoint"]
    method = intent_config["method"]
    
    # Check if all required parameters are provided
    missing_params = [param for param in intent_config["params"] if param not in params]
    if missing_params:
        raise HTTPException(status_code=400, detail=f"Missing required parameters: {missing_params}")
    
    # Format URL with path parameters
    formatted_endpoint = format_url(endpoint, params)
    
    # Extract query parameters (parameters that are not in the path)
    path_params = {param: params[param] for param in intent_config["params"] if f"{{{param}}}" in endpoint}
    query_params = {k: v for k, v in params.items() if k not in path_params}
    
    try:
        result = await call_umls_api(formatted_endpoint, method, query_params)
        return IntentResponse(result=result)
    except Exception as e:
        logger.error(f"Error processing intent: {e}")
        return IntentResponse(
            result=None,
            status="error",
            message=str(e)
        )

@app.get("/intents", response_model=List[str])
async def list_intents(api_key: str = Depends(verify_api_key)):
    """List all available intents."""
    return list(INTENT_MAPPINGS.keys())

@app.get("/intent_details/{intent}")
async def get_intent_details(intent: str, api_key: str = Depends(verify_api_key)):
    """Get details about a specific intent."""
    if intent not in INTENT_MAPPINGS:
        raise HTTPException(status_code=404, detail=f"Intent not found: {intent}")
    
    return {
        "intent": intent,
        "endpoint": INTENT_MAPPINGS[intent]["endpoint"],
        "method": INTENT_MAPPINGS[intent]["method"],
        "required_parameters": INTENT_MAPPINGS[intent]["params"]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001) 