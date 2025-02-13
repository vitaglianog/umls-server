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
@app.get("/cuis", summary="Search for CUIs by term")
def search_cui(query: str):
    """ Search for CUIs matching a given term. """
    sql = "SELECT CUI, STR FROM MRCONSO WHERE STR LIKE %s LIMIT 50"
    
    with connect_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql, (f"%{query}%",))
            results = cursor.fetchall()

    if not results:
        raise HTTPException(status_code=404, detail="No CUIs found for the given term")
    
    return {"query": query, "cuis": [{"cui": r["CUI"], "name": r["STR"]} for r in results]}

# @app.get("/cuis/{cui}/relations", summary="Get hierarchical relations for a CUI")
# def get_relations(cui: str):
#     """ Get parent CUI(s) from MRHIER. """
#     sql = "SELECT SUBSTRING_INDEX(PTR, '.', -2) AS parent_cui FROM MRHIER WHERE CUI = %s"

#     with connect_db() as conn:
#         with conn.cursor() as cursor:
#             cursor.execute(sql, (cui,))
#             result = cursor.fetchone()

#     if not result or not result["parent_cui"]:
#         raise HTTPException(status_code=404, detail="No parent found")

#     return {"cui": cui, "parent": result["parent_cui"]}

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


@app.get("/cuis/{cui}/ancestors", summary="Get all ancestors of a CUI")
def get_ancestors(cui: str):
    """ Retrieve all ancestors of a CUI from MRHIER. """
    sql = "SELECT PTR FROM MRHIER WHERE CUI = %s"

    with connect_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql, (cui,))
            result = cursor.fetchone()

    if not result or not result["PTR"]:
        raise HTTPException(status_code=404, detail="No ancestors found")

    ancestors = result["PTR"].split(".")[:-1]  # Remove self
    return {"cui": cui, "ancestors": ancestors}



@app.get("/ontologies/{source}/{code}/cui", summary="Map an ontology term to a CUI")
def get_cui_from_ontology(source: str, code: str):
    """ Get the CUI for a given ontology term (HPO, SNOMED, etc.). """
    sql = "SELECT CUI FROM MRMAP WHERE MAPSUBSETID = %s AND MAPCODE = %s LIMIT 1"

    with connect_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql, (source, code))
            result = cursor.fetchone()

    if not result:
        raise HTTPException(status_code=404, detail="Mapping not found")
    
    return {"ontology": source, "term": code, "cui": result["CUI"]}

@app.get("/cuis/{cui1}/{cui2}/lca", summary="Get the lowest common ancestor of two CUIs")
def find_lowest_common_ancestor(cui1: str, cui2: str):
    """ Find the lowest common ancestor (LCA) of two CUIs. """
    ancestors1 = set(get_ancestors(cui1))
    ancestors2 = set(get_ancestors(cui2))

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
