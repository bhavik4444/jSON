import asyncio
from datetime import datetime
from fastmcp import Client
from google import genai
from google.genai import types

# Initialize Gemini client (automatically reads GEMINI_API_KEY env var)
gemini_client = genai.Client()

# Point the MCP Client at your local Calendar MCP Server
mcp_client = Client("calendar_server.py")


async def handle_user_message(user_text: str) -> str:
    """Core orchestrator function—later called directly by your WhatsApp/Telegram webhook."""
    today = datetime.now().strftime("%Y-%m-%d (%A)")
    system_prompt = (
        f"You are a concise personal assistant connected to the user's apps via MCP. "
        f"Today is {today}. Use the available tools to fulfill requests and confirm clearly."
    )

    response = await gemini_client.aio.models.generate_content(
        model="gemma-4-31B-it",
        contents=user_text,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0,
            tools=[mcp_client.session],  # Gemini auto-discovers & runs MCP tools
        ),
    )
    return response.text


async def main():
    print("Starting MCP Host... Connecting to Calendar MCP Server.")
    async with mcp_client:
        print("Connected! Type a message (or 'quit' to exit).\n")
        while True:
            user_msg = input("You: ").strip()
            if user_msg.lower() in {"quit", "exit"}:
                break
            if not user_msg:
                continue

            reply = await handle_user_message(user_msg)
            print(f"AI: {reply}\n")


if __name__ == "__main__":
    asyncio.run(main())