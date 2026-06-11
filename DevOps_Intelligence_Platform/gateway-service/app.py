from fastapi import FastAPI
import httpx

app = FastAPI()

PAYMENT_URL = "http://payment-service:80"
AUTH_URL = "http://auth-service:80"

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/pay")
async def pay(card_number: str, amount: float):
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{PAYMENT_URL}/payment", json={
            "card_number": card_number,
            "amount": amount
        })
    return response.json()

@app.post("/login")
async def login(username: str, password: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{AUTH_URL}/auth?username={username}&password={password}"
        )
    return response.json()