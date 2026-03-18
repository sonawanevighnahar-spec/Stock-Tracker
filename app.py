from flask import Flask, render_template, jsonify, request
import yfinance as yf
import json, os, math

app = Flask(__name__)
DATA_FILE = "data.json"

POPULAR = {
    "RELIANCE.NS": "Reliance Industries",
    "TCS.NS":      "TCS",
    "INFY.NS":     "Infosys",
    "HDFCBANK.NS": "HDFC Bank",
    "WIPRO.NS":    "Wipro",
    "AAPL":        "Apple",
    "GOOGL":       "Google",
    "TSLA":        "Tesla",
    "NVDA":        "NVIDIA",
    "MSFT":        "Microsoft",
}

def load_data():
    if not os.path.exists(DATA_FILE):
        return {"portfolio": [], "alerts": []}
    with open(DATA_FILE) as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

def fetch_price(symbol):
    try:
        t    = yf.Ticker(symbol)
        hist = t.history(period="2d")
        if hist.empty:
            return None, None
        curr = float(hist["Close"].iloc[-1])
        name = t.info.get("longName") or t.info.get("shortName") or symbol
        return round(curr, 2), name
    except:
        return None, None

@app.route("/")
def index():
    return render_template("index.html", popular=POPULAR)

@app.route("/api/stock")
def get_stock():
    symbol = request.args.get("symbol", "").upper()
    period = request.args.get("period", "1mo")
    if not symbol:
        return jsonify({"error": "No symbol"}), 400
    try:
        ticker = yf.Ticker(symbol)
        hist   = ticker.history(period=period)
        info   = ticker.info
        if hist.empty:
            return jsonify({"error": f"No data for {symbol}"}), 404
        prev = hist["Close"].iloc[-2] if len(hist) > 1 else hist["Close"].iloc[-1]
        curr = hist["Close"].iloc[-1]
        chg  = curr - prev
        chgp = (chg / prev) * 100
        chart = {
            "dates":  [str(d.date()) for d in hist.index],
            "close":  [round(float(v), 2) for v in hist["Close"]],
            "volume": [int(v) for v in hist["Volume"]],
        }
        if len(hist) >= 7:
            ma7 = hist["Close"].rolling(7).mean()
            chart["ma7"] = [round(float(v), 2) if not math.isnan(v) else None for v in ma7]
        if len(hist) >= 20:
            ma20 = hist["Close"].rolling(20).mean()
            chart["ma20"] = [round(float(v), 2) if not math.isnan(v) else None for v in ma20]
        currency = "₹" if symbol.endswith(".NS") or symbol.endswith(".BO") else "$"
        mkt_cap  = info.get("marketCap", 0) or 0
        if mkt_cap >= 1e12:   mkt_str = f"{currency}{mkt_cap/1e12:.2f}T"
        elif mkt_cap >= 1e9:  mkt_str = f"{currency}{mkt_cap/1e9:.2f}B"
        elif mkt_cap >= 1e6:  mkt_str = f"{currency}{mkt_cap/1e6:.2f}M"
        else:                 mkt_str = "N/A"
        return jsonify({
            "symbol": symbol,
            "name": info.get("longName") or info.get("shortName") or symbol,
            "currency": currency,
            "price": round(curr, 2),
            "change": round(chg, 2),
            "changePct": round(chgp, 2),
            "high52": round(info.get("fiftyTwoWeekHigh", 0) or 0, 2),
            "low52":  round(info.get("fiftyTwoWeekLow",  0) or 0, 2),
            "volume": int(hist["Volume"].iloc[-1]),
            "mktCap": mkt_str,
            "pe":     round(info.get("trailingPE", 0) or 0, 2),
            "chart":  chart,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ── PORTFOLIO ─────────────────────────────────────────────────
@app.route("/api/portfolio")
def get_portfolio():
    data  = load_data()
    items = []
    for h in data["portfolio"]:
        price, name = fetch_price(h["symbol"])
        if price is None: continue
        currency = "₹" if h["symbol"].endswith(".NS") or h["symbol"].endswith(".BO") else "$"
        invested = h["qty"] * h["buy_price"]
        current  = h["qty"] * price
        pnl      = current - invested
        pnl_pct  = (pnl / invested * 100) if invested else 0
        items.append({
            "symbol": h["symbol"], "name": name, "qty": h["qty"],
            "buyPrice": h["buy_price"], "currPrice": price, "currency": currency,
            "invested": round(invested, 2), "current": round(current, 2),
            "pnl": round(pnl, 2), "pnlPct": round(pnl_pct, 2),
        })
    ti = sum(i["invested"] for i in items)
    tc = sum(i["current"]  for i in items)
    tp = tc - ti
    return jsonify({
        "items": items,
        "totalInvested": round(ti, 2),
        "totalCurrent":  round(tc, 2),
        "totalPnl":      round(tp, 2),
        "totalPnlPct":   round((tp/ti*100) if ti else 0, 2),
    })

@app.route("/api/portfolio/add", methods=["POST"])
def add_holding():
    b = request.get_json()
    symbol = b.get("symbol","").upper()
    qty    = float(b.get("qty", 0))
    price  = float(b.get("buyPrice", 0))
    if not symbol or qty <= 0 or price <= 0:
        return jsonify({"error": "Invalid"}), 400
    data = load_data()
    for h in data["portfolio"]:
        if h["symbol"] == symbol:
            h["qty"] = qty; h["buy_price"] = price
            save_data(data)
            return jsonify({"ok": True})
    data["portfolio"].append({"symbol": symbol, "qty": qty, "buy_price": price})
    save_data(data)
    return jsonify({"ok": True})

@app.route("/api/portfolio/remove", methods=["POST"])
def remove_holding():
    symbol = request.get_json().get("symbol","").upper()
    data   = load_data()
    data["portfolio"] = [h for h in data["portfolio"] if h["symbol"] != symbol]
    save_data(data)
    return jsonify({"ok": True})

# ── ALERTS ────────────────────────────────────────────────────
@app.route("/api/alerts")
def get_alerts():
    data = load_data()
    out  = []
    for a in data["alerts"]:
        price, _ = fetch_price(a["symbol"])
        currency = "₹" if a["symbol"].endswith(".NS") else "$"
        hit = False
        if price:
            hit = (a["direction"] == "above" and price >= a["target"]) or \
                  (a["direction"] == "below" and price <= a["target"])
        out.append({**a, "currPrice": price, "currency": currency, "triggered": hit})
    return jsonify({"alerts": out})

@app.route("/api/alerts/add", methods=["POST"])
def add_alert():
    b = request.get_json()
    symbol    = b.get("symbol","").upper()
    target    = float(b.get("target", 0))
    direction = b.get("direction","above")
    if not symbol or target <= 0:
        return jsonify({"error": "Invalid"}), 400
    data = load_data()
    data["alerts"].append({"symbol": symbol, "target": target, "direction": direction})
    save_data(data)
    return jsonify({"ok": True})

@app.route("/api/alerts/remove", methods=["POST"])
def remove_alert():
    b = request.get_json()
    symbol = b.get("symbol","").upper()
    target = float(b.get("target", 0))
    data   = load_data()
    data["alerts"] = [a for a in data["alerts"]
                      if not (a["symbol"] == symbol and a["target"] == target)]
    save_data(data)
    return jsonify({"ok": True})

if __name__ == "__main__":
    app.run(debug=True)
