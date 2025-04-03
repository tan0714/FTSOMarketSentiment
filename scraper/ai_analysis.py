# ai_analysis.py
from dotenv import load_dotenv
import os
from langchain import hub
from langchain.memory import ConversationBufferMemory
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_structured_chat_agent
from langchain.schema import AIMessage, HumanMessage, SystemMessage
from langgraph.prebuilt import create_react_agent


# Optional: Attempt to import LangGraph for visualization support
try:
    from langgraph import visualize_chain
except ImportError:
    def visualize_chain(agent):
        print("LangGraph not installed or not available.")
        return

# Load environment variables from .env file
load_dotenv()
OPEN_AI_API_KEY = os.environ.get("OPEN_AI_API_KEY")

def initialize_tweet_analyzer():
    """
    Initialize an AI agent using LangChain and LangGraph to analyze tweet content.
    The agent outputs a deletion likelihood score (0-1) based on controversy and provides
    suggestions to adapt HTML extraction if needed.
    """
    system_prompt = (
        "You are an AI tweet analyzer. Your job is to analyze the tweet content and output "
        "a likelihood score between 0 and 1 for the tweet being deleted based on its controversial nature. "
        "If the HTML structure is non-standard, include suggestions for adapting the extraction process. "
        "Provide your answer as 'Score: <number>' followed by any analysis notes."
    )
    
    memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
    memory.chat_memory.add_message(SystemMessage(content=system_prompt))
    
    # Load a structured chat prompt from the LangChain hub
    prompt = hub.pull("hwchase17/structured-chat-agent")
    
    llm = ChatOpenAI(openai_api_key=OPEN_AI_API_KEY, model="gpt-4")
    agent = create_structured_chat_agent(llm=llm, tools=[], prompt=prompt)
    agent_executor = AgentExecutor.from_agent_and_tools(
        agent=agent,
        tools=[],  # No additional tools are used in this analysis
        verbose=True,
        memory=memory
    )
    
    # Visualize the chain with LangGraph (if available)
    try:
        visualize_chain(agent)
    except Exception as e:
        print("LangGraph visualization not available:", e)
    
    return agent_executor

def analyze_tweet(tweet_content, agent_executor=None):
    """
    Analyze the tweet content and return a deletion likelihood score (0-1)
    along with the full AI analysis text.
    """
    if agent_executor is None:
        agent_executor = initialize_tweet_analyzer()
    
    query = (
        f"Analyze this tweet and output a deletion likelihood score (0 to 1) "
        f"for it being deleted due to controversy. Tweet: {tweet_content}"
    )
    response = agent_executor.invoke({"input": query})
    output_text = response.get("output", "")
    
    # Naively parse the output to extract a score between 0 and 1.
    score = None
    for part in output_text.split():
        try:
            val = float(part)
            if 0 <= val <= 1:
                score = val
                break
        except:
            continue
    if score is None:
        score = 0.0  # Default fallback if no valid score is found
    
    return score, output_text
