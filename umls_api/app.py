from fastapi import FastAPI
import pymysql
import python_dotenv

app = FastAPI()

def connect_db():
    return pymysql.connect(
        host="localhost",
        user="umls_user",
        password="your_password",
        database="umls",
        cursorclass=pymysql.cursors.DictCursor
    )

@app.get("/search/{term}")
def search_umls(term: str):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM umls_table WHERE term LIKE %s LIMIT 10", (f"%{term}%",))
    results = cursor.fetchall()
    cursor.close()
    conn.close()
    return {"results": results}
