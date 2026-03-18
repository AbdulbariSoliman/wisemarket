# ============================================================
# WISEMARKET — AGENT ROUTE
# POST /agent/query
# GET  /agent/greeting
# ============================================================
from typing import Literal, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.services.agent import generate_greeting, run_agent

router = APIRouter()


class AgentRequest(BaseModel):
    input:   str
    lang:    Literal["en", "de", "fr", "it"] = "en"
    user_id: Optional[str] = None
    mode:    Literal["chat", "search", "scan", "voice"] = "chat"
    store:   Optional[str] = None


class AgentResponse(BaseModel):
    response: str
    intent:   str
    products: list = []


@router.post("/query", response_model=AgentResponse)
def agent_query(req: AgentRequest):
    """
    Main agent endpoint.
    Detects intent, queries DB, refines with LLM.
    Personalised if user_id provided.
    """
    if not req.input or not req.input.strip():
        raise HTTPException(status_code=422, detail="Input cannot be empty")

    result = run_agent(
        user_input=req.input,
        lang=req.lang,
        user_id=req.user_id,
        mode=req.mode,
        store=req.store,
    )

    return AgentResponse(
        response=result["response"],
        intent=result["intent"],
        products=result.get("products", []),
    )


@router.get("/greeting")
def agent_greeting(
    lang:      Literal["en", "de", "fr", "it"] = "en",
    user_id:   Optional[str] = None,
    user_name: Optional[str] = None,
):
    """
    Returns a personalised greeting when user opens the app.
    Uses user_preferences for context if user_id provided.
    """
    greeting = generate_greeting(
        user_id=user_id,
        lang=lang,
        user_name=user_name,
    )
    return {"greeting": greeting, "lang": lang}
