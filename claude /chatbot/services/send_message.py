from client import client
from chatbot.api.messages import MessageHandler

handler = MessageHandler(client)
response = handler.send("Hello, Claude!")
print(response)
