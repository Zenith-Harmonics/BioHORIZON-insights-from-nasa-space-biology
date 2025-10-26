
import asyncio

import chainlit as cl

from chainlit.types import ThreadDict
from chainlit.user import User

from src.chatbot.biohor_agent.agent import BioHorizonAgent


print(">>> main.py loaded")


def process_urls(raw_url_list: list[str]) -> str:
    without_images = [
        url
        for url in raw_url_list
        if not (
            url.strip().lower().endswith(".png")
            or url.strip().lower().endswith(".jpeg")
        )
    ]
    # Fix common mistakes like missing slashes
    fixed_urls = []
    for url in without_images:
        if url.startswith("https:/") and not url.startswith("https://"):
            url = url.replace("https:/", "https://", 1)
        if url.startswith("http:/") and not url.startswith("http://"):
            url = url.replace("http:/", "http://", 1)
        fixed_urls.append(url)

    links_md = "\n".join(f"- [{url}]({url})" for url in fixed_urls)
    return links_md


async def show_loading_animation(msg: cl.Message, text: str):
    await msg.send()
    dots = ["", ".", "..", "..."]
    i = 0
    try:
        while True:
            msg.content = f"{text}{dots[i % 4]}"
            await msg.update()
            i += 1
            await asyncio.sleep(0.42)
    except asyncio.CancelledError:
        msg.content = " "  # clear out "Processing..."
        await msg.update()
        # clean exit when we cancel the task
        return


@cl.oauth_callback
async def oauth_callback(
    provider_id: str,
    token: str,
    raw_user_data: dict[str, str],
    default_user: User,
    extra: str | None = None,  # Optional fifth parameter
) -> User | None:
    if provider_id != "gitlab":
        return None
    user_id = raw_user_data.get("sub") or raw_user_data.get("id")
    email = raw_user_data.get("email")
    name = raw_user_data.get("name") or raw_user_data.get("username")
    print("GitLab login from ", name)
    if not user_id or not email:
        return None

    return User(
        identifier=f"gitlab_{user_id}",
        display_name=name,
        metadata={"email": email, "provider": "gitlab"},
    )


@cl.on_chat_start
async def start_chat():
    # user = cl.user_session.get("id")  # each authenticated user has an ID
    # pick the agent once per session
    agent = BioHorizonAgent()
    cl.user_session.set("agent", agent)


@cl.on_message
async def main(message: cl.Message):
    msg = cl.Message(content="Pro")
    loading_task = asyncio.create_task(show_loading_animation(msg, "Processing"))
    agent = cl.user_session.get("agent")  # reuse same agent object

    if agent is None:
        agent = BioHorizonAgent()
        cl.user_session.set("agent", agent)

    # messaging
    try:
        async for event in agent.message_streamed(message.content):
            if event.type == "text":
                if not loading_task.done():
                    loading_task.cancel()
                    await asyncio.sleep(0.3)

                await msg.stream_token(token=event.content)
                await asyncio.sleep(1 / 500)

            else:
                msg.elements = [
                    cl.Text(
                        size="small",
                        name="Sources",
                        content=process_urls(event.content),
                        display="inline",
                    )
                ]

            # update the message with the text and element
            await msg.update()
    except Exception as e:
        loading_task.cancel()
        await asyncio.sleep(0.3)
        msg.content = f"We are sorry. It seems that an error occured: {e}"
        await msg.update()
        raise
    finally:
        loading_task.cancel()
        await asyncio.sleep(1)


@cl.on_chat_resume
async def resume(thread: ThreadDict):
    msg = cl.Message(content="Load")
    loading_task = asyncio.create_task(
        show_loading_animation(msg, "Loding conversation")
    )
    agent = BioHorizonAgent()
    steps = thread["steps"]
    question = None
    answer = None
    try:
        for step in steps:
            msg_type = step.get("type")
            output = step.get("output")

            if msg_type == "user_message":
                question = output
            elif msg_type == "assistant_message":
                answer = output

            # Only add to history when complete pair (answer+question)
            if question is not None and answer is not None:
                agent.add_to_history(answer=answer, question=question)
                question, answer = None, None  # reset for next turn

    except Exception as e:
        loading_task.cancel()
        await asyncio.sleep(0.3)
        msg.content = f"Old converstaion could not be loaded due to: {e} \n New conversation started"
        await msg.update()
    finally:
        loading_task.cancel()
        await asyncio.sleep(0.3)
    print(f"Loaded {len(agent.vllm_history)} messages")
    cl.user_session.set("agent", agent)
