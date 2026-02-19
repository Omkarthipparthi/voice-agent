import os
import uvicorn
from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import HTMLResponse
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

PORT = int(os.getenv("PORT", 8080))

# ── Provider instances (created once) ──────────────────────────
from providers.twilio import TwilioProvider
from providers.telnyx import TelnyxProvider

twilio_provider = TwilioProvider()
telnyx_provider = TelnyxProvider()

# ── Health check ───────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def index_page():
    return "<h1>Voice Agent Server is Running!</h1><p>Providers: Twilio, Telnyx</p>"

# ── Twilio endpoints ──────────────────────────────────────────
@app.api_route("/incoming-call/twilio", methods=["GET", "POST"])
async def handle_twilio_call(request: Request):
    """Handle incoming Twilio calls → TwiML response."""
    host = request.headers.get("host", "localhost")
    xml = twilio_provider.generate_call_response(host)
    return HTMLResponse(content=xml, media_type="application/xml")

@app.websocket("/media-stream/twilio")
async def handle_twilio_stream(websocket: WebSocket):
    """WebSocket for Twilio media stream."""
    print("📞 [Twilio] Client connected")
    await websocket.accept()
    from bot import VoiceBot
    bot = VoiceBot(provider=twilio_provider)
    await bot.start(websocket)

# ── Telnyx endpoints ──────────────────────────────────────────
@app.api_route("/incoming-call/telnyx", methods=["GET", "POST"])
async def handle_telnyx_call(request: Request):
    """Handle incoming Telnyx calls → TeXML response."""
    # Prefer forwarded host headers (ngrok sets these)
    host = (
        request.headers.get("x-forwarded-host")
        or request.headers.get("x-original-host")
        or request.headers.get("host", "localhost")
    )
    xml = telnyx_provider.generate_call_response(host)
    print(f"📞 [Telnyx] Incoming call webhook hit. Host: {host}")
    print(f"📞 [Telnyx] TeXML response:\n{xml}")
    return HTMLResponse(content=xml, media_type="application/xml")

@app.websocket("/media-stream/telnyx")
async def handle_telnyx_stream(websocket: WebSocket):
    """WebSocket for Telnyx media stream."""
    print("📞 [Telnyx] Client connected")
    await websocket.accept()
    from bot import VoiceBot
    bot = VoiceBot(provider=telnyx_provider)
    await bot.start(websocket)

# ── Legacy endpoints (backwards compatibility) ────────────────
@app.api_route("/incoming-call", methods=["GET", "POST"])
async def handle_incoming_call_legacy(request: Request):
    """Legacy endpoint — redirects to Twilio handler."""
    return await handle_twilio_call(request)

@app.websocket("/media-stream")
async def handle_media_stream_legacy(websocket: WebSocket):
    """Legacy endpoint — redirects to Twilio handler."""
    await handle_twilio_stream(websocket)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)
