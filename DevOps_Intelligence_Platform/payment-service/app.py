from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uuid

app = FastAPI()

transactions = {}

class PaymentRequest(BaseModel):
    card_number: str
    amount: float

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/payment")
def process_payment(payment: PaymentRequest):
    transaction_id = str(uuid.uuid4())
    transactions[transaction_id] = {
        "id": transaction_id,
        "card_number": payment.card_number[-4:], 
        "amount": payment.amount,
        "status": "success"
    }
    return {"transaction_id": transaction_id, "status": "success"}

@app.get("/payment/{transaction_id}")
def get_payment(transaction_id: str):
    if transaction_id not in transactions:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return transactions[transaction_id]