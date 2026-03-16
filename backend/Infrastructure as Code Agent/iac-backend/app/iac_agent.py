#creating reAct agent

from langchain_classic.agents import create_react_agent, AgentExecutor
from langchain_core.prompts import PromptTemplate
from app.agent_tools import generate_iac, check_policies, fix_iac
from app.llm.factory import get_llm

# Standard ReAct prompt (hwchase17/react) defined locally
# to avoid network dependency on LangChain Hub
REACT_PROMPT = PromptTemplate.from_template(
"""Answer the following questions as best you can. You have access to the following tools:

{tools}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Begin!

Question: {input}
Thought:{agent_scratchpad}""")

def create_agent():
    llm = get_llm()

    tools = [
        generate_iac,
        check_policies,
        fix_iac,
    ]

    agent = create_react_agent(
        llm=llm.llm,
        tools=tools,
        prompt=REACT_PROMPT
    )

    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        handle_parsing_errors=True,
        max_iterations=8,
        return_intermediate_steps=True
    )

    return agent_executor