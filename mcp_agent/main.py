#!/usr/bin/env python3
import sys
import os
from dotenv import load_dotenv

load_dotenv()

# Validate API key exists before starting
if not os.getenv("OPENAI_API_KEY"):
    print("Error: OPENAI_API_KEY not found in .env file")
    sys.exit(1)

from agent.agent import ask_agent

BANNER = """
╔══════════════════════════════════════════════════════╗
║         DevOps AI Agent  |  K8s Troubleshooter      ║
║         Powered by GPT-4o + MCP                     ║
╚══════════════════════════════════════════════════════╝
"""

# Preset questions to demo the agent quickly
QUICK_QUESTIONS = [
    "What is wrong in the production namespace?",
    "Why is payment-service crashing?",
    "Give me a full health report of production",
    "Which pods have the most restarts?"
]


def print_quick_menu():
    print("\nQuick questions:")
    for i, q in enumerate(QUICK_QUESTIONS, 1):
        print(f"  {i}. {q}")
    print("  0. Custom question")
    print()


def main():
    print(BANNER)
    print("Connected to Kubernetes cluster: minikube")
    print("Namespace: production")
    print("-" * 54)

    while True:
        print_quick_menu()

        choice = input("Choose (0-4) or 'q' to quit: ").strip()

        if choice == 'q':
            print("Goodbye.")
            break

        # Resolve question from menu or custom input
        if choice in ["1", "2", "3", "4"]:
            question = QUICK_QUESTIONS[int(choice) - 1]
            print(f"\nAsking: {question}")
        elif choice == "0":
            question = input("Your question: ").strip()
            if not question:
                continue
        else:
            print("Invalid choice.")
            continue

        # Run the agent
        print("\nThinking...\n")
        try:
            answer = ask_agent(question)
            print("\n" + "=" * 54)
            print("AGENT ANSWER:")
            print("=" * 54)
            print(answer)
            print("=" * 54)
        except Exception as e:
            print(f"Error: {e}")

        input("\nPress Enter to continue...")


if __name__ == "__main__":
    main()