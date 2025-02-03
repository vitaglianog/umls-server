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

@app.get("/search/{term}")
def search_umls(term: str):
    conn = connect_db()
    cursor = conn.cursor()

    # Search for the term in MRCONSO (Case-insensitive)
    query = """
        SELECT CUI, STR, SAB, LAT 
        FROM MRCONSO 
        WHERE STR LIKE %s 
        AND LAT = 'ENG' 
        LIMIT 10;
    """
    
    cursor.execute(query, (f"%{term}%",))
    results = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return {"results": results}
