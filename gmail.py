import os
import base64

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


# Gmail permission
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]


def connect_gmail():

    creds = None

    # Check if we already have a login token
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file(
            "token.json",
            SCOPES
        )

    # If there is no valid login, ask Google to authenticate
    if not creds or not creds.valid:

        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())

        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json",
                SCOPES
            )

            creds = flow.run_local_server(port=0)

        # Save login token
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    service = build("gmail", "v1", credentials=creds)

    return service

def extract_email_body(payload):
    """Extract readable text from a Gmail message."""

    if payload.get("mimeType") == "text/plain":
        data = payload.get("body", {}).get("data")

        if data:
            return base64.urlsafe_b64decode(
                data + "=" * (-len(data) % 4)
            ).decode("utf-8", errors="replace")

    for part in payload.get("parts", []):
        body = extract_email_body(part)

        if body:
            return body

    return ""

def get_emails():

    service = connect_gmail()

    print("\n📧 Checking Gmail...\n")

    results = service.users().messages().list(
        userId="me",
        maxResults=10
    ).execute()

    messages = results.get("messages", [])

    if not messages:
        print("No emails found.")
        return

    for message in messages:

        msg = service.users().messages().get(
            userId="me",
            id=message["id"],
            format="full"
        ).execute()

        headers = msg["payload"]["headers"]
        body = extract_email_body(msg["payload"])

        sender = ""
        subject = ""
        date = ""

        for header in headers:

            if header["name"] == "From":
                sender = header["value"]

            elif header["name"] == "Subject":
                subject = header["value"]

            elif header["name"] == "Date":
                date = header["value"]

        print("----------------------------------------")
        print("From:", sender)
        print("Subject:", subject)
        print("Date:", date)
        print("Body:", body[:500] if body else "No plain-text body available")
        

if __name__ == "__main__":
    get_emails()