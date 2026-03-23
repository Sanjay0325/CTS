"""
Query-type to tool mapping hints. Injected into system prompt so LLM reliably uses tools.

Optimized for small models (qwen3:8b, llama3.1): lead with notes/todos, explicit MCP mapping.
"""

# PRIMARY: Notes & Todos - shown first for small-model clarity (qwen3:8b, etc.)
PRIMARY_TOOLS_BLOCK = """
PRIMARY TOOLS - YOU HAVE THESE. Use them. Never refuse:
- save_note(title, content): Save a note. Triggers: save, remember, note, store, "MCP server notes", "notes".
- list_notes: List notes. Triggers: my notes, show notes.
- add_todo(task): Add task. Triggers: add todo, task, reminder.

"MCP server notes" / "MCP notes" / "notes server" = save_note or list_notes. CALL them.
"""

# When user asks for these, ALWAYS use the corresponding tool.
TOOL_TRIGGER_HINTS = """
CRITICAL: When user asks to save/note/remember/store → CALL save_note. When user says add todo → CALL add_todo. NEVER refuse.

MULTI-TOOL CHAINS: When user asks to SAVE/STORE (e.g. "save that to a note"):
1. Get data with search/get_weather/etc. if needed.
2. Call save_note(title="...", content="...") or add_todo(task="...") with actual values.
- save_note: ALWAYS pass non-empty title AND content. Extract from user message.
- add_todo: ONE call per distinct task. Never empty task.

SINGLE-TOOL:
- Weather/temperature/forecast in a city → get_weather or get_forecast
- Currency conversion / exchange rate / USD to INR / convert money → convert_currency or get_rates
- Stock price / share quote / stock market → get_quote or get_historical
- Calculate / multiply / add numbers / math → add, multiply, or power (Calculator)
- Jio recharge / mobile recharge / prepaid plan / ₹19 plan → search_jio_plans or recharge_jio
- Flight search / book flight / flights from X to Y → search_flights or book_flight
- Hotel search / book hotel / accommodation → search_hotels or book_hotel
- Translate / translation to Spanish/French → translate or list_languages
- Wikipedia / lookup / encyclopedia → search_wikipedia
- News / latest news / headlines → get_news
- Todo / task / reminder / add to list → add_todo, list_todos, complete_todo, set_reminder
- Notes / remember / save / note / "save my name as title" / "MCP notes" / "notes server" → save_note (CALL it; title=, content=)
- My notes / show notes / list notes / what did I save → list_notes or get_notes_summary
- IRCTC / train / seat availability / trains from X to Y → search_trains_between_stations, check_seat_availability
- Calendar / event / schedule meeting → create_event or list_events
- Send email / email to someone → send_email
- Search the web / find information → search
- Send WhatsApp / text on WhatsApp / WhatsApp message → send_whatsapp_message or send_whatsapp_template
- LinkedIn post / post on LinkedIn / share on LinkedIn → create_linkedin_post or draft_linkedin_post
- Supabase / query database / SQL / edge function → use Supabase MCP tools
- Hash / checksum / MD5 / SHA256 → hash_md5 or hash_sha256
- UUID / generate ID → generate_uuid
- Unit conversion / convert kg to lb / miles to km → convert_units
- JSON parse / validate JSON → parse_json or validate_json
- QR code / generate QR → generate_qr or decode_qr
"""
