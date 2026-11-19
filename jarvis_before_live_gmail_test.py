import os
from dotenv import load_dotenv

load_dotenv()
import base64
import mimetypes
from email.message import EmailMessage
from email.utils import parseaddr, getaddresses

import speech_recognition as sr
import pyttsx3
from google import genai
import os
import subprocess
import webbrowser

from email.mime.text import MIMEText

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# ============================================================
# JARVIS CONTACTS
# ============================================================

CONTACTS = {
    # Add your contacts here
    # "name": "email@example.com",

    "pavitra": "pavitrash123124@gmail.com",
    "harshil": "sharmaharshil5212@gmail.com",
    "honey": "honeyyysinghhh789@gmail.com"
}

# ============================================================
# GMAIL SETTINGS
# ============================================================

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CREDENTIALS_FILE = os.path.join(BASE_DIR, "credentials.json")
TOKEN_FILE = os.path.join(BASE_DIR, "token.json")


# ============================================================
# TEXT TO SPEECH
# ============================================================

engine = pyttsx3.init()
engine.setProperty("rate", 170)


def speak(text):
    print("JARVIS:", text)

    # Clean text for voice output
    voice_text = str(text)

    voice_text = voice_text.replace("*", "")
    voice_text = voice_text.replace("#", "")
    voice_text = voice_text.replace("`", "")
    voice_text = voice_text.replace("\n", " ")

    engine.say(voice_text)
    engine.runAndWait()

# ============================================================
# GEMINI AI
# ============================================================

def ask_ai(prompt):

    try:

        client = genai.Client(
            api_key=os.getenv("GEMINI_API_KEY")
        )

        response = client.models.generate_content(
            model="gemini-flash-lite-latest",
            contents=prompt
        )

        return response.text

    except Exception as e:

        print("❌ Gemini error:", e)

        return "Sorry, I couldn't connect to my AI system."

def analyze_email(sender, subject, body):

    prompt = f"""
You are JARVIS, a careful personal email assistant.

Analyze the email using its actual content, sender, and subject.
Do not assume an email needs a reply just because it mentions jobs.

Return ONLY this format:

CATEGORY: [JOB/HR, IMPORTANT, NORMAL, PROMOTIONAL, SPAM, OTHER]
PRIORITY: [HIGH, MEDIUM, LOW]
SUMMARY: [one or two short sentences]
ACTION: [REPLY, REVIEW, NO_ACTION]
SUGGESTED_REPLY: [a complete professional reply, or NONE]

Rules:
1. JOB ALERTS, newsletters, automated notifications, and job listing digests:
   - CATEGORY: JOB/HR if relevant to employment.
   - ACTION: REVIEW
   - SUGGESTED_REPLY: NONE
   - Do not draft a reply unless the sender asks a specific question
     or requests a response.

2. Recruiter messages, interview invitations, job offers, or HR messages:
   - CATEGORY: JOB/HR
   - ACTION: REPLY when a response is genuinely appropriate;
     otherwise use REVIEW.
   - If a response is appropriate, draft a complete, polite,
     professional reply based only on known information.
   - Never invent qualifications, experience, availability,
     salary expectations, or commitments.

3. Important personal or business emails:
   - Use ACTION: REPLY only when a response is appropriate.
   - Otherwise use REVIEW or NO_ACTION as suitable.

4. Promotional emails, advertisements, and newsletters:
   - CATEGORY: PROMOTIONAL
   - ACTION: NO_ACTION
   - SUGGESTED_REPLY: NONE

5. Spam or suspicious emails:
   - CATEGORY: SPAM
   - ACTION: NO_ACTION
   - SUGGESTED_REPLY: NONE

6. If the email body is missing or unclear, do not invent its contents.
   Use ACTION: REVIEW and SUGGESTED_REPLY: NONE.

7. SUGGESTED_REPLY must be NONE when no response is needed.
   Never write explanatory text after the required fields.

EMAIL:
From: {sender}
Subject: {subject}
Body:
{body[:4000]}
"""

    result = ask_ai(prompt)

    if not result:
        return "CATEGORY: OTHER\nPRIORITY: LOW\nSUMMARY: AI analysis was unavailable.\nACTION: NO_ACTION\nSUGGESTED_REPLY: NONE"

    return result

def get_email_action_level(analysis):

    if not analysis:
        return "NO_ACTION"

    analysis_upper = analysis.upper()

    # Block spam and promotional emails before considering replies.
    if "CATEGORY: SPAM" in analysis_upper:
        return "NO_ACTION"

    if "CATEGORY: PROMOTIONAL" in analysis_upper:
        return "NO_ACTION"

    # Never send when Gemini has not suggested a reply.
    if "SUGGESTED_REPLY: NONE" in analysis_upper:
        if "ACTION: REVIEW" in analysis_upper:
            return "SAFE_REVIEW"
        return "NO_ACTION"

    # Every suggested reply requires explicit user approval.
    if "ACTION: REPLY" in analysis_upper:
        return "APPROVAL_REQUIRED"

    # Important emails can be reviewed without sending.
    if "PRIORITY: HIGH" in analysis_upper:
        return "SAFE_REVIEW"

    if "CATEGORY: IMPORTANT" in analysis_upper:
        return "SAFE_REVIEW"

    return "SAFE_REVIEW"

def show_email_permission_preview(sender, subject, analysis):

    action_level = get_email_action_level(analysis)

    print("\n" + "=" * 60)
    print("📧 JARVIS EMAIL DECISION")
    print("=" * 60)

    print("FROM:", sender)
    print("SUBJECT:", subject)

    print("\nAI ANALYSIS:")
    print(analysis)

    print("\n🔐 ACTION LEVEL:", action_level)

    if action_level == "APPROVAL_REQUIRED":

        print("\n⚠️ USER PERMISSION REQUIRED")
        print("JARVIS will NOT send a reply without your approval.")

    elif action_level == "NO_ACTION":

        print("\n🚫 NO ACTION REQUIRED")

    else:

        print("\n🟢 SAFE TO REVIEW")

    print("=" * 60)

def get_user_email_permission(analysis):

    action_level = get_email_action_level(analysis)

    if action_level != "APPROVAL_REQUIRED":
        return "NO_ACTION", ""

    # Extract the complete AI-generated reply, including paragraphs.
    suggested_reply = "NONE"

    marker = "SUGGESTED_REPLY:"
    position = analysis.upper().find(marker)

    if position != -1:
        suggested_reply = analysis[
            position + len(marker):
        ].strip()

    # Never approve an empty or missing reply.
    if not suggested_reply:
        suggested_reply = "NONE"

    print("\n⚠️ USER APPROVAL REQUIRED")
    print("JARVIS will NOT send anything automatically.")

    print("\n📧 SUGGESTED REPLY")
    print("-" * 60)
    print(suggested_reply)
    print("-" * 60)

    print("\nWhat would you like me to do?")
    print("[S] Send")
    print("[E] Edit")
    print("[C] Cancel")

    while True:

        choice = input("\nYour choice: ").strip().lower()

        if choice == "s":

            if not suggested_reply or suggested_reply.upper() == "NONE":

                print("⚠️ There is no suggested reply to send.")
                print("✏️ Please choose E to write a reply.")

                continue

            print("✅ Send approved.")

            return "SEND", suggested_reply

        elif choice == "e":

            print("\n✏️ Enter your edited reply.")

            edited_reply = input(
                "\nReply: "
            ).strip()

            if edited_reply:

                print("✅ Edited reply approved.")

                return "SEND", edited_reply

            print("⚠️ Reply cannot be empty.")

        elif choice == "c":

            print("❌ Cancelled.")

            return "CANCEL", ""

        else:

            print("Please choose S, E, or C.")

def analyze_unread_emails():

    emails = get_unread_emails()

    if not emails:
        return

    print("\n🤖 JARVIS EMAIL ANALYSIS")
    print("=" * 60)

    for i, email in enumerate(emails, 1):

        if is_automated_email(email):
            print(f"\n🚫 Email {i}: Automated email detected.")
            print("Sender:", get_header(email, "From"))
            print("Skipping AI reply and sending.")
            continue

        sender = get_header(
            email,
            "From"
        )

        subject = get_header(
            email,
            "Subject"
        )

        body = get_email_body(email)

        analysis = analyze_email(
            sender,
            subject,
            body
        )

        print("\n📧 EMAIL", i)
        print("FROM:", sender)
        print("SUBJECT:", subject)

        print("\nAI ANALYSIS:")
        print(analysis)

        reply_to = get_header(email, "Reply-To")

        actual_recipient = parseaddr(
            reply_to if reply_to else sender
        )[1].strip().lower()

        print("\n" + "=" * 60)
        print("🔐 RECIPIENT VERIFICATION")
        print("Original sender:", sender)
        print("Actual reply recipient:", actual_recipient)
        print("=" * 60)

        show_email_permission_preview(
            sender,
            subject,
            analysis
        )

        action, reply_text = get_user_email_permission(
            analysis
        )

        if action == "SEND":

            print("\nFINAL SEND CONFIRMATION")
            print("TO:", actual_recipient)
            print("SUBJECT:", subject)
            print("\nREPLY:")
            print(reply_text)

            confirmation = input(
                "\nType SEND to confirm, or anything else to cancel: "
            ).strip()

            if confirmation != "SEND":
                print("❌ Sending cancelled.")
                continue

            print("\n📤 Sending confirmed reply...")

            send_email(
                email,
                reply_text
            )

        elif action == "CANCEL":

            print("❌ No action taken.")

        print("=" * 60)
def analyze_job_emails():

    emails = get_unread_emails()

    if not emails:
        return

    print("\n💼 JARVIS JOB EMAILS")
    print("=" * 60)

    job_count = 0

    for email in emails:

        sender = get_header(
            email,
            "From"
        )

        subject = get_header(
            email,
            "Subject"
        )

        body = get_email_body(email)

        analysis = analyze_email(
            sender,
            subject,
            body
        )

        if "CATEGORY: JOB/HR" in analysis.upper():

            job_count += 1

            print("\n💼 JOB", job_count)
            print("FROM:", sender)
            print("SUBJECT:", subject)

            print("\nAI ANALYSIS:")
            print(analysis)

            print("=" * 60)

    if job_count == 0:

        speak("I couldn't find any job related unread emails.")

    else:

        speak(
            f"I found {job_count} job related emails."
        )
# ============================================================
# MICROPHONE
# ============================================================

def listen():
    recognizer = sr.Recognizer()

    recognizer.pause_threshold = 0.8
    recognizer.phrase_threshold = 0.3
    recognizer.non_speaking_duration = 0.5

    with sr.Microphone(device_index=0) as source:

        print("\n🎤 Listening...")

        try:
            audio = recognizer.listen(
                source,
                timeout=10,
                phrase_time_limit=10
            )

            print("🔄 Processing...")

            text = recognizer.recognize_google(audio)

            print("YOU:", text)

            return text.lower()

        except sr.WaitTimeoutError:
            print("⏱️ No speech detected.")
            return ""

        except sr.UnknownValueError:
            print("❌ I couldn't understand that.")
            return ""

        except sr.RequestError as e:
            print("❌ Speech recognition service error:", e)
            return ""

        except KeyboardInterrupt:
            print("\n🛑 Jarvis stopped.")
            raise


# ============================================================
# GMAIL LOGIN
# ============================================================

def get_gmail_service():

    creds = None

    # Load existing login
    if os.path.exists(TOKEN_FILE):

        creds = Credentials.from_authorized_user_file(
            TOKEN_FILE,
            SCOPES
        )

    # Refresh expired login
    if creds and creds.expired and creds.refresh_token:

        creds.refresh(Request())

    # Login if necessary
    if not creds or not creds.valid:

        print("\n🔐 Opening Google login...")

        flow = InstalledAppFlow.from_client_secrets_file(
            CREDENTIALS_FILE,
            SCOPES
        )

        creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, "w") as token:

            token.write(creds.to_json())

    service = build(
        "gmail",
        "v1",
        credentials=creds
    )

    return service


# ============================================================
# GET EMAIL BODY
# ============================================================

def get_email_body(message):

    payload = message.get("payload", {})

    # Simple email
    if "body" in payload:

        data = payload["body"].get("data")

        if data:

            return base64.urlsafe_b64decode(
                data
            ).decode(
                "utf-8",
                errors="ignore"
            )

    # Multipart email
    parts = payload.get("parts", [])

    for part in parts:

        if part.get("mimeType") == "text/plain":

            data = part.get("body", {}).get("data")

            if data:

                return base64.urlsafe_b64decode(
                    data
                ).decode(
                    "utf-8",
                    errors="ignore"
                )

    return "No readable message body."


# ============================================================
# GET HEADER
# ============================================================

def get_header(message, name):

    headers = message.get(
        "payload",
        {}
    ).get(
        "headers",
        []
    )

    for header in headers:

        if header["name"].lower() == name.lower():

            return header["value"]

    return ""

# ============================================================
# DETECT AUTOMATED EMAILS
# ============================================================

def is_automated_email(message):

    sender = parseaddr(
        get_header(message, "From")
    )[1].strip().lower()

    local_part = sender.split("@", 1)[0]

    blocked_names = [
        "noreply",
        "no-reply",
        "donotreply",
        "do-not-reply",
        "mailer-daemon",
        "postmaster",
    ]

    if any(name in local_part for name in blocked_names):
        return True

    auto_submitted = get_header(
        message, "Auto-Submitted"
    ).strip().lower()

    if auto_submitted and auto_submitted != "no":
        return True

    if get_header(message, "List-Unsubscribe"):
        return True

    if get_header(message, "List-Id"):
        return True

    precedence = get_header(
        message, "Precedence"
    ).strip().lower()

    if precedence in ["bulk", "junk", "list"]:
        return True

    return False

# ============================================================
# GET UNREAD EMAILS
# ============================================================

def get_unread_emails():

    service = get_gmail_service()

    results = service.users().messages().list(
        userId="me",
        q="in:inbox is:unread -in:sent -in:spam -in:trash",
        maxResults=5
    ).execute()

    messages = results.get("messages", [])

    if not messages:

        speak("You have no unread emails.")

        return []

    speak(
        f"You have {len(messages)} unread emails."
    )

    emails = []

    for item in messages:

        message = service.users().messages().get(
            userId="me",
            id=item["id"],
            format="full"
        ).execute()

        sender = get_header(
            message,
            "From"
        )

        subject = get_header(
            message,
            "Subject"
        )

        print("\n--------------------------------")
        print("FROM:", sender)
        print("SUBJECT:", subject)
        print("--------------------------------")

        print(
            get_email_body(message)[:500]
        )

        emails.append(message)

    return emails


# ============================================================
# READ LATEST EMAIL
# ============================================================

def read_latest_email():

    service = get_gmail_service()

    results = service.users().messages().list(
        userId="me",
        maxResults=1
    ).execute()

    messages = results.get("messages", [])

    if not messages:

        speak("Your inbox appears to be empty.")

        return None

    message = service.users().messages().get(
        userId="me",
        id=messages[0]["id"],
        format="full"
    ).execute()

    sender = get_header(
        message,
        "From"
    )

    subject = get_header(
        message,
        "Subject"
    )

    body = get_email_body(message)

    print("\n================================")
    print("FROM:", sender)
    print("SUBJECT:", subject)
    print("BODY:")
    print(body[:3000])
    print("================================")

    speak(
        f"Your latest email is from {sender}. "
        f"The subject is {subject}."
    )

    return message


# ============================================================
# SEARCH EMAILS
# ============================================================

def search_emails(query):

    service = get_gmail_service()

    results = service.users().messages().list(
        userId="me",
        q=query,
        maxResults=5
    ).execute()

    messages = results.get("messages", [])

    if not messages:

        speak("I couldn't find any matching emails.")

        return []

    speak(
        f"I found {len(messages)} matching emails."
    )

    emails = []

    for item in messages:

        message = service.users().messages().get(
            userId="me",
            id=item["id"],
            format="full"
        ).execute()

        sender = get_header(
            message,
            "From"
        )

        subject = get_header(
            message,
            "Subject"
        )

        print("\n--------------------------------")
        print("FROM:", sender)
        print("SUBJECT:", subject)
        print("--------------------------------")

        emails.append(message)

    return emails


# ============================================================
# CREATE REPLY
# ============================================================

def create_reply(original_message, reply_text):

    sender = get_header(
        original_message,
        "From"
    )

    subject = get_header(
        original_message,
        "Subject"
    )

    message_id = get_header(
        original_message,
        "Message-ID"
    )

    thread_id = original_message["threadId"]

    if not subject.lower().startswith("re:"):

        subject = "Re: " + subject

    email = MIMEText(
        reply_text
    )

    reply_to = get_header(original_message, "Reply-To")

    sender_address = parseaddr(sender)[1].strip().lower()

    recipient_header = reply_to if reply_to else sender

    addresses = getaddresses([recipient_header])

    if len(addresses) != 1:
        raise ValueError(
            "Reply blocked: expected exactly one recipient."
        )

    recipient = addresses[0][1].strip().lower()

    if (
        recipient.count("@") != 1
        or any(char.isspace() for char in recipient)
        or "," in recipient
        or "\n" in recipient_header
        or "\r" in recipient_header
    ):
        raise ValueError(
            "Reply blocked: malformed recipient address."
        )

    print(f"Original sender: {sender_address}")
    print(f"Proposed reply recipient: {recipient}")

    if reply_to and not recipient:
        raise ValueError("Reply blocked: invalid Reply-To address.")

    if not recipient or "@" not in recipient:
        raise ValueError("Reply blocked: invalid sender email address.")

    blocked_senders = [
        "noreply",
        "no-reply",
        "do-not-reply",
        "donotreply",
        "mailer-daemon",
        "postmaster",
    ]

    local_part = recipient.split("@", 1)[0]

    if any(blocked in local_part for blocked in blocked_senders):
        raise ValueError(
            f"Reply blocked: automated sender ({recipient})."
        )

    email["To"] = recipient
    email["Subject"] = subject

    if message_id:

        email["In-Reply-To"] = message_id
        email["References"] = message_id

    raw_message = base64.urlsafe_b64encode(
        email.as_bytes()
    ).decode()

    body = {
        "raw": raw_message,
        "threadId": thread_id
    }

    return body


# ============================================================
# SEND EMAIL
# ============================================================

def send_email(original_message, reply_text):

    service = get_gmail_service()

    body = create_reply(
        original_message,
        reply_text
    )

    service.users().messages().send(
        userId="me",
        body=body
    ).execute()

    speak("The email has been sent successfully.")

# ============================================================
# SEND NEW EMAIL
# ============================================================

def send_new_email(to_email, subject, message_text):

    service = get_gmail_service()

    email = MIMEText(message_text)

    email["To"] = to_email
    email["Subject"] = subject

    raw_message = base64.urlsafe_b64encode(
        email.as_bytes()
    ).decode()

    body = {
        "raw": raw_message
    }

    service.users().messages().send(
        userId="me",
        body=body
    ).execute()

    speak("The email has been sent successfully.")

# ============================================================
# SEND EMAIL WITH ATTACHMENT
# ============================================================

def send_email_with_attachment(
    to_email,
    subject,
    message_text,
    file_path
):

    service = get_gmail_service()

    if not os.path.exists(file_path):

        speak("I couldn't find that file.")

        return False

    email = EmailMessage()

    email["To"] = to_email
    email["Subject"] = subject

    email.set_content(message_text)

    mime_type, _ = mimetypes.guess_type(file_path)

    if mime_type is None:
        mime_type = "application/octet-stream"

    maintype, subtype = mime_type.split("/", 1)

    with open(file_path, "rb") as file:

        file_data = file.read()

    email.add_attachment(
        file_data,
        maintype=maintype,
        subtype=subtype,
        filename=os.path.basename(file_path)
    )

    raw_message = base64.urlsafe_b64encode(
        email.as_bytes()
    ).decode()

    body = {
        "raw": raw_message
    }

    service.users().messages().send(
        userId="me",
        body=body
    ).execute()

    speak(
        "The email with the attachment has been sent successfully."
    )

    return True


# ============================================================
# FIND CONTACT
# ============================================================

def find_contact(name):

    name = name.lower().strip()

    if name in CONTACTS:
        return CONTACTS[name]

    return None


# ============================================================
# FIND CONTACT IN GMAIL HISTORY
# ============================================================

def find_contact_in_gmail(name):

    service = get_gmail_service()

    name = name.lower().strip()

    results = service.users().messages().list(
        userId="me",
        q=name,
        maxResults=20
    ).execute()

    messages = results.get("messages", [])

    contacts = {}

    for item in messages:

        message = service.users().messages().get(
            userId="me",
            id=item["id"],
            format="metadata",
            metadataHeaders=["From"]
        ).execute()

        sender = get_header(
            message,
            "From"
        )

        display_name, email_address = parseaddr(sender)

        if not email_address:
            continue

        if (
            name in display_name.lower()
            or name in email_address.lower()
        ):

            contacts[email_address] = (
                display_name or email_address
            )

    return contacts


# ============================================================
# MAIN JARVIS
# ============================================================

def main():

    speak(
        "Hello. I am Jarvis. "
        "Your assistant is ready."
    )

    speak(
        "I can now work with your Gmail."
    )

    while True:

        command = listen()

        if command:
            command = command.replace("jarvis", "")
            command = command.replace("javed", "")
            command = command.strip().lower()
        # ============================================================
        # ANALYZE EMAILS
        # ============================================================

        if (
            command == "analyze my emails"
            or command == "analyse my emails"
            or command == "analyze my email"
            or command == "analyse my email"
            or command == "analyze"
            or command == "analyse"
            or "analyze my emails" in command
            or "analyse my emails" in command
            or "reply to all my emails" in command
            or "reply to all of my emails" in command
            or "reply to my emails" in command
            or "reply to my unread emails" in command
            or "prepare replies to my emails" in command
            or "prepare ai replies" in command
            or "read and analyze my emails" in command
            or "read and analyse my emails" in command
        ):

            speak("Analyzing your unread emails.")

            analyze_unread_emails()

            continue
                # ============================================================
        # JOB EMAILS
        # ============================================================

        if (
            command == "show me my job emails"
            or command == "show my job emails"
            or command == "check my job emails"
            or command == "check job emails"
            or command == "find job emails"
            or command == "show job emails"
            or command == "show me my jobs email"
            or command == "show me my job email"
            or command == "show my jobs email"
            or command == "show my job email"
            or command == "check my jobs email"
            or command == "check my job email"
        ):

            speak("Checking your job related emails.")

            analyze_job_emails()

            continue
        # ============================================================
        # SMART EMAIL COMMAND
        # ============================================================

        if (
            command.startswith("email ")
            and " and tell " in command
        ):

            email_part, message_part = command.split(
                " and tell ",
                1
            )

            smart_recipient = email_part.replace(
                "email ",
                "",
                1
            ).strip()

            smart_message = message_part.strip()

            if smart_message.startswith("him "):
                smart_message = smart_message[4:].strip()

            elif smart_message.startswith("her "):
                smart_message = smart_message[4:].strip()

            # Convert the command into the normal email workflow
            command = "send an email"

            # Store the extracted information
            smart_email_recipient = smart_recipient
            smart_email_message = smart_message

        else:

            smart_email_recipient = None
            smart_email_message = None

        if not command:
            continue

        # ----------------------------------------------------
        # STOP
        # ----------------------------------------------------

        if (
            "stop jarvis" in command
            or "jarvis stop" in command
            or command.strip() == "stop"
            or command.strip() == "jarvis"
        ):
            speak("Goodbye.")
            break

        # ----------------------------------------------------
        # HELLO
        # ----------------------------------------------------

        elif "hello" in command:

            speak(
                "Hello! How can I help you?"
            )

        # ----------------------------------------------------
        # HOW ARE YOU
        # ----------------------------------------------------

        elif "how are you" in command:

            speak(
                "I am doing great. Ready to work."
            )
        # ----------------------------------------------------
        # OPEN APPLICATION
        # ----------------------------------------------------

        elif command.startswith("open "):

            app_name = command[5:].strip()

            if app_name:

                speak("Opening " + app_name)

                try:

                    subprocess.run(
                        ["open", "-a", app_name]
                    )

                except Exception as e:

                    print("❌ Error opening app:", e)

                    speak(
                        "Sorry, I could not open "
                        + app_name
                    )

        # ----------------------------------------------------
        # OPEN WEBSITE
        # ----------------------------------------------------

        elif command in [
            "open youtube",
            "open gmail",
            "open google",
            "open chatgpt",
            "open github",
            "open linkedin"
        ]:

            websites = {
                "open youtube": "https://www.youtube.com",
                "open gmail": "https://mail.google.com",
                "open google": "https://www.google.com",
                "open chatgpt": "https://chatgpt.com",
                "open github": "https://github.com",
                "open linkedin": "https://www.linkedin.com"
            }

            url = websites[command]

            speak("Opening " + command.replace("open ", ""))

            webbrowser.open(url)

            # ----------------------------------------------------
        # UNREAD EMAILS
        # ----------------------------------------------------

        elif (
            "unread emails" in command
            or "unread email" in command
        ):

            get_unread_emails()

                 # ============================================================
        # SEND EMAIL WITH ATTACHMENT
        # ============================================================

        elif (
            "email with attachment" in command
            or "send email with attachment" in command
            or "send an email with attachment" in command
        ):

            speak(
                "What email address should I send it to?"
            )

            to_email = input(
                "\n📧 Recipient email: "
            ).strip()

            if not to_email:

                speak(
                    "No email address was provided."
                )

                continue

            speak(
                "What should the subject be?"
            )

            subject = input(
                "\n📝 Subject: "
            ).strip()

            if not subject:

                subject = "No subject"

            speak(
                "What should the email say?"
            )

            message_text = input(
                "\n✉️ Message: "
            ).strip()

            if not message_text:

                speak(
                    "No message was provided."
                )

                continue

            speak(
                "What is the full path of the file you want to attach?"
            )

            file_path = input(
                "\n📎 File path: "
            ).strip()

            if not os.path.exists(file_path):

                speak(
                    "I couldn't find that file."
                )

                continue

            # ----------------------------------------------------
            # EMAIL PREVIEW
            # ----------------------------------------------------

            print("\n")
            print("========================================")
            print("📎 EMAIL PREVIEW")
            print("========================================")
            print("TO:", to_email)
            print("SUBJECT:", subject)
            print("MESSAGE:")
            print(message_text)
            print("ATTACHMENT:", file_path)
            print("========================================")

            speak(
                "I have prepared the email with the attachment. "
                "Please check the preview."
            )

            speak(
                "Should I send it?"
            )

            # ----------------------------------------------------
            # CONFIRMATION
            # ----------------------------------------------------

            while True:

                confirmation = listen()

                if not confirmation:
                    continue

                confirmation = confirmation.strip().lower()

                if (
                    confirmation == "yes"
                    or confirmation == "yes send it"
                    or confirmation == "yes send"
                    or confirmation == "send it"
                    or confirmation == "send"
                    or confirmation.startswith("yes ")
                ):

                    speak(
                        "Okay. I will send the email with the attachment."
                    )

                    send_email_with_attachment(
                        to_email,
                        subject,
                        message_text,
                        file_path
                    )

                    break

                elif (
                    confirmation == "no"
                    or confirmation == "cancel"
                    or confirmation == "don't send"
                    or confirmation == "do not send"
                    or confirmation.startswith("no ")
                ):

                    speak(
                        "Okay. I will not send the email."
                    )

                    break

                else:

                    speak(
                        "Please say yes to send, or no to cancel."
                    )


            # ============================================================
# COMPOSE AND SEND NEW EMAIL
# ============================================================

        elif (
            "send an email" in command
            or "send email" in command
            or "compose an email" in command
            or "compose email" in command
            or command.startswith("email ")
        ):

            if smart_email_recipient:

                recipient = smart_email_recipient

                print(
                    "\n👤 Recipient:",
                    recipient
                )

            else:

                speak(
                    "Who should I send the email to?"
                )

                recipient = input(
                    "\n👤 Recipient name or email: "
                ).strip()

            if not recipient:

                speak(
                    "No recipient was provided."
                )

                continue

            # --------------------------------------------------------
            # CHECK SAVED CONTACTS FIRST
            # --------------------------------------------------------

            to_email = None

            if "@" in recipient:

                to_email = recipient

            else:

                to_email = find_contact(recipient)

            # --------------------------------------------------------
            # IF NOT FOUND, SEARCH GMAIL
            # --------------------------------------------------------

            if not to_email:

                speak(
                    f"I couldn't find {recipient} in your saved contacts."
                )

                speak(
                    "I will search your Gmail history."
                )

                gmail_contacts = find_contact_in_gmail(
                    recipient
                )

                if len(gmail_contacts) == 1:

                    to_email = list(
                        gmail_contacts.keys()
                    )[0]

                    print(
                        "\n📧 Contact found:"
                    )

                    print(
                        to_email
                    )

                    speak(
                        f"I found {to_email}."
                    )

                elif len(gmail_contacts) > 1:

                    print(
                        "\n========================================"
                    )

                    print(
                        "📧 MULTIPLE CONTACTS FOUND"
                    )

                    print(
                        "========================================"
                    )

                    contact_list = list(
                        gmail_contacts.items()
                    )

                    for index, (
                        email_address,
                        display_name
                    ) in enumerate(
                        contact_list,
                        start=1
                    ):

                        print(
                            f"{index}. {display_name} <{email_address}>"
                        )

                    print(
                        "========================================"
                    )

                    selection = input(
                        "\nChoose contact number: "
                    ).strip()

                    if not selection.isdigit():

                        speak(
                            "That was not a valid selection."
                        )

                        continue

                    selection = int(selection)

                    if (
                        selection < 1
                        or selection > len(contact_list)
                    ):

                        speak(
                            "That contact number is not valid."
                        )

                        continue

                    to_email = contact_list[
                        selection - 1
                    ][0]

                else:

                    speak(
                        f"I couldn't find an email address for {recipient}."
                    )

                    to_email = input(
                        "\n📧 Please enter the email address: "
                    ).strip()

                    if not to_email:

                        speak(
                            "No email address was provided."
                        )

                        continue

            # --------------------------------------------------------
            # SUBJECT
            # --------------------------------------------------------

            speak(
                "What should the subject be?"
            )

            subject = input(
                "\n📝 Subject: "
            ).strip()

            if not subject:

                subject = "No subject"

            # --------------------------------------------------------
            # MESSAGE
            # --------------------------------------------------------

            if smart_email_message:

                message_text = smart_email_message

                print(
                    "\n✉️ Message:",
                    message_text
                )

            else:

                speak(
                    "What should the email say?"
                )

                message_text = input(
                    "\n✉️ Message: "
                ).strip()

            if not message_text:

                speak(
                    "No message was provided."
                )

                continue

            # --------------------------------------------------------
            # PREVIEW
            # --------------------------------------------------------

            print("\n")
            print("========================================")
            print("📧 EMAIL PREVIEW")
            print("========================================")
            print("TO:", to_email)
            print("SUBJECT:", subject)
            print("MESSAGE:")
            print(message_text)
            print("========================================")

            speak(
                "I have prepared the email. "
                "Please check the preview."
            )

            # --------------------------------------------------------
            # CONFIRMATION
            # --------------------------------------------------------

            speak(
                "Should I send it?"
            )

            while True:

                confirmation = listen()

                if not confirmation:
                    continue

                confirmation = confirmation.strip().lower()

                if (
                    confirmation == "yes"
                    or confirmation == "yes send it"
                    or confirmation == "yes send"
                    or confirmation == "send it"
                    or confirmation == "send"
                    or confirmation.startswith("yes ")
                ):

                    speak(
                        "Okay. I will send the email."
                    )

                    send_new_email(
                        to_email,
                        subject,
                        message_text
                    )

                    break

                elif (
                    confirmation == "no"
                    or confirmation == "cancel"
                    or confirmation == "don't send"
                    or confirmation == "do not send"
                    or confirmation.startswith("no ")
                ):

                    speak(
                        "Okay. I will not send the email."
                    )

                    break

                else:

                    speak(
                        "Please say yes to send, or no to cancel."
                    )

       
                # ============================================================
                # SMART EMAIL SEARCH
                # ============================================================

        elif (
            "search email" in command
            or "search emails" in command
            or "find email" in command
            or "find emails" in command
        ):

            # SEARCH BY SENDER
            if " from " in command:

                query = command.split(" from ", 1)[1].strip()

                speak(
                    f"I will search for emails from {query}."
                )

                search_emails(f"from:{query}")


            # SEARCH BY SUBJECT
            elif (
                " subject " in command
                or "with subject " in command
            ):

                if "with subject " in command:

                    query = command.split(
                        "with subject ",
                        1
                    )[1].strip()

                else:

                    query = command.split(
                        " subject ",
                        1
                    )[1].strip()

                speak(
                    f"I will search for emails with the subject {query}."
                )

                search_emails(
                    f"subject:{query}"
                )


            # SEARCH BY TOPIC
            elif " about " in command:

                query = command.split(
                    " about ",
                    1
                )[1].strip()

                speak(
                    f"I will search for emails about {query}."
                )

                search_emails(query)


            # SEARCH BY GENERAL KEYWORD
            elif " for " in command:

                query = command.split(
                    " for ",
                    1
                )[1].strip()

                speak(
                    f"I will search for emails about {query}."
                )

                search_emails(query)


            # ASK WHAT TO SEARCH
            else:

                speak(
                    "What should I search for?"
                )

                query = listen()

                if query:

                    search_emails(query)

        # ----------------------------------------------------
        # REPLY TO A SPECIFIC EMAIL
        # ----------------------------------------------------

        elif (
            "reply to email from" in command
            or "reply to a email from" in command
            or "reply to an email from" in command
            or "reply to the email from" in command
            or "reply to email about" in command
            or "reply to a email about" in command
            or "reply to an email about" in command
            or "reply to the email about" in command
        ):

            speak("I will search for the email you mentioned.")

            if "from" in command:
                query = command.split("from", 1)[1].strip()
            else:
                query = command.split("about", 1)[1].strip()

            emails = search_emails(query)

            if emails:

                print("\n📧 Matching emails:")

                for index, email in enumerate(emails, start=1):

                    sender = get_header(email, "From")
                    subject = get_header(email, "Subject")

                    print(
                        f"{index}. FROM: {sender} | SUBJECT: {subject}"
                    )

                print("\n⌨️ Type the number of the email you want to reply to.")

                try:
                    choice = int(input("YOU: ").strip())

                    if 1 <= choice <= len(emails):

                        selected_email = emails[choice - 1]

                        sender = get_header(
                            selected_email,
                            "From"
                        )

                        subject = get_header(
                            selected_email,
                            "Subject"
                        )

                        speak(
                            f"You selected the email from {sender}, "
                            f"with subject {subject}."
                        )

                        print("\n📝 Type your reply below.")
                        print(
                            "Example: I will get back to you tomorrow."
                        )

                        reply_text = input("YOU: ").strip()

                        if reply_text:

                            print("\n================================")
                            print("📝 DRAFT REPLY")
                            print("================================")
                            print(reply_text)
                            print("================================")

                            speak("Here is the reply I prepared.")
                            speak(reply_text)

                            speak(
                                "Do you want me to send this email?"
                            )

                            print(
                                "\n🎤 Say YES to send it, "
                                "or NO to cancel."
                            )

                            while True:

                                confirmation = listen()

                                if (
                                    "yes" in confirmation
                                    or "send it" in confirmation
                                    or "send" in confirmation
                                ):

                                    speak(
                                        "Okay. I will send the email."
                                    )

                                    send_email(
                                        selected_email,
                                        reply_text
                                    )

                                    break

                                elif (
                                    "no" in confirmation
                                    or "cancel" in confirmation
                                    or "don't send" in confirmation
                                ):

                                    speak(
                                        "Okay. I will not send the email."
                                    )

                                    break

                                else:

                                    speak(
                                        "I didn't understand. "
                                        "Please say yes to send, "
                                        "or no to cancel."
                                    )

                    else:

                        speak("That email number is not valid.")

                except ValueError:

                    speak(
                        "I couldn't understand the email number."
                    )

        # ----------------------------------------------------
        # REPLY TO LATEST EMAIL
        # ----------------------------------------------------

        elif (
            "reply to latest email" in command
            or "reply to the latest email" in command
            or "reply to my latest email" in command
        ):

            speak("I will prepare a reply to your latest email.")

            latest = read_latest_email()

            if latest:

                speak("What would you like me to say in the reply?")

                print("\n📝 Speak your reply now...")
                print("Example: I will get back to you tomorrow.")

                print("\n⌨️ Type the reply you want to send.")
                reply_text = input("YOU: ").strip()

                # If voice recognition fails, allow typing the reply
                if not reply_text:
                    print("\n⚠️ I couldn't understand your voice.")
                    print("⌨️ You can type your reply instead.")
                    reply_text = input("YOU: ").strip()

                if reply_text:

                    print("\n================================")
                    print("📝 DRAFT REPLY")
                    print("================================")
                    print(reply_text)
                    print("================================")

                    speak("Here is the reply I prepared.")
                    speak(reply_text)

                    speak("Do you want me to send this email?")

                    print("\n🎤 Say YES to send it, or NO to cancel.")

                                        # Ask for confirmation until we receive YES or NO
                    while True:

                        confirmation = listen()

                        if (
                            "yes" in confirmation
                            or "send it" in confirmation
                            or "send" in confirmation
                        ):

                            speak("Okay. I will send the email.")
                            send_email(latest, reply_text)
                            break

                        elif (
                            "no" in confirmation
                            or "cancel" in confirmation
                            or "don't send" in confirmation
                        ):

                            speak("Okay. I will not send the email.")
                            break

                        else:

                            speak(
                                "I didn't understand. "
                                "Please say yes to send, or no to cancel."
                            )

                else:

                    speak(
                        "I didn't receive a reply message. "
                        "I will not send anything."
                    )

        # ----------------------------------------------------
        # LATEST EMAIL
        # ----------------------------------------------------

        elif (
            "latest email" in command
            or "last email" in command
            or "read my latest email" in command
        ):

            read_latest_email()
        # ----------------------------------------------------
        # DEFAULT — GEMINI AI
        # ----------------------------------------------------

        else:

            print("\n🤖 Asking Gemini...")

            ai_response = ask_ai(command)

            print(
                "\nJARVIS AI:",
                ai_response
            )

            speak(ai_response)


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    try:

        main()

    except KeyboardInterrupt:

        print(
            "\n🛑 Jarvis stopped."
        )