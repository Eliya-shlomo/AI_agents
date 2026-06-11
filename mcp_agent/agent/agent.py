import json
import os
import subprocess
from openai import OpenAI
from dotenv import load_dotenv
from mcp_server.k8s_client import (
    get_pods,
    get_pod_logs,
    get_pod_events,
    get_deployment_status
)
from mcp_server.server import (
    list_pods,
    fetch_pod_logs,
    fetch_pod_events,
    check_deployments,
    diagnose_namespace
)
from agent.prompts import SYSTEM_PROMPT

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Tool definitions - OpenAI reads these to decide which function to call
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "list_pods",
            "description": "List all pods in a namespace with status and restart count.",
            "parameters": {
                "type": "object",
                "properties": {
                    "namespace": {
                        "type": "string",
                        "default": "production",
                        "description": "Kubernetes namespace"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_pod_logs",
            "description": "Fetch logs from a pod. Use previous=True for crashed containers.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pod_name": {"type": "string"},
                    "namespace": {"type": "string", "default": "production"},
                    "lines": {"type": "integer", "default": 50},
                    "previous": {
                        "type": "boolean",
                        "default": False,
                        "description": "Fetch logs from previous crashed container"
                    }
                },
                "required": ["pod_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_pod_events",
            "description": "Get Kubernetes events for a pod. Reveals OOMKills, probe failures.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pod_name": {"type": "string"},
                    "namespace": {"type": "string", "default": "production"}
                },
                "required": ["pod_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_deployments",
            "description": "Get deployment health: desired vs ready replicas.",
            "parameters": {
                "type": "object",
                "properties": {
                    "namespace": {"type": "string", "default": "production"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "diagnose_namespace",
            "description": "Full namespace diagnosis. Returns deployments + pods + logs + events for unhealthy pods. Use this first.",
            "parameters": {
                "type": "object",
                "properties": {
                    "namespace": {"type": "string", "default": "production"}
                }
            }
        }
    }
]

# Maps tool name string to actual function
TOOL_MAP = {
    "list_pods": list_pods,
    "fetch_pod_logs": fetch_pod_logs,
    "fetch_pod_events": fetch_pod_events,
    "check_deployments": check_deployments,
    "diagnose_namespace": diagnose_namespace
}


def run_tool(tool_name: str, tool_args: dict) -> str:
    """Execute a tool and return result as JSON string"""
    func = TOOL_MAP.get(tool_name)
    if not func:
        return json.dumps({"error": f"Unknown tool: {tool_name}"})

    try:
        result = func(**tool_args)
        return json.dumps(result, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


def ask_agent(question: str) -> str:
    """
    Main agent loop:
    1. Send question to GPT-4o with tools
    2. If model calls a tool - execute it and feed result back
    3. Repeat until model returns a final text answer (no more tool calls)
    """
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question}
    ]

    print(f"\nQuestion: {question}")
    print("-" * 50)

    # Agentic loop - keeps running until no more tool calls
    while True:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            tools=TOOLS,
            tool_choice="auto"   # model decides when to use tools
        )

        message = response.choices[0].message

        # No tool calls = final answer
        if not message.tool_calls:
            return message.content

        # Process all tool calls the model requested
        print(f"Tools called: {[tc.id for tc in message.tool_calls]}")
        messages.append(message)

        for tool_call in message.tool_calls:
            tool_name = tool_call.function.name
            tool_args = json.loads(tool_call.function.arguments)

            print(f"  -> {tool_name}({tool_args})")
            result = run_tool(tool_name, tool_args)

            # Feed tool result back to the model
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result
            })


