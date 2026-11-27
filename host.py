"""MCP host: Telegram bot (long polling) + Gemini + an MCP server.

The laptop IS the server: this script polls Telegram outbound, so no public URL,
ngrok or port forwarding is needed. Keep it running during the demo.

MCP flow (done explicitly here so you can see every step):
  1. tools/list  -> ask the MCP server what tools it has, give that menu to Gemini
  2. Gemini replies with a function_call ("please run add_task(...)")
  3. tools/call  -> we forward that request to the MCP server and get the result
  4. send the result back to Gemini; repeat until Gemini answers in plain text
"""
import asyncio
import logging
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from fastmcp import Client
from google import genai
from google.genai import types
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

load_dotenv()

# Show Telegram errors (bad token, conflicts) instead of hiding them
logging.basicConfig(format="%(asctime)s %(levelname)s %(name)s: %(message)s", level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)  # httpx logs would print your bot token

MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
TZ_NAME = os.getenv("USER_TZ", "Asia/Kolkata")
ALLOWED_CHAT_ID = os.getenv("ALLOWED_CHAT_ID", "").strip()
MAX_TOOL_ROUNDS = 6  # safety limit on Gemini <-> MCP back-and-forth

gemini_client = genai.Client()  # reads GEMINI_API_KEY from env
MCP_SERVER = os.getenv("MCP_SERVER", "todoist_server.py")  # or calendar_server.py
mcp_client = Client(str(Path(__file__).parent / MCP_SERVER))

GEMINI_TOOLS: list[types.Tool] = []  # the tool menu, filled in at startup from the MCP server

# Short in-memory conversation history per chat so "move it to 2 PM" works.
HISTORY: dict[str, list[types.Content]] = {}
MAX_HISTORY = 12


def _result_text(result) -> str:
    """Pull plain text out of an MCP tool result (works across fastmcp versions)."""
    blocks = getattr(result, "content", result)
    return "\n".join(getattr(b, "text", str(b)) for b in blocks)


async def handle_user_message(chat_id: str, user_text: str) -> str:
    now = datetime.now(ZoneInfo(TZ_NAME)).strftime("%Y-%m-%d %H:%M (%A)")
    system_prompt = (
        "You are a concise personal assistant connected to the user's apps via MCP tools. "
        f"Current local date and time: {now}. User timezone: {TZ_NAME}. "
        "Resolve words like 'today', 'tomorrow', 'next Monday' using that date. "
        "To change, complete or delete an existing item, first call the matching list tool to find its id. "
        "If a request is missing a required detail, ask one short question. "
        "Reply in plain text (no markdown), in one or two short sentences, confirming what you did."
    )
    config = types.GenerateContentConfig(
        system_instruction=system_prompt,
        temperature=0,  # 0 = most predictable behavior
        tools=GEMINI_TOOLS,  # the menu we got from the MCP server
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )

    history = HISTORY.setdefault(chat_id, [])
    user_content = types.Content(role="user", parts=[types.Part(text=user_text)])
    contents = history + [user_content]

    reply = ""
    for _ in range(MAX_TOOL_ROUNDS):
        # Ask Gemini: instructions + conversation so far + tool menu
        response = await gemini_client.aio.models.generate_content(
            model=MODEL, contents=contents, config=config
        )
        calls = response.function_calls
        if not calls:  # plain text answer, we're done
            reply = response.text or ""
            break

        # Gemini asked for tools. Keep its message in the conversation, then run each call via MCP.
        contents.append(response.candidates[0].content)
        result_parts = []
        for fc in calls:
            args = dict(fc.args or {})
            print(f"   🔧 MCP TOOL CALL  {fc.name}({args})")
            try:
                result = await mcp_client.call_tool(fc.name, args)  # <-- MCP tools/call
                text = _result_text(result)
            except Exception as e:
                text = f"Error: {e}"
            print(f"   ✅ TOOL RESULT    {text[:300]}")
            result_parts.append(types.Part.from_function_response(name=fc.name, response={"result": text}))
        contents.append(types.Content(role="user", parts=result_parts))

    reply = reply or "Done."
    history += [user_content, types.Content(role="model", parts=[types.Part(text=reply)])]
    del history[:-MAX_HISTORY]
    return reply


async def _authorized(update: Update) -> bool:
    """Only your own Telegram account may use the bot."""
    chat_id = str(update.effective_chat.id)
    if not ALLOWED_CHAT_ID:
        await update.effective_message.reply_text(
            f"Setup: your chat ID is {chat_id}\n"
            f"Add ALLOWED_CHAT_ID={chat_id} to your .env file and restart the bot."
        )
        print(f"ℹ️  ALLOWED_CHAT_ID not set. Message came from chat ID {chat_id}")
        return False
    if chat_id != ALLOWED_CHAT_ID:
        print(f"⛔ Ignored message from unauthorized chat {chat_id}")
        return False
    return True


async def on_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await _authorized(update):
        await update.effective_message.reply_text(
            "Hi! Try: 'Remind me to submit the deck tomorrow at 5 PM' or 'What's on my list today?'"
        )


async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _authorized(update):
        return
    text = update.effective_message.text
    chat_id = str(update.effective_chat.id)
    print(f"\n📩 Telegram: {text}")
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    try:
        reply = await handle_user_message(chat_id, text)
    except Exception as e:  # keep the demo alive on any error
        logging.exception("Error while handling message")
        print(f"❌ Error: {e!r}")
        reply = "Sorry, something went wrong. Please try again."
    print(f"🤖 Reply: {reply}")
    await update.effective_message.reply_text(reply)


async def main():
    app = ApplicationBuilder().token(os.environ["TELEGRAM_TOKEN"]).build()
    app.add_handler(CommandHandler("start", on_start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))

    print(f"Starting MCP host... connecting to {MCP_SERVER}")
    async with mcp_client:  # starts the MCP server and connects
        mcp_tools = await mcp_client.list_tools()  # MCP tools/list: "what can you do?"
        print("MCP tools available:", ", ".join(t.name for t in mcp_tools))
        # Translate the MCP tool descriptions into the format Gemini understands
        GEMINI_TOOLS.append(
            types.Tool(
                function_declarations=[
                    types.FunctionDeclaration(
                        name=t.name,
                        description=t.description or "",
                        parameters_json_schema=t.inputSchema,
                    )
                    for t in mcp_tools
                ]
            )
        )
        async with app:
            me = await app.bot.get_me()  # fails right away if TELEGRAM_TOKEN is wrong
            print(f"Telegram login OK: bot is @{me.username}. Open THAT bot in Telegram and send /start")
            if not ALLOWED_CHAT_ID:
                print("ALLOWED_CHAT_ID is empty, so the bot will reply with your chat ID.")
            await app.start()
            await app.updater.start_polling()  # keep asking Telegram for new messages
            print(f"Bot is live (model: {MODEL}). Message it on Telegram. Ctrl+C to stop.\n")
            try:
                await asyncio.Event().wait()  # run forever
            finally:
                await app.updater.stop()
                await app.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nStopped.")