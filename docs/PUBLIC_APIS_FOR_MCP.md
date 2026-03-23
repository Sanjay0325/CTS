# Public APIs for MCP – Application Details

Frequently used public APIs you can wire to MCP servers for production. Add API keys to `.env`.

---

## Weather

| API | Free Tier | Key Env | Endpoint |
|-----|-----------|---------|----------|
| [OpenWeatherMap](https://openweathermap.org/api) | 1000 calls/day | `OPENWEATHER_API_KEY` | `api.openweathermap.org/data/2.5/weather` |
| [WeatherAPI](https://www.weatherapi.com/) | 1M calls/mo | `WEATHERAPI_KEY` | `api.weatherapi.com/v1/current.json` |

**In `mcp-servers/weather/server.py`:**
```python
import os
import httpx
key = os.environ.get("OPENWEATHER_API_KEY")
# GET f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={key}"
```

---

## Currency

| API | Free Tier | Key Env | Endpoint |
|-----|-----------|---------|----------|
| [ExchangeRate-API](https://www.exchangerate-api.com/) | 1500/mo | `EXCHANGERATE_API_KEY` | `v6.exchangerate-api.com/v6/{key}/latest/{base}` |
| [Fixer.io](https://fixer.io/) | 100/mo | `FIXER_API_KEY` | `data.fixer.io/api/latest` |

---

## Stocks

| API | Free Tier | Key Env |
|-----|-----------|---------|
| [Alpha Vantage](https://www.alphavantage.co/) | 25/day | `ALPHAVANTAGE_API_KEY` |
| [Yahoo Finance](https://github.com/ranaroussi/yfinance) | Unlimited (library) | None |

---

## News

| API | Free Tier | Key Env |
|-----|-----------|---------|
| [NewsAPI](https://newsapi.org/) | 100/day | `NEWS_API_KEY` |
| [GNews](https://gnews.io/) | 100/day | `GNEWS_API_KEY` |

---

## Search

| API | Free Tier | Key Env |
|-----|-----------|---------|
| [Serper](https://serper.dev/) | 2500/mo | `SERPER_API_KEY` |
| [Brave Search](https://brave.com/search/api/) | 2000/mo | `BRAVE_API_KEY` |

---

## How to prompt the LLM to use tools

The system prompt now includes **query-type → tool** hints. Example triggers:

| User says | Tool to use |
|-----------|-------------|
| "Weather in London" | `get_weather` |
| "Convert 100 USD to INR" | `convert_currency` |
| "Stock price of AAPL" | `get_quote` |
| "Jio plans for ₹19" | `search_jio_plans` |
| "15 * 27" | `multiply` |
| "Translate hello to Spanish" | `translate` |

**Best prompts:** Be specific. "What's the weather in Mumbai?" works better than "weather?". The LLM receives trigger hints and will call the tool.

---

## Tools Used in metadata

- **Tools Available:** Count of tools from your MCP servers.
- **Tools Used:** Only tools the LLM actually **executed** (stored in `message_metadata.tools_used`).

When no tools are called, "Tools Used" shows `0`. This lets you see which responses used live data vs. model knowledge.
