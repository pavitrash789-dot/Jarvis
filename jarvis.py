import os
import sys
from dotenv import load_dotenv
import time

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
import re
from html import unescape
from datetime import datetime
import json
import urllib.parse
import urllib.request

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
# EMAIL SENDING SAFETY
DRY_RUN = False
# Restrict live email sending during initial testing.
LIVE_TEST_MODE = True
ALLOWED_TEST_RECIPIENT = "pavitrash123123@gmail.com"


# ============================================================
# TEXT TO SPEECH
# ============================================================

try:
    engine = pyttsx3.init()
    engine.setProperty("rate", 170)
except Exception as e:
    print(f"⚠️ TTS engine initialization failed ({e}). Running in silent display mode.")
    engine = None


def speak(text, voice_text=None):
    print("\nJARVIS:", text)

    if os.getenv("JARVIS_SILENT") == "1" or "--silent" in sys.argv:
        return

    if engine:
        try:
            to_speak = str(voice_text) if voice_text is not None else str(text)

            # Clean text for voice output
            clean = to_speak.replace("*", "").replace("#", "").replace("`", "").replace("\n", " ")
            clean = re.sub(r"https?://\S+", "link", clean)
            clean = re.sub(r"\s+", " ", clean).strip()

            # Prevent voice synthesizer droning on long technical output
            if len(clean) > 280:
                split_point = clean.find(".", 150, 270)
                if split_point != -1:
                    clean = clean[:split_point + 1] + " Details are displayed on your screen, Sir."
                else:
                    clean = clean[:250] + "... Details displayed on screen, Sir."

            if clean:
                engine.say(clean)
                engine.runAndWait()
        except Exception as e:
            print(f"⚠️ Speech output error: {e}")

# ============================================================
# KNOWLEDGE & OFFLINE INTELLIGENCE ENGINE
# ============================================================

JARVIS_JOKES = [
    "Why do programmers prefer dark mode? Because light attracts bugs, Sir.",
    "Why did the developer go broke? Because he used up all his cache, Sir.",
    "There are 10 types of people in the world: those who understand binary, and those who don't.",
    "Why was the computer cold? It left its Windows open, Sir.",
    "A SQL query walks into a bar, walks up to two tables and asks: 'Can I join you?'",
    "Why do Java programmers wear glasses? Because they don't C#, Sir.",
]


def get_wikipedia_summary(query):
    """Retrieve concise, factual encyclopedic summary from Wikipedia API."""
    query = (query or "").strip()
    if not query:
        return None
    try:
        # Strip conversational question framing
        clean_topic = re.sub(
            r"^(who\s+is|who\s+was|what\s+is|what\s+are|what\s+was|tell\s+me\s+about|explain|search\s+wikipedia\s+for|wikipedia)\s+",
            "",
            query,
            flags=re.IGNORECASE,
        ).strip().rstrip("?.,!")

        if not clean_topic:
            clean_topic = query.strip("?.,!")

        encoded = urllib.parse.quote(clean_topic.replace(" ", "_"))
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{encoded}"
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "JARVIS-Assistant/2.0 (macOS; personal-assistant)"}
        )
        with urllib.request.urlopen(req, timeout=4) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            extract = data.get("extract")
            if extract and len(extract) > 25:
                title = data.get("title", clean_topic)
                return f"According to Wikipedia: {extract}"
    except Exception:
        pass
    return None


def get_duckduckgo_answer(query):
    """Query DuckDuckGo Instant Answer API for fast facts and definitions."""
    query = (query or "").strip()
    if not query:
        return None
    try:
        encoded = urllib.parse.quote(query)
        url = f"https://api.duckduckgo.com/?q={encoded}&format=json&no_html=1&skip_disambig=1"
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "JARVIS-Assistant/2.0"}
        )
        with urllib.request.urlopen(req, timeout=4) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            answer = data.get("Answer")
            if answer:
                return f"Here is what I found, Sir: {answer}"
            abstract = data.get("AbstractText")
            if abstract and len(abstract) > 25:
                return f"According to DuckDuckGo: {abstract}"
    except Exception:
        pass
    return None


def get_offline_knowledge(query):
    """Provide immediate intelligent answers when offline or API is unavailable."""
    q = (query or "").lower().strip().rstrip("?.!")

    # Check math calculation first
    math_res = safe_calculate(query)
    if math_res:
        return math_res

    # Personal identity & JARVIS persona
    if any(p in q for p in ["who are you", "what are you", "your name", "who is jarvis", "what is jarvis"]):
        return "I am JARVIS (Just A Rather Very Intelligent System), the personal AI assistant for Harshil Sharma. I can answer questions, control your Mac, manage emails, track jobs, calculate math, take notes, and automate your workflows."

    if any(p in q for p in ["who made you", "who created you", "who is your creator", "who built you"]):
        return "I was created as an intelligent autonomous assistant for Harshil Sharma, running right here on macOS."

    if any(p in q for p in ["who is harshil", "tell me about harshil", "who am i", "harshil sharma"]):
        return show_career_profile()

    if any(p in q for p in ["tell me a joke", "make me laugh", "say something funny", "a joke"]):
        import random
        return random.choice(JARVIS_JOKES)

    if any(p in q for p in ["thank you", "thanks", "good job", "well done"]):
        return "Always at your service, Sir. Glad I could assist."

    # Free encyclopedic query via Wikipedia
    wiki_res = get_wikipedia_summary(query)
    if wiki_res:
        return wiki_res

    # Fast Instant Answer via DuckDuckGo
    ddg_res = get_duckduckgo_answer(query)
    if ddg_res:
        return ddg_res

    return None


# ============================================================
# GEMINI AI & CONVERSATIONAL MEMORY
# ============================================================

FALLBACK_MODELS = [
    "gemini-2.0-flash",
    "gemini-2.5-flash",
    "gemini-1.5-flash",
    "gemini-flash-lite-latest",
]

CONVERSATION_HISTORY = []
MAX_HISTORY = 10


def ask_ai(prompt, is_email=False):
    api_key = os.getenv("GEMINI_API_KEY")

    is_email_prompt = (
        is_email
        or "Analyze the email" in prompt
        or "SUGGESTED_REPLY:" in prompt
        or "CATEGORY:" in prompt
    )

    if not api_key:
        if is_email_prompt:
            return """CATEGORY: OTHER
PRIORITY: MEDIUM
SUMMARY: GEMINI_API_KEY is not configured in .env.
ACTION: REVIEW
SUGGESTED_REPLY: NONE"""
        offline_res = get_offline_knowledge(prompt)
        if offline_res:
            return offline_res
        return "I'm sorry, Sir. GEMINI_API_KEY is not configured in your .env file, and no local answer was found."

    client = None
    try:
        client = genai.Client(api_key=api_key)
    except Exception as e:
        print(f"⚠️ GenAI Client initialization failed: {e}")

    contents = prompt
    system_instruction = None

    if not is_email_prompt:
        now_str = datetime.now().strftime("%I:%M %p on %A, %B %d, %Y")
        system_instruction = f"""You are JARVIS (Just A Rather Very Intelligent System), the personal AI assistant for Harshil Sharma.

Real-world Context:
- Current Date and Time: {now_str}
- User: Harshil Sharma (B.Com graduate with 1 year experience, skilled in Python, SQL, Financial Analysis, Full-Stack Development, Excel, Power BI).
- System: macOS (Darwin).
- Workspace: /Users/harshilsharma/jarvis.

Capabilities & Local Tools:
When Harshil asks you to DO something, you can execute an action by prefixing your response with an action tag:
- [[ACTION: open_website("https://...")]]
- [[ACTION: open_app("AppName")]]
- [[ACTION: close_app("AppName")]]
- [[ACTION: search_google("query")]]
- [[ACTION: search_youtube("query")]]
- [[ACTION: search_wikipedia("query")]]
- [[ACTION: set_volume("up"|"down"|"mute"|"unmute"|0-100)]]
- [[ACTION: get_battery()]]
- [[ACTION: get_ip()]]
- [[ACTION: get_disk_space()]]
- [[ACTION: get_memory()]]
- [[ACTION: get_system_info()]]
- [[ACTION: take_screenshot()]]
- [[ACTION: lock_screen()]]
- [[ACTION: empty_trash()]]
- [[ACTION: get_weather("city")]]
- [[ACTION: take_note("note text")]]
- [[ACTION: get_notes()]]
- [[ACTION: delete_note(id)]]
- [[ACTION: clear_notes()]]
- [[ACTION: set_reminder("reminder text")]]
- [[ACTION: get_reminders()]]
- [[ACTION: delete_reminder(id)]]
- [[ACTION: clear_reminders()]]
- [[ACTION: calculate("expression")]]
- [[ACTION: get_time()]]
- [[ACTION: search_jobs()]]
- [[ACTION: show_top_jobs()]]
- [[ACTION: open_dashboard()]]
- [[ACTION: show_career_profile()]]
- [[ACTION: read_latest_email()]]
- [[ACTION: get_unread_emails()]]
- [[ACTION: run_command("command")]]

Instructions:
1. If the user asks a question, answer it intelligently, accurately, and courteously like Tony Stark's JARVIS.
2. If the user asks you to perform an action, output the matching [[ACTION: ...]] tag followed by your natural spoken response.
3. Be respectful, witty, and concise. Address Harshil as 'Sir' or 'Harshil'.
4. Keep the spoken response natural (1-3 sentences suitable for speech) followed by any detailed breakdown or code.
"""
        if CONVERSATION_HISTORY:
            history_context = "\nRecent Conversation History:\n"
            for turn in CONVERSATION_HISTORY[-MAX_HISTORY:]:
                history_context += f"{turn['role'].upper()}: {turn['text']}\n"
            contents = f"{history_context}\nUSER: {prompt}\nJARVIS:"

    if client:
        for model_name in FALLBACK_MODELS:
            for attempt in range(1, 3):
                try:
                    kwargs = {"model": model_name, "contents": contents}
                    if system_instruction:
                        kwargs["config"] = {"system_instruction": system_instruction}

                    response = client.models.generate_content(**kwargs)

                    if response.text and response.text.strip():
                        res_text = response.text.strip()
                        if not is_email_prompt:
                            CONVERSATION_HISTORY.append({"role": "user", "text": prompt})
                            CONVERSATION_HISTORY.append({"role": "model", "text": res_text})
                            if len(CONVERSATION_HISTORY) > MAX_HISTORY * 2:
                                del CONVERSATION_HISTORY[:2]
                        return res_text

                    break
                except Exception as e:
                    error_text = str(e)
                    # If model not found or forbidden, switch to next model immediately
                    if "404" in error_text or "not found" in error_text.lower():
                        break
                    if attempt == 2:
                        break
                    time.sleep(1)

    # If Gemini failed or is unavailable, use knowledge engine fallback
    if not is_email_prompt:
        offline_res = get_offline_knowledge(prompt)
        if offline_res:
            return offline_res

    if is_email_prompt:
        return """CATEGORY: OTHER
PRIORITY: MEDIUM
SUMMARY: AI analysis is temporarily unavailable.
ACTION: REVIEW
SUGGESTED_REPLY: NONE"""

    return "I'm sorry, Sir. I am currently unable to reach Gemini AI or offline knowledge sources. Please check your internet connection or API key."


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

8. CRITICAL — NEVER MAKE DECISIONS FOR THE USER:
   - Never claim the user is available for an interview or meeting.
   - Never confirm attendance, accept an offer, agree to a salary,
     promise payment, or make any commitment without explicit
     confirmation from the user.
   - If someone asks the user to confirm availability, draft a
     response acknowledging the invitation and saying the user
     will check their schedule and confirm shortly.
   - Do not invent dates, qualifications, personal details,
     preferences, or decisions.
   - A suggested reply is only a draft, not authorization to
     make commitments on the user's behalf.

9. Write natural, human-sounding emails with proper paragraphs.
   Avoid robotic wording. Keep replies polite, concise, and
   relevant to the original email.

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

        try:
            preview_body = create_reply(
                email,
                "Recipient verification preview"
            )

            from email import message_from_bytes

            preview_message = message_from_bytes(
                base64.urlsafe_b64decode(preview_body["raw"])
            )

            actual_recipient = preview_message["To"]

        except (ValueError, KeyError, TypeError) as error:
            print("🚫 Recipient validation failed:", error)
            print("Skipping this email.")
            continue

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
# MICROPHONE & INPUT
# ============================================================

def listen():
    if os.getenv("JARVIS_INPUT", "").lower() in ("keyboard", "text") or "--keyboard" in sys.argv or "--text" in sys.argv:
        try:
            typed = input("\n⌨️ YOU (type command): ").strip()
            return typed.lower()
        except (EOFError, KeyboardInterrupt):
            print("\n🛑 Jarvis stopped.")
            raise

    recognizer = sr.Recognizer()

    recognizer.pause_threshold = 0.8
    recognizer.phrase_threshold = 0.3
    recognizer.non_speaking_duration = 0.5

    try:
        # Prefer default input device; fall back to device 0 if default fails
        try:
            mic = sr.Microphone()
        except Exception:
            mic = sr.Microphone(device_index=0)

        with mic as source:
            print("\n🎤 Listening... (or press Ctrl+C to cancel)")

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

    except (KeyboardInterrupt, SystemExit):
        print("\n🛑 Jarvis stopped.")
        raise
    except Exception as e:
        print(f"⚠️ Microphone unavailable ({e}). Falling back to keyboard input.")
        try:
            typed = input("\n⌨️ YOU (type command): ").strip()
            return typed.lower()
        except (EOFError, KeyboardInterrupt):
            print("\n🛑 Jarvis stopped.")
            raise


# ============================================================
# GMAIL LOGIN
# ============================================================

def get_gmail_service():

    creds = None

    # Load existing login
    if os.path.exists(TOKEN_FILE):
        try:
            creds = Credentials.from_authorized_user_file(
                TOKEN_FILE,
                SCOPES
            )
        except Exception as e:
            print(f"⚠️ Failed to load existing token ({e}). Re-authenticating...")
            creds = None

    # Refresh expired login
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            # Save refreshed credentials back to disk
            with open(TOKEN_FILE, "w") as token:
                token.write(creds.to_json())
        except Exception as e:
            print(f"⚠️ Token refresh failed ({e}). Re-authenticating...")
            creds = None

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

    def decode_content(part):
        data = part.get("body", {}).get("data")

        if not data:
            return ""

        try:
            decoded = base64.urlsafe_b64decode(
                data + "=" * (-len(data) % 4)
            )

            return decoded.decode("utf-8", errors="replace")

        except Exception:
            return ""

    def html_to_text(html):

        # Remove scripts, styles and hidden document metadata.
        html = re.sub(
            r"(?is)<(script|style|head|noscript)\b[^>]*>.*?</\1\s*>",
            " ",
            html
        )

        # Preserve useful line breaks.
        html = re.sub(
            r"(?i)<br\s*/?>|</(?:p|div|tr|li|h[1-6])\s*>",
            "\n",
            html
        )

        # Remove remaining HTML tags.
        html = re.sub(r"(?s)<[^>]+>", " ", html)

        # Decode HTML entities.
        html = unescape(html)

        # Clean whitespace.
        html = re.sub(r"[ \t]+", " ", html)
        html = re.sub(r" *\n *", "\n", html)
        html = re.sub(r"\n{3,}", "\n\n", html)

        return html.strip()

    def extract_text(part):

        mime_type = part.get("mimeType", "").lower()

        # Prefer plain text.
        if mime_type == "text/plain":
            return decode_content(part).strip()

        # Search nested multipart sections.
        for child in part.get("parts", []):
            if child.get("mimeType", "").lower() == "text/plain":
                result = extract_text(child)
                if result:
                    return result

        for child in part.get("parts", []):
            result = extract_text(child)
            if result:
                return result

        # Fall back to HTML when plain text is unavailable.
        if mime_type == "text/html":
            return html_to_text(decode_content(part))

        return ""

    body = extract_text(message.get("payload", {}))

    return body if body.strip() else "No readable message body."

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
        maxResults=20
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

    # Construct and validate the actual outgoing message first.
    body = create_reply(original_message, reply_text)

    # Read the recipient from the actual outgoing Gmail message.
    from email import message_from_bytes

    outgoing = message_from_bytes(
        base64.urlsafe_b64decode(body["raw"])
    )

    actual_recipient = outgoing["To"]

    # Restrict live sending to the designated test address.
    if LIVE_TEST_MODE:
        if actual_recipient != ALLOWED_TEST_RECIPIENT:
            print("🚫 LIVE TEST SAFETY: Sending blocked.")
            print("Recipient:", actual_recipient)
            print("Only permitted recipient:", ALLOWED_TEST_RECIPIENT)
            return

    if DRY_RUN:
        print("\n" + "=" * 60)
        print("🧪 JARVIS EMAIL DRY RUN")
        print("No real email will be sent.")
        print("Validated recipient and reply payload created.")
        print("REPLY:")
        print(reply_text)
        print("=" * 60)
        return

    # Final live-test recipient restriction.
    if LIVE_TEST_MODE and actual_recipient != ALLOWED_TEST_RECIPIENT:
        raise ValueError("LIVE SEND BLOCKED: Unauthorized recipient.")

    service = get_gmail_service()

    result = service.users().messages().send(
        userId="me",
        body=body
    ).execute()

    print("✅ Gmail accepted the reply.")
    print("Message ID:", result.get("id"))

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
# SYSTEM CONTROLS (macOS)
# ============================================================

def get_current_time_date():
    now = datetime.now()
    time_str = now.strftime("%I:%M %p")
    date_str = now.strftime("%A, %B %d, %Y")
    return f"The current time is {time_str} on {date_str}."


def system_volume(action="get", level=None):
    try:
        act = str(action).lower().strip()
        if act in ("up", "louder", "increase", "turn up"):
            res = subprocess.run(
                ["osascript", "-e", "output volume of (get volume settings)"],
                capture_output=True,
                text=True
            )
            curr = int(res.stdout.strip()) if res.stdout.strip().isdigit() else 50
            new_vol = min(100, curr + 10)
            subprocess.run(["osascript", "-e", f"set volume output volume {new_vol}"])
            return f"Volume increased to {new_vol}%."
        elif act in ("down", "quieter", "decrease", "lower", "turn down"):
            res = subprocess.run(
                ["osascript", "-e", "output volume of (get volume settings)"],
                capture_output=True,
                text=True
            )
            curr = int(res.stdout.strip()) if res.stdout.strip().isdigit() else 50
            new_vol = max(0, curr - 10)
            subprocess.run(["osascript", "-e", f"set volume output volume {new_vol}"])
            return f"Volume decreased to {new_vol}%."
        elif act in ("mute", "silence"):
            subprocess.run(["osascript", "-e", "set volume output muted true"])
            return "Audio is now muted."
        elif act == "unmute":
            subprocess.run(["osascript", "-e", "set volume output muted false"])
            return "Audio unmuted."
        elif act in ("max", "maximum", "full", "100"):
            subprocess.run(["osascript", "-e", "set volume output volume 100"])
            return "Volume set to maximum (100%)."
        elif act in ("half", "medium", "50"):
            subprocess.run(["osascript", "-e", "set volume output volume 50"])
            return "Volume set to 50%."
        elif act in ("min", "minimum", "10"):
            subprocess.run(["osascript", "-e", "set volume output volume 10"])
            return "Volume set to minimum (10%)."
        elif act == "set" or level is not None or re.search(r"\d+", act):
            val = level if level is not None else act
            match = re.search(r"\d+", str(val))
            if match:
                lvl = max(0, min(100, int(match.group(0))))
                subprocess.run(["osascript", "-e", f"set volume output volume {lvl}"])
                return f"Volume set to {lvl}%."
            return system_volume("get")
        else:
            res = subprocess.run(
                ["osascript", "-e", "output volume of (get volume settings)"],
                capture_output=True,
                text=True
            )
            vol = res.stdout.strip()
            return f"Current volume level is {vol}%."
    except Exception as e:
        return f"Could not adjust volume: {e}"


def get_battery_status():
    try:
        res = subprocess.run(["pmset", "-g", "batt"], capture_output=True, text=True)
        out = res.stdout
        pct_match = re.search(r"(\d+)%", out)
        state_match = re.search(r";\s*(discharging|charging|charged|finishing charge|AC attached)", out, re.IGNORECASE)
        if pct_match:
            pct = pct_match.group(1)
            state = state_match.group(1) if state_match else "on battery"
            return f"Battery is at {pct}%, currently {state}."
        if "ac power" in out.lower():
            return "Running on AC wall power (desktop Mac or fully powered without battery drain)."
        return f"Battery status: {out.strip()}"
    except Exception as e:
        return f"Unable to read battery status: {e}"


def get_ip_address():
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(1)
        try:
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
        except Exception:
            local_ip = "127.0.0.1"
        finally:
            s.close()

        public_ip = "Offline / Unknown"
        try:
            req = urllib.request.Request("https://api.ipify.org?format=json", headers={"User-Agent": "curl/7.68.0"})
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read().decode())
                public_ip = data.get("ip", "Unknown")
        except Exception:
            pass

        return f"Local network IP: {local_ip} | Public IP: {public_ip}"
    except Exception as e:
        return f"Could not read IP address: {e}"


def get_disk_space():
    try:
        import shutil
        total, used, free = shutil.disk_usage("/")
        gb = 1024 ** 3
        total_gb = round(total / gb, 1)
        used_gb = round(used / gb, 1)
        free_gb = round(free / gb, 1)
        pct = round((used / total) * 100, 1)
        return f"Disk storage: {free_gb} GB free of {total_gb} GB total ({pct}% used)."
    except Exception as e:
        return f"Could not read disk space: {e}"


def get_memory_status():
    try:
        res = subprocess.run(["vm_stat"], capture_output=True, text=True)
        if res.returncode == 0:
            lines = res.stdout.split("\n")
            stats = {}
            for line in lines:
                parts = line.split(":")
                if len(parts) == 2:
                    val = re.search(r"\d+", parts[1])
                    if val:
                        stats[parts[0].strip()] = int(val.group(0))
            page_size = 4096
            mem_res = subprocess.run(["sysctl", "-n", "hw.memsize"], capture_output=True, text=True)
            total_ram = int(mem_res.stdout.strip()) if mem_res.stdout.strip().isdigit() else (16 * 1024**3)
            free_pages = stats.get("Pages free", 0) + stats.get("Pages speculative", 0)
            free_ram = free_pages * page_size
            used_ram = max(0, total_ram - free_ram)
            gb = 1024 ** 3
            return f"RAM usage: {round(used_ram / gb, 1)} GB used of {round(total_ram / gb, 1)} GB total."
        return "Memory statistics currently unavailable."
    except Exception as e:
        return f"Could not read memory: {e}"


def get_system_info():
    try:
        import platform
        os_version = platform.mac_ver()[0] or platform.platform()
        machine = platform.machine()
        processor = platform.processor() or machine
        return f"System: macOS {os_version} on {machine} architecture ({processor}). User: Harshil Sharma."
    except Exception as e:
        return f"Could not read system info: {e}"


def empty_trash():
    try:
        script = 'tell application "Finder" to empty trash'
        subprocess.run(["osascript", "-e", script], capture_output=True)
        return "macOS Trash has been emptied, Sir."
    except Exception as e:
        return f"Could not empty trash: {e}"


def take_screenshot():
    try:
        desktop = os.path.expanduser("~/Desktop")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"Screenshot_{timestamp}.png"
        filepath = os.path.join(desktop, filename)
        subprocess.run(["screencapture", "-x", filepath], check=True)
        return f"Screenshot saved to your Desktop as {filename}."
    except Exception as e:
        return f"Failed to capture screenshot: {e}"


def lock_screen():
    try:
        subprocess.run(["pmset", "displaysleepnow"])
        return "Screen locked and display set to sleep."
    except Exception as e:
        return f"Failed to lock screen: {e}"


# ============================================================
# WEBSITES & APPLICATION CONTROL
# ============================================================

APP_ALIASES = {
    "vscode": "Visual Studio Code",
    "vs code": "Visual Studio Code",
    "code": "Visual Studio Code",
    "chrome": "Google Chrome",
    "google chrome": "Google Chrome",
    "safari": "Safari",
    "terminal": "Terminal",
    "iterm": "iTerm",
    "iterm2": "iTerm2",
    "calculator": "Calculator",
    "calc": "Calculator",
    "notes": "Notes",
    "apple notes": "Notes",
    "calendar": "Calendar",
    "music": "Music",
    "apple music": "Music",
    "spotify": "Spotify",
    "photos": "Photos",
    "settings": "System Settings",
    "system settings": "System Settings",
    "system preferences": "System Settings",
    "preferences": "System Settings",
    "finder": "Finder",
    "messages": "Messages",
    "imessage": "Messages",
    "mail": "Mail",
    "reminders": "Reminders",
    "slack": "Slack",
    "discord": "Discord",
    "zoom": "zoom.us",
    "sublime": "Sublime Text",
    "sublime text": "Sublime Text",
}

POPULAR_WEBSITES = {
    "youtube": "https://www.youtube.com",
    "gmail": "https://mail.google.com",
    "google": "https://www.google.com",
    "chatgpt": "https://chatgpt.com",
    "claude": "https://claude.ai",
    "github": "https://github.com",
    "linkedin": "https://www.linkedin.com",
    "reddit": "https://www.reddit.com",
    "twitter": "https://x.com",
    "x": "https://x.com",
    "netflix": "https://www.netflix.com",
    "amazon": "https://www.amazon.com",
    "spotify": "https://open.spotify.com",
    "whatsapp": "https://web.whatsapp.com",
    "canva": "https://www.canva.com",
    "notion": "https://www.notion.so",
    "stackoverflow": "https://stackoverflow.com",
    "leetcode": "https://leetcode.com",
    "wikipedia": "https://www.wikipedia.org",
    "twitch": "https://www.twitch.tv",
    "coursera": "https://www.coursera.org",
    "maps": "https://maps.google.com",
    "google maps": "https://maps.google.com",
}


def open_target(target):
    target = target.strip()
    target_clean = target.lower()

    if target_clean in ("dashboard", "job dashboard"):
        return open_dashboard()

    # Check popular websites first
    if target_clean in POPULAR_WEBSITES:
        url = POPULAR_WEBSITES[target_clean]
        webbrowser.open(url)
        return f"Opening {target} in your browser."

    # Check app aliases next
    if target_clean in APP_ALIASES:
        canonical_app = APP_ALIASES[target_clean]
        try:
            res = subprocess.run(["open", "-a", canonical_app], capture_output=True, text=True)
            if res.returncode == 0:
                return f"Opening application {canonical_app}."
        except Exception:
            pass

    # Check URLs or web domains
    if (
        target_clean.startswith("http://")
        or target_clean.startswith("https://")
        or re.search(r"^[a-zA-Z0-9-]+\.(com|org|net|io|in|co|ai|edu|gov|dev|me)(/.*)?$", target_clean)
    ):
        url = target if target.startswith("http") else f"https://{target}"
        webbrowser.open(url)
        return f"Opening {target} in your browser."

    # Try opening as Mac application
    try:
        res = subprocess.run(["open", "-a", target], capture_output=True, text=True)
        if res.returncode == 0:
            return f"Opening application {target}."
    except Exception:
        pass

    # Fallback to browser search / domain
    try:
        url = f"https://www.{target_clean.replace(' ', '')}.com"
        webbrowser.open(url)
        return f"Opening {url} in your browser."
    except Exception as e:
        return f"Sorry, I could not open {target}: {e}"


def close_app(app_name):
    app_name = app_name.strip()
    canonical_app = APP_ALIASES.get(app_name.lower(), app_name)
    try:
        subprocess.run(["osascript", "-e", f'tell application "{canonical_app}" to quit'], capture_output=True)
        return f"Closed application {canonical_app}."
    except Exception as e:
        return f"Could not close {app_name}: {e}"


# ============================================================
# SEARCH & INFORMATION
# ============================================================

def search_google(query):
    query = query.strip()
    url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
    webbrowser.open(url)
    return f"Searching Google for '{query}'."


def search_youtube(query):
    query = query.strip()
    url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}"
    webbrowser.open(url)
    return f"Searching YouTube for '{query}'."


def search_wikipedia(query):
    query = query.strip()
    url = f"https://en.wikipedia.org/wiki/Special:Search?search={urllib.parse.quote(query)}"
    webbrowser.open(url)
    return f"Searching Wikipedia for '{query}'."


def get_weather(city=None):
    try:
        location = city.strip() if city else ""
        url = f"https://wttr.in/{urllib.parse.quote(location)}?format=3"
        req = urllib.request.Request(url, headers={"User-Agent": "curl/7.68.0"})
        with urllib.request.urlopen(req, timeout=5) as response:
            weather_text = response.read().decode("utf-8").strip()
            # Validate output is not HTML error page
            if weather_text and not weather_text.startswith("<") and "html" not in weather_text.lower():
                return f"Current weather report: {weather_text}"
    except Exception:
        pass

    if city:
        return f"I couldn't fetch live weather for {city}. Please check your weather app."
    return "I couldn't reach the live weather service at this moment."


# ============================================================
# NOTES & REMINDERS
# ============================================================

NOTES_FILE = os.path.join(BASE_DIR, "notes.json")
REMINDERS_FILE = os.path.join(BASE_DIR, "reminders.json")


def manage_notes(action="show", text=None):
    notes = []
    if os.path.exists(NOTES_FILE):
        try:
            with open(NOTES_FILE, "r", encoding="utf-8") as f:
                notes = json.load(f)
        except Exception:
            notes = []

    act = (action or "show").lower().strip()

    if act == "add" and text:
        note_entry = {
            "id": len(notes) + 1,
            "timestamp": datetime.now().strftime("%Y-%m-%d %I:%M %p"),
            "text": text.strip()
        }
        notes.append(note_entry)
        with open(NOTES_FILE, "w", encoding="utf-8") as f:
            json.dump(notes, f, indent=4)
        return f"Note recorded: '{text.strip()}'"

    elif act == "delete" and text:
        note_id = None
        digits = re.search(r"\d+", str(text))
        if digits:
            note_id = int(digits.group(0))
        if note_id:
            filtered = [n for n in notes if n.get("id") != note_id]
            if len(filtered) < len(notes):
                for idx, n in enumerate(filtered, 1):
                    n["id"] = idx
                with open(NOTES_FILE, "w", encoding="utf-8") as f:
                    json.dump(filtered, f, indent=4)
                return f"Note #{note_id} has been deleted."
            return f"Note #{note_id} was not found."
        return "Please specify the note number to delete."

    elif act == "search" and text:
        q = str(text).lower().strip()
        matched = [n for n in notes if q in n.get("text", "").lower()]
        if not matched:
            return f"No notes found matching '{text}'."
        print(f"\n📝 SEARCH RESULTS FOR '{text}':")
        print("=" * 50)
        for n in matched:
            print(f"{n['id']}. [{n['timestamp']}] {n['text']}")
        print("=" * 50)
        return f"Found {len(matched)} matching note{'s' if len(matched) > 1 else ''}. The first is: {matched[0]['text']}"

    elif act == "clear":
        with open(NOTES_FILE, "w", encoding="utf-8") as f:
            json.dump([], f, indent=4)
        return "All saved notes have been cleared, Sir."

    else:
        if not notes:
            return "You currently have no saved notes."
        print("\n📝 YOUR SAVED NOTES:")
        print("=" * 50)
        for n in notes:
            print(f"{n['id']}. [{n['timestamp']}] {n['text']}")
        print("=" * 50)
        return f"You have {len(notes)} note{'s' if len(notes) > 1 else ''}. The latest is: {notes[-1]['text']}"


def manage_reminders(action="show", text=None):
    reminders = []
    if os.path.exists(REMINDERS_FILE):
        try:
            with open(REMINDERS_FILE, "r", encoding="utf-8") as f:
                reminders = json.load(f)
        except Exception:
            reminders = []

    act = (action or "show").lower().strip()

    if act == "add" and text:
        entry = {
            "id": len(reminders) + 1,
            "timestamp": datetime.now().strftime("%Y-%m-%d %I:%M %p"),
            "text": text.strip()
        }
        reminders.append(entry)
        with open(REMINDERS_FILE, "w", encoding="utf-8") as f:
            json.dump(reminders, f, indent=4)
        return f"Reminder set: '{text.strip()}'"

    elif act == "delete" and text:
        reminder_id = None
        digits = re.search(r"\d+", str(text))
        if digits:
            reminder_id = int(digits.group(0))
        if reminder_id:
            filtered = [r for r in reminders if r.get("id") != reminder_id]
            if len(filtered) < len(reminders):
                for idx, r in enumerate(filtered, 1):
                    r["id"] = idx
                with open(REMINDERS_FILE, "w", encoding="utf-8") as f:
                    json.dump(filtered, f, indent=4)
                return f"Reminder #{reminder_id} has been deleted."
            return f"Reminder #{reminder_id} was not found."
        return "Please specify the reminder number to delete."

    elif act == "search" and text:
        q = str(text).lower().strip()
        matched = [r for r in reminders if q in r.get("text", "").lower()]
        if not matched:
            return f"No reminders found matching '{text}'."
        print(f"\n⏰ SEARCH RESULTS FOR '{text}':")
        print("=" * 50)
        for r in matched:
            print(f"{r['id']}. [{r['timestamp']}] {r['text']}")
        print("=" * 50)
        return f"Found {len(matched)} matching reminder{'s' if len(matched) > 1 else ''}. The first is: {matched[0]['text']}"

    elif act == "clear":
        with open(REMINDERS_FILE, "w", encoding="utf-8") as f:
            json.dump([], f, indent=4)
        return "All active reminders have been cleared."

    else:
        if not reminders:
            return "You have no active reminders."
        print("\n⏰ YOUR ACTIVE REMINDERS:")
        print("=" * 50)
        for r in reminders:
            print(f"{r['id']}. [{r['timestamp']}] {r['text']}")
        print("=" * 50)
        return f"You have {len(reminders)} reminder{'s' if len(reminders) > 1 else ''}. The first is: {reminders[0]['text']}"


# ============================================================
# CAREER & JOB HUNTING AUTOMATION
# ============================================================

def run_job_search():
    speak("Starting daily job discovery search across remote sources...")
    try:
        import job_search
        job_search.search_and_save()
        return "Job discovery completed. Saved jobs database updated."
    except Exception as e:
        return f"Error executing job search: {e}"


def show_top_job_matches(limit=5):
    try:
        jobs_path = os.path.join(BASE_DIR, "saved_jobs.json")
        if not os.path.exists(jobs_path):
            return "No saved jobs found. Say 'search for jobs' to find some."
        with open(jobs_path, "r", encoding="utf-8") as f:
            jobs = json.load(f)
        if not jobs:
            return "No jobs in database. Say 'search for jobs' to discover new ones."

        scored_jobs = sorted(jobs, key=lambda j: j.get("score") or 0, reverse=True)
        top = scored_jobs[:limit]

        print("\n💼 TOP JOB MATCHES FOR YOU:")
        print("=" * 60)
        for idx, j in enumerate(top, 1):
            score = j.get("score", "N/A")
            company = j.get("company", "Unknown")
            title = j.get("title", "Unknown")
            skills = ", ".join(j.get("matched_skills", [])) or "None detected"
            print(f"{idx}. {title} at {company}")
            print(f"   Match Score: {score}/100 | Skills: {skills}")
            print(f"   URL: {j.get('apply_url') or j.get('url')}")
            print("-" * 60)
        top_title = top[0].get("title", "")
        top_company = top[0].get("company", "")
        return f"Found {len(jobs)} total jobs. Your top match is {top_title} at {top_company} with a score of {top[0].get('score', 0)} out of 100."
    except Exception as e:
        return f"Error retrieving jobs: {e}"


def show_career_profile():
    try:
        prof_path = os.path.join(BASE_DIR, "career_profile.json")
        if os.path.exists(prof_path):
            with open(prof_path, "r", encoding="utf-8") as f:
                prof = json.load(f)
            skills = prof.get("skills", [])
            education = prof.get("education", "B.Com Graduate")
            exp = prof.get("experience_years", 1)
            print("\n👤 HARSHIL'S CAREER PROFILE:")
            print("=" * 60)
            print(f"Education: {education}")
            print(f"Experience: {exp} year(s)")
            print(f"Key Skills ({len(skills)} listed):")
            print(", ".join(skills[:20]) + ("..." if len(skills) > 20 else ""))
            print("=" * 60)
            return f"You are a {education} with {exp} year of experience and {len(skills)} verified skills across Finance, Accounting, Data Analysis, and Python Development."
        return "Career profile not found."
    except Exception as e:
        return f"Could not read profile: {e}"


def open_dashboard():
    dashboard_url = "http://127.0.0.1:5000"
    is_running = False
    try:
        req = urllib.request.Request(dashboard_url)
        with urllib.request.urlopen(req, timeout=1):
            is_running = True
    except Exception:
        is_running = False

    if not is_running:
        dashboard_script = os.path.join(BASE_DIR, "dashboard.py")
        if os.path.exists(dashboard_script):
            subprocess.Popen([sys.executable, dashboard_script], cwd=BASE_DIR)
            time.sleep(1.5)

    webbrowser.open(dashboard_url)
    return "Job dashboard opened in your browser at http://127.0.0.1:5000."


# ============================================================
# CALCULATIONS & SHELL COMMANDS
# ============================================================

def safe_calculate(expression):
    expr = (expression or "").strip().lower()
    expr = re.sub(r"^(what\s+is\s+the|what\'s\s+the|what\s+is|what\'s|calculate\s+the|calculate|solve\s+the|solve|how\s+much\s+is\s+the|how\s+much\s+is)\s+", "", expr).strip()
    expr = re.sub(r"^the\s+", "", expr).strip()

    # Replace math terms
    expr = re.sub(r"%\s*of\b", "* 0.01 *", expr)
    expr = re.sub(r"\bpercent of\b", "* 0.01 *", expr)
    expr = re.sub(r"(\d+(?:\.\d+)?)%", r"(\1 * 0.01)", expr)
    expr = re.sub(r"\b(?:square root of|square root|sqrt of|root of)\s*(\([^\)]+\)|\d+(?:\.\d+)?)", r"sqrt(\1)", expr)
    expr = re.sub(r"\bsqrt\s*\(?(\d+(?:\.\d+)?)\)?", r"sqrt(\1)", expr)
    expr = re.sub(r"\b(?:cube root of|cube root)\s*(\([^\)]+\)|\d+(?:\.\d+)?)", r"(\1 ** (1/3))", expr)
    expr = re.sub(r"\b(?:square of)\s*(\([^\)]+\)|\d+(?:\.\d+)?)", r"(\1 ** 2)", expr)
    expr = re.sub(r"\b(?:cube of)\s*(\([^\)]+\)|\d+(?:\.\d+)?)", r"(\1 ** 3)", expr)
    expr = re.sub(r"(\d+(?:\.\d+)?)\s*squared\b", r"(\1 ** 2)", expr)
    expr = re.sub(r"(\d+(?:\.\d+)?)\s*cubed\b", r"(\1 ** 3)", expr)
    expr = re.sub(r"\bplus\b", "+", expr)
    expr = re.sub(r"\bminus\b", "-", expr)
    expr = re.sub(r"\btimes\b|\bmultiplied by\b|\bx\b", "*", expr)
    expr = re.sub(r"\bdivided by\b", "/", expr)
    expr = re.sub(r"\bto the power of\b|\bpower\b", "**", expr)
    expr = re.sub(r"\bmodulo\b|\bmod\b", "%", expr)

    import math
    safe_dict = {
        "__builtins__": {},
        "math": math,
        "sqrt": math.sqrt,
        "abs": abs,
        "round": round,
    }

    clean_expr = re.sub(r"[^0-9\+\-\*\/\.\(\)\%\smath\.sqrtabsround]", "", expr)
    if not clean_expr.strip():
        return None
    try:
        result = eval(clean_expr, safe_dict, {})
        if isinstance(result, (int, float)):
            if isinstance(result, float):
                rounded = round(result, 8)
                if rounded.is_integer():
                    result = int(rounded)
                else:
                    result = round(result, 4)
            return f"The answer is {result}"
        return None
    except Exception:
        return None


def execute_terminal_command(cmd):
    cmd = cmd.strip()
    dangerous = ["rm ", "rmdir", "dd ", "mkfs", "shutdown", "reboot", "> /", "chmod -R", "chown -R"]
    if any(d in cmd for d in dangerous):
        print(f"\n⚠️ CAUTION: The command '{cmd}' may modify or delete files.")
        confirm = input("Are you sure you want to run this? (yes/no): ").strip().lower()
        if confirm not in ("yes", "y"):
            return "Command execution cancelled."

    try:
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
        out = res.stdout if res.stdout else res.stderr
        out = (out or "").strip()
        print("\n🖥️ TERMINAL OUTPUT:")
        print("=" * 50)
        print(out if out else "[No output]")
        print("=" * 50)
        if len(out) > 200:
            return "Command executed successfully. Output displayed on screen, Sir."
        return f"Command executed: {out}" if out else "Command executed successfully with no output."
    except subprocess.TimeoutExpired:
        return "Command timed out after 15 seconds."
    except Exception as e:
        return f"Error executing command: {e}"


# ============================================================
# HELP & CAPABILITIES
# ============================================================

def show_help():
    help_text = """
============================================================
🤖 JARVIS CAPABILITIES & COMMANDS GUIDE
============================================================
🗣️ CONVERSATIONAL AI & GENERAL KNOWLEDGE:
   - Ask anything: "Who was Nikola Tesla?", "Explain quantum computing",
     "Tell me a joke", "What is the capital of France?"
   - Intelligent multi-turn memory + Wikipedia & DuckDuckGo fallback!

📧 GMAIL & COMMUNICATIONS:
   - "analyze my emails"      - AI analysis of unread emails with smart reply drafts
   - "unread emails"          - Read latest unread inbox emails
   - "latest email"           - Read your latest email
   - "search email from/about"- Search emails by sender or topic
   - "send an email"          - Compose and send a new email
   - "email pavitra and tell him ..." - Smart one-shot email
   - "reply to latest email"  - Draft and send a reply
   - "email with attachment"  - Send email with local file attached
   - "show my job emails"     - Filter and analyze job-related emails

💼 CAREER & JOB SEARCH:
   - "search for jobs"        - Discover new remote jobs matching your profile
   - "top jobs" / "job matches"- View best matching jobs with scores
   - "my skills" / "profile"  - View your career profile and skills
   - "open dashboard"         - Open interactive Flask Job Dashboard

🌐 WEB & APPLICATIONS:
   - "open [app]"             - Launch Mac apps (Safari, Chrome, VS Code, Terminal, Spotify, etc.)
   - "open [website]"         - Open YouTube, GitHub, LinkedIn, ChatGPT, Netflix, etc.
   - "close [app]"            - Close running application
   - "google [query]"         - Search Google in browser
   - "youtube [query]"        - Search YouTube in browser
   - "wikipedia [query]"      - Look up articles on Wikipedia

⚙️ SYSTEM CONTROLS (macOS):
   - "volume up / down / mute / unmute / volume to X% / volume to max"
   - "battery status"         - Check battery percentage and charging state
   - "ip address" / "my ip"   - Check local and public IP addresses
   - "disk space" / "storage" - Check free and total disk storage
   - "memory" / "ram usage"   - Check active RAM usage
   - "system info"            - View macOS version and processor architecture
   - "take a screenshot"      - Capture screen to Desktop
   - "lock screen"            - Lock your Mac
   - "empty trash"            - Clean macOS trash
   - "what time is it?"       - Current time and date
   - "weather [city]"         - Live weather report

📝 PRODUCTIVITY:
   - "take a note: [text]"    - Save note with timestamp
   - "show notes" / "search notes [keyword]" / "delete note [id]" / "clear notes"
   - "remind me to [text]"    - Set reminder
   - "show reminders" / "search reminders [keyword]" / "delete reminder [id]" / "clear reminders"
   - "calculate [math]"       - Solve arithmetic expressions (sqrt, squared, %, etc.)
   - "run command [cmd]"      - Run shell command

🛑 CONTROL:
   - "stop" / "exit" / "bye"  - Shut down JARVIS
============================================================
"""
    print(help_text)
    return "I have displayed all my capabilities on your screen, Sir. I can manage GMAIL and emails, search jobs, control your Mac, browse the web, take notes, and answer basically any question you have."


# ============================================================
# AI ACTION EXECUTOR
# ============================================================

def execute_ai_action(response_text):
    action_match = re.search(r"\[\[ACTION:\s*([a-zA-Z0-9_]+)\((.*?)\)\s*\]\]", response_text)
    if not action_match:
        return response_text

    func_name = action_match.group(1)
    args_str = action_match.group(2).strip()
    spoken_text = response_text.replace(action_match.group(0), "").strip()
    spoken_text = re.sub(r"^`+|`+$", "", spoken_text).strip()

    arg_val = ""
    args_list = []
    if args_str:
        raw_args = [a.strip().strip('"\'') for a in re.findall(r'(?:[^\s,"]|"(?:\\.|[^"])*"|\'(?:\\.|[^\'])*\')+', args_str)]
        args_list = raw_args
        arg_val = args_list[0] if args_list else ""
        if str(arg_val).isdigit():
            arg_val = int(arg_val)

    action_result = None
    try:
        if func_name in ("open_website", "open_app"):
            action_result = open_target(str(arg_val))
        elif func_name == "close_app":
            action_result = close_app(str(arg_val))
        elif func_name == "search_google":
            action_result = search_google(str(arg_val))
        elif func_name == "search_youtube":
            action_result = search_youtube(str(arg_val))
        elif func_name == "search_wikipedia":
            action_result = search_wikipedia(str(arg_val))
        elif func_name == "set_volume":
            action_result = system_volume("set" if isinstance(arg_val, int) or str(arg_val).isdigit() else str(arg_val).lower(), arg_val)
        elif func_name == "get_battery":
            action_result = get_battery_status()
        elif func_name == "get_ip":
            action_result = get_ip_address()
        elif func_name == "get_disk_space":
            action_result = get_disk_space()
        elif func_name == "get_memory":
            action_result = get_memory_status()
        elif func_name == "get_system_info":
            action_result = get_system_info()
        elif func_name == "empty_trash":
            action_result = empty_trash()
        elif func_name == "take_screenshot":
            action_result = take_screenshot()
        elif func_name == "lock_screen":
            action_result = lock_screen()
        elif func_name == "get_weather":
            action_result = get_weather(str(arg_val) if arg_val else None)
        elif func_name == "take_note":
            action_result = manage_notes("add", str(arg_val))
        elif func_name == "get_notes":
            action_result = manage_notes("show")
        elif func_name == "clear_notes":
            action_result = manage_notes("clear")
        elif func_name == "delete_note":
            action_result = manage_notes("delete", str(arg_val))
        elif func_name == "search_notes":
            action_result = manage_notes("search", str(arg_val))
        elif func_name == "set_reminder":
            action_result = manage_reminders("add", str(arg_val))
        elif func_name == "get_reminders":
            action_result = manage_reminders("show")
        elif func_name == "clear_reminders":
            action_result = manage_reminders("clear")
        elif func_name == "delete_reminder":
            action_result = manage_reminders("delete", str(arg_val))
        elif func_name == "search_reminders":
            action_result = manage_reminders("search", str(arg_val))
        elif func_name == "calculate":
            calc = safe_calculate(str(arg_val))
            action_result = calc if calc else f"Calculated: {arg_val}"
        elif func_name in ("get_time", "get_date"):
            action_result = get_current_time_date()
        elif func_name == "search_jobs":
            action_result = run_job_search()
        elif func_name == "show_top_jobs":
            action_result = show_top_job_matches()
        elif func_name == "open_dashboard":
            action_result = open_dashboard()
        elif func_name == "show_career_profile":
            action_result = show_career_profile()
        elif func_name == "read_latest_email":
            action_result = "Checking your latest email, Sir."
            read_latest_email()
        elif func_name == "get_unread_emails":
            action_result = "Checking unread emails, Sir."
            get_unread_emails()
        elif func_name == "run_command":
            action_result = execute_terminal_command(str(arg_val))
    except Exception as e:
        print(f"⚠️ Action execution error: {e}")

    if action_result:
        print(f"⚡ [JARVIS Action Executed]: {action_result}")
        if not spoken_text:
            spoken_text = action_result
        else:
            if action_result.strip() not in spoken_text:
                spoken_text = f"{spoken_text}\n{action_result}"

    return spoken_text


def normalize_command(raw_text):
    text = (raw_text or "").strip().lower()
    # Remove leading assistant wake words cleanly without stripping 'jarvis' from inside queries
    text = re.sub(r"^(hey\s+jarvis|ok\s+jarvis|hello\s+jarvis|jarvis|javed)\b[,\s\-\:]*", "", text, flags=re.IGNORECASE).strip()
    text = text.lstrip(",;: -")

    # Remove politeness & conversational filler prefixes
    polite_prefixes = [
        r"^(could|can|would)\s+you\s+(please\s+)?(tell\s+me|help\s+me\s+with|show\s+me\s+)?",
        r"^(please|kindly)\s+",
        r"^(i\s+want\s+you\s+to|i\s+need\s+you\s+to|i'd\s+like\s+you\s+to)\s+",
        r"^(help\s+me\s+to|help\s+me)\s+",
        r"^(tell\s+me|show\s+me)\s+",
    ]
    changed = True
    while changed:
        prev = text
        for pat in polite_prefixes:
            text = re.sub(pat, "", text, flags=re.IGNORECASE).strip()
            text = text.lstrip(",;: -")
        changed = (text != prev)

    return text


# ============================================================
# MAIN JARVIS
# ============================================================

def main():

    speak(
        "Hello, Sir. I am JARVIS. All systems are online, and I am ready to assist you with everything."
    )

    while True:

        command = listen()

        if not command:
            continue

        raw_command = command.strip().lower()

        # Handle wake word alone
        if raw_command in ("jarvis", "hey jarvis", "ok jarvis", "hello jarvis", "javed"):
            speak("Yes, Sir? How can I assist you?")
            continue

        clean_command = normalize_command(raw_command)

        if not clean_command:
            continue

        command = clean_command

        # ============================================================
        # ANALYZE EMAILS
        # ============================================================

        if (
            command in ("analyze my emails", "analyse my emails", "analyze my email", "analyse my email", "analyze", "analyse")
            or any(p in command for p in [
                "analyze my emails", "analyse my emails", "analyze my unread emails",
                "analyse my unread emails", "reply to all my emails", "reply to my emails",
                "prepare ai replies", "read and analyze my emails"
            ])
        ):

            speak("Analyzing your unread emails.")

            analyze_unread_emails()

            continue

        # ============================================================
        # JOB EMAILS
        # ============================================================

        if any(p in command for p in [
            "show me my job emails", "show my job emails", "check my job emails",
            "check job emails", "find job emails", "show job emails",
            "show me my jobs email", "check my job email", "my job emails", "job emails"
        ]):

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

            command = "send an email"

            smart_email_recipient = smart_recipient
            smart_email_message = smart_message

        else:

            smart_email_recipient = None
            smart_email_message = None

        # ============================================================
        # SYSTEM & ASSISTANT COMMANDS
        # ============================================================

        # ----------------------------------------------------
        # STOP / EXIT
        # ----------------------------------------------------

        if (
            command in ("stop", "exit", "quit", "bye", "goodbye", "sleep", "shut down", "turn off")
            or "stop jarvis" in command
            or "jarvis stop" in command
        ):
            speak("Goodbye, Sir. Standing by.")
            break

        # ----------------------------------------------------
        # HELP / CAPABILITIES
        # ----------------------------------------------------

        elif command in ("help", "what can you do", "commands", "show commands", "capabilities", "features") or "what can you do" in command:
            speak(show_help())

        # ----------------------------------------------------
        # GREETINGS
        # ----------------------------------------------------

        elif command in ("hello", "hi", "hey", "good morning", "good afternoon", "good evening"):
            speak("Hello, Sir! All systems are online. How may I be of service?")

        # ----------------------------------------------------
        # HOW ARE YOU / STATUS
        # ----------------------------------------------------

        elif command in ("how are you", "how are you doing", "status", "system status", "system check") or "how are you" in command:
            speak("All systems are fully operational and ready, Sir.")

        # ----------------------------------------------------
        # TIME & DATE
        # ----------------------------------------------------

        elif any(p in command for p in [
            "what time is it", "the time", "current time", "what's the time", "tell me the time", "time now",
            "what date is today", "what is today's date", "what day is today", "what day is it",
            "what is the date", "today's date", "current date"
        ]):
            speak(get_current_time_date())

        # ----------------------------------------------------
        # BATTERY
        # ----------------------------------------------------

        elif any(p in command for p in ["battery", "battery status", "power level", "battery percent", "check battery"]):
            speak(get_battery_status())

        # ----------------------------------------------------
        # SYSTEM HARDWARE & STATS (IP, DISK, RAM, SPECS, TRASH)
        # ----------------------------------------------------

        elif any(p in command for p in ["ip address", "my ip", "what's my ip", "whats my ip", "local ip", "public ip"]):
            speak(get_ip_address())

        elif any(p in command for p in ["disk space", "storage", "free disk", "free storage", "disk usage", "how much storage"]):
            speak(get_disk_space())

        elif any(p in command for p in ["ram usage", "memory usage", "memory status", "check ram", "ram", "memory"]):
            speak(get_memory_status())

        elif any(p in command for p in ["system info", "system information", "mac specs", "computer specs", "specs"]):
            speak(get_system_info())

        elif any(p in command for p in ["empty trash", "clear trash", "clean trash"]):
            speak(empty_trash())

        # ----------------------------------------------------
        # SCREENSHOT
        # ----------------------------------------------------

        elif any(p in command for p in ["screenshot", "take a screenshot", "capture screen", "screen grab"]):
            speak(take_screenshot())

        # ----------------------------------------------------
        # LOCK SCREEN
        # ----------------------------------------------------

        elif any(p in command for p in ["lock screen", "lock mac", "lock my mac", "lock computer", "sleep screen"]):
            speak(lock_screen())

        # ----------------------------------------------------
        # VOLUME CONTROL
        # ----------------------------------------------------

        elif any(p in command for p in ["volume up", "increase volume", "turn up the volume", "turn up volume", "louder", "make it louder"]):
            speak(system_volume("up"))

        elif any(p in command for p in ["volume down", "decrease volume", "lower volume", "turn down the volume", "turn down volume", "quieter"]):
            speak(system_volume("down"))

        elif "unmute" in command:
            speak(system_volume("unmute"))

        elif "mute" in command or "silence" in command:
            speak(system_volume("mute"))

        elif "volume to max" in command or "maximum volume" in command:
            speak(system_volume("max"))

        elif "volume to half" in command:
            speak(system_volume("half"))

        elif "set volume to" in command or "volume to" in command or (command.startswith("volume ") and re.search(r"\d+", command)):
            vol_match = re.search(r"\d+", command)
            if vol_match:
                speak(system_volume("set", int(vol_match.group(0))))
            else:
                speak(system_volume("get"))

        # ----------------------------------------------------
        # WEATHER
        # ----------------------------------------------------

        elif command.startswith("weather") or "what's the weather" in command or "weather in" in command:
            city = None
            if " in " in command:
                city = command.split(" in ", 1)[1].strip()
            elif command.startswith("weather "):
                city = command[8:].strip()
            speak(get_weather(city))

        # ----------------------------------------------------
        # NOTES
        # ----------------------------------------------------

        elif any(command.startswith(p) for p in ["search notes for", "search notes", "find note", "search note"]):
            q = re.sub(r"^(search notes for|search notes|find note|search note)\s*", "", command).strip(" :")
            speak(manage_notes("search", q))

        elif any(command.startswith(p) for p in ["delete note", "remove note"]):
            nid = re.sub(r"^(delete note|remove note)\s*", "", command).strip(" :")
            speak(manage_notes("delete", nid))

        elif any(command.startswith(p) for p in ["take a note", "add note", "note down", "write note", "note "]):
            text = None
            for p in ["take a note:", "take a note of", "take a note that", "take a note", "add note:", "add note", "note down:", "note down", "write note:", "write note", "note:"]:
                if command.startswith(p):
                    text = command[len(p):].strip()
                    break
            if not text:
                text = command.split("note", 1)[1].strip(" :")
            if text:
                speak(manage_notes("add", text))
            else:
                speak("What note would you like me to record, Sir?")
                note_text = input("YOU (note): ").strip()
                if note_text:
                    speak(manage_notes("add", note_text))

        elif any(p in command for p in ["show notes", "read notes", "my notes", "list notes", "view notes"]) or command == "notes":
            speak(manage_notes("show"))

        elif any(p in command for p in ["clear notes", "delete all notes", "remove all notes"]):
            speak(manage_notes("clear"))

        # ----------------------------------------------------
        # REMINDERS
        # ----------------------------------------------------

        elif any(command.startswith(p) for p in ["search reminders for", "search reminders", "find reminder"]):
            q = re.sub(r"^(search reminders for|search reminders|find reminder)\s*", "", command).strip(" :")
            speak(manage_reminders("search", q))

        elif any(command.startswith(p) for p in ["delete reminder", "remove reminder"]):
            rid = re.sub(r"^(delete reminder|remove reminder)\s*", "", command).strip(" :")
            speak(manage_reminders("delete", rid))

        elif any(command.startswith(p) for p in ["remind me to ", "set reminder ", "add reminder ", "set a reminder to ", "set a reminder "]):
            text = None
            for p in ["remind me to ", "set reminder to ", "set a reminder to ", "set reminder: ", "set reminder ", "set a reminder ", "add reminder "]:
                if command.startswith(p):
                    text = command[len(p):].strip()
                    break
            if text:
                speak(manage_reminders("add", text))
            else:
                speak(manage_reminders("show"))

        elif any(p in command for p in ["show reminders", "read reminders", "my reminders", "list reminders"]) or command == "reminders":
            speak(manage_reminders("show"))

        elif any(p in command for p in ["clear reminders", "delete all reminders"]):
            speak(manage_reminders("clear"))

        # ----------------------------------------------------
        # MATH & CALCULATIONS
        # ----------------------------------------------------

        elif command.startswith("calculate ") or command.startswith("solve ") or command.startswith("how much is ") or (
            command.startswith("what is ") and any(op in command for op in ["+", "-", "*", "/", "%", "times", "multiplied", "divided", "plus", "minus", "power", "percent", "sqrt", "root", "squared", "cubed"])
        ):
            expr = re.sub(r"^(calculate|solve|how much is|what is)\s+", "", command).strip()
            calc_res = safe_calculate(expr)
            if calc_res:
                speak(calc_res)
                continue

        # ----------------------------------------------------
        # CAREER & JOB HUNTING AUTOMATION
        # ----------------------------------------------------

        elif any(p in command for p in ["search for jobs", "find jobs", "job search", "search jobs", "discover jobs"]):
            speak(run_job_search())

        elif any(p in command for p in ["top jobs", "job matches", "my jobs", "show saved jobs", "best jobs"]):
            speak(show_top_job_matches())

        elif any(p in command for p in ["my skills", "career profile", "show profile", "who am i"]):
            speak(show_career_profile())

        elif any(p in command for p in ["open dashboard", "job dashboard", "show dashboard", "launch dashboard"]):
            speak(open_dashboard())

        # ----------------------------------------------------
        # WEB SEARCHES
        # ----------------------------------------------------

        elif command.startswith("google ") or command.startswith("search google for ") or ("search for " in command and "on google" in command):
            q = command.replace("search google for ", "").replace("google ", "").replace("on google", "").replace("search for ", "").strip()
            speak(search_google(q))

        elif command.startswith("youtube ") or command.startswith("search youtube for ") or ("play " in command and "on youtube" in command):
            q = command.replace("search youtube for ", "").replace("youtube ", "").replace("on youtube", "").replace("play ", "").strip()
            speak(search_youtube(q))

        elif command.startswith("wikipedia ") or command.startswith("search wikipedia for "):
            q = command.replace("search wikipedia for ", "").replace("wikipedia ", "").strip()
            speak(search_wikipedia(q))

        elif command.startswith("search for ") or command.startswith("search "):
            q = re.sub(r"^(search for|search)\s+", "", command).strip()
            speak(search_google(q))

        # ----------------------------------------------------
        # CLOSE APPLICATION
        # ----------------------------------------------------

        elif command.startswith("close ") or command.startswith("quit ") or command.startswith("kill ") or command.startswith("exit "):
            target = re.sub(r"^(close|quit|kill|exit)\s+", "", command).strip()
            speak(close_app(target))

        # ----------------------------------------------------
        # OPEN WEBSITE / APPLICATION / DASHBOARD
        # ----------------------------------------------------

        elif command.startswith("open ") or command.startswith("launch ") or command.startswith("start "):
            target = re.sub(r"^(open|launch|start)\s+", "", command).strip()
            if target in ("dashboard", "job dashboard"):
                speak(open_dashboard())
            else:
                speak(open_target(target))

        # ----------------------------------------------------
        # TERMINAL / SHELL COMMANDS
        # ----------------------------------------------------

        elif command.startswith("run command ") or command.startswith("execute ") or command.startswith("terminal "):
            cmd = command.replace("run command ", "").replace("execute ", "").replace("terminal ", "").strip()
            speak(execute_terminal_command(cmd))

        elif command in ("list files", "show files", "show directory", "ls"):
            speak(execute_terminal_command("ls -la"))

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
        # DEFAULT — GEMINI AI & ACTION AGENT
        # ----------------------------------------------------

        else:

            print("\n🤖 Consulting JARVIS Core (Gemini AI)...")

            ai_response = ask_ai(command)

            print(
                "\nJARVIS AI:\n"
                + ai_response
            )

            final_spoken = execute_ai_action(ai_response)

            speak(final_spoken)


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