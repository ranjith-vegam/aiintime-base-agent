from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm

from aiintime_agent.config import get_config
from aiintime_agent.agent.gateway import tools

#Load model config
agent_config = get_config().agent

def get_agent():

    try:
        #Initialize Model
        llm = LiteLlm(
            model=agent_config.model.name,
            api_base=agent_config.model.base_url,
            api_key=agent_config.model.api_key,
        )
    except Exception as e:
        print(f"Failed to initialize Model: {e}")
        return None


    try:
        #Instruction
        with open("aiintime_agent/agent/instruction.txt", "r") as f:
            instruction = f.read()

        #Create Agent
        agent = LlmAgent(
            name=agent_config.name,
            model=llm,
            instruction=instruction,
            tools=tools
        )

        return agent
    
    except Exception as e:
        print(f"Failed to initialize Agent: {e}")
        return None