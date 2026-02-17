import asyncio
import requests
import pandas as pd
import ta
from datetime import datetime, time
import pytz
from telegram import Bot

# ====== CONFIG ======
TOKEN = "8213426353:AAE8PUsCnaaeMm5QYsDKo5pfFEmtEc2x6ho"
CHAT_ID = "1330477563"
API_KEY = "cdd3b804b58642c68f8aaa89880d420c"

SYMBOLS = ["EUR/USD", "GBP/USD"]

KSA = pytz.timezone("Asia/Riyadh")

bot = Bot(token=TOKEN)

active_trade = False

# ====== SESSION FILTER ======
def is_us_session():
    now = datetime.now(KSA).time()
    return time(16, 0) <= now <= time(22, 30)

# ====== GET DATA ======
def get_data(symbol):
    url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval=1min&outputsize=100&apikey={API_KEY}"
    r = requests.get(url).json()

    if "values" not in r:
        return None

    df = pd.DataFrame(r["values"])
    df = df.astype(float)
    df = df.sort_index()
    return df

# ====== STRATEGY ======
def check_signal(df):
    df["ema"] = ta.trend.ema_indicator(df["close"], window=20)
    df["sar"] = ta.trend.psar_up(df["high"], df["low"], df["close"])
    df["dem"] = ta.momentum.demarker(df["high"], df["low"], window=14)

    last = df.iloc[-1]

    # Avoid neutral DeMarker zone
    if 0.45 < last["dem"] < 0.55:
        return None

    # PUT CONDITIONS
    if (
        last["close"] < last["ema"]
        and last["dem"] < 0.5
        and last["close"] < df.iloc[-1]["open"]
    ):
        return "PUT"

    # CALL CONDITIONS
    if (
        last["close"] > last["ema"]
        and last["dem"] > 0.5
        and last["close"] > df.iloc[-1]["open"]
    ):
        return "CALL"

    return None

# ====== MAIN LOOP ======
async def run():
    global active_trade

    while True:
        if is_us_session() and not active_trade:
            for symbol in SYMBOLS:
                df = get_data(symbol)
                if df is None:
                    continue

                signal = check_signal(df)

                if signal:
                    price = df.iloc[-1]["close"]
                    now = datetime.now(KSA).strftime("%H:%M")

                    message = (
                        f"🎯 Empire Sniper\n\n"
                        f"Pair: {symbol}\n"
                        f"Signal: {signal}\n"
                        f"Expiry: 3 Minutes\n"
                        f"Entry Time: {now}\n"
                        f"Price: {price}"
                    )

                    await bot.send_message(chat_id=CHAT_ID, text=message)

                    active_trade = True
                    await asyncio.sleep(180)
                    active_trade = False

        await asyncio.sleep(60)

asyncio.run(run())
