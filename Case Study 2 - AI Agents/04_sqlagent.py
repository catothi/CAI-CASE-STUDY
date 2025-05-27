import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage
from langchain_mongodb.chat_message_histories import MongoDBChatMessageHistory
from langchain_community.utilities import SQLDatabase
from langchain_community.tools.sql_database.tool import QuerySQLDatabaseTool, ListSQLDatabaseTool
from langchain.agents import create_react_agent, AgentExecutor
from langchain_core.prompts import PromptTemplate
from langchain_core.tools import BaseTool
from pydantic import Field

# Load environment variables from the .env file
env_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path=env_path)

# Read important variables from the environment
MONGODB_URI = os.getenv("MONGODB_URI")
MONGODB_DATABASE = os.getenv("MONGODB_DATABASE")
MONGODB_COLLECTION = os.getenv("MONGODB_COLLECTION")
DATABASE_URL = os.getenv("DATABASE_URL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CHAT_MODEL = os.getenv("CHAT_MODEL", "gpt-3.5-turbo")
CHAT_TEMPERATURE = float(os.getenv("CHAT_TEMPERATURE", 0.7))
SESSION_ID = "session_123"

# Error if mandatory fields are missing
if not all([MONGODB_URI, MONGODB_DATABASE, MONGODB_COLLECTION, DATABASE_URL, OPENAI_API_KEY]):
    raise ValueError("Error: One or more environment variables are missing!")

# Initialize chat model & message history
try:
    chat = ChatOpenAI(model=CHAT_MODEL, temperature=CHAT_TEMPERATURE, api_key=OPENAI_API_KEY)
    history = MongoDBChatMessageHistory(
        session_id=SESSION_ID,
        connection_string=MONGODB_URI,
        database_name=MONGODB_DATABASE,
        collection_name=MONGODB_COLLECTION
    )
    print("Chat model and message history initialized.")
except Exception as e:
    raise Exception(f"Error initializing chat or history: {e}")

# Initialize PostgreSQL database connection
try:
    db = SQLDatabase.from_uri(DATABASE_URL)
    print("Database connection established. Tables:", db.get_usable_table_names())
except Exception as e:
    raise Exception(f"Error connecting to database: {e}")

def execute_sql_query(query: str, db) -> str:
    """Execute an SQL query and return results or an error message."""
    try:
        result = db.run(query)
        return str(result) if result else "No result found."
    except Exception as e:
        return f"Error during SQL query: {str(e)}"

def list_schemas(db) -> str:
    """List all schemas in the database."""
    query = """
    SELECT schema_name, schema_owner,
           CASE
               WHEN schema_name LIKE 'pg_%' THEN 'System Schema'
               WHEN schema_name = 'information_schema' THEN 'System Information Schema'
               ELSE 'User Schema'
           END as schema_type
    FROM information_schema.schemata
    ORDER BY schema_type, schema_name
    """
    return execute_sql_query(query, db)

def list_objects(schema_name: str, object_type: str, db) -> str:
    """List objects in a schema (tables, views, sequences, extensions)."""
    if not schema_name:
        return "Error: Schema name not specified."
    if not object_type:
        object_type = "table"
    if object_type not in ["table", "view", "sequence", "extension"]:
        return f"Error: Unsupported object type: {object_type}"

    if object_type in ("table", "view"):
        table_type = "BASE TABLE" if object_type == "table" else "VIEW"
        query = f"""
        SELECT table_schema, table_name, table_type
        FROM information_schema.tables
        WHERE table_schema = '{schema_name}' AND table_type = '{table_type}'
        ORDER BY table_name
        """
        result = execute_sql_query(query, db)
        if "No result found." in result:
            return f"No {object_type}s found in schema '{schema_name}'."
        return result
    elif object_type == "sequence":
        query = f"""
        SELECT sequence_schema, sequence_name, data_type
        FROM information_schema.sequences
        WHERE sequence_schema = '{schema_name}'
        ORDER BY sequence_name
        """
        return execute_sql_query(query, db)
    else:  # extension
        query = """
        SELECT extname, extversion, extrelocatable
        FROM pg_extension
        ORDER BY extname
        """
        return execute_sql_query(query, db)

def get_object_details(schema_name: str, object_name: str, object_type: str, db) -> str:
    """Get detailed information about a database object."""
    if not schema_name:
        return "Error: Schema name not specified."
    if not object_name or object_name.strip() == "":
        return "Error: Object name not specified."
    if not object_type:
        object_type = "table"
    if object_type not in ["table", "view", "sequence", "extension"]:
        return f"Error: Unsupported object type: {object_type}"

    if object_type in ("table", "view"):
        check_query = f"""
        SELECT COUNT(*)
        FROM information_schema.tables
        WHERE table_schema = '{schema_name}' AND table_name = '{object_name}'
        """
        check_result = execute_sql_query(check_query, db)
        if "No result found." in check_result or "0" in check_result: # Check if table exists
            return f"Error: Table '{object_name}' not found in schema '{schema_name}'."

        columns_query = f"""
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_schema = '{schema_name}' AND table_name = '{object_name}'
        ORDER BY ordinal_position
        """
        constraints_query = f"""
        SELECT tc.constraint_name, tc.constraint_type, kcu.column_name
        FROM information_schema.table_constraints AS tc
        LEFT JOIN information_schema.key_column_usage AS kcu
          ON tc.constraint_name = kcu.constraint_name
         AND tc.table_schema = kcu.table_schema
        WHERE tc.table_schema = '{schema_name}' AND tc.table_name = '{object_name}'
        """
        indexes_query = f"""
        SELECT indexname, indexdef
        FROM pg_indexes
        WHERE schemaname = '{schema_name}' AND tablename = '{object_name}'
        """
        columns_result = execute_sql_query(columns_query, db)
        constraints_result = execute_sql_query(constraints_query, db)
        indexes_result = execute_sql_query(indexes_query, db)
        return f"Columns: {columns_result}\nConstraints: {constraints_result}\nIndexes: {indexes_result}"
    elif object_type == "sequence":
        query = f"""
        SELECT sequence_schema, sequence_name, data_type, start_value, increment
        FROM information_schema.sequences
        WHERE sequence_schema = '{schema_name}' AND sequence_name = '{object_name}'
        """
        return execute_sql_query(query, db)
    else:  # extension
        query = f"""
        SELECT extname, extversion, extrelocatable
        FROM pg_extension
        WHERE extname = '{object_name}'
        """
        return execute_sql_query(query, db)

# LangChain-compatible Tools
class ListSchemasTool(BaseTool):
    name: str = "list_schemas"
    description: str = "List all schemas in the database."

    def __init__(self, db_instance):
        super().__init__()
        object.__setattr__(self, 'db', db_instance)

    def _run(self, query: str = "") -> str:
        return list_schemas(self.db)

    async def _arun(self, query: str = "") -> str:
        return self._run(query)

class ListObjectsTool(BaseTool):
    name: str = "list_objects"
    description: str = "List objects (tables, views, sequences, extensions) in a specific schema."

    def __init__(self, db_instance):
        super().__init__()
        object.__setattr__(self, 'db', db_instance)

    def _run(self, schema_name: str = "public", object_type: str = "table") -> str:
        if not schema_name:
            return "Error: Schema name not specified."
        schema_name = schema_name.split("=")[-1].strip("'") if "=" in schema_name else schema_name
        object_type = object_type.split("=")[-1].strip("'") if "=" in object_type else object_type
        if not object_type:
            object_type = "table"
        return list_objects(schema_name, object_type, self.db)

    async def _arun(self, schema_name: str = "public", object_type: str = "table") -> str:
        return self._run(schema_name, object_type)

class GetObjectDetailsTool(BaseTool):
    name: str = "get_object_details"
    description: str = "Get detailed information (columns, constraints, indexes) about a specific database object."

    def __init__(self, db_instance):
        super().__init__()
        object.__setattr__(self, 'db', db_instance)

    def _run(self, schema_name: str = "public", object_name: str = "", object_type: str = "table") -> str:
        schema_name = schema_name.split("=")[-1].strip("'") if "=" in schema_name else schema_name
        object_name = object_name.split("=")[-1].strip("'") if "=" in object_name else object_name
        object_type = object_type.split("=")[-1].strip("'") if "=" in object_type else object_type
        if not object_name or object_name.strip() == "":
            return "Error: Object name not specified."
        if not object_type:
            object_type = "table"
        return get_object_details(schema_name, object_name, object_type, self.db)

    async def _arun(self, schema_name: str = "public", object_name: str = "", object_type: str = "table") -> str:
        return self._run(schema_name, object_name, object_type)

# Tools for the React agent
query_tool = QuerySQLDatabaseTool(db=db)
list_tables_tool = ListSQLDatabaseTool(db=db) # Note: This tool is initialized but not explicitly described in the main prompt.
list_schemas_tool = ListSchemasTool(db)
list_objects_tool = ListObjectsTool(db)
get_object_details_tool = GetObjectDetailsTool(db)
tools = [query_tool, list_tables_tool, list_schemas_tool, list_objects_tool, get_object_details_tool]

# Prompt for the React agent
SQL_PROMPT = PromptTemplate.from_template(
    """
    You are an expert SQL assistant that answers user questions by generating and executing SQL queries based on the database schema.
    Your goal is to:
    - Identify available schemas in the database using 'list_schemas'.
    - Find relevant schemas and objects contained within them (tables, views, etc.) using 'list_objects'.
    - Query detailed information about relevant objects (columns, constraints, indexes) using 'get_object_details'.
    - Generate a syntactically correct SQL query to answer the question.
    - **ABSOLUTELY execute the query using the 'sql_db_query' tool to retrieve the result. This is a mandatory step to answer the user's request.**
    - Ensure that the result matches the question.
    If the query fails, analyze the error, correct the query, and try again.

    Question: {question}
    Schema: {schema}

    Available Tools:
    {tools}

    Tool Names: {tool_names}

    Follow this process and strictly adhere to the format. Use exactly the following labels without additional numbers, dots, or text:
    Thought: [Explain what you will do next, e.g., list schemas, investigate objects, or formulate a query]
    Action: [Name of the tool, e.g., list_schemas, list_objects, get_object_details, or sql_db_query]
    Action Input: [The input for the tool, e.g., schema_name='public', object_type='table', or an SQL query]
    Observation: [The result of the tool or the error that occurs]
    Thought: [Analyze the result or the error and decide what to do next]
    Repeat the steps until you have a final answer.
    Final Answer: [The result of the query, e.g., 'There are 5 orders this month.' Return ONLY the result of the SQL query and NEVER just the SQL code.]

    Important Note for PostgreSQL:
    - You are working with a PostgreSQL database. Use PostgreSQL-specific functions like CURRENT_DATE instead of CURDATE().
    - Always start by listing the schemas with 'list_schemas' to get an overview.
    - Use 'list_objects' to find relevant tables or other objects in a schema (e.g., with schema_name='public' and object_type='table').
    - Use 'get_object_details' to get detailed information about a table or object (e.g., columns, indexes) before formulating a query.
    - Ensure that 'Action Input' is always in the format 'parameter=value' when parameters are specified.
    - If a tool returns an error (e.g., "Error: Object name not specified."), check the inputs and ensure all required parameters are correctly specified.
    - If a table or object is not found (e.g., error message like "Table not found"), check other schemas with 'list_objects' or inform the user that the object does not exist.
    - Do not repeat the same action more than twice for repeated errors. If a tool like 'get_object_details' repeatedly fails, use the 'sql_db_query' tool to directly execute an SQL query (e.g., SELECT * FROM information_schema.columns WHERE table_schema='schema_name' AND table_name='table_name'), or provide a final answer with an explanation of the problem.
    - In SQL queries, always specify the schema explicitly (e.g., 'cd.members' instead of just 'members') to avoid errors like "Relation does not exist". If an error like "Relation does not exist" occurs, check the schema and correct the query accordingly.
    - **Important: Once an SQL query is formulated, it MUST be executed with 'sql_db_query'. Under no circumstances return only the SQL code as 'Final Answer'. If execution fails, analyze the error and try again with a corrected query.**

    Scratchpad for intermediate steps:
    {agent_scratchpad}
    """
)

# Initialize React agent and executor
try:
    agent = create_react_agent(
        llm=chat,
        tools=tools,
        prompt=SQL_PROMPT,
    )
    executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        max_iterations=100,
        max_execution_time=600,
        handle_parsing_errors=True,
    )
    print("Agent and executor initialized successfully.")
except Exception as e:
    raise Exception(f"Error initializing agent/executor: {e}")

system_message = SystemMessage(
    content="You are a helpful chatbot. Always answer in a friendly manner and in English." 
)

print("Welcome! Type 'quit' to exit.")

while True:
    try:
        user_input = input("You: ")
        if user_input.strip().lower() == "quit":
            print("Session ended.")
            break
        if not user_input.strip():
            print("Please enter something!")
            continue

        chat_history = history.messages
        if not chat_history or not isinstance(chat_history[0], SystemMessage):
            chat_history = [system_message] + chat_history

        chat_history.append(HumanMessage(content=user_input))

        db_keywords = ["revenue", "data", "query", "last month", "customers", "orders", "schema", "table", "index", "object", "member", "association", "sql","postgreSQL", "postgresql", "database", "column", "constraint", "view", "sequence", "extension"]
        if any(keyword in user_input.lower() for keyword in db_keywords):
            schema = "Initial schema unknown, use tools to discover schemas, objects, and details." # This string was already in English.
            print(f"Processing database-related request: {user_input}")
            result = executor.invoke({"question": user_input, "schema": schema})
            output = result.get('output', 'No result returned.')
            print(f"AI: {output}")
            history.add_ai_message(output)
        else:
            print(f"Processing general request: {user_input}")
            response = chat.invoke(chat_history)
            print(f"AI: {response.content}")
            history.add_ai_message(response.content)

        history.add_user_message(user_input)
    except Exception as e:
        print(f"An error occurred: {e}")