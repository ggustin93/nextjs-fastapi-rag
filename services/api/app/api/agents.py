"""Agent management API endpoints."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from packages.core.agents import ensure_agents_registered, get_agent_config, list_agents

router = APIRouter(prefix="/agents", tags=["agents"])


class AgentInfo(BaseModel):
    """Agent information response."""

    id: str
    name: str
    icon: str
    description: str


class SwitchResponse(BaseModel):
    """Agent switch response."""

    switched_to: str
    agent: AgentInfo


@router.get("", response_model=list[AgentInfo])
async def get_agents() -> list[AgentInfo]:
    """List all available agents.

    Returns:
        List of agent information.
    """
    ensure_agents_registered()
    return [AgentInfo(**agent) for agent in list_agents()]


@router.get("/current", response_model=AgentInfo)
async def get_current_agent() -> AgentInfo:
    """Get the currently active agent.

    Note: This endpoint requires the AgentSwitcher to be initialized
    in the app state. Returns the default agent if not initialized.
    """
    from services.api.app.main import app_state

    ensure_agents_registered()

    if hasattr(app_state, "agent_switcher"):
        config = app_state.agent_switcher.get_current_config()
        if config:
            return AgentInfo(
                id=config.id,
                name=config.name,
                icon=config.icon,
                description=config.description,
            )

    # Fallback to default
    config = get_agent_config("rag")
    if config:
        return AgentInfo(
            id=config.id,
            name=config.name,
            icon=config.icon,
            description=config.description,
        )

    raise HTTPException(status_code=500, detail="No agent configured")


@router.post("/switch/{agent_id}", response_model=SwitchResponse)
async def switch_agent(agent_id: str) -> SwitchResponse:
    """Switch to a different agent.

    Args:
        agent_id: The ID of the agent to switch to.

    Returns:
        Confirmation of the switch with agent info.

    Raises:
        HTTPException: If the agent ID is not found.
    """
    from services.api.app.main import app_state

    ensure_agents_registered()

    config = get_agent_config(agent_id)
    if not config:
        available = [a["id"] for a in list_agents()]
        raise HTTPException(
            status_code=404,
            detail=f"Agent '{agent_id}' not found. Available: {available}",
        )

    # Switch the agent
    if hasattr(app_state, "agent_switcher"):
        app_state.agent_switcher.switch_to(agent_id)

    return SwitchResponse(
        switched_to=config.id,
        agent=AgentInfo(
            id=config.id,
            name=config.name,
            icon=config.icon,
            description=config.description,
        ),
    )
