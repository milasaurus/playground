from client import client
from chatbot.api.history import HistoryHandler
from chatbot.api.messages import MessageHandler
from chatbot.usage_tracking.tracker import UsageTracker

EXIT_COMMAND = "quit"

def run_chat(handler, tracker, input_fn=input, print_fn=print):
    while True:
        user_input = input_fn("\nYou: ")
        if user_input == EXIT_COMMAND:
            print_fn(tracker.report())
            break

        response = handler.send(user_input)
        print_fn(f"\nClaude: {response}")
        print_fn(f"\n(Type '{EXIT_COMMAND}' to exit)")


if __name__ == "__main__":
    history = HistoryHandler()
    tracker = UsageTracker()
    handler = MessageHandler(client, history, tracker)
    run_chat(handler, tracker)
