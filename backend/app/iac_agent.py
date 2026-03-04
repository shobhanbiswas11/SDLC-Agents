#creating reAct agent

from langchain import hub
from langchain.agents import create_react_agent, AgentExecutor
from app.agent_tools import generate_iac, check_policies, fix_iac
from app.llm.factory import get_llm

def create_agent():
    llm = get_llm()

    tools = [
        generate_iac,
        check_policies,
        fix_iac,
    ]

    prompt = hub.pull("hwchase17/react")

    agent = create_react_agent(
        llm=llm.llm,
        tools=tools,
        prompt=prompt
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