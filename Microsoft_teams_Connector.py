from fastapi import FastAPI, Request
import requests
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

@app.get("/")
def home():
    return {"message": "Welcome to the Microsoft Teams Connector API!"}

# Microsoft Azure Credentials
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
TENANT_ID = os.getenv("TENANT_ID")
REDIRECT_URI = "http://localhost:8000/auth/callback"
AUTH_URL = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/authorize"
TOKEN_URL = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
GRAPH_API_URL = "https://graph.microsoft.com/v1.0"

user_tokens = {}

# Step 1: Redirect user to Microsoft Login
@app.get("/login")
def login():
    auth_redirect_url = (
        f"{AUTH_URL}?client_id={CLIENT_ID}&response_type=code&redirect_uri={REDIRECT_URI}"
        f"&scope=User.Read Chat.ReadWrite Presence.Read Calendars.Read offline_access"
    )
    return {"message": "Click the link to login", "url": auth_redirect_url}

# Step 2: Handle OAuth Callback & Get Access Token
@app.get("/auth/callback")
def auth_callback(request: Request):
    code = request.query_params.get("code")
    if not code:
        return {"error": "Authorization code not found"}

    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "scope": "User.Read Chat.ReadWrite Presence.Read Calendars.Read offline_access"
    }

    response = requests.post(TOKEN_URL, data=data)
    if response.status_code == 200:
        token_data = response.json()
        user_tokens["access_token"] = token_data["access_token"]
        return {"message": "Authentication successful", "access_token": token_data["access_token"]}
    else:
        return {"error": "Failed to authenticate", "details": response.json()}

# Step 3: Fetch User Profile
@app.get("/me")
def get_user():
    headers = {"Authorization": f"Bearer {user_tokens.get('access_token')}"}
    response = requests.get(f"{GRAPH_API_URL}/me", headers=headers)
    return response.json()

# Step 4: Get User Presence (Online/Busy/Away)
@app.get("/me/presence")
def get_user_presence():
    headers = {"Authorization": f"Bearer {user_tokens.get('access_token')}"}
    response = requests.get(f"{GRAPH_API_URL}/me/presence", headers=headers)
    return response.json()

# Step 5: Fetch User Chats
@app.get("/me/chats")
def get_user_chats():
    headers = {"Authorization": f"Bearer {user_tokens.get('access_token')}"}
    response = requests.get(f"{GRAPH_API_URL}/me/chats", headers=headers)
    return response.json()

# Step 6: Send Message to a Chat
@app.post("/send_message/{chat_id}")
def send_message(chat_id: str, message: str):
    headers = {
        "Authorization": f"Bearer {user_tokens.get('access_token')}",
        "Content-Type": "application/json"
    }
    data = {"body": {"content": message}}
    response = requests.post(f"{GRAPH_API_URL}/me/chats/{chat_id}/messages", headers=headers, json=data)
    return response.json()
