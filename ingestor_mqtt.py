import argparse, sqlite3, os, json
from datetime import datetime
import paho.mqtt.client as mqtt

DB_PATH = "data/db.sqlite"

def get_conn():
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("""CREATE TABLE IF NOT EXISTS measurements(
        ts TEXT PRIMARY KEY,
        source TEXT,
        tag TEXT,
        voltage REAL,
        current REAL,
        power_kw REAL,
        pf REAL,
        thd REAL
    )""")
    return conn

def insert_row(conn, row):
    conn.execute(
        "INSERT OR REPLACE INTO measurements (ts, source, tag, voltage, current, power_kw, pf, thd) VALUES (?,?,?,?,?,?,?,?)",
        (row["ts"], row["source"], row["tag"], row["voltage"], row["current"], row["power_kw"], row["pf"], row["thd"])
    ); conn.commit()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--broker", required=True)
    ap.add_argument("--port", type=int, default=1883)
    ap.add_argument("--topic", required=True)
    ap.add_argument("--tag", default="main-bus")
    args = ap.parse_args()

    conn = get_conn()
    def on_message(client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
            v = float(payload.get("voltage", 0.0))
            i = float(payload.get("current", 0.0))
            pf = float(payload.get("pf", 1.0))
            thd = float(payload.get("thd", 0.0))
            tag = payload.get("tag", args.tag)
            pkw = (v * i * (3**0.5) * pf) / 1000.0
            insert_row(conn, {"ts": datetime.now().isoformat(), "source":"mqtt", "tag":tag,
                              "voltage":v, "current":i, "power_kw":pkw, "pf":pf, "thd":thd})
        except Exception:
            pass
    client = mqtt.Client()
    client.on_message = on_message
    client.connect(args.broker, args.port, 60)
    client.subscribe(args.topic)
    try:
        client.loop_forever()
    except KeyboardInterrupt:
        client.disconnect()

if __name__ == "__main__":
    main()
