import os
import base64
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
import requests
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Zoom Connector API is running!"}

ZOOM_CLIENT_ID = os.getenv("ZOOM_CLIENT_ID")
ZOOM_CLIENT_SECRET = os.getenv("ZOOM_CLIENT_SECRET")
ZOOM_REDIRECT_URI = os.getenv("ZOOM_REDIRECT_URI")

if not all([ZOOM_CLIENT_ID, ZOOM_CLIENT_SECRET, ZOOM_REDIRECT_URI]):
    raise Exception("Please set ZOOM_CLIENT_ID, ZOOM_CLIENT_SECRET, and ZOOM_REDIRECT_URI in your environment.")

# Zoom endpoints
ZOOM_AUTHORIZE_URL = "https://zoom.us/oauth/authorize"
ZOOM_TOKEN_URL = "https://zoom.us/oauth/token"

zoom_tokens = {}

@app.get("/zoom/login")
def zoom_login():
    from urllib.parse import urlencode
    params = {
        "response_type": "code",
        "client_id": ZOOM_CLIENT_ID,
        "redirect_uri": ZOOM_REDIRECT_URI,
    }
    auth_url = f"{ZOOM_AUTHORIZE_URL}?{urlencode(params)}"
    return RedirectResponse(auth_url)


@app.get("/zoom/callback")
def zoom_callback(request: Request):
    code = request.query_params.get("code")
    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code.")

    # Basic Auth header with base64-encoded client_id:client_secret
    credentials = f"{ZOOM_CLIENT_ID}:{ZOOM_CLIENT_SECRET}"
    encoded_credentials = base64.b64encode(credentials.encode("utf-8")).decode("utf-8")
    headers = {
        "Authorization": f"Basic {encoded_credentials}"
    }
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": ZOOM_REDIRECT_URI
    }
    token_response = requests.post(ZOOM_TOKEN_URL, headers=headers, data=data)
    if token_response.status_code != 200:
        raise HTTPException(status_code=token_response.status_code, detail=token_response.text)

    token_data = token_response.json()
    # Save tokens (for demo, in-memory)
    zoom_tokens["access_token"] = token_data.get("access_token")
    zoom_tokens["refresh_token"] = token_data.get("refresh_token")
    return JSONResponse({"message": "Zoom authentication successful!", "token_data": token_data})

@app.post("/zoom/meeting")
def create_zoom_meeting():
    access_token = zoom_tokens.get("access_token")
    if not access_token:
        raise HTTPException(status_code=401, detail="User not authenticated with Zoom. Please log in first.")

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    # Endpoint to create a meeting on the authorized user's account
    meeting_url = "https://api.zoom.us/v2/users/me/meetings"

    payload = {
        "topic": "Digital Twin Meeting",
        "type": 2,  # Scheduled meeting
        "start_time": "2025-03-27T10:00:00Z",  # a format
        "duration": 30,  # duration in minutes
        "timezone": "UTC",
        "agenda": "Meeting scheduled via Zoom connector for Digital Twin"
    }
    response = requests.post(meeting_url, headers=headers, json=payload)
    if response.status_code not in [200, 201]:
        raise HTTPException(status_code=response.status_code, detail=response.text)
    return JSONResponse(response.json())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=True)