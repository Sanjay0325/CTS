"""MCP IRCTC / Indian Railways - train search, seat availability. Uses Indian Rail API when key is set."""

import os
from datetime import datetime
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("IRCTC Trains", json_response=True, host="0.0.0.0", port=8026, stateless_http=True)

API_KEY = os.environ.get("INDIAN_RAIL_API_KEY", "")
BASE_URL = "https://indianrailapi.com/api/v2"

# Class codes: 1A, 2A, 3A, SL, CC, 2S, etc.
CLASS_CODES = ["1A", "2A", "3A", "SL", "CC", "2S", "3E", "EC"]

# Demo data when no API key
DEMO_TRAINS = [
    {"TrainNo": "12301", "TrainName": "RAJDHANI EXPRESS", "Source": "NDLS", "Destination": "HWH", "DepartureTime": "16:55", "ArrivalTime": "07:15", "TravelTime": "14:20H", "TrainType": "RAJ"},
    {"TrainNo": "12259", "TrainName": "SHATABDI EXPRESS", "Source": "NDLS", "Destination": "HWH", "DepartureTime": "06:00", "ArrivalTime": "14:05", "TravelTime": "08:05H", "TrainType": "SF"},
    {"TrainNo": "12345", "TrainName": "RANCHI RAJDHANI", "Source": "NDLS", "Destination": "HWH", "DepartureTime": "17:15", "ArrivalTime": "06:50", "TravelTime": "13:35H", "TrainType": "RAJ"},
]

DEMO_AVAILABILITY = [
    {"JourneyDate": "2025-03-22", "Availability": "Available", "Confirm": "100%", "Class": "3A"},
    {"JourneyDate": "2025-03-22", "Availability": "GNWL12/WL5", "Confirm": "85%", "Class": "SL"},
]


def _station_code(station: str) -> str:
    """Resolve station name to code. Returns as-is if already 3 chars (code), else fetches or uses demo."""
    s = (station or "").strip().upper()
    if len(s) == 3 and s.isalpha():
        return s
    if API_KEY:
        import httpx
        try:
            resp = httpx.get(
                f"{BASE_URL}/AutoCompleteStation/apikey/{API_KEY}/StationCodeOrName/{s}/",
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                stations = data.get("Station") or []
                if stations:
                    return stations[0].get("StationCode", s[:3])
        except Exception:
            pass
    # Demo fallback: use first 3 chars or common codes
    common = {"delhi": "NDLS", "new delhi": "NDLS", "mumbai": "BCT", "kolkata": "HWH", "chennai": "MAS", "bangalore": "SBC", "hyderabad": "HYB"}
    return common.get(s.lower(), s[:3] if len(s) >= 3 else "XXX")


@mcp.tool()
def search_trains_between_stations(from_station: str, to_station: str, date: str | None = None) -> str:
    """Search trains between two stations. Use station names (e.g. Delhi, Mumbai) or 3-letter codes (NDLS, BCT).
    Date in YYYY-MM-DD optional; if omitted uses tomorrow. Returns train list with numbers, names, times."""
    from_code = _station_code(from_station)
    to_code = _station_code(to_station)
    if API_KEY:
        import httpx
        try:
            resp = httpx.get(
                f"{BASE_URL}/TrainBetweenStation/apikey/{API_KEY}/From/{from_code}/To/{to_code}/",
                timeout=15,
            )
            if resp.status_code == 200:
                data = resp.json()
                if data.get("ResponseCode") == "200" and data.get("Status") == "SUCCESS":
                    trains = data.get("Trains") or []
                    if not trains:
                        return f"No trains found between {from_station} ({from_code}) and {to_station} ({to_code})."
                    lines = [f"- {t.get('TrainNo')} {t.get('TrainName')}: Dep {t.get('DepartureTime')} | Arr {t.get('ArrivalTime')} | {t.get('TravelTime')}" for t in trains[:15]]
                    return f"Trains between {from_station}–{to_station}:\n" + "\n".join(lines)
        except Exception as e:
            return f"API error: {e}. Using demo data."
    # Demo
    lines = [f"- {t['TrainNo']} {t['TrainName']}: Dep {t['DepartureTime']} | Arr {t['ArrivalTime']} | {t['TravelTime']}" for t in DEMO_TRAINS]
    return f"[Demo] Trains between {from_station}–{to_station}:\n" + "\n".join(lines) + "\n\nSet INDIAN_RAIL_API_KEY for live data."


@mcp.tool()
def check_seat_availability(
    train_number: str,
    from_station: str,
    to_station: str,
    date: str,
    class_code: str = "3A",
) -> str:
    """Check seat availability on a train. Provide train number, source/dest station (name or code), date (YYYY-MM-DD), class (1A, 2A, 3A, SL, CC, 2S). Returns availability status, GNWL/WL, confirmation %."""
    from_code = _station_code(from_station)
    to_code = _station_code(to_station)
    cls = (class_code or "3A").upper()
    if cls not in CLASS_CODES:
        cls = "3A"
    # Date: yyyyMMdd
    try:
        dt = datetime.strptime(date.strip(), "%Y-%m-%d")
        date_fmt = dt.strftime("%Y%m%d")
    except ValueError:
        return "Invalid date. Use YYYY-MM-DD."
    if API_KEY:
        import httpx
        try:
            url = f"{BASE_URL}/SeatAvailability/apikey/{API_KEY}/TrainNumber/{train_number}/From/{from_code}/To/{to_code}/Date/{date_fmt}/Quota/GN/Class/{cls}"
            resp = httpx.get(url, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("ResponseCode") == "200":
                    avail = data.get("Availability") or []
                    if avail:
                        lines = [f"- {a.get('JourneyDate', '')}: {a.get('Availability', 'N/A')} | Confirm: {a.get('Confirm', '')}" for a in avail[:7]]
                        return f"Seat availability {train_number} {from_station}→{to_station} ({cls}):\n" + "\n".join(lines)
                    return f"No availability data for {train_number} on {date}."
        except Exception as e:
            return f"API error: {e}. Using demo."
    # Demo
    return f"[Demo] {train_number} {from_station}→{to_station} ({cls}) on {date}: Available / GNWL12 (85% confirm). Set INDIAN_RAIL_API_KEY for live data."


@mcp.tool()
def get_station_code(station_name: str) -> str:
    """Resolve station name to 3-letter code. E.g. Delhi→NDLS, Mumbai→BCT. Use before search_trains if unsure of code."""
    code = _station_code(station_name)
    if API_KEY:
        import httpx
        try:
            resp = httpx.get(
                f"{BASE_URL}/AutoCompleteStation/apikey/{API_KEY}/StationCodeOrName/{station_name.strip()}/",
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                stations = data.get("Station") or []
                if stations:
                    return f"{station_name} → {stations[0].get('StationCode', '')} ({stations[0].get('NameEn', '')})"
        except Exception:
            pass
    return f"{station_name} → {code}"


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
