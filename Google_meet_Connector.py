import uvicorn
import requests
import json
import os
from fastapi import HTTPException
from fastapi import FastAPI, Depends, Request
from fastapi.responses import RedirectResponse
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request as GoogleRequest
from google.auth.exceptions import RefreshError

# Constants
CLIENT_SECRETS_FILE = "credentials.json"
SCOPES = ["https://www.googleapis.com/auth/calendar.events"]
REDIRECT_URI = "http://localhost:8000/auth/callback"
CREDENTIALS_FILE = "session.json"  # File to store tokens

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Google Meet Connector API is running!"}

# Load credentials file
if not os.path.exists(CLIENT_SECRETS_FILE):
    raise FileNotFoundError("credentials.json not found. Download it from Google Cloud Console.")

# Function to load saved credentials
def load_credentials():
    if os.path.exists(CREDENTIALS_FILE):
        with open(CREDENTIALS_FILE, "r") as f:
            return json.load(f)
    return {}

# Function to save credentials
def save_credentials(data):
    with open(CREDENTIALS_FILE, "w") as f:
        json.dump(data, f)


# Step 1: Login Route
@app.get("/login", response_class=RedirectResponse)
async def login():
    """ Redirects user to Google OAuth 2.0 consent screen. """
    flow = Flow.from_client_secrets_file(CLIENT_SECRETS_FILE, scopes=SCOPES, redirect_uri=REDIRECT_URI)
    auth_url, _ = flow.authorization_url(prompt="consent")
    return RedirectResponse(auth_url)


# Step 2: OAuth Callback
@app.get("/auth/callback")
async def auth_callback(request: Request):
    try:
        query_params = dict(request.query_params)
        query_params = dict(request.query_params)
        code = query_params.get("code")

        if not code:
            return {"error": "Missing OAuth authorization code. Please try logging in again."}

        flow = Flow.from_client_secrets_file(CLIENT_SECRETS_FILE, scopes=SCOPES, redirect_uri=REDIRECT_URI)
        # flow.fetch_token(code=query_params.get("code"))
        flow.fetch_token(code=code)
        credentials = flow.credentials

        # Save credentials to file
        credentials_data = {
            "token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "token_uri": credentials.token_uri,
            "client_id": credentials.client_id,
            "client_secret": credentials.client_secret,
        }
        save_credentials(credentials_data)

        return {"message": "Authentication successful!",
                "access_token": credentials.token}

    except Exception as e:
        return {"error": "Authentication failed", "details": str(e)}


# Step 3: Generate Google Meet Link
@app.post("/create_meeting")
async def create_meeting():
    try:
        credentials_data = load_credentials()
        if not credentials_data:
            return {"error": "User not authenticated. Please login first."}

        credentials = Credentials.from_authorized_user_info(credentials_data)

        # Refresh the token if expired
        if credentials.expired and credentials.refresh_token:
            credentials.refresh(GoogleRequest())
            credentials_data["token"] = credentials.token
            save_credentials(credentials_data)

        event_data = {
            "summary": "Google Meet AI Meeting",
            "start": {"dateTime": "2025-03-26T10:00:00", "timeZone": "Asia/Kolkata"},
            "end": {"dateTime": "2025-03-26T11:00:00", "timeZone": "Asia/Kolkata"},
            "conferenceData": {"createRequest": {"requestId": "unique-meet-id"}},
        }

        headers = {"Authorization": f"Bearer {credentials.token}", "Content-Type": "application/json"}
        response = requests.post(
            "https://www.googleapis.com/calendar/v3/calendars/primary/events?conferenceDataVersion=1",
            json=event_data,
            headers=headers
        )

        response_json = response.json()
        meet_link = response_json.get("hangoutLink", "Meeting link not generated")
        return {"message": "Meeting Created", "meet_link": meet_link}

    except RefreshError:
        return {"error": "Token expired, please re-authenticate."}
    except Exception as e:
        return {"error": str(e)}


# Step 4: Retrieve Google Meet Events
@app.get("/meetings")
async def get_meetings():
    try:
        credentials_data = load_credentials()
        if not credentials_data:
            return {"error": "User not authenticated. Please login first."}

        credentials = Credentials.from_authorized_user_info(credentials_data)

        # Refresh the token if expired
        if credentials.expired and credentials.refresh_token:
            credentials.refresh(GoogleRequest())
            credentials_data["token"] = credentials.token
            save_credentials(credentials_data)

        headers = {"Authorization": f"Bearer {credentials.token}"}
        response = requests.get(
            "https://www.googleapis.com/calendar/v3/calendars/primary/events",
            headers=headers
        )

        response_json = response.json()
        events = response_json.get("items", [])
        meet_links = [event["hangoutLink"] for event in events if "hangoutLink" in event]
        return {"message": "Meetings Retrieved", "meet_links": meet_links}

    except RefreshError:
        return {"error": "Token expired, please re-authenticate."}
    except Exception as e:
        return {"error": str(e)}


# Run the FastAPI server
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
