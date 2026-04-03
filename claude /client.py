# install deps and load envs
from dotenv import load_dotenv
load_dotenv()
import os
from anthropic import Anthropic

# create the claude client
client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
