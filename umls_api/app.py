from fastapi import FastAPI
import pymysql
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

app = FastAPI()

def connect_db():
    return pymysql.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
        cursorclass=pymysql.cursors.DictCursor
    )

# @app.get("/search/{term}")
# def search_umls(term: str):
#     conn = connect_db()
#     cursor = conn.cursor()

#     # Search for the term in MRCONSO (Case-insensitive)
#     query = """
#         SELECT CUI, STR, SAB, LAT 
#         FROM MRCONSO 
#         WHERE STR LIKE %s 
#         AND LAT = 'ENG' 
#         LIMIT 10;
#     """
    
#     cursor.execute(query, (f"%{term}%",))
#     results = cursor.fetchall()
    
#     cursor.close()
#     conn.close()
    
#     return {"results": results}


# Processing code based on Saidie's original code in https://github.com/geneialco/arpa-h/blob/main/mapping/ontology_mapping/local_query.py

from fastapi import FastAPI
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

@app.get("/query/{search_term}")
def query_umls(search_term: str, ontology_abbreviation: str = "HPO"):
    """Search for HPO/NCIT codes matching a medical term."""
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
            cursor.execute(query, (ontology_abbreviation, f"%{search_term}%"))
            results = cursor.fetchall()

            # Process and clean results
            formatted_results = []
            seen_codes = set()  # To avoid duplicates

            for row in results:
                code = row["CODE"]
                term = row["STR"]
                description = clean_html(row["DEF"])

                # Avoid duplicates
                if code not in seen_codes:
                    formatted_results.append({"code": code, "term": term, "description": description})
                    seen_codes.add(code)

    finally:
        conn.close()

    return {"results": formatted_results}
