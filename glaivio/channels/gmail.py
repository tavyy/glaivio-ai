import os
import base64
import time
import datetime
from email.mime.text import MIMEText
from email.utils import parseaddr


def _get_gmail_service(credentials_file: str, token_file: str):
    """Authenticate and return a Gmail API service instance."""
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]
    creds = None

    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_file, "w") as f:
            f.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)


def _extract_body(payload: dict) -> str:
    """Extract plain text body from a Gmail message payload."""
    if payload.get("mimeType") == "text/plain":
        data = payload.get("body", {}).get("data", "")
        return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")

    for part in payload.get("parts", []):
        result = _extract_body(part)
        if result:
            return result

    return ""


def _send_reply(service, original: dict, reply_text: str):
    """Send a reply to an email, keeping it in the same thread."""
    headers = {h["name"]: h["value"] for h in original["payload"]["headers"]}
    to = headers.get("From", "")
    subject = headers.get("Subject", "")
    message_id = headers.get("Message-ID", "")
    thread_id = original["threadId"]

    if not subject.lower().startswith("re:"):
        subject = f"Re: {subject}"

    msg = MIMEText(reply_text)
    msg["To"] = to
    msg["Subject"] = subject
    msg["In-Reply-To"] = message_id
    msg["References"] = message_id

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    service.users().messages().send(
        userId="me",
        body={"raw": raw, "threadId": thread_id},
    ).execute()


def _is_support_email(body: str, agent_instructions: str) -> bool:
    """Use the LLM to decide if this email is relevant for the agent to handle."""
    from langchain_anthropic import ChatAnthropic
    from langchain_core.messages import HumanMessage, SystemMessage

    llm = ChatAnthropic(model="claude-haiku-4-5-20251001", max_tokens=10)
    result = llm.invoke([
        SystemMessage(content=agent_instructions),
        HumanMessage(content=f"Should you handle this email? Reply YES or NO only.\n\n{body}"),
    ])
    return result.content.strip().upper().startswith("YES")


class GmailChannel:
    """
    Gmail channel — polls for unread emails and replies via Gmail API.

    Requires:
        GMAIL_CREDENTIALS_FILE — path to OAuth credentials JSON (default: credentials.json)
        GMAIL_TOKEN_FILE       — path to store the access token (default: .gmail_token.json)
        GMAIL_POLL_INTERVAL    — seconds between polls (default: 30)

    Optional:
        target_email — only process emails sent to this address (e.g. support@theirclinic.com)
    """

    def start(self, agent, target_email: str = None, **kwargs):
        credentials_file = os.getenv("GMAIL_CREDENTIALS_FILE", "credentials.json")
        token_file = os.getenv("GMAIL_TOKEN_FILE", ".gmail_token.json")
        poll_interval = int(os.getenv("GMAIL_POLL_INTERVAL", "30"))

        service = _get_gmail_service(credentials_file, token_file)

        target = target_email or os.getenv("GMAIL_TARGET_EMAIL")
        if target:
            print(f"Glaivio Gmail agent running — watching {target}, polling every {poll_interval}s")
        else:
            print(f"Glaivio Gmail agent running — polling every {poll_interval}s")

        while True:
            try:
                today = datetime.date.today().strftime("%Y/%m/%d")
                results = service.users().messages().list(
                    userId="me",
                    labelIds=["INBOX", "UNREAD"],
                    q=f"after:{today}",
                    maxResults=10,
                ).execute()

                messages = results.get("messages", [])

                for msg_ref in messages:
                    msg = service.users().messages().get(
                        userId="me",
                        id=msg_ref["id"],
                        format="full",
                    ).execute()

                    headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
                    sender = headers.get("From", "")
                    _, user_id = parseaddr(sender)
                    body = _extract_body(msg["payload"]).strip()

                    if not body or not user_id:
                        continue

                    # filter by target email if specified
                    if target:
                        to_header = headers.get("To", "")
                        _, to_email = parseaddr(to_header)
                        if to_email.lower() != target.lower():
                            continue

                    # skip if not relevant for this agent
                    if not _is_support_email(body, agent.instructions):
                        print(f"[Glaivio] ⏭ skipped (not a support question): {user_id}")
                        # mark as read so we don't keep seeing it
                        service.users().messages().modify(
                            userId="me",
                            id=msg_ref["id"],
                            body={"removeLabelIds": ["UNREAD"]},
                        ).execute()
                        continue

                    print(f"\n[Glaivio] ← {user_id}: {body[:80]}...")

                    reply = agent.reply(user_id=user_id, message=body)
                    _send_reply(service, msg, reply)

                    # mark as read
                    service.users().messages().modify(
                        userId="me",
                        id=msg_ref["id"],
                        body={"removeLabelIds": ["UNREAD"]},
                    ).execute()

                    print(f"[Glaivio] → {user_id}: {reply[:80]}...")

            except Exception as e:
                print(f"[Glaivio] Gmail error: {e}")

            time.sleep(poll_interval)
