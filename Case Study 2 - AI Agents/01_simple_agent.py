import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage
#pip install python-dotenv langchain langchain-community langchain-openai openai

load_dotenv()

if not os.getenv("OPENAI_API_KEY"):
    raise ValueError("Please set the OPENAI_API_KEY environment variable in a .env file.")

chat = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.7)

print("Welcome to the command-line chatbot! Type 'quit' to exit.")

while True:
    user_input = input("You: ")
    if user_input.lower() == 'quit':
        break
    if not user_input.strip():
        print("Please enter a question or a statement!") # <--- Translated
        continue
    try:
        messages = [HumanMessage(content=user_input)]
        response = chat.invoke(messages)
        print(f"AI: {response.content}")
    except Exception as e:
        print(f"An error occurred: {e}")

print("Chatbot session ended.")


