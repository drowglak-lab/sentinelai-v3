import asyncio
from fastapi import FastAPI, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field
from typing import List, Dict, Any

from core.sub_manager import SubinterpreterManager
from execution.policy_engine import ActionFirewall

app = FastAPI(title="SentinelAI v3.0: Control Plane")

class ToolCall(BaseModel):
    name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)

class AgentRequest(BaseModel):
    prompt: str
    tool_calls: List[ToolCall] = Field(default_factory=list)

class AgentIdentity(BaseModel):
    id: str
    permissions: List[str]

async def get_current_agent(x_agent_token: str = Header(...)) -> AgentIdentity:
    """Mock identity resolution."""
    if x_agent_token != "valid_secret_token":
        raise HTTPException(status_code=401, detail="Invalid token.")
    return AgentIdentity(
        id="bot_01", 
        # Fixed: now the permissions exactly match the tool names from JSON
        permissions=["read_balance", "transfer_funds"] 
    )

@app.post("/v1/agent/execute", response_model=dict)
async def handle_agent_request(
    payload: AgentRequest, 
    agent: AgentIdentity = Depends(get_current_agent)
):
    try:
        clean_prompt = await SubinterpreterManager.run_task_async(
            module_path="security.pii_scrub", 
            function_name="scrub_pii", 
            data=payload.prompt
        )
    except Exception as e:
         raise HTTPException(status_code=500, detail="Shield layer failure.")

    firewall = ActionFirewall(agent.model_dump())
    
    for tool in payload.tool_calls:
        auth_status = firewall.validate_action(tool.model_dump())
        if auth_status.get("decision") == "DENIED":
            raise HTTPException(
                status_code=403,
                detail={"error": auth_status.get("reason"), "action": tool.name}
            )

    return {
        "status": "SUCCESS",
        "scrubbed_content": clean_prompt,
        "authorized_actions": [t.name for t in payload.tool_calls]
    }
