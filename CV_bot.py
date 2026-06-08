from dotenv import load_dotenv
from openai import OpenAI
import json
import os
import requests
from pypdf import PdfReader
import gradio as gr
import numpy as np

load_dotenv(override=True)
openai = OpenAI()

# ─── Pushover ───────────────────────────────────────
def push(message):
    print(f"Push: {message}")
    payload = {
        "user": os.getenv("PUSHOVER_USER"),
        "token": os.getenv("PUSHOVER_TOKEN"),
        "message": message
    }
    requests.post("https://api.pushover.net/1/messages.json", data=payload)

# ─── Tools ──────────────────────────────────────────
def record_user_details(email, name="Name not provided", notes="not provided"):
    push(f"Recording interest from {name} with email {email} and notes {notes}")
    return {"recorded": "ok"}

def record_unknown_question(question):
    push(f"Recording question that couldn't be answered: {question}")
    return {"recorded": "ok"}

tools = [
    {"type": "function", "function": {
        "name": "record_user_details",
        "description": "Use this tool when a user provides their email address and wants to be contacted",
        "parameters": {
            "type": "object",
            "properties": {
                "email": {"type": "string", "description": "The email address of this user"},
                "name": {"type": "string", "description": "The user's name, if provided"},
                "notes": {"type": "string", "description": "Any additional context worth recording"}
            },
            "required": ["email"],
            "additionalProperties": False
        }
    }},
    {"type": "function", "function": {
        "name": "record_unknown_question",
        "description": "Always use this tool to record any question that couldn't be answered",
        "parameters": {
            "type": "object",
            "properties": {
                "question": {"type": "string", "description": "The question that couldn't be answered"}
            },
            "required": ["question"],
            "additionalProperties": False
        }
    }}
]

def handle_tool_calls(tool_calls):
    results = []
    for tool_call in tool_calls:
        tool_name = tool_call.function.name
        arguments = json.loads(tool_call.function.arguments)
        print(f"Tool called: {tool_name}")
        tool = globals().get(tool_name)
        result = tool(**arguments) if tool else {}
        results.append({
            "role": "tool",
            "content": json.dumps(result),
            "tool_call_id": tool_call.id
        })
    return results

# ─── RAG ────────────────────────────────────────────
def chunk_text(text, chunk_size=300, overlap=50):
    """פירוק הטקסט ל-chunks עם overlap"""
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunk = " ".join(words[i:i + chunk_size])
        chunks.append(chunk)
        i += chunk_size - overlap
    return chunks

def get_embedding(text):
    """המרת טקסט לוקטור"""
    response = openai.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return response.data[0].embedding

def cosine_similarity(a, b):
    """חישוב דמיון בין שני וקטורים"""
    a, b = np.array(a), np.array(b)
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

def build_vector_db(text):
    """בניית ה-vector DB — רץ פעם אחת בהתחלה"""
    chunks = chunk_text(text)
    db = []
    for chunk in chunks:
        embedding = get_embedding(chunk)
        db.append({"text": chunk, "embedding": embedding})
    print(f"Vector DB built: {len(db)} chunks")
    return db

def retrieve(query, db, top_k=3):
    """שליפת ה-chunks הכי רלוונטיים לשאלה"""
    query_embedding = get_embedding(query)
    scored = []
    for item in db:
        score = cosine_similarity(query_embedding, item["embedding"])
        scored.append((score, item["text"]))
    scored.sort(reverse=True)
    return [text for _, text in scored[:top_k]]

# ─── טעינת מידע ─────────────────────────────────────
reader = PdfReader("me/linkedin.pdf")
linkedin = ""
for page in reader.pages:
    text = page.extract_text()
    if text:
        linkedin += text

with open("me/summary.txt", "r", encoding="utf-8") as f:
    summary = f.read()

name = "Eliya Shlomo"

# בניית ה-vector DB פעם אחת בלבד
print("Building vector DB...")
vector_db = build_vector_db(linkedin)

# ─── System Prompt ───────────────────────────────────
base_system_prompt = f"""You are acting as {name}. You are answering questions on {name}'s website,
particularly questions related to {name}'s career, background, skills and experience.
Be professional and engaging, as if talking to a potential client or future employer.
If you don't know the answer, use your record_unknown_question tool.
If the user wants to connect, ask for their email and use your record_user_details tool.

## Summary:
{summary}
"""

# ─── Chat ────────────────────────────────────────────
def chat(message, history):
    # שליפת המידע הרלוונטי מה-RAG
    relevant_chunks = retrieve(message, vector_db)
    rag_context = "\n\n".join(relevant_chunks)
    
    # בניית system prompt דינמי עם ה-context הרלוונטי
    system_prompt = base_system_prompt + f"\n\n## Relevant Background:\n{rag_context}"
    
    messages = [{"role": "system", "content": system_prompt}] + history + [{"role": "user", "content": message}]
    
    done = False
    while not done:
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            tools=tools
        )
        finish_reason = response.choices[0].finish_reason
        
        if finish_reason == "tool_calls":
            message_obj = response.choices[0].message
            tool_calls = message_obj.tool_calls
            results = handle_tool_calls(tool_calls)
            messages.append(message_obj)
            messages.extend(results)
        else:
            done = True
    
    return response.choices[0].message.content

# ─── Launch ──────────────────────────────────────────
gr.ChatInterface(chat).launch()