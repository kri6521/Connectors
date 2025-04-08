from fastapi import FastAPI, Request, UploadFile, File
from fastapi.responses import RedirectResponse
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2.credentials import Credentials
import requests
import json
import uvicorn
import os

app = FastAPI()

# Google API Configuration
CLIENT_SECRETS_FILE = "credentials_2.json"
SCOPES = ["https://www.googleapis.com/auth/drive.file"]
REDIRECT_URI = "http://localhost:8000/auth/callback"
TOKEN_FILE = "token.json"


# Helper Functions for Token Management
def save_credentials(credentials_data):
    with open(TOKEN_FILE, "w") as f:
        json.dump(credentials_data, f)


def load_credentials():
    try:
        with open(TOKEN_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return None


# Refresh Token if Expired
def get_credentials():
    credentials_data = load_credentials()
    if not credentials_data:
        return None

    credentials = Credentials.from_authorized_user_info(credentials_data)

    if credentials.expired and credentials.refresh_token:
        credentials.refresh(GoogleRequest())
        credentials_data["token"] = credentials.token
        save_credentials(credentials_data)

    return credentials


# API Root
@app.get("/")
async def root():
    return {"message": "Google Drive Connector API is running!"}


# Step 1: Login & OAuth Flow
@app.get("/login", response_class=RedirectResponse)
async def login():
    flow = Flow.from_client_secrets_file(CLIENT_SECRETS_FILE, scopes=SCOPES, redirect_uri=REDIRECT_URI)
    auth_url, _ = flow.authorization_url(prompt="consent")
    return RedirectResponse(auth_url)


# Step 2: OAuth Callback
@app.get("/auth/callback")
async def auth_callback(request: Request):
    query_params = dict(request.query_params)
    code = query_params.get("code")

    if not code:
        return {"error": "Missing OAuth authorization code. Please try logging in again."}

    flow = Flow.from_client_secrets_file(CLIENT_SECRETS_FILE, scopes=SCOPES, redirect_uri=REDIRECT_URI)
    flow.fetch_token(code=code)
    credentials = flow.credentials

    credentials_data = {
        "token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "token_uri": credentials.token_uri,
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
    }
    save_credentials(credentials_data)

    return {"message": "Authentication successful!", "access_token": credentials.token}


# Step 3: Upload File to Google Drive
@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    credentials = get_credentials()
    if not credentials:
        return {"error": "User not authenticated. Please login first."}

    headers = {"Authorization": f"Bearer {credentials.token}"}
    metadata = {"name": file.filename}
    files = {
        "data": ("metadata", json.dumps(metadata), "application/json"),
        "file": (file.filename, await file.read()),
    }

    response = requests.post("https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart", headers=headers,
                             files=files)

    if response.status_code == 200:
        return {"message": "File uploaded successfully!", "file_id": response.json().get("id")}
    else:
        return {"error": "File upload failed", "details": response.text}


# Step 4: List Files in Google Drive
@app.get("/files")
async def list_files():
    credentials = get_credentials()
    if not credentials:
        return {"error": "User not authenticated. Please login first."}

    headers = {"Authorization": f"Bearer {credentials.token}"}
    response = requests.get("https://www.googleapis.com/drive/v3/files", headers=headers)

    if response.status_code == 200:
        return {"files": response.json().get("files", [])}
    else:
        return {"error": "Failed to retrieve files", "details": response.text}


# Step 5: Download File from Google Drive
@app.get("/download/{file_id}")
async def download_file(file_id: str):
    credentials = get_credentials()
    if not credentials:
        return {"error": "User not authenticated. Please login first."}

    headers = {"Authorization": f"Bearer {credentials.token}"}
    metadata_response = requests.get(f"https://www.googleapis.com/drive/v3/files/{file_id}", headers=headers)

    if metadata_response.status_code != 200:
        return {"error": "Failed to get file metadata", "details": metadata_response.text}

    file_name = metadata_response.json().get("name", "downloaded_file")
    response = requests.get(f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media", headers=headers)

    if response.status_code == 200:
        with open(file_name, "wb") as f:
            f.write(response.content)
        return {"message": "File downloaded successfully!", "file_name": file_name}
    else:
        return {"error": "File download failed", "details": response.text}


# Step 6: Delete File from Google Drive
@app.delete("/delete/{file_id}")
async def delete_file(file_id: str):
    credentials = get_credentials()
    if not credentials:
        return {"error": "User not authenticated. Please login first."}

    headers = {"Authorization": f"Bearer {credentials.token}"}
    response = requests.delete(f"https://www.googleapis.com/drive/v3/files/{file_id}", headers=headers)

    if response.status_code == 204:
        return {"message": "File deleted successfully!"}
    else:
        return {"error": "File deletion failed", "details": response.text}


# Run FastAPI server
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
