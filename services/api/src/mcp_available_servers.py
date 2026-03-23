"""
Predefined MCP servers for one-click add in Settings.

Each entry has: name, server_url (include /mcp), description (tool names).
Start servers with: pnpm dev:mcp:all or scripts/start_all_mcps.ps1
"""

AVAILABLE_MCP_SERVERS = [
    {"name": "Demo", "server_url": "http://localhost:8001/mcp", "description": "add, get_current_time, echo"},
    {"name": "Calculator", "server_url": "http://localhost:8002/mcp", "description": "add, multiply, power"},
    {"name": "Weather", "server_url": "http://localhost:8003/mcp", "description": "get_weather, get_forecast"},
    {"name": "Notes", "server_url": "http://localhost:8004/mcp", "description": "save_note, list_notes"},
    {"name": "Timezone", "server_url": "http://localhost:8005/mcp", "description": "get_time_in_timezone, list_common_timezones"},
    {"name": "Search", "server_url": "http://localhost:8006/mcp", "description": "search"},
    {"name": "Translator", "server_url": "http://localhost:8007/mcp", "description": "translate, list_languages"},
    {"name": "Unit Converter", "server_url": "http://localhost:8008/mcp", "description": "convert_units"},
    {"name": "Todo", "server_url": "http://localhost:8009/mcp", "description": "add_todo, list_todos, complete_todo"},
    {"name": "Flight Booking", "server_url": "http://localhost:8010/mcp", "description": "search_flights, book_flight"},
    {"name": "Hotel Booking", "server_url": "http://localhost:8011/mcp", "description": "search_hotels, book_hotel"},
    {"name": "Currency", "server_url": "http://localhost:8012/mcp", "description": "convert_currency, get_rates"},
    {"name": "Wikipedia", "server_url": "http://localhost:8013/mcp", "description": "search_wikipedia"},
    {"name": "Email", "server_url": "http://localhost:8014/mcp", "description": "send_email"},
    {"name": "Calendar", "server_url": "http://localhost:8015/mcp", "description": "create_event, list_events"},
    {"name": "News", "server_url": "http://localhost:8016/mcp", "description": "get_news"},
    {"name": "Stocks", "server_url": "http://localhost:8017/mcp", "description": "get_quote, get_historical"},
    {"name": "Reminder", "server_url": "http://localhost:8018/mcp", "description": "set_reminder, list_reminders"},
    {"name": "QR Code", "server_url": "http://localhost:8019/mcp", "description": "generate_qr, decode_qr"},
    {"name": "JSON Tools", "server_url": "http://localhost:8020/mcp", "description": "parse_json, validate_json"},
    {"name": "Hash", "server_url": "http://localhost:8021/mcp", "description": "hash_md5, hash_sha256"},
    {"name": "UUID", "server_url": "http://localhost:8022/mcp", "description": "generate_uuid"},
    {"name": "Jio Recharge", "server_url": "http://localhost:8023/mcp", "description": "search_jio_plans, recharge_jio"},
    # External / messaging
    {"name": "WhatsApp Business", "server_url": "http://localhost:8024/mcp", "description": "send_whatsapp_message, send_whatsapp_template"},
    {"name": "LinkedIn", "server_url": "http://localhost:8025/mcp", "description": "create_linkedin_post, draft_linkedin_post"},
    {"name": "IRCTC Trains", "server_url": "http://localhost:8026/mcp", "description": "search_trains_between_stations, check_seat_availability, get_station_code"},
    # External hosted (add URL manually for OAuth)
    {"name": "Supabase (hosted)", "server_url": "https://mcp.supabase.com/mcp", "description": "Query DB, deploy functions, logs"},
]
