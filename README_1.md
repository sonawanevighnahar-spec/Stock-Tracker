# 📈 StockTrack — Live Market Dashboard

A sleek, dark-mode stock market web app built with Python (Flask) + yfinance + Chart.js. Track live prices, view historical charts with moving averages, and analyse Indian (NSE) and global stocks.

---

## ✨ Features

- **Live price** — current price, change %, 52-week high/low, market cap, P/E ratio
- **Interactive dark-mode chart** — price history with 7-day & 20-day moving averages
- **Volume chart** — green/red volume bars
- **Quick pick buttons** — one-click for popular Indian + global stocks
- **Multiple time periods** — 5 days to 5 years
- **Keyboard support** — press Enter to search

---

## 🚀 How To Run Locally

### Step 1 — Clone the repo
```bash
git clone https://github.com/YOUR-USERNAME/stocktrack.git
cd stocktrack
```

### Step 2 — Install dependencies
```bash
pip install -r requirements.txt
```

### Step 3 — Run the app
```bash
python app.py
```

### Step 4 — Open in browser
```
http://localhost:5000
```

---

## 🗂️ Project Structure

```
stocktrack/
│
├── app.py               # Flask backend — fetches stock data via yfinance
├── requirements.txt     # Python dependencies
├── README.md            # This file
└── templates/
    └── index.html       # Frontend — HTML + CSS + Chart.js
```

---

## 📦 Tech Stack

| Technology | Purpose |
|---|---|
| Python + Flask | Backend web server |
| yfinance | Fetches real stock data from Yahoo Finance (free) |
| Chart.js | Interactive charts |
| HTML + CSS + JS | Frontend |

---

## 📊 Supported Symbols

| Stock | Symbol |
|---|---|
| Reliance Industries | `RELIANCE.NS` |
| TCS | `TCS.NS` |
| Infosys | `INFY.NS` |
| HDFC Bank | `HDFCBANK.NS` |
| SBI | `SBIN.NS` |
| Apple | `AAPL` |
| NVIDIA | `NVDA` |
| Tesla | `TSLA` |

**Tip:** Add `.NS` for any NSE stock, `.BO` for BSE stocks.

---

## 💡 What I Learned

- Building REST APIs with Flask
- Fetching and processing financial data with yfinance
- Interactive chart rendering with Chart.js
- Frontend-backend communication using fetch API
- Dark mode UI design with CSS variables

---

## 🛣️ Future Plans

- [ ] Portfolio tracker — add multiple stocks + total P&L
- [ ] Price alerts — email/Telegram notification when price crosses a target
- [ ] Candlestick charts
- [ ] RSI, MACD technical indicators
- [ ] Deploy on Render / Railway (free hosting)

---

## 👤 About Me

Class 10 pass out from Kalyan-Dombivli.
Targeting IIT ECE → VLSI/FPGA → Hardware Quant.
Building projects from scratch to document my journey to IIT.

---

## ⭐ Give it a star if you find it useful!
