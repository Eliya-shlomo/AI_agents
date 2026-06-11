from mcp.server.fastmcp import FastMCP
from mcp_server.k8s_client import (
    get_pods,
    get_pod_logs,
    get_pod_events,
    get_deployment_status
)

# Creating the MCP Server
# The name "k8s-devops-agent" is what will appear in Claude Desktop / any MCP Client
mcp = FastMCP("k8s-devops-agent")


@mcp.tool()
def list_pods(namespace: str = "production") -> dict:
    """
    List all pods in a namespace with their status and restart count.
    Use this first to get an overview of what's running.
    """
    return get_pods(namespace)


@mcp.tool()
def fetch_pod_logs(
    pod_name: str,
    namespace: str = "production",
    lines: int = 50,
    previous: bool = False
) -> dict:
    """
    Fetch logs from a pod.
    Set previous=True to get logs from a crashed container - essential for CrashLoopBackOff diagnosis.
    """
    return get_pod_logs(pod_name, namespace, lines, previous)


@mcp.tool()
def fetch_pod_events(pod_name: str, namespace: str = "production") -> dict:
    """
    Get Kubernetes events for a pod.
    Events reveal OOMKills, failed pulls, probe failures - always check this during debugging.
    """
    return get_pod_events(pod_name, namespace)


@mcp.tool()
def check_deployments(namespace: str = "production") -> dict:
    """
    Get deployment health: desired vs ready replicas.
    A deployment is unhealthy when ready < desired.
    """
    return get_deployment_status(namespace)


@mcp.tool()
def diagnose_namespace(namespace: str = "production") -> dict:
    """
    Full namespace diagnosis in one shot.
    Returns deployments health + all pods status + events for unhealthy pods.
    Use this when asked 'what's wrong in production?'
    """
    # Step 1 – Deployment status
    deployments = get_deployment_status(namespace)

    # Step 2 – All pods
    pods_data = get_pods(namespace)

    # Step 3 – Fetch logs and events only for problematic pods
    # This saves unnecessary API calls
    unhealthy = []
    for pod in pods_data["pods"]:
        is_unhealthy = False

        # Check each container within the Pod
        for container in pod["containers"]:
            state = container.get("state", {})
            reason = state.get("reason", "")

            # Common problematic statuses
            if reason in ["CrashLoopBackOff", "OOMKilled", "Error", "ImagePullBackOff"]:
                is_unhealthy = True
            if container.get("restart_count", 0) > 2:
                is_unhealthy = True

        if pod["phase"] in ["Failed", "Unknown"]:
            is_unhealthy = True

        if is_unhealthy:
            # Fetch logs and events only for unhealthy pods
            logs = get_pod_logs(pod["name"], namespace, lines=30, previous=True)
            events = get_pod_events(pod["name"], namespace)
            unhealthy.append({
                "pod": pod,
                "logs": logs,
                "events": events
            })

    return {
        "deployments": deployments,
        "total_pods": pods_data["count"],
        "unhealthy_pods": unhealthy,
        "healthy": len(unhealthy) == 0
    }

if __name__ == "__main__":
    # Stdio transport – default for local development
    # The MCP Client (our Agent) will run the server as a subprocess
    mcp.run(transport="stdio")