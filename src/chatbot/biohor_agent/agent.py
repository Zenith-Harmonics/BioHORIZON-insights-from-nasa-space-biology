'''
This file contains the logic for the LLM based agent
'''
from openai import AsyncOpenAI
from pydantic import BaseModel
from pydantic_ai import Agent, Tool
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    SystemPromptPart,
    TextPart,
    UserPromptPart,
)
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from .prompts import (
    INSTRUCTIONS,
    SYSTEM_PROMPT,
)
from src.environment import (
    CONTEXT_LENGTH,
    LLM_MODEL,
    OPENAI_COMPAT_URL,
    API_KEY,
)
from src.utils import num_tokens_from_string, convert_results_to_docs

from src.database.wrapper import default_qdrant_client




# JSON schema for the tool parameters
json_schema = {
    "type": "object",
    "properties": {
        "keyword_text": {
            "description": "Keywords to search in the database. / Schlüsselwörter, die in der Datenbank gesucht werden soll.",
            "type": "string",
        },
    },
    "required": ["keyword_text"],
}
context_length = int(CONTEXT_LENGTH)


class ResponseType(BaseModel):
    FINAL_RESPONSE: str
    SOURCE_LINK: list[str]


class StreamChunk(BaseModel):
    type: str  # "text" | "links"
    content: str | list[str]




class BioHorizonAgent:
    def __init__(self):
        self.print_message = "BioHorizonAgent using host: " + OPENAI_COMPAT_URL
        print(self.print_message)
        print("LLM model: ", LLM_MODEL)

        self.client = AsyncOpenAI(
            api_key=API_KEY, base_url=OPENAI_COMPAT_URL,
        )
        self.llm = OpenAIChatModel(
            model_name=LLM_MODEL, provider=OpenAIProvider(openai_client=self.client)
        )
        # register tool parameters
        self.top_k: int = 4
        self.max_query_results: int = 30

        self.qdrant_tool = [
            Tool.from_schema(
                function=self._query_tool,
                name="search_database",
                description="Searches the vector database given a keyword based text and the language of the user's question / Durchsucht die Vektordatenbank mit einem Text basiert auf Schlüsselwörter und der Sprache des Nutzers.",
                json_schema=json_schema,
            )
        ]
        self.system_prompt = SYSTEM_PROMPT
        self.instructions = INSTRUCTIONS
        self.system_prompt_tokens = num_tokens_from_string(self.system_prompt)
        self.instructions_tokens = num_tokens_from_string(self.instructions) + 1
        self.agent = Agent(
            model=self.llm,
            instructions=self.instructions,
            system_prompt=self.system_prompt,
            tools=self.qdrant_tool,
            output_type=ResponseType,
        )
        self.vllm_history: list[ModelMessage] = []

    async def _query_tool(self, keyword_text: str) -> list[dict]:
        print("QDRAND_SEARCH >>>", keyword_text)
        try:
            results = default_qdrant_client.query(
                search_input=keyword_text,
                max_results=self.max_query_results,
            )
        except Exception as e:
            raise ValueError(f"Error from Qdrant search: {e}") from e

        if not results:
            return [{"Retrieved contexts": "No retrieved context for the questions"}]
        dicts=convert_results_to_docs(results=results)
        result_dicts: list[str] = []
        # map reranked back to original ChunkResult objects
        for doc in dicts:
            if doc is not None:
                result_dicts.append(doc["text"])

        return result_dicts



    async def message_streamed(self, user_input: str):
        final_result: str = ""
        print("strat streaming...")
        try:
            try:
                async with self.agent.run_stream(
                    user_input, message_history=self.vllm_history
                ) as result:
                    async for chunk in result.stream_output():
                        if chunk.FINAL_RESPONSE:
                            yield StreamChunk(type="text", content=chunk.FINAL_RESPONSE)
                            final_result = final_result + chunk.FINAL_RESPONSE
                        if chunk.SOURCE_LINK:
                            yield StreamChunk(type="links", content=chunk.SOURCE_LINK)
            except Exception as stream_err:
                print(f"[DEBUG] Streaming failed inside message_streamed: {stream_err}")
                result = None
                raise RuntimeError("Error while streaming")
        except RuntimeError:
            # traceback.print_exc()
            # Streaming failed — fallback to blocking run
            try:
                result = await self.agent.run(
                    user_input, message_history=self.vllm_history
                )
                text = result.output.FINAL_RESPONSE
                links = result.output.SOURCE_LINK
                for i in range(0, len(text), 200):
                    part = text[i : i + 200]
                    yield StreamChunk(type="text", content=part)
                    final_result += part
                yield StreamChunk(type="links", content=links)
            except Exception as e:
                print(f"Fallback failed due to error: {e}")
                raise ValueError(f"In PydanticAgent: {e}") from e
        # add the progress to history
        self.add_to_history(answer=final_result, question=user_input)

    def add_to_history(self, answer: str, question: str):
        self.vllm_history.append(ModelRequest(parts=[UserPromptPart(content=question)]))
        self.vllm_history.append(ModelResponse(parts=[TextPart(content=answer)]))

        system_message = ModelRequest(
            parts=[SystemPromptPart(content=self.system_prompt)]
        )

        total_tokens = self.system_prompt_tokens
        kept: list[ModelMessage] = []

        for msg in reversed(self.vllm_history):
            # Only keep Q/A messages (skip system prompts)
            if not any(
                isinstance(part, (UserPromptPart, TextPart)) for part in msg.parts
            ):
                continue

            content = "".join(part.content for part in msg.parts)
            tok = num_tokens_from_string(content) + self.instructions_tokens / 2

            if total_tokens + tok > context_length:
                print("Breaking point:", total_tokens, tok)
                break

            kept.append(msg)
            total_tokens += tok
            # Keep system prompt + latest messages that fit
            kept.reverse()  # restore chronological order once
            self.vllm_history = [system_message, *kept]

