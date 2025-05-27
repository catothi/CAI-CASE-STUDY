import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.prompts.chat import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate
)
from langchain.schema import HumanMessage

# Load API-Key
load_dotenv()
if not os.getenv("OPENAI_API_KEY"):
    raise ValueError("Please set OPENAI_API_KEY in your .env file.") # <--- Translated


chat = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.7)

# System-Prompt 
system_template = SystemMessagePromptTemplate.from_template(
    "You are a helpful, English-speaking chatbot. " 
    "Always answer in a friendly and understandable manner." 
)

#  Human-Prompt 
human_template = HumanMessagePromptTemplate.from_template(
    "{user_input}"
)

# Chat-Prompt 
chat_prompt = ChatPromptTemplate.from_messages([
    system_template,
    human_template
])

print("Welcome! Type 'quit' to exit.") # <--- Translated

while True:
    user_input = input("You: ")
    if user_input.lower() == "quit":
        print("Chatbot session ended.") # <--- Translated
        break
    if not user_input.strip():
        print("Please enter a question or a statement!") # <--- Translated
        continue

    # Create message object
    messages = chat_prompt.format_prompt(user_input=user_input).to_messages()

    try:
        # invoke statt call
        response = chat.invoke(messages)
        print(f"AI: {response.content}")
    except Exception as e:
        print(f"An error occurred: {e}") # <--- Translated