from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path
import sys
import traceback
import io
import base64
import re
import threading
import time
import uuid
import soundfile as sf

ENGINE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ENGINE_DIR))
from main import SaraswatiEngine
from tools.agent_planner import PlannedAction, plan_query
from tools.desktop_automation import VisibleDesktopAutomation
from tools.local_agent import LocalAgentBrain, LocalModelInvalid, LocalModelUnavailable

app = FastAPI(title="Saraswati AI Engine API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:1420",
        "http://127.0.0.1:1420",
        "tauri://localhost",
        "http://tauri.localhost",
        "https://tauri.localhost",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

model_directory = ENGINE_DIR / "models"
assistant = SaraswatiEngine(model_directory)
desktop_automation = VisibleDesktopAutomation()
local_agent = LocalAgentBrain()
pending_emails: dict[str, float] = {}
pending_emails_lock = threading.Lock()

class QueryRequest(BaseModel):
    query: str

class SpeakRequest(BaseModel):
    text: str


class EmailConfirmation(BaseModel):
    recipient: str
    subject: str
    body: str


EMAIL_REQUEST_PATTERN = re.compile(
    r"\b(?:send|write|compose|draft)\b.{0,60}\b(?:e-?mail|gmail|message)\b|"
    r"\b(?:e-?mail|gmail)\b.{0,80}\b(?:send|write|compose|draft)\b",
    re.IGNORECASE,
)


def generate_audio_base64(text: str) -> str:
    """Generates speech audio using Saraswati/Kokoro engine and returns base64 WAV string."""
    try:
        audio_data, sample_rate = assistant.generate_audio(text)
        buffer = io.BytesIO()
        sf.write(buffer, audio_data, sample_rate, format="WAV")
        return base64.b64encode(buffer.getvalue()).decode("ascii")
    except Exception as error:
        raise HTTPException(
            status_code=503,
            detail=f"Neural audio generation failed: {error}",
        ) from error


def prepare_email_draft(query: str) -> dict[str, str]:
    recipient_name_match = re.search(
        r"\bto\s+([A-Za-z][A-Za-z'-]*)",
        query,
        re.IGNORECASE,
    )
    recipient_match = re.search(
        r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", query
    )
    topic_match = re.search(
        r"\babout\s+(.+?)(?:[.!?]|,\s*(?:and\s+)?send\b|\s+and\s+send\b|$)",
        query,
        re.IGNORECASE,
    )
    custom_body_match = re.search(
        r"\b(?:saying|that says|message body is|body:)\s+(.+?)(?:\s+and\s+send\b|$)",
        query,
        re.IGNORECASE,
    )

    topic = topic_match.group(1).strip(" ,.") if topic_match else "the topic you mentioned"
    subject = topic[:1].upper() + topic[1:] if topic else "Follow-up"
    name = recipient_name_match.group(1).strip() if recipient_name_match else "there"
    body = (
        custom_body_match.group(1).strip()
        if custom_body_match
        else f"Hi {name},\n\nI am writing about {topic}.\n\nBest,"
    )
    return {
        "recipient": recipient_match.group(0) if recipient_match else "",
        "subject": subject,
        "body": body,
        "recipient_name": name,
    }


def create_pending_email(
    recipient: str,
    subject: str,
    body: str,
    recipient_name: str = "",
) -> dict[str, str]:
    subject = subject.strip() or "Follow-up"
    body = body.strip() or (
        f"Hi {recipient_name or 'there'},\n\n"
        "I am writing to follow up on this topic.\n\nBest,"
    )
    action_id = uuid.uuid4().hex
    with pending_emails_lock:
        now = time.monotonic()
        for expired_id, created_at in list(pending_emails.items()):
            if now - created_at > 20 * 60:
                del pending_emails[expired_id]
        pending_emails[action_id] = now

    return {
        "id": action_id,
        "recipient": recipient,
        "subject": subject.strip(),
        "body": body.strip(),
        "recipient_name": recipient_name,
    }


@app.post("/api/speak")
def speak_audio(payload: SpeakRequest):
    text = payload.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Speech text must not be empty.")
    audio_b64 = generate_audio_base64(text)
    return {"success": True, "audio_base64": audio_b64}

@app.post("/api/query")
def execute_query(payload: QueryRequest):
    try:
        user_query = payload.query.strip()
        if not user_query:
            raise HTTPException(status_code=400, detail="Empty query provided.")

        print(f"Received query: {user_query}")
        planner = "ollama"
        try:
            actions = local_agent.plan_query(user_query)
        except (LocalModelUnavailable, LocalModelInvalid) as error:
            print(f"Local model unavailable; using deterministic fallback: {error}")
            planner = "intent_fallback"
            actions = plan_query(user_query, assistant)
        if EMAIL_REQUEST_PATTERN.search(user_query) and not any(
            action.tool == "email.prepare_draft" for action in actions
        ):
            email = prepare_email_draft(user_query)
            actions.append(
                PlannedAction(
                    "email.prepare_draft",
                    "email_draft",
                    "Prepare an email draft for your review",
                    recipient=email["recipient"],
                    subject=email["subject"],
                    body=email["body"],
                )
            )
        if not actions:
            intent, confidence = assistant.predict_intent(user_query)
            response_text = "I could not identify a supported action in that request."
            plan = []
            action_success = False
            terminal_output = ""
            pending_action = None
        else:
            intent = actions[0].intent if len(actions) == 1 else "agent_plan"
            confidence = 1.0
            plan = []
            terminal_output_parts = []
            response_parts = []
            action_success = True
            pending_action = None

            for action in actions:
                if action.tool == "system.command":
                    result = assistant.terminal_tool.execute_command(action.command)
                    succeeded = bool(result.get("success"))
                    output = str(result.get("output", result.get("error", ""))).strip()
                    if action.intent == "process_management" and succeeded:
                        output = "\n".join(output.splitlines()[:10])
                    if output:
                        terminal_output_parts.append(output)
                    step_response = (
                        action.description
                        if succeeded
                        else f"Unable to execute that action: {result.get('error', 'unknown error')}"
                    )
                elif action.tool == "desktop.launch_app":
                    result = assistant.app_launcher.launch_application(action.app_key)
                    succeeded = bool(result.get("success"))
                    step_response = (
                        f"Launched {action.app_key}."
                        if succeeded
                        else f"Unable to launch {action.app_key}: {result.get('error', 'unknown error')}"
                    )
                elif action.tool == "browser.open_url":
                    result = desktop_automation.open_url(action.url)
                    succeeded = bool(result.get("success"))
                    step_response = (
                        result.get("output", action.description)
                        if succeeded
                        else str(result.get("error", "Unable to open the requested URL."))
                    )
                elif action.tool == "email.prepare_draft":
                    name_match = re.search(
                        r"\bto\s+([A-Za-z][A-Za-z'-]*)",
                        user_query,
                        re.IGNORECASE,
                    )
                    recipient_name = name_match.group(1) if name_match else ""
                    pending_action = {
                        "kind": "send_email",
                        **create_pending_email(
                            action.recipient,
                            action.subject,
                            action.body,
                            recipient_name,
                        ),
                    }
                    succeeded = True
                    step_response = (
                        "I prepared an email draft. Review and edit the recipient, "
                        "subject, and message before choosing Send Email."
                    )
                else:
                    succeeded = False
                    step_response = f"Unsupported tool: {action.tool}"

                action_success = action_success and succeeded
                plan.append(
                    {
                        **action.as_dict(),
                        "status": (
                            "awaiting_confirmation"
                            if action.tool == "email.prepare_draft"
                            else "completed" if succeeded else "failed"
                        ),
                    }
                )
                response_parts.append(step_response)
                if action.tool == "email.prepare_draft":
                    break

            response_text = " ".join(response_parts)
            terminal_output = "\n\n".join(terminal_output_parts)

        audio_base64 = generate_audio_base64(response_text)

        return {
            "success": action_success,
            "intent": intent,
            "confidence": confidence,
            "language": "en",
            "response": response_text,
            "terminal_output": terminal_output,
            "plan": plan,
            "pending_action": pending_action,
            "planner": planner,
            "audio_base64": audio_base64
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print("--- ERROR IN API ---")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/confirm/{action_id}")
def confirm_email(action_id: str, payload: EmailConfirmation):
    recipient = payload.recipient.strip()
    subject = payload.subject.strip()
    body = payload.body.strip()
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", recipient):
        raise HTTPException(status_code=422, detail="Enter a valid recipient email address.")
    if not subject or not body:
        raise HTTPException(status_code=422, detail="Email subject and body are required.")

    with pending_emails_lock:
        pending = pending_emails.get(action_id)
        if pending is None:
            raise HTTPException(status_code=404, detail="Draft not found or expired.")
        created_at = pending
        if time.monotonic() - created_at > 20 * 60:
            del pending_emails[action_id]
            raise HTTPException(status_code=410, detail="Draft expired; please prepare it again.")

    response_text = f"Email sent to {recipient}."
    audio_base64 = generate_audio_base64(response_text)

    with pending_emails_lock:
        if pending_emails.pop(action_id, None) is None:
            raise HTTPException(status_code=404, detail="Draft already confirmed or cancelled.")

    try:
        result = desktop_automation.send_email(
            recipient,
            subject,
            body,
        )
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=str(result.get("error", "Email was not sent.")))

    return {
        "success": True,
        "response": response_text,
        "audio_base64": audio_base64,
    }


@app.delete("/api/confirm/{action_id}")
def cancel_email(action_id: str):
    with pending_emails_lock:
        if pending_emails.pop(action_id, None) is None:
            raise HTTPException(status_code=404, detail="Draft not found or expired.")
    return {"success": True, "response": "Email draft cancelled."}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)