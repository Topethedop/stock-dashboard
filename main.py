from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import yfinance as yf
from datetime import datetime

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# === Persistent Watchlist ===
WATCHLIST_FILE = "watchlist.txt"

def load_watchlist():
    try:
        with open(WATCHLIST_FILE, "r") as f:
            return [line.strip().upper() for line in f.readlines() if line.strip()]
    except FileNotFoundError:
        return []

def save_watchlist(tickers):
    with open(WATCHLIST_FILE, "w") as f:
        f.write("\n".join(tickers))

tracked_symbols = load_watchlist()

# === Event Log ===
event_log = []

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/api/stocks")
async def get_stocks():
    stocks = []
    for symbol in tracked_symbols:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        price = info.get("regularMarketPrice", 0)
        previous = info.get("previousClose", price)
        change_percent = ((price - previous) / previous) * 100 if previous else 0
        direction = "up" if change_percent > 0 else "down" if change_percent < 0 else "neutral"

        stocks.append({
            "symbol": symbol,
            "price": round(price, 2),
            "change_percent": round(change_percent, 2),
            "direction": direction
        })

        # Log events
        if abs(change_percent) >= 1.5:
            timestamp = datetime.now().strftime("%H:%M:%S")
            action = "spiked up" if change_percent > 0 else "dropped"
            event_log.append(f"[{timestamp}] {symbol} {action} {round(change_percent, 2)}%")
            event_log[:] = event_log[-10:]

    top_gainer = max(stocks, key=lambda x: x["change_percent"], default=None)
    top_loser = min(stocks, key=lambda x: x["change_percent"], default=None)

    return {
        "stocks": stocks,
        "leaderboard": {
            "top_gainer": top_gainer,
            "top_loser": top_loser
        },
        "events": list(reversed(event_log))
    }

@app.post("/api/add_ticker")
async def add_ticker(ticker: str = Form(...)):
    ticker = ticker.upper()
    if ticker not in tracked_symbols:
        tracked_symbols.append(ticker)
        save_watchlist(tracked_symbols)
    return {"success": True, "watchlist": tracked_symbols}
