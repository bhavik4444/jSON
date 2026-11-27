# jSON 🚀

> **Making MCP Matter:** Turn everyday WhatsApp messages into cross-app actions across your calendar, classroom, finances, and food delivery using the Model Context Protocol (MCP).

## 🎯 Problem Statement: *Making MCP Matter*

AI assistants today are trapped in isolated chat windows, while our daily lives happen inside messaging apps like WhatsApp. Even worse, getting real work done still forces us to jump between five different apps—checking a budget in one app, browsing food in another, and blocking study time in a third.

**WhatsMCP** proves why the **Model Context Protocol (MCP)** matters to everyday users. Instead of building *yet another dashboard app*, WhatsMCP uses WhatsApp as a zero-friction universal remote. Send one natural-language message, and our AI agent dynamically orchestrates multiple MCP servers behind the scenes to get things done.

## ✨ Key Capabilities & Cross-App Magic

Send a text on WhatsApp—just like messaging a friend—and WhatsMCP chains the right MCP tools together:

* 🍔 **Budget-Aware Food Ordering (Zomato / Swiggy MCP + Finance MCP):**
  *"I'm hungry, find me a veg dinner under my remaining daily budget."*
  → Checks your remaining food budget from your Finance MCP, searches nearby menus via Zomato/Swiggy MCP, applies offers, and builds a ready-to-pay cart (open the app to tap pay or scan the UPI QR).
* 📅 **Smart Scheduling (Google Calendar MCP):**
  *"Move my 4 PM study session to 6 PM and add a team sync tomorrow at 11 AM."*
  → Reads availability and creates or updates calendar events automatically.
* 🎓 **Academic Assistant (Google Classroom MCP):**
  *"What assignments are due this week? Block 2 hours tomorrow to finish them."*
  → Fetches upcoming coursework deadlines and coordinates with Google Calendar MCP to schedule focus blocks.
* 💰 **Personal Finance Tracking (Finance MCP):**
  *"Spent ₹250 on coffee today"*
  → Logs expenses automatically, tracks category limits, and provides real-time budget context to other MCP tools.
* ⏰ **Smart Reminders:**
  *"Remind me to submit the deck in 2 hours."*
  → Schedules timely follow-up reminders directly back on WhatsApp.

## 🏗️ High-Level Architecture

WhatsApp serves as the **zero-friction user interface**, paired with a lightweight **Live MCP Trace Dashboard** to visualize tool calls in real time during demos.

```text
[ User on WhatsApp ]
         │
         ▼ (WhatsApp Cloud API / Twilio Webhook)
[ Backend Server & MCP Host ] ──► [ Live Trace Dashboard (Demo View) ]
         │
         ▼ (Intent Analysis & Multi-Tool Orchestration via LLM)
[ MCP Client Layer ]
   ├──► 💰 Personal Finance MCP Server (Expenses & Budget)
   ├──► 🍔 Zomato / Swiggy MCP Server (Discovery & Cart Building)
   ├──► 📅 Google Calendar MCP Server (Scheduling)
   ├──► 🎓 Google Classroom MCP Server (Assignments & Deadlines)
   └──► ⏰ Reminders MCP Server (Scheduled Nudges)
         │
         ▼
[ Actions Executed & Summary Sent Back to WhatsApp ]
```

## 🛠️ Tech Stack (Planned)

* **Messaging Interface:** WhatsApp Business Cloud API / Twilio Sandbox for WhatsApp
* **Core Protocol:** [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) (Stdio & Streamable HTTP)
* **Backend & MCP Host:** Python (FastAPI) / Node.js (TypeScript)
* **LLM & Tool Orchestration:** Gemini / Claude / OpenAI with native tool-calling
* **Connected MCP Servers:** Zomato / Swiggy Remote MCP (OAuth 2.1), Google Calendar, Google Classroom, Custom Personal Finance & Reminders MCP
* **Demo Trace UI:** Lightweight React / HTML WebSocket dashboard displaying live MCP tool execution

## 🗺️ Hackathon Roadmap

- [x] Problem framing & cross-app MCP architecture
- [x] Initial repository setup (`v0.1`)
- [ ] Set up WhatsApp webhook receiver & message responder
- [ ] Build core MCP Host & LLM multi-tool routing engine
- [ ] Connect **Personal Finance** & **Google Calendar** MCP servers
- [ ] Integrate **Zomato / Swiggy MCP** (budget-aware cart builder) & **Google Classroom MCP**
- [ ] Add Live MCP Trace Dashboard for real-time demo visualization
- [ ] End-to-end testing & final hackathon pitch

## 📄 License

Built for a hackathon and licensed under the MIT License.
