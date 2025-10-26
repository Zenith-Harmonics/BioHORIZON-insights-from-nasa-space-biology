'''
This file contains the logic for the LLM based agent
'''
from openai import AsyncOpenAI
from pydantic import BaseModel
from pydantic_ai import Agent, Tool
from pydantic_ai.messages import (
    FinalResultEvent,
    ModelMessage,
    ModelRequest,
    ModelResponse,
    SystemPromptPart,
    TextPart,
    UserPromptPart,
)
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from rag_pcon_planner.ai_search_agent.prompts import (
    INSTRUCTIONS,
    SYSTEM_PROMPT,
)
from rag_pcon_planner.environment import (
    CONTEXT_LENGTH,
    LLM_MODEL,
    OPENAI_COMPAT_URL,
    USE_RERANKER,
)
from rag_pcon_planner.headers import NGINX_HEADERS
from rag_pcon_planner.qdrant.qdrant_wrapper import default_qdrant_client
from rag_pcon_planner.qdrant.query import (
    convert_results_to_docs,
    convert_results_to_text,
)


# JSON schema for the tool parameters
json_schema = {
    "type": "object",
    "properties": {
        "keyword_text": {
            "description": "Keywords to search in the database. / Schlüsselwörter, die in der Datenbank gesucht werden soll.",
            "type": "string",
        },
        "language": {
            "description": "Either 'en' (user question in English) or 'de' (question in German). / Entweder 'en' (Frage auf Englisch) oder 'de' (Nutzerfrage auf Deutsch).",
            "type": "string",
        },
    },
    "required": ["keyword_text", "language"],
}
context_length = int(CONTEXT_LENGTH)


class ResponseType(BaseModel):
    FINAL_RESPONSE: str
    SOURCE_LINK: list[str]


class StreamChunk(BaseModel):
    type: str  # "text" | "links"
    content: str | list[str]


re = RerankerClient()

"""
async def stream_custom(
    rrr: StreamedRunResult[None, ResponseType],
    delta: bool = False,
    debounce_by: float | None = 0.1,
) -> AsyncIterator[str]:
    if rrr._run_result is not None:
        if not isinstance(rrr._run_result.output, str):
            raise Exception("stream_text() can only be used with text responses")
        yield rrr._run_result.output
        await rrr._marked_completed()
    elif rrr._stream_response is not None:
        async for text in rrr._stream_response.stream_text(
            delta=delta, debounce_by=debounce_by
        ):
            yield text
        await rrr._marked_completed(rrr._stream_response.get())"""


class PydanticAgentRerank:
    def __init__(self):
        self.print_message = "PydanticAgentRerank using host: " + OPENAI_COMPAT_URL
        print(self.print_message)
        print("LLM model: ", LLM_MODEL)

        self.client = AsyncOpenAI(
            api_key="XXX", base_url=OPENAI_COMPAT_URL, default_headers=NGINX_HEADERS
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

    async def _query_tool(self, keyword_text: str, language: str) -> list[dict]:
        print("QDRAND_SEARCH >>>", keyword_text, language)
        try:
            results = default_qdrant_client.query(
                search_input=keyword_text,
                max_results=self.max_query_results,
                language=language,
            )
        except Exception as e:
            raise ValueError(f"Error from Qdrant search: {e}") from e

        if not results:
            return [{"Retrieved contexts": "No retrieved context for the questions"}]

        docs = convert_results_to_docs(results)
        try:
            reranked = re.rerank(query=keyword_text, docs=docs, top_k=self.top_k)
        except Exception as e:
            raise ValueError(f"Error from reranking: {e}") from e

        result_dicts: list[dict] = []
        # map reranked back to original ChunkResult objects
        id_to_chunk = {c["id"]: c for c in results}
        for id_, _ in reranked:
            # since our reranker returns ids, id_or_text is an id
            chunk = id_to_chunk.get(id_)
            if chunk is not None and isinstance(chunk["payload"], dict):
                metainfo = chunk["payload"]["meta_info"]
                dicto = {  # new dict each time
                    "text": chunk["payload"]["chunk_text"],
                    "source": metainfo["source"],
                }
                result_dicts.append(dicto)

        return result_dicts

    async def handler(self, event_stream, queue):
        async for event in event_stream:
            if isinstance(event, FinalResultEvent):
                await queue.put(event)
        await queue.put(None)

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


class PydanticAgent(PydanticAgentRerank):
    def __init__(self):
        super().__init__()
        self.treshold: float = (
            0  # can be set to any vvalue between 0 and 1 to limit a the search
        )
        self.max_query_results = 6
        self.qdrant_tool = [
            Tool.from_schema(
                function=self.tool,
                name="issue_query",
                description="Searches the vector database given a query and the language of the user's question / Durchsucht die Vektordatenbank mit einer Anfrage und der Sprache des Nutzers.",
                json_schema=json_schema,
            )
        ]

    async def tool(self, query_text: str, language: str) -> list[str]:
        query_results = default_qdrant_client.query(
            search_input=query_text,
            max_results=self.max_query_results,
            threshold=self.treshold,
            language=language,
        )
        print(query_text, "SparDens8Th")

        return convert_results_to_text(query_results)


class PydanticAgentWrapper:
    def __init__(self, use_reranker: bool | None = None):
        # If not explicitly passed, fall back to env flag
        if use_reranker is None:
            use_reranker = USE_RERANKER

        if use_reranker:
            self.agent = PydanticAgentRerank()
        else:
            self.agent = PydanticAgent()

    async def message_streamed(self, user_input: str):
        async for chunk in self.agent.message_streamed(user_input):
            yield chunk

    def add_to_history(self, answer: str, question: str):
        return self.agent.add_to_history(answer, question)