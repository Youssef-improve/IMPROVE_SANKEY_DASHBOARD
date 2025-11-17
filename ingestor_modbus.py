import argparse, time, sqlite3, os, math
from datetime import datetime
from pymodbus.client import ModbusTcpClient

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
    ap.add_argument("--ip", required=True)
    ap.add_argument("--port", type=int, default=502)
    ap.add_argument("--unit", type=int, default=1)
    ap.add_argument("--tag", default="main-bus")
    ap.add_argument("--regV", type=int, required=True)
    ap.add_argument("--regI", type=int, required=True)
    ap.add_argument("--regPF", type=int, required=True)
    ap.add_argument("--regTHD", type=int, required=True)
    ap.add_argument("--scaleV", type=float, default=0.1)
    ap.add_argument("--scaleI", type=float, default=0.1)
    ap.add_argument("--scalePF", type=float, default=0.001)
    ap.add_argument("--scaleTHD", type=float, default=0.1)
    ap.add_argument("--period", type=float, default=1.0)
    args = ap.parse_args()

    conn = get_conn()
    client = ModbusTcpClient(args.ip, port=args.port, timeout=1)
    while True:
        try:
            if not client.connect():
                time.sleep(args.period); continue
            rr = client.read_holding_registers(args.regV, 4, unit=args.unit)
            if rr.isError():
                client.close(); time.sleep(args.period); continue
            regs = rr.registers
            v = regs[0]*args.scaleV
            i = regs[1]*args.scaleI
            pf = max(0.0, min(1.0, regs[2]*args.scalePF))
            thd = regs[3]*args.scaleTHD
            pkw = (v * i * math.sqrt(3) * pf) / 1000.0
            insert_row(conn, {"ts": datetime.now().isoformat(), "source":"modbus", "tag":args.tag,
                              "voltage":v, "current":i, "power_kw":pkw, "pf":pf, "thd":thd})
            time.sleep(args.period)
        except KeyboardInterrupt:
            break
        except Exception:
            time.sleep(args.period)
    client.close()

if __name__ == "__main__":
    main()
