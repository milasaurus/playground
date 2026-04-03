from client import client
from claude_conversation_engine.api.history import HistoryHandler
from claude_conversation_engine.api.messages import MessageHandler
from claude_conversation_engine.usage_tracking.tracker import UsageTracker

EXIT_COMMAND = "quit"

def run_chat(handler, tracker, input_fn=input, print_fn=print):
    while True:
        user_input = input_fn("\nYou: ")
        if user_input == EXIT_COMMAND:
            print_fn(tracker.report())
            break

        print("\nClaude: ", end="", flush=True)
        handler.send(user_input)
        print_fn(f"(Type '{EXIT_COMMAND}' to exit)")


if __name__ == "__main__":
    history = HistoryHandler()
    tracker = UsageTracker()
    handler = MessageHandler(client, history, tracker)
    run_chat(handler, tracker)
