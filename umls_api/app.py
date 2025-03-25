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
TIMEOUT = 5

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




@app.get("/cuis/{cui}/depth", summary="Get depth of a CUI in the hierarchy")
async def get_depth(cui: str):
    """ Determine depth using MRHIER PTR column. """
    sql = "SELECT LENGTH(PTR) - LENGTH(REPLACE(PTR, '.', '')) + 1 AS depth FROM MRHIER WHERE CUI = %s"

    with connect_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql, (cui,))
            result = cursor.fetchone()

    if not result or result["depth"] is None:
        raise HTTPException(status_code=404, detail="Depth not found")

    return {"cui": cui, "depth": result["depth"]}

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

@app.get("/cuis/{cui1}/{cui2}/lca", summary="Get the lowest common ancestor of two CUIs")
async def find_lowest_common_ancestor(cui1: str, cui2: str):
    """ Find the lowest common ancestor (LCA) of two CUIs. """
    try:
        # Fetch ancestors for cui1 with a timeout
        logging.info(f"Fetching ancestors for {cui1}")
        ancestors1_response = await asyncio.wait_for(get_ancestors(cui1), timeout=TIMEOUT)
        ancestors1 = set(ancestors1_response["ancestors"])
        logging.info(f"Ancestors for {cui1}: {ancestors1}")

        # Fetch ancestors for cui2 with a timeout
        logging.info(f"Fetching ancestors for {cui2}")
        ancestors2_response = await asyncio.wait_for(get_ancestors(cui2), timeout=TIMEOUT)
        ancestors2 = set(ancestors2_response["ancestors"])
        logging.info(f"Ancestors for {cui2}: {ancestors2}")

        # Compute common ancestors
        common_ancestors = ancestors1 & ancestors2
        logging.info(f"Common ancestors: {common_ancestors}")

        if not common_ancestors:
            raise HTTPException(status_code=404, detail="No common ancestor found")

        # Helper to get depth with logging and timeout
        async def get_depth_safe(cui: str) -> int:
            try:
                logging.info(f"Fetching depth for {cui}")
                depth_response = await asyncio.wait_for(get_depth(cui), timeout=TIMEOUT)
                depth = depth_response["depth"]
                logging.info(f"Depth for {cui}: {depth}")
                return depth
            except Exception as e:
                logging.error(f"Error fetching depth for {cui}: {e}")
                return 0  # Default depth if an error occurs

        # Run all depth calculations concurrently
        tasks = [get_depth_safe(ancestor) for ancestor in common_ancestors]
        depth_results = await asyncio.gather(*tasks)
        depth_dict = {ancestor: depth for ancestor, depth in zip(common_ancestors, depth_results)}
        logging.info(f"Depths for common ancestors: {depth_dict}")

        # Determine the lowest common ancestor by maximum depth
        lca = max(depths, key=depths.get)
        logging.info(f"Lowest common ancestor: {lca}")

        return {"cui1": cui1, "cui2": cui2, "lca": lca, "depth":depth_dict[lca]}

    except Exception as e:
        logging.error(f"Error in find_lowest_common_ancestor: {e}")
        return {"error": str(e)}





async def fetch_depth(cui: str) -> int:
    logging.debug("Starting fetch_depth for CUI: %s", cui)
    try:
        loop = asyncio.get_running_loop()
        start_time = time.perf_counter()
        depth = await asyncio.wait_for(loop.run_in_executor(executor, query_depth, cui), timeout=TIMEOUT)
        elapsed = time.perf_counter() - start_time
        logging.debug("fetch_depth for CUI %s returned %s in %.3f seconds.", cui, depth, elapsed)
    except asyncio.TimeoutError:
        logging.error("Timeout retrieving depth for CUI: %s", cui)
        raise HTTPException(status_code=504, detail=f"Timeout retrieving depth for CUI {cui}")
    except Exception as e:
        logging.error("Error retrieving depth for CUI %s: %s", cui, e)
        raise HTTPException(status_code=500, detail=f"Error retrieving depth for CUI {cui}")
    
    if depth is None:
        logging.error("Depth not found for CUI: %s", cui)
        raise HTTPException(status_code=404, detail=f"Depth not found for CUI {cui}")

    logging.debug("Depth for CUI %s is %s", cui, depth)
    return depth


@app.get("/cuis/{cui1}/{cui2}/similarity/wu-palmer", summary="Compute Wu-Palmer similarity")
async def wu_palmer_similarity(cui1: str, cui2: str):
    """Compute Wu-Palmer similarity between two CUIs using asynchronous DB access."""

    # Get LCA (make sure it's async and uses fetch_depth!)
    lca_result = await find_lowest_common_ancestor(cui1, cui2)
    lca = lca_result["lca"]

    # Run depth queries concurrently using your async-safe fetch_depth function
    try:
        depth_c1, depth_c2, depth_lca = await asyncio.gather(
            fetch_depth(cui1),
            fetch_depth(cui2),
            fetch_depth(lca),
        )
    except HTTPException as e:
        raise e  # Re-raise if one of the depths failed

    if depth_c1 == 0 or depth_c2 == 0:
        raise HTTPException(status_code=400, detail="One or both CUIs have no valid depth")

    similarity = (2 * depth_lca) / (depth_c1 + depth_c2)

    return {
        "cui1": cui1,
        "cui2": cui2,
        "lca": lca,
        "depth_c1": depth_c1,
        "depth_c2": depth_c2,
        "depth_lca": depth_lca,
        "similarity": similarity,
    }
