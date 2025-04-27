# ai_coin_identifier.py

from dotenv import load_dotenv
import os
from langchain import hub
from langchain.memory import ConversationBufferMemory
from langchain_openai import ChatOpenAI
from langchain.schema import SystemMessage
from langchain.agents import AgentExecutor, create_structured_chat_agent
from langgraph.prebuilt import create_react_agent

load_dotenv()
OPENAI_API_KEY = os.getenv("OPEN_AI_API_KEY")

def initialize_coin_agent():
    system_prompt = (
        "You are an AI that reads a batch of tweet texts and tells me, in a single "
        "token, which cryptocurrency they are referring to. "
        "Valid outputs are exactly one of: "
        "C2FLR, testXRP, testLTC, testXLM, testDOGE, testADA, testALGO, testBTC, "
        "testETH, testFIL, testARB, testAVAX, testBNB, testMATIC, testSOL, testUSDC, "
        "testUSDT, testXDC, testPOL.\n\n"
        "Respond with exactly the one symbol, no punctuation."
    )
    memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
    memory.chat_memory.add_message(SystemMessage(content=system_prompt))
    prompt = hub.pull("hwchase17/structured-chat-agent")
    llm = ChatOpenAI(openai_api_key=OPENAI_API_KEY, model="gpt-4")
    agent = create_structured_chat_agent(llm=llm, tools=[], prompt=prompt)
    executor = AgentExecutor.from_agent_and_tools(
      agent=agent,
      tools=[],
      verbose=False,
      memory=memory,
      handle_parsing_errors=True
    )
    return executor

_coin_agent = None

def identify_coin(tweet_texts):
    global _coin_agent
    if _coin_agent is None:
        _coin_agent = initialize_coin_agent()
    joined = "\n\n---\n\n".join(tweet_texts[:20])
    resp = _coin_agent.invoke({"input": f"Tweets:\n{joined}"})
    return resp.get("output", "").strip()
