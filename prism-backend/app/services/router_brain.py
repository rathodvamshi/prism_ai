from app.models.chat_models import ChatRequest
from app.services.main_brain import generate_response
from app.services.search_service import search_web
from app.services.task_service import build_task_draft
from app.services.email_service import send_email_notification

# Optional capabilities (present in newer builds)
try:
    from app.services.research_service import deep_research  # type: ignore
except Exception:  # pragma: no cover
    deep_research = None  # fallback if module not available

try:
    from app.services.media_play_service import media_play_service  # type: ignore
except Exception:  # pragma: no cover
    media_play_service = None  # fallback if module not available


# ------------------------------------------------------
# 1. Intent Detection (Mini-Agent Router)
# ------------------------------------------------------
async def decide_intent(request: ChatRequest) -> str:
    """Rule-based intent detection. Keep it fast and clear."""
    msg = (request.message or "").lower()

    # YouTube / media playback - Match "play X", "watch X", "listen X"
    if ("play" in msg or "watch" in msg or "listen" in msg):
        # Exclude task/reminder commands
        if not any(x in msg for x in ["remind", "schedule", "task", "todo", "role", "game"]):
            return "youtube_play"

    # Deep research for purchases and comparisons
    if any(k in msg for k in ["best", "top", "under", "vs", "compare", "buy"]):
        if any(k in msg for k in ["laptop", "phone", "camera", "monitor", "headphones", "gpu", "tv"]):
            return "deep_research"

    # Tasks / reminders
    if any(word in msg for word in ["remind", "schedule", "task", "todo", "appointment", "calendar", "set a reminder"]):
        return "task_management"

    # Conversational memory: self-questions must hit memory, not web
    if "my name" in msg or "who am i" in msg:
        return "general_chat"

    # Web search (factual / current topics)
    if any(word in msg for word in ["weather", "news", "price of", "price", "current", "search", "who is", "what is", "latest", "trending", "google"]):
        return "web_search"

    # Email
    if any(word in msg for word in ["email", "send a mail", "send mail", "gmail", "notify", "send notification"]):
        return "email_service"

    # Fallback
    return "general_chat"


# ------------------------------------------------------
# 2. Main Router Logic
# ------------------------------------------------------
async def process_chat(request: ChatRequest):
    """Route the message to the appropriate subsystem and unify the response."""
    intent = await decide_intent(request)
    reply = ""
    action_data = None  # Optional payload (e.g., YouTube video info)
    
    # Extract user_id from request (use email as user_id for now)
    user_id = getattr(request, 'user_email', 'default_user')

    # If ChatRequest is extended later to include images, pass them through.
    image_url = getattr(request, "image_url", None)

    try:
        if intent == "youtube_play":
            # Media handling: use new hybrid intent pipeline
            if media_play_service is None:
                reply = "Media service unavailable right now."
            else:
                media_response = await media_play_service.process_media_request(
                    user_input=request.message,
                    mode="redirect",  # Default to redirect mode
                    user_id=user_id
                )
                
                # Use the media service's generated message
                reply = media_response.message
                
                # Build action payload for frontend
                action_data = {
                    "type": "media_play",
                    "payload": {
                        "mode": media_response.type,
                        "url": media_response.url,
                        "video_id": media_response.video_id,
                        "query": media_response.query,
                        "message": media_response.message,
                        "cached": media_response.cached,
                        "source": media_response.source,
                    }
                }

        elif intent == "deep_research":
            if deep_research is None:
                # Fallback to simple web search if deep research service is absent
                search_data = await search_web(request.message, mode="deep", max_results=5)
                reply = await generate_response(
                    user_id=user_id,
                    message=request.message,
                    search_results=search_data,
                    image_url=image_url,
                )
            else:
                research_data = await deep_research(request.message)
                reply = await generate_response(
                    user_id=user_id,
                    message=request.message,
                    search_results=research_data,
                    image_url=image_url,
                )

        elif intent == "task_management":
            draft = await build_task_draft(request.message)
            if draft.get("missing_time"):
                reply = (
                    f"I've noted you want to **{draft.get('description')}**.\n\n"
                    "When should I remind you? (e.g., \"in 20 minutes\" or \"tomorrow at 5 PM\")"
                )
            else:
                reply = (
                    f"Got it. I'll remind you to **{draft.get('description')}** "
                    f"at **{draft.get('due_date_human_readable')}**. Please confirm."
                )
                action_data = {
                    "type": "task_draft",
                    "payload": {
                        "description": draft.get("description"),
                        "due_date": draft.get("due_date_iso"),
                        "due_date_human_readable": draft.get("due_date_human_readable"),
                    },
                }

        elif intent == "web_search":
            search_data = await search_web(request.message, mode="quick")
            reply = await generate_response(
                user_id=user_id,
                message=request.message,
                search_results=search_data,
                image_url=image_url,
            )

        elif intent == "email_service":
            # Use Celery task for email notifications\n            try:\n                from app.tasks.email_tasks import send_email_notification_task\n                from app.core.celery_app import CELERY_AVAILABLE, celery_app\n                \n                if CELERY_AVAILABLE and celery_app:\n                    # Send via Celery task (preferred)\n                    celery_app.send_task(\n                        \"prism_tasks.send_email_notification\",\n                        args=[request.message],\n                        queue=\"email\"\n                    )\n                    reply = \"\u2705 Email notification queued successfully! It will be processed shortly.\"\n                else:\n                    # Fallback to direct sending if Celery unavailable\n                    reply = await send_email_notification(request.message)\n                    \n            except Exception as e:\n                reply = f\"\u274c Failed to queue email notification: {str(e)}\"

        else:
            reply = await generate_response(
                user_id=user_id,
                message=request.message,
                image_url=image_url,
            )
    except Exception as e:
        reply = f"I'm having trouble routing your request right now: {e}"

    model_used = (
        "llama-3.3-70b-versatile"
        if intent in ["general_chat", "web_search", "deep_research", "youtube_play"]
        else "rule-based"
    )

    return {
        "reply": reply,
        "intent": intent,
        "action_data": action_data,  # Frontend can use this to auto-play video
        "debug_info": {
            "router_decision": intent,
            "model_used": model_used,
            "has_image": bool(image_url),
        },
    }
