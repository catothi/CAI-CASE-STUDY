#pip install python-dotenv langchain langchain-openai langchain-mongodb
import os
from dotenv import load_dotenv
import os # Note: duplicate import of os, present in original
from dotenv import load_dotenv # Note: duplicate import of load_dotenv, present in original
# Imports only after .env variables are loaded
from langchain_openai import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage
from langchain_mongodb.chat_message_histories import MongoDBChatMessageHistory

# Load environment variables from the .env in the same directory
env_path = os.path.join(os.path.dirname(__file__), ".env")
print(f"Loading .env from {env_path}")
load_dotenv(dotenv_path=env_path)
print("Working directory:", os.getcwd())
print("Files in working directory:", os.listdir())
env_path = os.path.join(os.path.dirname(__file__), ".env") # Note: env_path re-assigned, present in original
print("Does .env exist?", os.path.exists(env_path))
load_dotenv(dotenv_path=env_path) # Note: load_dotenv called again, present in original
print("MONGODB_URI:", repr(os.getenv("MONGODB_URI"))) # Note: This print was here before variable assignments
# Read important variables from the environment
MONGODB_URI = os.getenv("MONGODB_URI")
MONGODB_DATABASE = os.getenv("MONGODB_DATABASE")
MONGODB_COLLECTION = os.getenv("MONGODB_COLLECTION")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CHAT_MODEL = os.getenv("CHAT_MODEL", "gpt-3.5-turbo")
CHAT_TEMPERATURE = float(os.getenv("CHAT_TEMPERATURE", 0.7))
SESSION_ID = "session_123"

# Test output
print("MONGODB_URI:", repr(MONGODB_URI))
print("MONGODB_DATABASE:", repr(MONGODB_DATABASE))
print("MONGODB_COLLECTION:", repr(MONGODB_COLLECTION))
print("OPENAI_API_KEY present?", bool(OPENAI_API_KEY))

# Error if mandatory fields are missing
if not MONGODB_URI:
    raise ValueError("Error: MONGODB_URI not set!")
if not MONGODB_DATABASE:
    raise ValueError("Error: MONGODB_DATABASE not set!")
if not MONGODB_COLLECTION:
    raise ValueError("Error: MONGODB_COLLECTION not set!")
if not OPENAI_API_KEY:
    raise ValueError("Error: OPENAI_API_KEY not set!")



# Initialize chat model & message history
chat = ChatOpenAI(model=CHAT_MODEL, temperature=CHAT_TEMPERATURE, openai_api_key=OPENAI_API_KEY)
history = MongoDBChatMessageHistory(
    session_id=SESSION_ID,
    connection_string=MONGODB_URI,
    database_name=MONGODB_DATABASE,
    collection_name=MONGODB_COLLECTION
)

system_message = SystemMessage(
    content="You are a helpful chatbot. Always answer in a friendly manner and in English. Keep answers concise, no more than 3 sentences unless otherwise requested.  "      
)

print("Welcome! Type 'quit' to exit.")

while True:
    user_input = input("You: ")
    if user_input.strip().lower() == "quit":
        print("Session ended.")
        break
    if not user_input.strip():
        print("Please enter something!")
        continue

    chat_history = history.messages
    # Add system message if necessary
    if not chat_history or not isinstance(chat_history[0], SystemMessage):
        chat_history = [system_message] + chat_history

    chat_history.append(HumanMessage(content=user_input))

    try:
        response = chat.invoke(chat_history)
        print(f"AI: {response.content}")
        history.add_user_message(user_input)
        history.add_ai_message(response.content)
    except Exception as e:
        print(f"An error occurred: {e}")