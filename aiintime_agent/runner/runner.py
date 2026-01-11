from google.adk.runners import Runner, types
from aiintime_agent.config import get_config
from aiintime_agent.agent import get_agent
from aiintime_agent.services.session import RedisSessionService
from aiintime_agent.services.memory import RedisMemoryService

class AgentRunner:
    def __init__(self):
        self.app_config = get_config().app
        self.agent_config = get_config().agent
        self.app_name = f"{self.app_config.name}_{self.agent_config.name}"
        self.runner = None

    def initialize_runner(self):
        try:
            self.runner = Runner(
            app_name=self.app_name,
            agent=get_agent(),
            session_service=RedisSessionService(), 
            memory_service=RedisMemoryService()
        )            
        except Exception as e:
            print(f"Failed to initialize Runner: {e}")
            raise e
    
    async def create_new_session(
        self, 
        user_id: str,
        session_id: str
    ):
        try:
            await self.runner.session_service.create_session(
                app_name=self.app_name,
                session_id=session_id,
                user_id=user_id
            )  
        except Exception as e:
            print(f"Failed to create new session: {e}")
            raise e
    
    async def run_async_chat(
        self,
        parent_session_id: str,
        session_id: str,
        user_id: str,
        message: str
    ):
        try:
            # Construct Content object
            message = types.Content(parts=[types.Part.from_text(text=message)])
            ctx = {
                "user_id" : user_id,
                "parent_session_id": parent_session_id
            }
            async for event in self.runner.run_async(
                user_id=user_id,
                session_id=session_id,
                new_message=message,
                state_delta=ctx
            ):
                if event.content:
                    for part in event.content.parts:
                        if part.text:
                            print("🧠 MODEL:", part.text)

                        if part.function_call:
                            print("🔧 TOOL CALL:")
                            print("  name:", part.function_call.name)
                            print("  args:", part.function_call.args)

                        if part.function_response:
                            print("📦 TOOL RESPONSE:")
                            result = part.function_response.response.get("result")
                            if result:
                                if hasattr(result, "isError"):
                                    print("  isError:", result.isError)
                                    print("  content:", result.content)
                                else:
                                    print("  result:", result)

            # After the generator completes, ingest the updated session into RAG memory
            session = await self.runner.session_service.get_session(
                app_name=self.app_name, 
                user_id=user_id, 
                session_id=session_id
            )
            if session and self.runner.memory_service:
                await self.runner.memory_service.add_session_to_memory(session)            
        except Exception as e:
            print(f"Failed to run async chat: {e}")
            raise e

agent_runner = AgentRunner()