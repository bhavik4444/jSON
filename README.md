# jSON 🚀

> **Making MCP Matter:** Text a Telegram bot in plain English and an AI agent runs the right tools across your tasks, calendar and personal finances using the Model Context Protocol (MCP).

## 🎯 Problem Statement: *Making MCP Matter*

AI assistants are trapped in isolated chat windows, while our daily lives happen inside messaging apps. Getting real work done still means jumping between several apps: checking a budget in one, scheduling in another, writing a to-do in a third.

**jSON** shows why the **Model Context Protocol (MCP)** matters to everyday users. Instead of building *yet another dashboard*, it uses Telegram as a zero-friction remote. Send one natural-language message and the agent discovers the available MCP tools, picks the ones the request needs (possibly from several servers), and replies with what it did.

## ✨ What Works Today

| MCP server | File | Tools | Storage / API |
|---|---|---|---|
| 💰 **Finance** | `finance_server.py` | `add_expense`, `list_expenses`, `delete_expense`, `get_spending_summary`, `set_budget`, `get_budget_status` | Local SQLite (`finance.db`), amounts in ₹ |
| ✅ **Todoist** | `todoist_server.py` | `add_task`, `list_tasks`, `update_task`, `complete_task`, `delete_task` | Todoist REST API (personal API token) |
| 📅 **Google Calendar** | `calendar_server.py` | `create_event`, `list_events`, `update_event`, `delete_event` | Google Calendar API (OAuth `token.json`) |

Example messages:

- *"Spent 250 on coffee"* → logs a ₹250 `food` expense and tells you how much of the food budget is left.
- *"How much food budget is left?"* → reads budget status from the Finance server.
- *"Remind me to submit the deck tomorrow at 5 PM"* → creates a Todoist task with a due time.
- *"Move my 4 PM study session to 6 PM"* → lists events to find the id, then updates it (Calendar server).
- Follow-ups like *"move it to 2 PM"* work because the host keeps the last 12 messages per chat in memory.

## 🏗️ Architecture

```
[ You on Telegram ]
        │  (long polling, outbound only: no public URL or ngrok needed)
        ▼
[ host.py: Telegram bot + MCP host ]
        │  1. tools/list on every MCP server → one combined tool menu
        │  2. Gemini reads your message + the menu, replies with function calls
        │  3. tools/call is routed to the server that owns each tool
        │  4. results go back to Gemini, repeat (max 6 rounds) until it answers in text
        ▼
[ MCP servers: stdio subprocesses started by host.py ]
   ├──► finance_server.py   (SQLite)
   ├──► todoist_server.py   (Todoist API)
   └──► calendar_server.py  (Google Calendar API)
        │
        ▼
[ Short plain-text confirmation sent back to Telegram ]
```

Design notes:

- **The laptop is the server.** The bot polls Telegram, so just keep `host.py` running.
- **One MCP client per server** (`fastmcp.Client`). Tools from all servers are merged into a single Gemini tool menu. Two servers defining the same tool name raises an error at startup.
- **The MCP loop is explicit.** Automatic function calling is disabled so every `tools/list` → function call → `tools/call` step is visible in the console (🔧 tool call, ✅ result).
- **Single-user by design.** Only the Telegram chat ID in `ALLOWED_CHAT_ID` can use the bot.

## 🛠️ Tech Stack

- **Interface:** Telegram bot (`python-telegram-bot`, long polling)
- **LLM:** Google Gemini via `google-genai` (default `gemini-2.5-flash`, temperature 0)
- **Protocol:** Model Context Protocol over stdio, using `fastmcp`
- **Runtime:** Python 3.14, managed with `uv`
- **Integrations:** Todoist REST API, Google Calendar API, SQLite

## 🚀 Setup

### 1. Install

```bash
git clone https://github.com/bhavik4444/jSON.git
cd jSON
uv sync            # or: pip install -r requirements.txt
```

If you use `requirements.txt` and want the Calendar server, also install `google-api-python-client` and `google-auth-oauthlib`.

### 2. Get your keys

- **Telegram bot token:** message [@BotFather](https://t.me/BotFather) and create a bot.
- **Gemini API key:** from [Google AI Studio](https://aistudio.google.com/).
- **Todoist API token:** Todoist → Settings → Integrations → Developer.
- **Google Calendar (optional):** create OAuth credentials, then generate `token.json` with the `calendar` scope.

### 3. Create `.env`

```env
TELEGRAM_TOKEN=123456:your-bot-token
GEMINI_API_KEY=your-gemini-key
TODOIST_API_TOKEN=your-todoist-token
ALLOWED_CHAT_ID=            # fill in after step 4

# Optional
GEMINI_MODEL=gemini-2.5-flash
USER_TZ=Asia/Kolkata
MCP_SERVERS=todoist_server.py,finance_server.py   # add calendar_server.py to enable Calendar
FINANCE_DB=./finance.db
```

`.env`, `credentials.json` and `token.json` are git-ignored. Never commit them.

### 4. Run

```bash
uv run host.py     # or: python host.py
```

Open your bot in Telegram and send `/start`. On the first run `ALLOWED_CHAT_ID` is empty, so the bot replies with your chat ID. Put it in `.env` and restart. After that, just chat.

## ⚠️ Known Limitations

- **Timezone:** the three servers hardcode `Asia/Kolkata`. `USER_TZ` only affects the host's date/time context, so change the `TZ` constants in the servers too if you're elsewhere.
- **Currency:** the finance server and the host's system prompt assume Indian rupees.
- **Google Calendar setup:** `calendar_server.py` expects a `token.json` and mentions `auth_google.py`, but that script isn't in the repo yet.
- **Memory:** conversation history lives in process memory and is lost on restart.
- **Security:** anyone who can message the bot from the allowed chat can read and change your tasks, calendar and expenses. Keep the bot token private.

## 🗺️ Roadmap

- [x] Problem framing & cross-app MCP architecture
- [x] Initial repository setup
- [x] Telegram bot with long polling and chat-ID allowlist
- [x] Core MCP host with Gemini multi-tool routing across several servers
- [x] Personal Finance MCP server (expenses, budgets, summaries)
- [x] Todoist MCP server (tasks and reminders)
- [x] Google Calendar MCP server
- [ ] `auth_google.py` helper for Calendar OAuth
- [ ] Google Classroom MCP server (assignments → focus blocks on Calendar)
- [ ] Zomato / Swiggy MCP integration (budget-aware cart builder)
- [ ] WhatsApp interface (WhatsApp Cloud API / Twilio) alongside Telegram
- [ ] Live MCP trace dashboard (tool calls currently print to the console)
- [ ] Persistent conversation history
- [ ] End-to-end testing & final hackathon pitch

## 📄 License

Built for a hackathon and licensed under the MIT License.
