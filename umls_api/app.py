from fastapi import FastAPI, HTTPException
import pymysql
from dotenv import load_dotenv
import os
from bs4 import BeautifulSoup

# Load environment variables
load_dotenv()

app = FastAPI()

def connect_db():
    """Establish database connection."""
    return pymysql.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
        cursorclass=pymysql.cursors.DictCursor
    )

def clean_html(html_text):
    """Remove HTML tags from text."""
    return BeautifulSoup(html_text, "html.parser").get_text() if html_text else None

@app.get("/terms")
def search_terms(search: str, ontology: str = "HPO"):
    """Search for medical terms in UMLS based on ontology."""
    conn = connect_db()
    query = """
        SELECT DISTINCT MRCONSO.CODE, MRCONSO.STR, MRDEF.DEF
        FROM MRCONSO
        LEFT JOIN MRDEF ON MRCONSO.CUI = MRDEF.CUI
        WHERE MRCONSO.SAB = %s
        AND MRCONSO.STR LIKE %s
        LIMIT 10;
    """

    try:
        with conn.cursor() as cursor:
            cursor.execute(query, (ontology, f"%{search}%"))
            results = cursor.fetchall()

            formatted_results = []
            seen_codes = set()

            for row in results:
                code = row["CODE"]
                term = row["STR"]
                description = clean_html(row["DEF"])

                if code not in seen_codes:
                    formatted_results.append({"code": code, "term": term, "description": description})
                    seen_codes.add(code)

    finally:
        conn.close()

    if not formatted_results:
        raise HTTPException(status_code=404, detail="No results found")

    return {"results": formatted_results}

@app.get("/concepts/{cui}")
def get_concept(cui: str):
    """Fetch details for a specific CUI."""
    conn = connect_db()
    query = """
        SELECT MRCONSO.CODE, MRCONSO.STR, MRDEF.DEF
        FROM MRCONSO
        LEFT JOIN MRDEF ON MRCONSO.CUI = MRDEF.CUI
        WHERE MRCONSO.CODE = %s
        LIMIT 1;
    """

    try:
        with conn.cursor() as cursor:
            cursor.execute(query, (cui,))
            result = cursor.fetchone()

    finally:
        conn.close()

    if not result:
        raise HTTPException(status_code=404, detail=f"No concept found for CUI {cui}")

    return {
        "code": result["CODE"],
        "term": result["STR"],
        "description": clean_html(result["DEF"])
    }


## UMLS CUI toolkit
def fetch_umls_data(endpoint: str):
    """ Helper function to make requests to the UMLS API. """
    url = f"{BASE_URL}/{endpoint}?apiKey={API_KEY}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json().get("result", [])
    raise HTTPException(status_code=response.status_code, detail=f"UMLS API Error: {response.text}")

@app.get("/cuis", summary="Search for CUIs by term")
def search_cui(query: str = Query(..., description="Search term for CUI lookup")):
    """ Search for CUIs matching a given term. """
    results = fetch_umls_data(f"search?string={query}")
    cuis = [(r["ui"], r["name"]) for r in results if r["ui"].startswith("C")]
    
    if not cuis:
        raise HTTPException(status_code=404, detail="No CUIs found for the given term")
    
    return {"query": query, "cuis": cuis}

@app.get("/cuis/{cui}", summary="Get details about a specific CUI")
def get_cui_info(cui: str):
    """ Get details about a given CUI. """
    result = fetch_umls_data(f"CUI/{cui}")
    if not result:
        raise HTTPException(status_code=404, detail="CUI not found")
    return result

@app.get("/cuis/{cui}/relations", summary="Get hierarchical relations for a CUI")
def get_relations(cui: str):
    """ Get hierarchical relations (parents, children, etc.) of a CUI. """
    return fetch_umls_data(f"CUI/{cui}/relations")

@app.get("/cuis/{cui}/depth", summary="Get depth of a CUI in the hierarchy")
def get_depth(cui: str, depth: int = 0):
    """ Recursively determine depth of a CUI in the hierarchy. """
    relations = fetch_umls_data(f"CUI/{cui}/relations")
    parents = [r["relatedId"] for r in relations if r.get("relationLabel") == "PAR"]

    if not parents:
        return {"cui": cui, "depth": depth}  # Root concept reached
    
    return {"cui": cui, "depth": max(get_depth(parent, depth + 1)["depth"] for parent in parents)}

@app.get("/cuis/{cui}/ancestors", summary="Get all ancestors of a CUI")
def get_ancestors(cui: str):
    """ Retrieve all ancestors of a CUI. """
    return fetch_umls_data(f"CUI/{cui}/ancestors")

@app.get("/ontologies/{source}/{code}/cui", summary="Map an ontology term to a CUI")
def get_cui_from_ontology(source: str, code: str):
    """ Get the CUI for a given ontology term (HPO, SNOMED, etc.). """
    result = fetch_umls_data(f"source/{source}/{code}")
    if "ui" not in result:
        raise HTTPException(status_code=404, detail="Mapping not found")
    return {"ontology": source, "term": code, "cui": result["ui"]}

@app.get("/cuis/{cui1}/{cui2}/lca", summary="Get the lowest common ancestor of two CUIs")
def find_lowest_common_ancestor(cui1: str, cui2: str):
    """ Find the lowest common ancestor (LCA) of two CUIs. """
    ancestors1 = set(a["ui"] for a in fetch_umls_data(f"CUI/{cui1}/ancestors"))
    ancestors2 = set(a["ui"] for a in fetch_umls_data(f"CUI/{cui2}/ancestors"))

    common_ancestors = ancestors1 & ancestors2
    if not common_ancestors:
        raise HTTPException(status_code=404, detail="No common ancestor found")

    lca = max(common_ancestors, key=lambda cui: get_depth(cui)["depth"])
    return {"cui1": cui1, "cui2": cui2, "lca": lca}

@app.get("/cuis/{cui1}/{cui2}/similarity/wu-palmer", summary="Compute Wu-Palmer similarity")
def wu_palmer_similarity(cui1: str, cui2: str):
    """ Compute Wu-Palmer similarity between two CUIs. """
    lca = find_lowest_common_ancestor(cui1, cui2)["lca"]
    
    depth_c1 = get_depth(cui1)["depth"]
    depth_c2 = get_depth(cui2)["depth"]
    depth_lca = get_depth(lca)["depth"]

    similarity = (2 * depth_lca) / (depth_c1 + depth_c2)
    return {"cui1": cui1, "cui2": cui2, "similarity": similarity}