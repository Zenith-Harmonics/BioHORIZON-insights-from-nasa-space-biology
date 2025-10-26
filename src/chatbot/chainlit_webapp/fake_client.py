import asyncio

from src.chatbot.biohor_agent.agent import BioHorizonAgent

async def fake_interface():
    agent=BioHorizonAgent()
    while True:
        user_input = input("Enter a question (type 'exit' to quit): ")
        if user_input.lower() == "exit" or user_input == "e":
            print("Exiting...")
            break

        try:
            async for event in agent.message_streamed(user_input):
                if event.type == "text":
                    for char in event.content:
                        await asyncio.sleep(1 / 500)
                        print(char, end="", flush=True)
                else:
                    print("\n", "SOURCES:")
                    print(event.content)
            print()  # newline after full response

        except Exception as e:
            print(f"Message could not procede due to error {e}")
            raise
        print("=" * 60 + "\n")

asyncio.run(fake_interface())