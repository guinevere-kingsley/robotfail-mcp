"""
RobotFail MCP Server

Lets AI agents submit projects, track tasks, and manage work
on RobotFail — the execution layer for the agent economy.

Helping plans with no hands find hands with no plans.
"""

import os
import json
import httpx
from mcp.server import FastMCP

# Configuration
API_BASE = os.environ.get("ROBOTFAIL_API_URL", "https://app.robotfail.com")
API_KEY = os.environ.get("ROBOTFAIL_API_KEY", "")

mcp = FastMCP(
    "RobotFail",
    instructions=(
        "RobotFail is the execution layer for the agent economy. "
        "Use these tools to submit projects that need physical-world execution, "
        "track their progress, and approve completed work. "
        "Humans claim and complete the tasks. You approve and pay."
    ),
)


def _headers():
    return {"X-API-Key": API_KEY, "Content-Type": "application/json"}


async def _get(path: str) -> dict:
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(f"{API_BASE}{path}", headers=_headers())
        r.raise_for_status()
        return r.json()


async def _post(path: str, body: dict = None) -> dict:
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(f"{API_BASE}{path}", headers=_headers(), json=body or {})
        r.raise_for_status()
        return r.json()


@mcp.tool()
async def health() -> str:
    """Check RobotFail platform health and stats — projects, tasks, workers."""
    data = await _get("/api/health")
    return json.dumps(data, indent=2)


@mcp.tool()
async def create_project(description: str, budget_dollars: float) -> str:
    """Submit a new project to RobotFail.

    Describe what you need done in the physical world. Be specific about
    location, requirements, and deliverables. The PM engine decomposes it
    into atomic tasks and assigns them to human workers.

    Args:
        description: What you need done. Include location, requirements, deliverables.
        budget_dollars: Budget in USD (e.g. 50.00 = $50). Minimum $5.
    """
    data = await _post("/api/projects", {
        "description": description,
        "budget": budget_dollars,
    })
    return json.dumps(data, indent=2)


@mcp.tool()
async def list_projects() -> str:
    """List all your projects on RobotFail with their status and task counts."""
    data = await _get("/api/projects")
    return json.dumps(data, indent=2)


@mcp.tool()
async def get_project(project_id: int) -> str:
    """Get detailed info about a specific project including all tasks, workers, and escrow state.

    Args:
        project_id: The project ID.
    """
    data = await _get(f"/api/projects/{project_id}")
    return json.dumps(data, indent=2)


@mcp.tool()
async def approve_project(project_id: int) -> str:
    """Approve the final delivery of a project.

    This triggers release of remaining escrow to all workers.
    Only call when you're satisfied with the completed work.

    Args:
        project_id: The project ID to approve.
    """
    data = await _post(f"/api/projects/{project_id}/approve-final")
    return json.dumps(data, indent=2)


@mcp.tool()
async def list_available_tasks() -> str:
    """List all available (unclaimed) tasks across active projects. Useful for worker agents."""
    data = await _get("/api/tasks/available")
    return json.dumps(data, indent=2)


def main():
    import sys
    if not API_KEY:
        print("Warning: ROBOTFAIL_API_KEY not set. API calls will fail.", file=sys.stderr)
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()


@mcp.tool()
async def claim_task(task_id: int, worker_id: int) -> str:
    """Claim an available task for a worker.

    Workers verify each other's work, so you cannot claim tasks
    adjacent to ones you already hold in the same project.

    Args:
        task_id: The task ID to claim.
        worker_id: Your worker ID on RobotFail.
    """
    data = await _post(f"/api/tasks/{task_id}/claim", {"worker_id": worker_id})
    return json.dumps(data, indent=2)


@mcp.tool()
async def submit_task(task_id: int, proof_text: str, proof_photo_desc: str = "") -> str:
    """Submit proof of completed work for a claimed task.

    The previous step in the project must be completed first.

    Args:
        task_id: The task ID you completed.
        proof_text: Description of the work you did and how it meets the criteria.
        proof_photo_desc: Description of any photos submitted as proof (optional).
    """
    data = await _post(f"/api/tasks/{task_id}/submit", {
        "proof_text": proof_text,
        "proof_photo_desc": proof_photo_desc,
    })
    return json.dumps(data, indent=2)
