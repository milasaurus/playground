# Shared Anthropic client, imported by any dir that needs Claude API access
from dotenv import load_dotenv
load_dotenv()
import os
from anthropic import Anthropic

client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
