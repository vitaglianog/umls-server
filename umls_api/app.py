from fastapi import FastAPI, HTTPException, Query
import pymysql
from dotenv import load_dotenv
import os
from bs4 import BeautifulSoup
import asyncio
import logging

# Load environment variables
load_dotenv()

app = FastAPI()

# Configure logging
logging.basicConfig(level=logging.INFO)

# Timeout in seconds for external calls
TIMEOUT = 500

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


@app.get("/cuis/{cui}/ancestors", summary="Get all ancestors of a CUI")
async def get_ancestors(cui: str):
    """ Retrieve all ancestors of a CUI by extracting AUIs from MRHIER.PTR and mapping them to CUIs via MRCONSO. """
    
    # Step 1: Retrieve the AUI paths (PTR) from MRHIER
    sql_get_ptr = "SELECT PTR FROM MRHIER WHERE CUI = %s"

    try:
        with connect_db() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql_get_ptr, (cui,))
                results = cursor.fetchall()

        if not results:
            raise HTTPException(status_code=404, detail=f"No ancestors found for CUI {cui}")

        # Step 2: Extract AUIs from PTR and map them to CUIs
        auis = set()
        for row in results:
            ptr_path = row["PTR"]
            if ptr_path:
                auis.update(ptr_path.split("."))  # Extract AUIs from dot-separated paths

        if not auis:
            return {"cui": cui, "ancestors": []}  # No ancestors found

        # Step 3: Map AUIs to CUIs using MRCONSO
        sql_map_aui_to_cui = """
            SELECT DISTINCT AUI, CUI FROM MRCONSO WHERE AUI IN %s
        """

        with connect_db() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql_map_aui_to_cui, (tuple(auis),))
                mappings = cursor.fetchall()

        # Convert AUIs to CUIs
        aui_to_cui = {m["AUI"]: m["CUI"] for m in mappings}
        ancestors_cuis = {aui_to_cui[aui] for aui in auis if aui in aui_to_cui}

        return {"cui": cui, "ancestors": list(ancestors_cuis)}

    except Exception as e:
        return {"error": str(e)}

@app.get("/cuis/{cui}", summary="Get details about a specific CUI")
def get_cui_info(cui: str):
    """ Get details about a given CUI. """
    sql = "SELECT CUI, STR FROM MRCONSO WHERE CUI = %s LIMIT 1"

    with connect_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql, (cui,))
            result = cursor.fetchone()

    if not result:
        raise HTTPException(status_code=404, detail="CUI not found")
    
    return {"cui": result["CUI"], "name": result["STR"]}


## UMLS CUI toolkit
@app.get("/cuis", summary="Search for CUIs by term")
def search_cui(query: str = Query(..., description="Search term for CUI lookup")):
    """ Search for CUIs matching a given term. """
    sql = "SELECT CUI, STR FROM MRCONSO WHERE STR LIKE %s LIMIT 50"
    
    with connect_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql, (f"%{query}%",))
            results = cursor.fetchall()

    if not results:
        raise HTTPException(status_code=404, detail="No CUIs found for the given term")
    
    return {"query": query, "cuis": [{"cui": r["CUI"], "name": r["STR"]} for r in results]}




@app.get("/cuis/{cui}/relations", summary="Get hierarchical relations for a CUI")
def get_relations(cui: str):
    """ Get parent(s), children, and ancestors of a CUI, correctly mapping AUIs to CUIs. """
    
    # Query for retrieving PTR (path to root) for ancestors
    sql_ancestors = "SELECT PTR FROM MRHIER WHERE CUI = %s"

    # Query for retrieving children (CUIs where PTR contains the given CUI)
    sql_children = "SELECT DISTINCT CUI FROM MRHIER WHERE PTR LIKE %s"

    # Query for retrieving parents by extracting the last component from PTR
    sql_parents = """
        SELECT DISTINCT SUBSTRING_INDEX(PTR, '.', -1) AS parent_aui
        FROM MRHIER WHERE CUI = %s
    """

    try:
        with connect_db() as conn:
            with conn.cursor() as cursor:
                # Get Ancestors (PTR -> AUIs)
                cursor.execute(sql_ancestors, (cui,))
                results = cursor.fetchall()

                auis = set()
                for row in results:
                    if row["PTR"]:
                        auis.update(row["PTR"].split("."))  # Extract AUIs from PTR

                # Map AUIs to CUIs using MRCONSO
                if auis:
                    sql_map_aui_to_cui = "SELECT DISTINCT AUI, CUI FROM MRCONSO WHERE AUI IN %s"
                    cursor.execute(sql_map_aui_to_cui, (tuple(auis),))
                    mappings = cursor.fetchall()
                    aui_to_cui = {m["AUI"]: m["CUI"] for m in mappings}
                    ancestors = {aui_to_cui[aui] for aui in auis if aui in aui_to_cui}
                else:
                    ancestors = set()

                # Get Parents (Convert last AUI in PTR to CUI)
                cursor.execute(sql_parents, (cui,))
                parent_auis = [row["parent_aui"] for row in cursor.fetchall() if row["parent_aui"]]

                parents = {aui_to_cui[aui] for aui in parent_auis if aui in aui_to_cui}

                # Get Children (CUIs where PTR contains this CUI)
                cursor.execute(sql_children, (f'%.{cui}',))
                children = [row["CUI"] for row in cursor.fetchall()]

        return {
            "cui": cui,
            "parents": list(parents),
            "children": children,
            "ancestors": list(ancestors)
        }

    except Exception as e:
        return {"error": str(e)}


@app.get("/ontologies/{source}/{code}/cui", summary="Map an ontology term to a CUI")
def get_cui_from_ontology(source: str, code: str):
    """ Get the CUI for a given ontology term (HPO, SNOMED, etc.). """
    sql = """
    SELECT CUI 
    FROM MRCONSO 
    WHERE CODE = %s 
    AND SAB = %s
    LIMIT 1
    """

    with connect_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql, (code, source))
            result = cursor.fetchone()

    if not result:
        raise HTTPException(status_code=404, detail="Mapping not found")
    
    return {"ontology": source, "term": code, "cui": result["CUI"]}

def query_depth(cui: str) -> int:
    sql = "SELECT LENGTH(PTR) - LENGTH(REPLACE(PTR, '.', '')) + 1 AS depth FROM MRHIER WHERE CUI = %s"
    with connect_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql, (cui,))
            result = cursor.fetchone()
    # Return the depth if available; otherwise, None
    return result.get("depth") if result and result.get("depth") is not None else None

async def fetch_depth(cui: str) -> int:
    """Helper to fetch depth asynchronously with timeout and error handling."""
    try:
        depth = await asyncio.wait_for(asyncio.to_thread(query_depth, cui), timeout=TIMEOUT)
    except asyncio.TimeoutError:
        logging.error("Timeout retrieving depth for CUI: %s", cui)
        raise HTTPException(status_code=504, detail=f"Timeout retrieving depth for CUI {cui}")
    except Exception as e:
        logging.error("Error retrieving depth for CUI %s: %s", cui, e)
        raise HTTPException(status_code=500, detail=f"Error retrieving depth for CUI {cui}")
    
    if depth is None:
        logging.error("Depth not found for CUI: %s", cui)
        raise HTTPException(status_code=404, detail=f"Depth not found for CUI {cui}")
    
    logging.info("Depth for CUI %s is %s", cui, depth)
    return depth

# Updated get_depth endpoint that uses the helper function
@app.get("/cuis/{cui}/depth", summary="Get depth of a CUI in the hierarchy")
async def get_depth(cui: str):
    depth = await fetch_depth(cui)
    return {"cui": cui, "depth": depth}


@app.get("/cuis/{cui1}/{cui2}/similarity/wu-palmer", summary="Compute Wu-Palmer similarity")
async def wu_palmer_similarity(cui1: str, cui2: str):
    """Compute Wu-Palmer similarity between two CUIs using MRHIER and the fetch_depth helper."""
    logging.info("Computing Wu-Palmer similarity for %s and %s", cui1, cui2)

    # Get the lowest common ancestor asynchronously.
    lca_result = await find_lowest_common_ancestor(cui1, cui2)
    lca = lca_result.get("lca")
    logging.info("Lowest common ancestor for %s and %s is %s", cui1, cui2, lca)

    # Concurrently fetch depths for cui1, cui2, and the LCA.
    try:
        depth_c1, depth_c2, depth_lca = await asyncio.gather(
            fetch_depth(cui1),
            fetch_depth(cui2),
            fetch_depth(lca)
        )
    except HTTPException as e:
        logging.error("Error fetching depths: %s", e.detail)
        raise

    logging.info("Depths: %s -> %s, %s -> %s, LCA %s -> %s", cui1, depth_c1, cui2, depth_c2, lca, depth_lca)

    if depth_c1 == 0 or depth_c2 == 0:
        logging.error("One or both CUIs have no valid depth")
        raise HTTPException(status_code=400, detail="One or both CUIs have no valid depth")

    similarity = (2 * depth_lca) / (depth_c1 + depth_c2)
    logging.info("Computed Wu-Palmer similarity: %s", similarity)

    return {
        "cui1": cui1,
        "cui2": cui2,
        "lca": lca,
        "depth_c1": depth_c1,
        "depth_c2": depth_c2,
        "depth_lca": depth_lca,
        "similarity": similarity,
    }


@app.get("/cuis/{cui1}/{cui2}/lca", summary="Get the lowest common ancestor of two CUIs")
async def find_lowest_common_ancestor(cui1: str, cui2: str):
    """Find the lowest common ancestor (LCA) of two CUIs using the new depth functions."""
    logging.info("Fetching ancestors for %s and %s", cui1, cui2)
    try:
        # Get ancestors for each CUI. We assume these functions are asynchronous.
        ancestors1_response = await asyncio.wait_for(get_ancestors(cui1), timeout=TIMEOUT)
        ancestors2_response = await asyncio.wait_for(get_ancestors(cui2), timeout=TIMEOUT)
    except Exception as e:
        logging.error("Error fetching ancestors: %s", e)
        raise HTTPException(status_code=500, detail="Error fetching ancestors")

    ancestors1 = set(ancestors1_response.get("ancestors", []))
    ancestors2 = set(ancestors2_response.get("ancestors", []))
    common_ancestors = ancestors1 & ancestors2
    logging.info("Common ancestors: %s", common_ancestors)

    if not common_ancestors:
        raise HTTPException(status_code=404, detail="No common ancestor found")

    # Concurrently fetch depths for each common ancestor using our new helper.
    tasks = {ancestor: asyncio.create_task(fetch_depth(ancestor)) for ancestor in common_ancestors}
    depth_dict = {}
    for ancestor, task in tasks.items():
        try:
            depth_dict[ancestor] = await task
        except Exception as e:
            logging.error("Error fetching depth for %s: %s", ancestor, e)
            depth_dict[ancestor] = 0  # Fallback to 0 on error

    if not depth_dict:
        raise HTTPException(status_code=404, detail="Unable to compute depths for common ancestors")

    # Determine the LCA as the ancestor with the maximum depth.
    lca = max(depth_dict, key=depth_dict.get)
    logging.info("Lowest common ancestor for %s and %s is %s", cui1, cui2, lca)
    return {"cui1": cui1, "cui2": cui2, "lca": lca, "depth":depth_dict[lca]}