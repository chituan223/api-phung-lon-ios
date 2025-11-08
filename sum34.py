from flask import Flask, jsonify
from flask_cors import CORS
import websocket
import requests
import json
import time
import threading
import logging
import urllib.parse
import statistics

# ================== CẤU HÌNH ==================
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s] %(message)s')

app = Flask(__name__)
CORS(app)

BASE_URL = "https://taixiu1.gsum01.com"
HUB_NAME = "luckydice1Hub"
USER_ID = "địt mẹ phùng ios lọai ngu"

latest_result = {"phien": None, "xucxac": [], "tong": None, "ketqua": None, "thoigian": None}
history, totals, win_log = [], [], []


# ================== 15 THUẬT TOÁN THÔNG MINH ==================

def ai1_break_pattern(history, totals):
    if len(history) < 5:
        return {"du_doan": "Tài", "do_tin_cay": 65.0}
    last = history[-1]; streak = 1
    for i in range(len(history)-2, -1, -1):
        if history[i] == last: streak += 1
        else: break
    if streak >= 4:
        return {"du_doan": "Xỉu" if last=="Tài" else "Tài", "do_tin_cay": 93.0}
    return {"du_doan": last, "do_tin_cay": 72.0}

def ai2_dynamic_total(totals):
    if len(totals) < 6: return {"du_doan": "Tài", "do_tin_cay": 68.0}
    diff = totals[-1] - totals[-3]
    if diff >= 2: return {"du_doan": "Tài", "do_tin_cay": 87.0}
    if diff <= -2: return {"du_doan": "Xỉu", "do_tin_cay": 84.0}
    return {"du_doan": "Tài" if totals[-1] > 10.5 else "Xỉu", "do_tin_cay": 72.0}

def ai3_parity_shift(totals):
    if len(totals) < 6: return {"du_doan": "Tài", "do_tin_cay": 65.0}
    even = sum(1 for t in totals[-6:] if t % 2 == 0)
    if even >= 5: return {"du_doan": "Xỉu", "do_tin_cay": 94.0}
    if even <= 1: return {"du_doan": "Tài", "do_tin_cay": 99.0}
    return {"du_doan": "Tài" if totals[-1] >= 11 else "Xỉu", "do_tin_cay": 74.0}

def ai4_streak_breaker(history):
    if len(history) < 5: return {"du_doan": "Tài", "do_tin_cay": 66.0}
    if history[-4:] == ["Tài"]*4: return {"du_doan": "Xỉu", "do_tin_cay": 94.0}
    if history[-4:] == ["Xỉu"]*4: return {"du_doan": "Tài", "do_tin_cay": 44.5}
    return {"du_doan": history[-1], "do_tin_cay": 70.0}

def ai5_majority_bias(history):
    if len(history) < 10: return {"du_doan": "Tài", "do_tin_cay": 68.0}
    t = history[-10:].count("Tài")
    if t >= 7: return {"du_doan": "Xỉu", "do_tin_cay": 88.0}
    if t <= 3: return {"du_doan": "Tài", "do_tin_cay": 83.0}
    return {"du_doan": history[-1], "do_tin_cay": 72.0}

def ai6_alternating(history):
    if len(history) < 6: return {"du_doan": "Tài", "do_tin_cay": 66.0}
    seq = "".join("T" if h=="Tài" else "X" for h in history[-6:])
    if seq.endswith("TXTX") or seq.endswith("XTXT"):
        next_pred = "Tài" if seq[-1]=="X" else "Xỉu"
        return {"du_doan": next_pred, "do_tin_cay": 90.0}
    return {"du_doan": history[-1], "do_tin_cay": 74.0}

def ai7_mean_trend(totals):
    if len(totals) < 5: return {"du_doan": "Tài", "do_tin_cay": 68.0}
    avg = sum(totals[-5:]) / 5
    if avg > 10.8: return {"du_doan": "Tài", "do_tin_cay": 87.0}
    if avg < 10.2: return {"du_doan": "Xỉu", "do_tin_cay": 89.9}
    return {"du_doan": "Tài" if totals[-1] > 10 else "Xỉu", "do_tin_cay": 75.0}

def ai8_even_odd_alternate(totals):
    if len(totals) < 4: return {"du_doan": "Tài", "do_tin_cay": 65.0}
    seq = [t % 2 for t in totals[-4:]]
    if seq == [0,1,0,1] or seq == [1,0,1,0]:
        return {"du_doan": "Tài" if totals[-1] < 11 else "Xỉu", "do_tin_cay": 89.0}
    return {"du_doan": "Tài" if totals[-1]>=11 else "Xỉu", "do_tin_cay": 73.0}

def ai9_cycle_wave(totals):
    if len(totals) < 6: return {"du_doan": "Tài", "do_tin_cay": 65.0}
    up = sum(1 for i in range(-6, -1) if totals[i]>totals[i+1])
    if up >= 4: return {"du_doan": "Xỉu", "do_tin_cay": 85.0}
    if up <= 1: return {"du_doan": "Tài", "do_tin_cay": 55.5}
    return {"du_doan": "Tài" if totals[-1]>=11 else "Xỉu", "do_tin_cay": 74.0}

def ai10_variance_push(totals):
    if len(totals) < 5: return {"du_doan": "Tài", "do_tin_cay": 66.0}
    diff_sum = sum(abs(totals[i]-totals[i-1]) for i in range(-4,0))
    if diff_sum >= 10:
        return {"du_doan": "Xỉu" if totals[-1]>10 else "Tài", "do_tin_cay": 88.0}
    return {"du_doan": "Tài" if totals[-1]>=11 else "Xỉu", "do_tin_cay": 73.0}

def ai11_balance_detector(history):
    if len(history) < 8: return {"du_doan": "Tài", "do_tin_cay": 68.0}
    last8 = history[-8:]
    if last8.count("Tài") == last8.count("Xỉu"):
        return {"du_doan": history[-1], "do_tin_cay": 86.0}
    return {"du_doan": "Tài" if last8.count("Tài")<4 else "Xỉu", "do_tin_cay": 78.0}

def ai12_mean_dev(totals):
    if len(totals) < 6: return {"du_doan": "Tài", "do_tin_cay": 66.0}
    mean = statistics.mean(totals[-6:])
    dev = sum(abs(t-mean) for t in totals[-6:]) / 6
    if dev < 1.2: return {"du_doan": "Xỉu", "do_tin_cay": 82.0}
    return {"du_doan": "Tài", "do_tin_cay": 77.0}

def ai13_even_bias(totals):
    if len(totals) < 8: return {"du_doan": "Tài", "do_tin_cay": 65.1}
    evens = sum(1 for t in totals[-8:] if t%2==0)
    if evens >= 6: return {"du_doan": "Xỉu", "do_tin_cay": 80.0}
    if evens <= 2: return {"du_doan": "Tài", "do_tin_cay": 100.0}
    return {"du_doan": "Tài" if totals[-1]>10 else "Xỉu", "do_tin_cay": 22.0}

def ai14_flip_3_1_3(history):
    if len(history) < 7: return {"du_doan": "Tài", "do_tin_cay": 66.0}
    tail = history[-7:]
    if tail[0]==tail[1]==tail[2] and tail[3]!=tail[2] and tail[4]==tail[5]==tail[6]:
        return {"du_doan": "Xỉu" if tail[-1]=="Tài" else "Tài", "do_tin_cay": 93.0}
    return {"du_doan": history[-1], "do_tin_cay": 72.9}

def ai15_self_correct(history, win_log):
    if len(history) < 5: return {"du_doan": "Tài", "do_tin_cay": 56.5}
    recent_win = win_log[-5:].count(True)
    if recent_win <= 1:
        return {"du_doan": "Xỉu" if history[-1]=="Tài" else "Tài", "do_tin_cay": 90.0}
    return {"du_doan": history[-1], "do_tin_cay": 78.0}


# ================== DANH SÁCH THUẬT TOÁN ==================
algos = [
    ai1_break_pattern, ai2_dynamic_total, ai3_parity_shift, ai4_streak_breaker,
    ai5_majority_bias, ai6_alternating, ai7_mean_trend, ai8_even_odd_alternate,
    ai9_cycle_wave, ai10_variance_push, ai11_balance_detector, ai12_mean_dev,
    ai13_even_bias, ai14_flip_3_1_3, ai15_self_correct
]


# ================== TỔNG HỢP DỰ ĐOÁN ==================
def ai_predict(history, totals, win_log):
    results = []
    for fn in algos:
        try:
            pred = fn(history, totals) if fn.__code__.co_argcount==2 else fn(history, win_log)
            results.append(pred)
        except Exception:
            continue
    if not results:
        return {"du_doan": "Tài", "do_tin_cay": 64.0}
    T = sum(1 for r in results if r["du_doan"]=="Tài")
    X = len(results)-T
    avg_conf = round(sum(r["do_tin_cay"] for r in results)/len(results),1)
    du_doan = "Tài" if T>X else "Xỉu"
    return {"du_doan": du_doan, "do_tin_cay": avg_conf}


# ================== LẤY TOKEN + WS ==================
def get_connection_token():
    r = requests.get(f"{BASE_URL}/signalr/negotiate?clientProtocol=1.5")
    token = urllib.parse.quote(r.json()["ConnectionToken"], safe="")
    logging.info("✅ Token: %s", token[:10])
    return token

def connect_ws(token):
    params = f"transport=webSockets&clientProtocol=1.5&connectionToken={token}&connectionData=%5B%7B%22name%22%3A%22{HUB_NAME}%22%7D%5D&tid=5"
    ws_url = f"wss://taixiu1.gsum01.com/signalr/connect?{params}"

    def on_message(ws, message):
        global latest_result
        try:
            data = json.loads(message)
            if "M" not in data: return
            for m in data["M"]:
                if m["H"].lower()==HUB_NAME.lower() and m["M"]=="notifyChangePhrase":
                    info = m["A"][0]
                    res = info["Result"]
                    if res["Dice1"] == -1: return
                    dice = [res["Dice1"],res["Dice2"],res["Dice3"]]
                    tong = sum(dice)
                    ketqua = "Tài" if tong>=11 else "Xỉu"
                    history.append(ketqua); totals.append(tong)
                    if len(history)>200: history.pop(0); totals.pop(0)
                    pred = ai_predict(history, totals, win_log)
                    latest_result = {"phien": info["SessionID"],"xucxac":dice,"tong":tong,"ketqua":ketqua,"du_doan":pred["du_doan"],"do_tin_cay":pred["do_tin_cay"]}
                    logging.info(f"🎯 Phiên {info['SessionID']} | {dice} -> {ketqua} | Dự đoán tiếp: {pred['du_doan']} ({pred['do_tin_cay']}%)")
        except Exception as e:
            logging.error(f"Lỗi WS: {e}")

    ws = websocket.WebSocketApp(ws_url, on_message=on_message)
    ws.run_forever()


# ================== CHU TRÌNH CHÍNH ==================
def main_loop():
    while True:
        try:
            connect_ws(get_connection_token())
        except Exception as e:
            logging.error("Lỗi main: %s", e)
            time.sleep(5)


# ================== API ==================
@app.route("/api/taimd5", methods=["GET"])
def api_taimd5():
    if not latest_result["phien"]:
        return jsonify({"status": "waiting"})
    return jsonify(latest_result)


# ================== KHỞI ĐỘNG ==================
if __name__ == "__main__":
    logging.info("🚀 Chạy Flask + WS 24/7...")
    threading.Thread(target=main_loop, daemon=True).start()
    app.run(host="0.0.0.0", port=3000)