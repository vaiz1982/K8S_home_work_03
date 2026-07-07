from fastapi import FastAPI, Depends
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import platform
import mysql.connector
from mysql.connector import Error
from contextlib import contextmanager
import os

app = FastAPI(title="Cyberpunk API")

# БД подключение
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "cyberpunk"),
    "password": os.getenv("DB_PASSWORD", "password"),
    "database": os.getenv("DB_NAME", "cyberpunk_db")
}

@contextmanager
def get_db_connection():
    conn = None
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        yield conn
    except Error as e:
        print(f"DB Error: {e}")
        raise
    finally:
        if conn and conn.is_connected():
            conn.close()

@app.get("/health")
async def health_check():
    return {
        "server": platform.system(),
        "status": "OK"
    }

@app.get("/", response_class=HTMLResponse)
async def root():
    with open("static/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

@app.get("/courses")
async def get_courses():
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM courses ORDER BY name")
            courses = cursor.fetchall()
        return {"courses": courses}
    except:
        # Fallback список курсов
        return {
            "courses": [
                {"id": 1, "name": "Kubernetes для DevOps", "description": "Orchestration контейнеров"},
                {"id": 2, "name": "Terraform IaC", "description": "Infrastructure as Code"},
                {"id": 3, "name": "CI/CD Jenkins/GitLab", "description": "Автоматизация пайплайнов"},
                {"id": 4, "name": "Prometheus + Grafana", "description": "Мониторинг и алертинг"}
            ]
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

