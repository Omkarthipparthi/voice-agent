import os
import uvicorn
from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import HTMLResponse, JSONResponse
from twilio.twiml.voice_response import VoiceResponse, Connect
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI()

PORT = int(os.getenv("PORT", 8080))

@app.get("/", response_class=HTMLResponse)
async def index_page():
    return "<h1>Twilio Media Stream Server is Running!</h1>"

@app.api_route("/incoming-call", methods=["GET", "POST"])
async def handle_incoming_call(request: Request):
    """
    Handle incoming calls and direct them to the media stream.
    """
    response = VoiceResponse()
    response.say("Please wait while I connect you to the AI assistant.")
    response.pause(length=1)
    response.say("Okay, you can start talking!")
    connect = Connect()
    connect.stream(url=f"wss://{request.headers.get('host')}/media-stream")
    response.append(connect)
    return HTMLResponse(content=str(response), media_type="application/xml")

@app.websocket("/media-stream")
async def handle_media_stream(websocket: WebSocket):
    """
    WebSocket endpoint for handling the audio stream.
    """
    print("Client connected")
    await websocket.accept()
    
    try:
        while True:
            message = await websocket.receive_text()
            # print(f"Received message: {message}") 
            # Logic to handle Twilio Media Stream events will go here
            # 1. Receive audio payload
            # 2. Forward to OpenAI Realtime API
            # 3. Receive audio from OpenAI
            # 4. Send audio back to Twilio
            pass
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        await websocket.close()
        print("Connection closed")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)
