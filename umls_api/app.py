from fastapi import FastAPI, HTTPException, Query
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
def get_depth(cui: str):
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
def find_lowest_common_ancestor(cui1: str, cui2: str):
    """ Find the lowest common ancestor (LCA) of two CUIs. """

    try:
        # Step 1: Get ancestors for both CUIs
        ancestors1 = set(get_ancestors(cui1)["ancestors"])
        ancestors2 = set(get_ancestors(cui2)["ancestors"])

        # Step 2: Find common ancestors
        common_ancestors = ancestors1 & ancestors2  # Intersection

        if not common_ancestors:
            raise HTTPException(status_code=404, detail="No common ancestor found")

        # Step 3: Find LCA with the maximum depth
        def get_depth_safe(cui):
            """ Get depth, handling errors gracefully. """
            try:
                return get_depth(cui)["depth"]
            except Exception:
                return 0  # Default depth if an error occurs

        lca = max(common_ancestors, key=lambda cui: get_depth_safe(cui))

        return {"cui1": cui1, "cui2": cui2, "lca": lca}

    except Exception as e:
        return {"error": str(e)}




@app.get("/cuis/{cui1}/{cui2}/similarity/wu-palmer", summary="Compute Wu-Palmer similarity")
def wu_palmer_similarity(cui1: str, cui2: str):
    """ Compute Wu-Palmer similarity between two CUIs using MRHIER. """

    sql_depth = """
        SELECT MAX(LENGTH(PTR) - LENGTH(REPLACE(PTR, '.', '')) + 1) AS depth 
        FROM MRHIER WHERE CUI = %s
    """

    # Get LCA
    lca_result = find_lowest_common_ancestor(cui1, cui2)
    lca = lca_result["lca"]

    with connect_db() as conn:
        with conn.cursor() as cursor:
            # Get depth of CUI1
            cursor.execute(sql_depth, (cui1,))
            result1 = cursor.fetchone()
            depth_c1 = result1["depth"] if result1 and result1["depth"] else 0

            # Get depth of CUI2
            cursor.execute(sql_depth, (cui2,))
            result2 = cursor.fetchone()
            depth_c2 = result2["depth"] if result2 and result2["depth"] else 0

            # Get depth of LCA
            cursor.execute(sql_depth, (lca,))
            result_lca = cursor.fetchone()
            depth_lca = result_lca["depth"] if result_lca and result_lca["depth"] else 0

    # Compute Wu-Palmer similarity
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
        "similarity": similarity
    }

