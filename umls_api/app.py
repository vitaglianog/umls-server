from fastapi import FastAPI, HTTPException, Query
import aiomysql
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

async def connect_db():
    """Establish database connection."""
    try:
        logging.info("Attempting to connect to database...")
        logging.info(f"Database: {os.getenv('DB_NAME')}")
        logging.info(f"User: {os.getenv('DB_USER')}")
        logging.info(f"Host: {os.getenv('DB_HOST', 'localhost')}")
        
        # Use Docker-compatible connection or fallback to unix socket for local dev
        db_host = os.getenv("DB_HOST")
        if db_host and db_host != "localhost":
            # Docker connection
            conn = await aiomysql.connect(
                host=db_host,
                port=int(os.getenv("DB_PORT", 3306)),
                user=os.getenv("DB_USER"),
                password=os.getenv("DB_PASSWORD"),
                db=os.getenv("DB_NAME"),
                cursorclass=aiomysql.DictCursor,
                autocommit=True,
                connect_timeout=10,
                charset='utf8mb4',
                use_unicode=True
            )
        else:
            # Local development with unix socket
            conn = await aiomysql.connect(
                unix_socket='/var/lib/mysql/mysql.sock',
                user=os.getenv("DB_USER"),
                password=os.getenv("DB_PASSWORD"),
                db=os.getenv("DB_NAME"),
                cursorclass=aiomysql.DictCursor,
                autocommit=True,
                connect_timeout=10,
                charset='utf8mb4',
                use_unicode=True
            )
        logging.info("Successfully connected to database")
        return conn
    except Exception as e:
        logging.error(f"Database connection error: {str(e)}")
        logging.error(f"Error type: {type(e)}")
        logging.error(f"Error args: {e.args}")
        raise HTTPException(status_code=500, detail=f"Database connection error: {str(e)}")

def clean_html(html_text):
    """Remove HTML tags from text."""
    return BeautifulSoup(html_text, "html.parser").get_text() if html_text else None


@app.get("/hpo_to_cui/{hpo_code}")
async def get_cui_from_hpo(hpo_code: str):
    try:
        conn = await connect_db()
        async with conn.cursor(aiomysql.DictCursor) as cursor:
            await cursor.execute("""
                SELECT CUI 
                FROM MRCONSO 
                WHERE CODE = %s 
                AND SAB = 'HPO' 
                LIMIT 1
            """, (hpo_code,))
            result = await cursor.fetchone()

            if not result:
                raise HTTPException(status_code=404, detail="CUI not found for the given HPO code")

            return {
                "hpo_code": hpo_code,
                "cui": result["CUI"]
            }

    except Exception as e:
        logging.error(f"Error getting CUI from HPO: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        if 'conn' in locals():
            conn.close()


@app.get("/terms")
async def search_terms(search: str, ontology: str = "HPO"):
    """Search for medical terms in UMLS based on ontology."""
    try:
        conn = await connect_db()
        async with conn.cursor() as cursor:
            await cursor.execute("""
                SELECT DISTINCT MRCONSO.CODE, MRCONSO.STR, MRDEF.DEF, MRCONSO.CUI
                FROM MRCONSO
                LEFT JOIN MRDEF ON MRCONSO.CUI = MRDEF.CUI
                WHERE MRCONSO.SAB = %s
                AND MRCONSO.STR LIKE %s
                LIMIT 10;
            """, (ontology, f"%{search}%"))
            results = await cursor.fetchall()

            formatted_results = []
            seen_codes = set()

            for row in results:
                code = row["CODE"]
                term = row["STR"]
                description = clean_html(row["DEF"])

                if code not in seen_codes:
                    formatted_results.append({"code": code, "term": term, "description": description, "cui": row["CUI"]})
                    seen_codes.add(code)

    except Exception as e:
        logging.error(f"Error searching terms: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if 'conn' in locals():
            conn.close()

    if not formatted_results:
        raise HTTPException(status_code=404, detail="No results found")

    return {"results": formatted_results}


@app.get("/cuis/{cui}/ancestors", summary="Get all ancestors of a CUI")
async def get_ancestors(cui: str):
    """ Retrieve all ancestors of a CUI by extracting AUIs from MRHIER.PTR and mapping them to CUIs via MRCONSO. """
    try:
        conn = await connect_db()
        async with conn.cursor() as cursor:
            # Step 1: Retrieve the AUI paths (PTR) from MRHIER
            logging.info(f"Fetching PTR paths for CUI {cui}")
            await cursor.execute("SELECT PTR FROM MRHIER WHERE CUI = %s", (cui,))
            results = await cursor.fetchall()
            logging.info(f"Found {len(results)} PTR paths for CUI {cui}")

            if not results:
                logging.info(f"No ancestors found for CUI {cui}")
                return {"cui": cui, "ancestors": []}  # No ancestors found

            # Step 2: Extract AUIs from PTR and map them to CUIs
            auis = set()
            for row in results:
                ptr_path = row["PTR"]
                if ptr_path:
                    auis.update(ptr_path.split("."))  # Extract AUIs from dot-separated paths
            logging.info(f"Extracted {len(auis)} unique AUIs from PTR paths")

            if not auis:
                logging.info(f"No AUIs found in PTR paths for CUI {cui}")
                return {"cui": cui, "ancestors": []}  # No ancestors found

            # Step 3: Map AUIs to CUIs using MRCONSO
            logging.info(f"Mapping {len(auis)} AUIs to CUIs")
            await cursor.execute("""
                SELECT DISTINCT AUI, CUI FROM MRCONSO WHERE AUI IN %s
            """, (tuple(auis),))
            mappings = await cursor.fetchall()
            logging.info(f"Found {len(mappings)} AUI to CUI mappings")

            # Convert AUIs to CUIs
            aui_to_cui = {m["AUI"]: m["CUI"] for m in mappings}
            ancestors_cuis = {aui_to_cui[aui] for aui in auis if aui in aui_to_cui}
            logging.info(f"Found {len(ancestors_cuis)} unique ancestor CUIs")

            return {"cui": cui, "ancestors": list(ancestors_cuis)}

    except Exception as e:
        logging.error(f"Error getting ancestors: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if 'conn' in locals():
            conn.close()

@app.get("/cuis/{cui}", summary="Get details about a specific CUI")
async def get_cui_info(cui: str):
    """Get details about a given CUI."""
    try:
        conn = await connect_db()
        async with conn.cursor() as cursor:
            await cursor.execute("""
                SELECT CUI, STR 
                FROM MRCONSO 
                WHERE CUI = %s 
                LIMIT 1
            """, (cui,))
            result = await cursor.fetchone()

    except Exception as e:
        logging.error(f"Error getting CUI info: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if 'conn' in locals():
            conn.close()

    if not result:
        raise HTTPException(status_code=404, detail="CUI not found")
    
    return {"cui": result["CUI"], "name": result["STR"]}


@app.get("/code-map/", summary="Get billing codes for a CUI")
async def code_map(cui: str):
    """Get all registered codes for a given CUI."""
    try:
        conn = await connect_db()
        async with conn.cursor() as cursor:
            await cursor.execute("""
                SELECT CODE, SAB, STR 
                FROM MRCONSO 
                WHERE CUI = %s 
            """, (cui,))
            results = await cursor.fetchall()

    except Exception as e:
        logging.error(f"Error getting billing codes: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if 'conn' in locals():
            conn.close()

    if not results:
        raise HTTPException(status_code=404, detail="No billing codes found for the given CUI")

    return {"cui": cui, "code_maps": [{"code": r["CODE"], "sab": r["SAB"], "name": r["STR"]} for r in results]}


@app.get("/snomed_to_icd10cm", summary="Translate SNOMED-CT code to ICD10CM codes")
async def snomed_to_icd10cm(code: str):
    """
    Given a SNOMED-CT code, retrieve mapped ICD10CM codes using shared CUI.
    """
    try:
        conn = await connect_db()
        async with conn.cursor() as cursor:
            # Step 1: Get the CUI for the SNOMED-CT code
            await cursor.execute("""
                SELECT CUI
                FROM MRCONSO
                WHERE CODE = %s AND SAB = 'SNOMEDCT_US'
                LIMIT 1;
            """, (code,))
            cui_row = await cursor.fetchone()

            if not cui_row:
                return {
                        "snomed_code": code,
                        "cui": "No CUI found",
                        "icd10cm_mappings": []
                    }

            cui = cui_row["CUI"]

            # Step 2: Get ICD10CM codes that share the same CUI
            await cursor.execute("""
                SELECT DISTINCT CODE, STR
                FROM MRCONSO
                WHERE CUI = %s AND SAB = 'ICD10CM'
            """, (cui,))
            icd_results = await cursor.fetchall()

            if not icd_results:
                return {
                        "snomed_code": code,
                        "cui": cui,
                        "icd10cm_mappings": ["No ICD10CM mappings found"]
                    }

            return {
                "snomed_code": code,
                "cui": cui,
                "icd10cm_mappings": [{"code": r["CODE"], "description": r["STR"]} for r in icd_results]
            }

    except Exception as e:
        logging.error(f"Error mapping SNOMED to ICD10CM: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        if 'conn' in locals():
            conn.close()


## UMLS CUI toolkit
@app.get("/cuis", summary="Search for CUIs by term")
async def search_cui(query: str = Query(..., description="Search term for CUI lookup")):
    """Search for CUIs matching a given term."""
    try:
        conn = await connect_db()
        async with conn.cursor() as cursor:
            await cursor.execute("""
                SELECT CUI, STR, LAT
                FROM MRCONSO 
                WHERE STR LIKE %s 
                LIMIT 50
            """, (f"%{query}%",))
            results = await cursor.fetchall()

    except Exception as e:
        logging.error(f"Error searching CUIs: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if 'conn' in locals():
            conn.close()

    if not results:
        raise HTTPException(status_code=404, detail="No CUIs found for the given term")

    return {"query": query, "cuis": [{"cui": r["CUI"], "name": r["STR"], "language_code": r["LAT"]} for r in results]}


@app.get("/cuis/{cui}/depth")
async def get_depth(cui: str):
    """Get the depth of a CUI in the hierarchy."""
    try:
        conn = await connect_db()
        async with conn.cursor() as cursor:
            # Get the maximum depth from MRHIER table
            await cursor.execute("""
                SELECT MAX(LENGTH(PTR) - LENGTH(REPLACE(PTR, '.', '')) + 1) as max_depth
                FROM MRHIER
                WHERE CUI = %s
            """, (cui,))
            result = await cursor.fetchone()
            
            if not result or result["max_depth"] is None:
                raise HTTPException(status_code=404, detail="Depth not found")
                
            return {"cui": cui, "depth": result["max_depth"]}
    except Exception as e:
        logging.error(f"Error getting depth: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if 'conn' in locals():
            conn.close()

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
            get_depth(cui1),
            get_depth(cui2),
            get_depth(lca)
        )
    except HTTPException as e:
        logging.error("Error fetching depths: %s", e.detail)
        raise

    logging.info("Depths: %s -> %s, %s -> %s, LCA %s -> %s", cui1, depth_c1, cui2, depth_c2, lca, depth_lca)

    if depth_c1["depth"] == 0 or depth_c2["depth"] == 0:
        logging.error("One or both CUIs have no valid depth")
        raise HTTPException(status_code=400, detail="One or both CUIs have no valid depth")

    similarity = (2 * depth_lca["depth"]) / (depth_c1["depth"] + depth_c2["depth"])
    logging.info("Computed Wu-Palmer similarity: %s", similarity)

    return {
        "cui1": cui1,
        "cui2": cui2,
        "lca": lca,
        "depth_c1": depth_c1["depth"],
        "depth_c2": depth_c2["depth"],
        "depth_lca": depth_lca["depth"],
        "similarity": similarity,
    }


@app.get("/cuis/{cui1}/{cui2}/lca", summary="Get the lowest common ancestor of two CUIs")
async def find_lowest_common_ancestor(cui1: str, cui2: str):
    """Find the lowest common ancestor (LCA) of two CUIs using the new depth functions."""
    logging.info("Fetching ancestors for %s and %s", cui1, cui2)
    try:
        # Get ancestors for each CUI
        ancestors1_response = await get_ancestors(cui1)
        ancestors2_response = await get_ancestors(cui2)
        
        ancestors1 = set(ancestors1_response.get("ancestors", []))
        ancestors2 = set(ancestors2_response.get("ancestors", []))
        common_ancestors = ancestors1 & ancestors2
        logging.info("Common ancestors: %s", common_ancestors)

        if not common_ancestors:
            raise HTTPException(status_code=404, detail="No common ancestor found")

        # Fetch depths for each common ancestor
        depth_dict = {}
        for ancestor in common_ancestors:
            try:
                depth_response = await get_depth(ancestor)
                depth_dict[ancestor] = depth_response["depth"]
            except Exception as e:
                logging.error("Error fetching depth for %s: %s", ancestor, e)
                depth_dict[ancestor] = 0  # Fallback to 0 on error

        if not depth_dict:
            raise HTTPException(status_code=404, detail="Unable to compute depths for common ancestors")

        # Determine the LCA as the ancestor with the maximum depth
        lca = max(depth_dict.items(), key=lambda x: x[1])[0]
        logging.info("Lowest common ancestor for %s and %s is %s", cui1, cui2, lca)
        return {"cui1": cui1, "cui2": cui2, "lca": lca, "depth": depth_dict[lca]}
    except Exception as e:
        logging.error("Error finding LCA: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/cuis/{cui}/hpo", summary="Get HPO term and code from CUI")
async def get_hpo_term(cui: str):
    """Get the HPO term and code associated with a given CUI."""
    try:
        conn = await connect_db()
        async with conn.cursor() as cursor:
            await cursor.execute("""
                SELECT STR, CODE 
                FROM MRCONSO 
                WHERE CUI = %s 
                AND SAB = 'HPO' 
                LIMIT 1
            """, (cui,))
            result = await cursor.fetchone()

    except Exception as e:
        logging.error(f"Error getting HPO term: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if 'conn' in locals():
            conn.close()

    if not result:
        raise HTTPException(status_code=404, detail="HPO term not found for the given CUI")
    
    return {
        "cui": cui,
        "hpo_term": result["STR"],
        "hpo_code": result["CODE"]
    }
