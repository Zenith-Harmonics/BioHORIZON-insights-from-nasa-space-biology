from openai import AsyncOpenAI
from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from services.env import OPENAI_URL, LLM_MODEL, API_KEY
from services.prompts import SYSTEM_PROMPT, INSTRUCTIONS, SYSTEM_PROMPT_TITLE


class ResponseType(BaseModel):
    FINAL_RESPONSE: str


class Summarizer:
    def __init__(self):
        print("Sumamarizer using: " + OPENAI_URL)
        print("LLM model: ", LLM_MODEL)

        self.client = AsyncOpenAI(
            api_key=API_KEY, base_url=OPENAI_URL,
        )
        self.llm = OpenAIChatModel(
            model_name=LLM_MODEL, provider=OpenAIProvider(openai_client=self.client)
        )

        self.system_prompt = SYSTEM_PROMPT
        self.instructions = INSTRUCTIONS

        self.agent = Agent(
            model=self.llm,
            # instructions=self.instructions,
            system_prompt=self.system_prompt,
            output_type=ResponseType,
        )

    def summarize(self, input_paper: str) -> str:
        summary = self.agent.run_sync(input_paper)
        return summary.output.FINAL_RESPONSE

    
class TitleSummarizer(Summarizer):
    def __init__(self):
        super().__init__()  # properly call parent __init__
        self.system_prompt = SYSTEM_PROMPT_TITLE
        self.agent = Agent(
            model=self.llm,
            system_prompt=self.system_prompt,
            output_type=ResponseType,
        )


