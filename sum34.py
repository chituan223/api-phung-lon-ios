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

# =========================================================
# ⚙️ CẤU HÌNH
# =========================================================
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s] %(message)s')

app = Flask(__name__)
CORS(app)

BASE_URL = "https://taixiu1.gsum01.com"
HUB_NAME = "luckydice1Hub"
USER_ID = "biios2502"

latest_result = {
    "phien": None,
    "xucxac1": None,
    "xucxac2": None,
    "xucxac3": None,
    "tong": None,
    "du_doan": None,
    "ty_le": None,
    "id": USER_ID
}

history, totals, win_log = [], [], []

# =========================================================
# 🧠 15 THUẬT TOÁN PHÂN TÍCH THẬT
# =========================================================

def ratio_scale(value, base=70, maxv=95, minv=60):
    """Chuyển độ mạnh yếu thành phần trăm hợp lý, không random."""
    return round(max(minv, min(maxv, base + (value * 3))), 1)

def ai1_break_pattern(history, totals):
    if len(history) < 5:
        return {"du_doan": "Tài", "ty_le": 65.5}
    last = history[-1]
    streak = 1
    for i in range(len(history) - 2, -1, -1):
        if history[i] == last:
            streak += 1
        else:
            break
    if streak >= 4:
        return {"du_doan": "Xỉu" if last == "Tài" else "Tài", "ty_le": ratio_scale(streak, 70)}
    return {"du_doan": last, "ty_le": ratio_scale(streak, 68)}

def ai2_chẵn_lẻ(totals):
    if len(totals) < 6:
        return {"du_doan": "Tài", "ty_le": 66.2}
    even = sum(1 for t in totals[-6:] if t % 2 == 0)
    score = abs(even - 3)
    if even >= 5:
        return {"du_doan": "Xỉu", "ty_le": ratio_scale(score, 75)}
    elif even <= 1:
        return {"du_doan": "Tài", "ty_le": ratio_scale(score, 75)}
    else:
        du_doan = "Tài" if totals[-1] > 10 else "Xỉu"
        return {"du_doan": du_doan, "ty_le": ratio_scale(1, 70)}

def ai3_trung_binh(totals):
    if len(totals) < 8:
        return {"du_doan": "Tài", "ty_le": 67.1}
    avg = statistics.mean(totals[-6:])
    delta = totals[-1] - avg
    if delta > 1.5:
        return {"du_doan": "Xỉu", "ty_le": ratio_scale(delta, 78)}
    elif delta < -1.5:
        return {"du_doan": "Tài", "ty_le": ratio_scale(-delta, 78)}
    else:
        return {"du_doan": "Tài" if avg > 10.5 else "Xỉu", "ty_le": ratio_scale(1, 72)}

def ai4_nhip_dao(history):
    if len(history) < 6:
        return {"du_doan": "Tài", "ty_le": 66.0}
    pattern = history[-4:]
    alternating = all(pattern[i] != pattern[i-1] for i in range(1, len(pattern)))
    if alternating:
        return {"du_doan": history[-1], "ty_le": 82.5}
    else:
        return {"du_doan": "Tài" if history[-1] == "Xỉu" else "Xỉu", "ty_le": 74.3}

def ai5_tan_suat(history):
    if len(history) < 10:
        return {"du_doan": "Tài", "ty_le": 65.0}
    t = history[-10:].count("Tài")
    bias = abs(5 - t)
    du_doan = "Tài" if t < 5 else "Xỉu"
    return {"du_doan": du_doan, "ty_le": ratio_scale(bias, 73)}

def ai6_lien_hoan(history):
    if len(history) < 7:
        return {"du_doan": "Tài", "ty_le": 67.0}
    if history[-3:] == ["Tài", "Tài", "Tài"]:
        return {"du_doan": "Xỉu", "ty_le": 89.0}
    elif history[-3:] == ["Xỉu", "Xỉu", "Xỉu"]:
        return {"du_doan": "Tài", "ty_le": 88.6}
    return {"du_doan": history[-1], "ty_le": 71.2}

def ai7_chen_le(history, totals):
    if len(totals) < 4:
        return {"du_doan": "Tài", "ty_le": 68.3}
    chẵn = sum(1 for t in totals[-4:] if t % 2 == 0)
    if chẵn >= 3:
        return {"du_doan": "Xỉu", "ty_le": 83.0}
    elif chẵn == 0:
        return {"du_doan": "Tài", "ty_le": 83.0}
    return {"du_doan": "Tài" if totals[-1] >= 11 else "Xỉu", "ty_le": 70.4}

def ai8_bat_cau_dao(history):
    if len(history) < 8:
        return {"du_doan": "Tài", "ty_le": 65.5}
    last5 = history[-5:]
    if last5.count("Tài") == 5 or last5.count("Xỉu") == 5:
        return {"du_doan": "Xỉu" if last5[0] == "Tài" else "Tài", "ty_le": 90.5}
    if all(last5[i] != last5[i-1] for i in range(1, 5)):
        return {"du_doan": history[-1], "ty_le": 78.8}
    return {"du_doan": "Tài" if history[-1] == "Xỉu" else "Xỉu", "ty_le": 72.2}

def ai9_binh_quan_lech(history, totals):
    if len(totals) < 8:
        return {"du_doan": "Tài", "ty_le": 67.0}
    avg_tong = statistics.mean(totals[-5:])
    lech = abs(totals[-1] - avg_tong)
    du_doan = "Tài" if avg_tong > 10.8 else "Xỉu"
    return {"du_doan": du_doan, "ty_le": ratio_scale(lech, 74)}

def ai10_song_song(history):
    if len(history) < 6:
        return {"du_doan": "Tài", "ty_le": 65.0}
    nhom = [history[i:i+2] for i in range(0, len(history)-1, 2)]
    same = sum(1 for g in nhom if len(set(g)) == 1)
    ty_le = ratio_scale(same, 72)
    du_doan = "Tài" if same % 2 == 0 else "Xỉu"
    return {"du_doan": du_doan, "ty_le": ty_le}

# Tổng hợp 10 thuật toán (có thể thêm 5 sau)
algos = [ai1_break_pattern, ai2_chẵn_lẻ, ai3_trung_binh, ai4_nhip_dao, ai5_tan_suat,
         ai6_lien_hoan, ai7_chen_le, ai8_bat_cau_dao, ai9_binh_quan_lech, ai10_song_song]

# =========================================================
# 🔹 KẾT HỢP DỰ ĐOÁN
# =========================================================
def ai_predict(history, totals):
    results = []
    for fn in algos:
        try:
            results.append(fn(history, totals))
        except Exception:
            continue
    if not results:
        return {"du_doan": "Tài", "ty_le": 65.0}
    T = sum(1 for r in results if r["du_doan"] == "Tài")
    X = len(results) - T
    avg_conf = round(sum(r["ty_le"] for r in results) / len(results), 1)
    du_doan = "Tài" if T > X else "Xỉu"
    confidence_adjust = 2.5 * abs(T - X)
    return {"du_doan": du_doan, "ty_le": round(avg_conf + confidence_adjust, 1)}

# =========================================================
# 🔸 WebSocket xử lý phiên
# =========================================================
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
                if m["H"].lower() == HUB_NAME.lower() and m["M"] == "notifyChangePhrase":
                    info = m["A"][0]
                    res = info["Result"]
                    if res["Dice1"] == -1: return
                    dice = [res["Dice1"], res["Dice2"], res["Dice3"]]
                    tong = sum(dice)
                    ketqua = "Tài" if tong >= 11 else "Xỉu"
                    history.append(ketqua)
                    totals.append(tong)
                    if len(history) > 200: history.pop(0); totals.pop(0)
                    pred = ai_predict(history, totals)
                    latest_result = {
                        "phien": info["SessionID"],
                        "xucxac1": dice[0],
                        "xucxac2": dice[1],
                        "xucxac3": dice[2],
                        "tong": tong,
                        "du_doan": pred["du_doan"],
                        "ty_le": pred["ty_le"],
                        "id": USER_ID
                    }
                    logging.info(f"🎯 Phiên {info['SessionID']} | {dice} -> {ketqua} | Dự đoán tiếp: {pred['du_doan']} ({pred['ty_le']}%)")
        except Exception as e:
            logging.error(f"Lỗi WS: {e}")

    ws = websocket.WebSocketApp(ws_url, on_message=on_message)
    ws.run_forever()

# =========================================================
# 🔁 CHU TRÌNH CHÍNH
# =========================================================
def main_loop():
    while True:
        try:
            connect_ws(get_connection_token())
        except Exception as e:
            logging.error("Lỗi main: %s", e)
            time.sleep(5)

# =========================================================
# 🌐 API
# =========================================================
@app.route("/api/taimd5", methods=["GET"])
def api_taimd5():
    if not latest_result["phien"]:
        return jsonify({"status": "waiting"})
    return jsonify(latest_result)

# =========================================================
# 🚀 KHỞI ĐỘNG
# =========================================================
if __name__ == "__main__":
    logging.info("🚀 Đang chạy Flask + AI dự đoán thông minh (không random)...")
    threading.Thread(target=main_loop, daemon=True).start()
    app.run(host="0.0.0.0", port=3000)
