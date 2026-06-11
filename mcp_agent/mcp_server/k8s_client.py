from kubernetes import client, config
from typing import Optional
import json


def load_k8s_config():
    """Loads configuration – works both locally and inside a cluster."""
    try:
        config.load_incluster_config()  # Running inside K8s
    except:
        config.load_kube_config()       # Running locally with ~/.kube/config


def get_pods(namespace: str = "production") -> dict:
    """Returns a list of Pods with their current status."""
    load_k8s_config()
    v1 = client.CoreV1Api()

    pods = v1.list_namespaced_pod(namespace=namespace)

    result = []
    for pod in pods.items:
        # Information about each container inside the Pod
        container_statuses = []
        if pod.status.container_statuses:
            for cs in pod.status.container_statuses:
                container_statuses.append({
                    "name": cs.name,
                    "ready": cs.ready,
                    "restart_count": cs.restart_count,
                    # Current state – Running/Waiting/Terminated
                    "state": _parse_container_state(cs.state),
                    # Last state – important for diagnosing CrashLoopBackOff
                    "last_state": _parse_container_state(cs.last_state)
                })

        result.append({
            "name": pod.metadata.name,
            "namespace": namespace,
            "phase": pod.status.phase,          # Running/Pending/Failed
            "conditions": _parse_conditions(pod.status.conditions),
            "containers": container_statuses,
            "node": pod.spec.node_name,
            "start_time": str(pod.status.start_time)
        })

    return {"pods": result, "count": len(result)}


def get_pod_logs(pod_name: str, namespace: str = "production",
                 lines: int = 50, previous: bool = False) -> dict:
    """Fetches logs – previous=True retrieves logs from the previous crashed instance."""
    load_k8s_config()
    v1 = client.CoreV1Api()

    try:
        logs = v1.read_namespaced_pod_log(
            name=pod_name,
            namespace=namespace,
            tail_lines=lines,
            previous=previous         # The magic flag for crashed containers
        )
        return {"logs": logs, "pod": pod_name, "previous": previous}
    except Exception as e:
        return {"error": str(e), "pod": pod_name}


def get_pod_events(pod_name: str, namespace: str = "production") -> dict:
    """Events are the most important tool for troubleshooting – K8s logs everything here."""
    load_k8s_config()
    v1 = client.CoreV1Api()

    # Filter events by Pod name
    events = v1.list_namespaced_event(
        namespace=namespace,
        field_selector=f"involvedObject.name={pod_name}"
    )

    result = []
    for event in events.items:
        result.append({
            "type": event.type,               # Normal / Warning
            "reason": event.reason,           # OOMKilling, BackOff, Pulled...
            "message": event.message,
            "count": event.count,
            "first_time": str(event.first_timestamp),
            "last_time": str(event.last_timestamp)
        })

    # Sort by time – latest first
    result.sort(key=lambda x: x["last_time"], reverse=True)
    return {"events": result, "pod": pod_name}


def get_deployment_status(namespace: str = "production") -> dict:
    """Deployment status – number of ready replicas vs desired replicas."""
    load_k8s_config()
    apps_v1 = client.AppsV1Api()

    deployments = apps_v1.list_namespaced_deployment(namespace=namespace)

    result = []
    for d in deployments.items:
        result.append({
            "name": d.metadata.name,
            "desired": d.spec.replicas,
            "ready": d.status.ready_replicas or 0,
            "available": d.status.available_replicas or 0,
            # Healthy = desired equals ready
            "healthy": d.status.ready_replicas == d.spec.replicas
        })

    return {"deployments": result}


# ── Internal Helpers ──────────────────────────────────────────

def _parse_container_state(state) -> dict:
    """Converts ContainerState object to a readable dictionary."""
    if not state:
        return {}
    if state.running:
        return {"status": "running", "started_at": str(state.running.started_at)}
    if state.waiting:
        return {
            "status": "waiting",
            "reason": state.waiting.reason,      # CrashLoopBackOff, ImagePullBackOff...
            "message": state.waiting.message
        }
    if state.terminated:
        return {
            "status": "terminated",
            "exit_code": state.terminated.exit_code,   # 0 = OK, non-zero = error
            "reason": state.terminated.reason,          # OOMKilled, Error, Completed
            "message": state.terminated.message
        }
    return {}


def _parse_conditions(conditions) -> list:
    """Conditions = Health checks of the Pod."""
    if not conditions:
        return []
    return [
        {
            "type": c.type,       # Ready, PodScheduled, ContainersReady
            "status": c.status,   # True / False
            "reason": c.reason
        }
        for c in conditions
    ]