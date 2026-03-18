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
        return {"portfolio": [], "alerts": [], "watchlist": []}
    d = json.load(open(DATA_FILE))
    if "watchlist" not in d:
        d["watchlist"] = []
    return d

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

def fetch_price(symbol):
    try:
        t    = yf.Ticker(symbol)
        hist = t.history(period="2d")
        if hist.empty: return None, None
        return round(float(hist["Close"].iloc[-1]), 2), \
               t.info.get("longName") or t.info.get("shortName") or symbol
    except:
        return None, None

def calc_rsi(closes, period=14):
    if len(closes) < period + 1:
        return [None] * len(closes)
    rsi = [None] * period
    gains, losses = [], []
    for i in range(1, period + 1):
        diff = closes[i] - closes[i-1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    def to_rsi(ag, al):
        if al == 0: return 100.0
        rs = ag / al
        return round(100 - (100 / (1 + rs)), 2)
    rsi.append(to_rsi(avg_gain, avg_loss))
    for i in range(period + 1, len(closes)):
        diff = closes[i] - closes[i-1]
        g = max(diff, 0); l = max(-diff, 0)
        avg_gain = (avg_gain * (period-1) + g) / period
        avg_loss = (avg_loss * (period-1) + l) / period
        rsi.append(to_rsi(avg_gain, avg_loss))
    return rsi

@app.route("/")
def index():
    return render_template("index.html", popular=POPULAR)

@app.route("/api/stock")
def get_stock():
    symbol = request.args.get("symbol","").upper()
    period = request.args.get("period","1mo")
    if not symbol: return jsonify({"error":"No symbol"}), 400
    try:
        ticker = yf.Ticker(symbol)
        hist   = ticker.history(period=period)
        info   = ticker.info
        if hist.empty: return jsonify({"error":f"No data for {symbol}"}), 404

        prev  = hist["Close"].iloc[-2] if len(hist) > 1 else hist["Close"].iloc[-1]
        curr  = hist["Close"].iloc[-1]
        chg   = curr - prev
        chgp  = (chg / prev) * 100

        closes = [float(v) for v in hist["Close"]]
        rsi_vals = calc_rsi(closes)

        chart = {
            "dates":  [str(d.date()) for d in hist.index],
            "open":   [round(float(v),2) for v in hist["Open"]],
            "high":   [round(float(v),2) for v in hist["High"]],
            "low":    [round(float(v),2) for v in hist["Low"]],
            "close":  [round(float(v),2) for v in hist["Close"]],
            "volume": [int(v) for v in hist["Volume"]],
            "rsi":    rsi_vals,
        }
        if len(hist) >= 7:
            ma7 = hist["Close"].rolling(7).mean()
            chart["ma7"] = [round(float(v),2) if not math.isnan(v) else None for v in ma7]
        if len(hist) >= 20:
            ma20 = hist["Close"].rolling(20).mean()
            chart["ma20"] = [round(float(v),2) if not math.isnan(v) else None for v in ma20]

        currency = "₹" if symbol.endswith(".NS") or symbol.endswith(".BO") else "$"
        mkt_cap  = info.get("marketCap",0) or 0
        if mkt_cap>=1e12:   mkt_str=f"{currency}{mkt_cap/1e12:.2f}T"
        elif mkt_cap>=1e9:  mkt_str=f"{currency}{mkt_cap/1e9:.2f}B"
        elif mkt_cap>=1e6:  mkt_str=f"{currency}{mkt_cap/1e6:.2f}M"
        else:               mkt_str="N/A"

        return jsonify({
            "symbol":    symbol,
            "name":      info.get("longName") or info.get("shortName") or symbol,
            "currency":  currency,
            "price":     round(curr,2),
            "change":    round(chg,2),
            "changePct": round(chgp,2),
            "high52":    round(info.get("fiftyTwoWeekHigh",0) or 0,2),
            "low52":     round(info.get("fiftyTwoWeekLow",0) or 0,2),
            "volume":    int(hist["Volume"].iloc[-1]),
            "mktCap":    mkt_str,
            "pe":        round(info.get("trailingPE",0) or 0,2),
            "chart":     chart,
        })
    except Exception as e:
        return jsonify({"error":str(e)}), 500

# ── PORTFOLIO ─────────────────────────────────────────────────
@app.route("/api/portfolio")
def get_portfolio():
    data = load_data(); items = []
    for h in data["portfolio"]:
        price,name = fetch_price(h["symbol"])
        if price is None: continue
        currency = "₹" if h["symbol"].endswith(".NS") or h["symbol"].endswith(".BO") else "$"
        invested = h["qty"] * h["buy_price"]
        current  = h["qty"] * price
        pnl      = current - invested
        items.append({
            "symbol":h["symbol"],"name":name,"qty":h["qty"],
            "buyPrice":h["buy_price"],"currPrice":price,"currency":currency,
            "invested":round(invested,2),"current":round(current,2),
            "pnl":round(pnl,2),"pnlPct":round((pnl/invested*100) if invested else 0,2),
        })
    ti=sum(i["invested"] for i in items); tc=sum(i["current"] for i in items); tp=tc-ti
    return jsonify({"items":items,"totalInvested":round(ti,2),"totalCurrent":round(tc,2),
                    "totalPnl":round(tp,2),"totalPnlPct":round((tp/ti*100) if ti else 0,2)})

@app.route("/api/portfolio/add", methods=["POST"])
def add_holding():
    b=request.get_json(); symbol=b.get("symbol","").upper()
    qty=float(b.get("qty",0)); price=float(b.get("buyPrice",0))
    if not symbol or qty<=0 or price<=0: return jsonify({"error":"Invalid"}),400
    data=load_data()
    for h in data["portfolio"]:
        if h["symbol"]==symbol: h["qty"]=qty; h["buy_price"]=price; save_data(data); return jsonify({"ok":True})
    data["portfolio"].append({"symbol":symbol,"qty":qty,"buy_price":price})
    save_data(data); return jsonify({"ok":True})

@app.route("/api/portfolio/remove", methods=["POST"])
def remove_holding():
    symbol=request.get_json().get("symbol","").upper(); data=load_data()
    data["portfolio"]=[h for h in data["portfolio"] if h["symbol"]!=symbol]
    save_data(data); return jsonify({"ok":True})

# ── ALERTS ────────────────────────────────────────────────────
@app.route("/api/alerts")
def get_alerts():
    data=load_data(); out=[]
    for a in data["alerts"]:
        price,_=fetch_price(a["symbol"])
        currency="₹" if a["symbol"].endswith(".NS") else "$"
        hit=False
        if price:
            hit=(a["direction"]=="above" and price>=a["target"]) or \
                (a["direction"]=="below" and price<=a["target"])
        out.append({**a,"currPrice":price,"currency":currency,"triggered":hit})
    return jsonify({"alerts":out})

@app.route("/api/alerts/add", methods=["POST"])
def add_alert():
    b=request.get_json(); symbol=b.get("symbol","").upper()
    target=float(b.get("target",0)); direction=b.get("direction","above")
    if not symbol or target<=0: return jsonify({"error":"Invalid"}),400
    data=load_data()
    data["alerts"].append({"symbol":symbol,"target":target,"direction":direction})
    save_data(data); return jsonify({"ok":True})

@app.route("/api/alerts/remove", methods=["POST"])
def remove_alert():
    b=request.get_json(); symbol=b.get("symbol","").upper(); target=float(b.get("target",0))
    data=load_data()
    data["alerts"]=[a for a in data["alerts"] if not(a["symbol"]==symbol and a["target"]==target)]
    save_data(data); return jsonify({"ok":True})

# ── WATCHLIST ─────────────────────────────────────────────────
@app.route("/api/watchlist")
def get_watchlist():
    data=load_data(); items=[]
    for sym in data["watchlist"]:
        price,name=fetch_price(sym)
        currency="₹" if sym.endswith(".NS") or sym.endswith(".BO") else "$"
        items.append({"symbol":sym,"name":name or sym,"price":price,"currency":currency})
    return jsonify({"items":items})

@app.route("/api/watchlist/add", methods=["POST"])
def add_watchlist():
    symbol=request.get_json().get("symbol","").upper()
    if not symbol: return jsonify({"error":"No symbol"}),400
    data=load_data()
    if symbol not in data["watchlist"]: data["watchlist"].append(symbol)
    save_data(data); return jsonify({"ok":True})

@app.route("/api/watchlist/remove", methods=["POST"])
def remove_watchlist():
    symbol=request.get_json().get("symbol","").upper(); data=load_data()
    data["watchlist"]=[s for s in data["watchlist"] if s!=symbol]
    save_data(data); return jsonify({"ok":True})

if __name__=="__main__":
    app.run(debug=True)
