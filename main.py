from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
from google import genai
from google.genai import types
from dotenv import load_dotenv
import os

# Import tools registry
from tools import TOOLS

load_dotenv()

GCP_PROJECT  = os.getenv("GCP_PROJECT_ID", "ecommerce-ass")
GCP_LOCATION = os.getenv("GCP_LOCATION", "us-central1")

# Vertex AI client
client = genai.Client(
    vertexai=True,
    project=GCP_PROJECT,
    location=GCP_LOCATION,
)

# Use the model available in your project
MODEL = "gemini-2.5-flash-lite"

SYSTEM_INSTRUCTION = (
    "You are a professional and friendly AI E-commerce Assistant. "
    "The system will automatically provide you with the logically authenticated User ID in the System Context. "
    "If the user is logged in, you will be given their name, greet them EXACTLY via 'hi [user name] can i help you today'. "
    "If the user is NOT logged in, NEVER ask them to provide their User ID. Simply call the required tool right away anyway. "
    "Do NOT ask the user to provide their ID."
)

# Build a lookup map: function name -> function object
TOOL_MAP: dict = {fn.__name__: fn for fn in TOOLS}

app = FastAPI(title="Gemini Agentic E-commerce Assistant")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve frontend static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# In-memory session store: session_id -> list of Content objects
sessions: dict[str, list] = {}


class Message(BaseModel):
    session_id: str
    text: str
    user_id: Optional[str] = None
    user_name: Optional[str] = None


class LoginRequest(BaseModel):
    email: str


class SignupRequest(BaseModel):
    name: str
    email: str
    address: str


class HistoryEntry(BaseModel):
    role: str
    text: str


class ChatResponse(BaseModel):
    reply: str
    history: List[HistoryEntry]
    requires_auth: bool = False


@app.get("/")
async def serve_frontend():
    return FileResponse("frontend/index.html")


@app.post("/auth/login")
async def login(req: LoginRequest):
    import database as db
    for uid, user in db.users.items():
        if user["email"].lower() == req.email.lower():
            return {"status": "success", "user_id": uid, "name": user["name"], "email": user["email"]}
    raise HTTPException(status_code=404, detail="User not found. Please sign up.")


@app.post("/auth/signup")
async def signup(req: SignupRequest):
    from ecommerce_tools import register_user
    import database as db
    
    # Check if exists
    for uid, user in db.users.items():
        if user["email"].lower() == req.email.lower():
            raise HTTPException(status_code=400, detail="Email already registered.")
            
    # Use existing DB logic
    user_id = db.generate_user_id()
    db.users[user_id] = {
        "name": req.name,
        "email": req.email,
        "address": req.address
    }
    return {"status": "success", "user_id": user_id, "name": req.name, "email": req.email}



@app.post("/chat", response_model=ChatResponse)
async def chat(message: Message):
    session_id = message.session_id.strip()
    user_text  = message.text.strip()

    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required.")
    if not user_text:
        raise HTTPException(status_code=400, detail="Message text cannot be empty.")

    history = sessions.get(session_id, [])

    # If user is logged in, inform the system exactly who it is ONLY if we haven't already
    current_contents = []
    already_informed = any("System Context: The user is currently logged in" in getattr(p, "text", "") for msg in history for p in msg.parts if msg.role == "user")
    
    if message.user_id and not already_informed:
        current_contents.append(
            types.Content(role="user", parts=[types.Part(text=f"System Context: The user is currently logged in. Their name is {message.user_name} and their User ID is {message.user_id}. Proceed to help them.")])
        )
        current_contents.append(
            types.Content(role="model", parts=[types.Part(text=f"Understood. I will assist {message.user_name} securely using their logically verified session.")])
        )

    # Start with current history + user input. Inject current login state AFTER history to override old chat context!
    contents = history + current_contents + [
        types.Content(role="user", parts=[types.Part(text=user_text)])
    ]

    # Server-side automatic order lookup: if the user message contains an
    # explicit order id (simple numeric pattern) and the requester is logged
    # in, perform a safe server-side tool call and append the result as a
    # `tool` content so the model can reference authorized data.
    try:
        import re
        order_match = re.search(r"\b\d{4,6}\b", user_text)
        if order_match and message.user_id:
            order_id = order_match.group(0)
            import database as db
            order = db.orders.get(order_id)
            if order:
                if order.get("user_id") == message.user_id:
                    # Choose status vs details heuristically
                    fn_name = "get_order_status" if "status" in user_text.lower() else "get_order_details"
                    fn = TOOL_MAP.get(fn_name)
                    if fn:
                        try:
                            server_result = fn(order_id=order_id)
                        except Exception as e:
                            server_result = f"Error during server-side lookup: {str(e)}"
                    else:
                        server_result = f"Error: Tool '{fn_name}' not available."

                    # Immediately return the server-side result for authorized
                    # requests so the user sees the factual order information
                    # without relying on the model to synthesize it.
                    from typing import List
                    history_entries: List[HistoryEntry] = [HistoryEntry(role="model", text=str(server_result))]
                    return ChatResponse(reply=str(server_result), history=history_entries, requires_auth=False)
                else:
                    # Order exists but belongs to a different user — append
                    # an authorized denial so the model can't leak other users' data.
                    err = f"Error: You do not have permission to access order #{order_id}."
                    tool_part = types.Part(function_response=types.FunctionResponse(name="get_order_status", response={"result": err}))
                    contents.append(types.Content(role="tool", parts=[tool_part]))
    except Exception:
        pass

    try:
        # Determine if any prior tool responses in the session already provided
        # authorized order data (so the model can safely reference it).
        order_tools = {"get_order_status", "get_order_details", "cancel_order", "update_order_address", "update_order_quantity"}
        authorized_order_data_retrieved = False
        for msg in contents:
            if getattr(msg, "role", None) == "tool":
                for p in getattr(msg, "parts", []) or []:
                    fr = getattr(p, "function_response", None)
                    if fr and fr.name in order_tools:
                        # function_response.response is expected to be a dict with 'result'
                        try:
                            res = fr.response.get("result", "")
                        except Exception:
                            res = ""
                        if res and not str(res).lower().startswith("error"):
                            authorized_order_data_retrieved = True
                            break
                if authorized_order_data_retrieved:
                    break

        # ── Agentic tool-calling loop ──────────────────────
        loop_count = 0
        while loop_count < 5:  # Safety break for infinite loops
            loop_count += 1
            response = client.models.generate_content(
                model=MODEL,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    tools=TOOLS,
                    temperature=0.7,
                ),
            )

            # Safety check: ensure response has candidates
            if not response.candidates:
                reply = "I'm sorry, I'm having trouble processing your request right now. Please try again."
                break
                
            candidate = response.candidates[0]
            
            # Safety check: ensure candidate has content and parts
            if not candidate.content or not candidate.content.parts:
                reply = response.text or "I'm sorry, I couldn't formulate a response."
                break

            # Check for tool calls
            tool_calls = [
                part for part in candidate.content.parts
                if part.function_call is not None
            ]

            if tool_calls:
                # Add the model's intent to call tools
                contents.append(candidate.content)

                tool_results = []
                for part in tool_calls:
                    fn_name = part.function_call.name
                    fn_args = dict(part.function_call.args) if part.function_call.args else {}
                    
                    # Hard intercept logic to prevent any unauthorized database reads!
                    if fn_name not in ["search_faq", "get_current_time", "calculator"]:
                        uid = str(message.user_id).strip().lower() if message.user_id else ""
                        if not uid or uid in ("none", "null", "undefined"):
                            print(f"[AUTH BLOCK] Blocked unauthorized tool access to {fn_name}")
                            return ChatResponse(
                                reply="You need to be logged in to securely access out store databases. Please sign in.",
                                history=[],
                                requires_auth=True
                            )
                        
                        # Validate resource ownership dynamically without trusting the AI
                        if fn_name in ["get_order_status", "get_order_details", "cancel_order", "update_order_address", "update_order_quantity"]:
                            order_id = fn_args.get("order_id")
                            import database as db
                            order = db.orders.get(order_id)
                            # If order exists but it doesn't belong to this user, block it!
                            if order and order.get("user_id") != message.user_id:
                                error_msg = f"Error: You do not have permission to access order #{order_id}."
                                tool_results.append(types.Part(
                                    function_response=types.FunctionResponse(name=fn_name, response={"result": error_msg})
                                ))
                                continue
                                
                    if fn_name in ["get_user_details", "get_user_coupons"]:
                        fn_args["user_id"] = message.user_id
                        
                    fn      = TOOL_MAP.get(fn_name)

                    if fn:
                        try:
                            result = fn(**fn_args)
                        except Exception as e:
                            result = f"Error during tool execution: {str(e)}"
                    else:
                        result = f"Error: Tool '{fn_name}' not available."

                    # If an order-related tool returned a non-error string, mark it as
                    # authorized data retrieved so the model is allowed to mention
                    # order information in subsequent replies.
                    order_tools = {"get_order_status", "get_order_details", "cancel_order", "update_order_address", "update_order_quantity"}
                    if fn_name in order_tools:
                        try:
                            result_text = str(result)
                        except Exception:
                            result_text = ""
                        if result_text and not result_text.lower().startswith("error"):
                            authorized_order_data_retrieved = True

                    tool_results.append(
                        types.Part(
                            function_response=types.FunctionResponse(
                                name=fn_name,
                                response={"result": str(result)},
                            )
                        )
                    )

                # Add the results of the tool calls to contents
                contents.append(
                    types.Content(role="tool", parts=tool_results)
                )
                continue  # Loop back to let the model process results

            # No tool calls - final text response
            reply = response.text or "I'm ready to help with something else."

            # Safety filter: Prevent the model from disclosing any personal/order
            # information in plain text when the user is NOT logged in. The agent
            # is allowed to answer FAQ knowledge without login, but must not
            # invent or reveal order details. If the reply contains sensitive
            # order-related keywords and no `user_id` is present, require login.
            import re
            sensitive_re = re.compile(r"\b(order|order\s+#|order\s+id|order\s+status|tracking|shipment|shipped|delivered|invoice|purchase)\b", re.I)
            if (not message.user_id) and sensitive_re.search(reply or ""):
                return ChatResponse(
                    reply="You need to be logged in to access personal order information. Please sign in.",
                    history=[],
                    requires_auth=True
                )
            # If the reply mentions orders but we did NOT retrieve authorized
            # order data for this user, block the reply to prevent leaking other
            # users' order details (covers cases where the model hallucinated
            # details instead of using the authorized tools).
            if sensitive_re.search(reply or "") and not authorized_order_data_retrieved:
                return ChatResponse(
                    reply="You do not have permission to access that order. Please check the order ID or sign in as the correct user.",
                    history=[],
                    requires_auth=False
                )
            break
        else:
            reply = "I'm sorry, I reached my maximum processing limit for this request."
        # ── End of loop ────────────────────────────────────

        # Finalize history
        contents.append(
            types.Content(role="model", parts=[types.Part(text=reply)])
        )
        sessions[session_id] = contents

        # Safe serialization for frontend
        serialized = []
        for msg in contents:
            if msg.role in ("user", "model") and msg.parts:
                # Only include parts that have text
                for p in msg.parts:
                    if hasattr(p, 'text') and p.text:
                        serialized.append(HistoryEntry(role=msg.role, text=p.text))
                        break # Only take first text part per message

        return ChatResponse(reply=reply, history=serialized, requires_auth=False)

    except Exception as e:
        # Return a friendly error response instead of crashing with 500
        return ChatResponse(
            reply=f"⚠️ **Assistant Error:** I encountered a technical problem while processing that. Please try again or ask for something else.",
            history=[],
            requires_auth=False
        )


@app.delete("/chat/{session_id}")
async def clear_history(session_id: str):
    sessions.pop(session_id, None)
    return {"message": "Chat history cleared."}


@app.get("/health")
async def health():
    return {
        "status": "online",
        "model": MODEL,
        "tools_active": list(TOOL_MAP.keys())
    }
