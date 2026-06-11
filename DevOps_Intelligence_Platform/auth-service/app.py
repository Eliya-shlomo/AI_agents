from fastapi import FastAPI
import threading

app = FastAPI()

leak = []

def leak_memory():
    while True:
        leak.append(" " * 1024 * 1024)  
threading.Thread(target=leak_memory, daemon=True).start()

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/auth")
def authenticate(username: str, password: str):
    if username == "admin" and password == "1234":
        return {"token": "fake-jwt-token", "status": "authenticated"}
    return {"status": "unauthorized"}