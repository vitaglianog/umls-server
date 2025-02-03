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