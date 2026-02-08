import requests
from fastapi import FastAPI, Request, Query, HTTPException
from fastapi.responses import PlainTextResponse
from dotenv import load_dotenv
import os 
load_dotenv()



app = FastAPI()
PAGE_ACCESS_TOKEN  = os.environ['PAGE_ACCESS_TOKEN']
VERIFY_TOKEN = os.environ['VERIFY_TOKEN']

def send_message(recipient_id, text):
    # Adres API Facebooka (wersja v19.0 lub nowsza)
    url = f"https://graph.facebook.com/v24.0/989545910907540/messages?access_token={PAGE_ACCESS_TOKEN}"
    
    # Struktura danych wymagana przez Facebooka
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": text}
    }
    
    # Wysyłamy zapytanie POST
    response = requests.post(url, json=payload)
    
    if response.status_code == 200:
        print(f"Wysłano odpowiedź do {recipient_id}")
    else:
        print(f"Błąd wysyłania: {response.status_code}, {response.text}")

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
async def receive_webhook(request: Request):
    data = await request.json()
    
    # Facebook może przesłać kilka zdarzeń naraz (batch), więc iterujemy
    # Struktura JSONa: entry -> messaging -> sender -> id
    
    try:
        if data.get("object") == "page":
            for entry in data.get("entry", []):
                for event in entry.get("messaging", []):
                    
                    # Sprawdzamy, czy to jest wiadomość (a nie np. potwierdzenie dostarczenia)
                    if "message" in event:
                        sender_id = event["sender"]["id"]
                        message_text = event["message"].get("text")
                        
                        print(f"Otrzymano wiadomość od {sender_id}: {message_text}")
                        
                        # --- TU WYSYŁAMY ODPOWIEDŹ ---
                        response_text = "Witamy, zaraz ktoś postara się odpowiedziec na pani/ pana pytanie"
                        send_message(sender_id, response_text)
                        
    except Exception as e:
        print(f"Wystąpił błąd przetwarzania: {e}")

    # Zawsze zwracamy 200 OK, żeby Facebook nie ponawiał wysyłki
    return {"status": "ok"}