import requests
from fastapi import FastAPI, Request, Query, HTTPException, BackgroundTasks
from fastapi.responses import PlainTextResponse
import google.genai as genai

from dotenv import load_dotenv
import os 
load_dotenv()



app = FastAPI()
PAGE_ACCESS_TOKEN  = os.environ['PAGE_ACCESS_TOKEN']
VERIFY_TOKEN = os.environ['VERIFY_TOKEN']
GEMINI_API_KEY  = os.environ['GEMINI_API_KEY']

client = genai.Client(api_key=GEMINI_API_KEY)


MODEL_ID = 'gemini-2.5-flash'


def send_message(recipient_id, text):
 
    url = f"https://graph.facebook.com/v24.0/989545910907540/messages?access_token={PAGE_ACCESS_TOKEN}"
    
    # Struktura danych wymagana przez Facebooka
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": text}
    }
    
    try:
        r = requests.post(url, json=payload)
        if r.status_code == 200:
            print(f"Wysłano do {recipient_id}: {text[:50]}...")
        else:
            print(f"Błąd FB: {r.text}")
    except Exception as e:
        print(f"Błąd sieci: {e}")

async def process_ai_response(sender_id, user_message):
    """
    background.
    """
    try:
        print(f"Pytam Gemini o: {user_message}")
        
        # --- NOWE WYWOŁANIE ASYNCHRONICZNE ---
        # Używamy 'client.aio.models.generate_content' dla operacji async
        response = await client.aio.models.generate_content(
            model=MODEL_ID,
            contents=user_message
        )
        
        # Pobieramy tekst z odpowiedzi
        ai_text = response.text
        
        # Wysyłamy odpowiedź na Messengera
        send_message(sender_id, ai_text)
        
    except Exception as e:
        print(f"Błąd Gemini: {e}")
        send_message(sender_id, "Przepraszam, mam problem z połączeniem do mojego mózgu 🤖")

# --- ENDPOINTY ---

@app.get("/webhook")
async def verify_webhook(
    mode: str = Query(alias="hub.mode"),
    token: str = Query(alias="hub.verify_token"),
    challenge: str = Query(alias="hub.challenge")
):
    if mode == "subscribe" and token == VERIFY_TOKEN:
        return PlainTextResponse(content=challenge, status_code=200)
    raise HTTPException(status_code=403, detail="Błędny token")

@app.post("/webhook")
async def receive_webhook(request: Request, background_tasks: BackgroundTasks):
    data = await request.json()

    try:
        if data.get("object") == "page":
            for entry in data.get("entry", []):
                for event in entry.get("messaging", []):
                    
                    # Sprawdzamy czy to wiadomość tekstowa i czy nie jest echem (od nas samych)
                    if "message" in event and "text" in event["message"] and not event["message"].get("is_echo"):
                        
                        sender_id = event["sender"]["id"]
                        user_text = event["message"]["text"]
                        
                        print(f"Otrzymano od {sender_id}: {user_text}")

                        # Zlecamy zadanie w tle
                        background_tasks.add_task(process_ai_response, sender_id, user_text)

    except Exception as e:
        print(f"Błąd przetwarzania webhooka: {e}")

    return {"status": "ok"}