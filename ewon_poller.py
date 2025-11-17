import time
import json
import sqlite3
from datetime import datetime
from pymodbus.client import ModbusTcpClient
from dotenv import load_dotenv
import os

# ================== CONFIG ==================

load_dotenv()

PLC_IP = os.getenv("EWON_PLC_IP", "192.168.1.10")
PLC_PORT = int(os.getenv("EWON_PLC_PORT", "502"))
UNIT_ID = int(os.getenv("EWON_PLC_UNIT_ID", "1"))
INTERVAL = float(os.getenv("POLL_INTERVAL_SEC", "2.0"))

# OJO: MISMO PATH QUE EN app.py
DB_PATH = "data/db.sqlite"

TAGS_FILE = "tags_ewon.json"


# ================== UTILIDADES ==================

def read_tags_from_json():
    """
    Lee tags_ewon.json
    Formato esperado (ejemplos):

    [
        {"tag": "V_L1N", "address": 40001, "type": "float"},
        {"tag": "I_L1", "address": 40011, "type": "float"},
        {"tag": "CORE_TEMP", "address": 40100, "type": "float"},
        {"tag": "STATE_MACHINE", "address": 0, "type": "bool", "func": "coil"},
        {"tag": "APF_ON", "address": 1, "type": "bool", "func": "coil"}
    ]

    - "tag" → nombre EXACTO de la columna en la tabla measurements
    - "address" → registro Modbus
    - "type" → "float", "int" o "bool"
    - "func" → opcional: "holding" (por defecto), "input", "coil"
    - "scale" → opcional: divisor (por defecto 1000.0 para float)
    """
    with open(TAGS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def read_modbus_value(client: ModbusTcpClient, addr: int, tipo: str, func: str, scale: float):
    """
    Lee un valor desde Modbus según tipo y función.
    Devuelve float/int/0/1 o None si error.
    """
    try:
        if tipo == "bool":
            # Estados / alarmas → normalmente coils
            if func == "coil":
                rr = client.read_coils(addr, 1, unit=UNIT_ID)
            else:
                rr = client.read_discrete_inputs(addr, 1, unit=UNIT_ID)
            if rr.isError():
                return None
            return 1 if rr.bits[0] else 0

        elif tipo == "int":
# Un solo registro entero
            if func == "input":
                rr = client.read_input_registers(addr, 1, unit=UNIT_ID)
            else:
                rr = client.read_holding_registers(addr, 1, unit=UNIT_ID)
            if rr.isError():
                return None
            return int(rr.registers[0])

        elif tipo == "float":
# Dos registros → 32 bits, se escala
            if func == "input":
                rr = client.read_input_registers(addr, 2, unit=UNIT_ID)
            else:
                rr = client.read_holding_registers(addr, 2, unit=UNIT_ID)
            if rr.isError():
                return None
            raw = (rr.registers[0] << 16) + rr.registers[1]
            return float(raw) / scale

        else:
# Tipo no soportado
            return None

    except Exception as e:
        print(f"[ERR] Modbus leyendo addr {addr}: {e}")
        return None


def save_row_to_db(row: dict):
    """
    Inserta UNA fila en measurements.
    - row debe tener clave 'ts'
    - el resto de claves = nombres de columnas en la tabla
    """
    if "ts" not in row:
        return

    cols = list(row.keys())
    vals = [row[c] for c in cols]

    col_list = ",".join(cols)
    placeholders = ",".join(["?"] * len(cols))

    con = sqlite3.connect(DB_PATH)
    try:
        # ts es PRIMARY KEY, así si coinciden segundos sustituye la fila
        sql = f"INSERT OR REPLACE INTO measurements ({col_list}) VALUES ({placeholders})"
        con.execute(sql, vals)
        con.commit()
    except Exception as e:
        print("[ERR] SQLite:", e)
    finally:
        con.close()


# ================== LOOP PRINCIPAL ==================

def main():
    print("=== EWON poller Improve Sankey ===")
    print(f"Conectando a {PLC_IP}:{PLC_PORT} (unit {UNIT_ID})")
    print(f"DB: {DB_PATH}")
    print(f"Tags: {TAGS_FILE}")

    tags = read_tags_from_json()
    if not tags:
        print("⚠️ No hay tags en tags_ewon.json")
        return

    client = ModbusTcpClient(PLC_IP, port=PLC_PORT)

    while True:
        ts = datetime.now().isoformat(timespec="seconds")
        row = {"ts": ts} # fila que vamos a guardar

        try:
            if not client.connect():
                print("❌ No se puede conectar al EWON")
                time.sleep(INTERVAL)
                continue

            for t in tags:
                name = t.get("tag")
                addr = int(t.get("address", 0))
                tipo = t.get("type", "float").lower()
                func = t.get("func", "holding").lower()
                scale = float(t.get("scale", 1000.0))

                if not name:
                    continue

                value = read_modbus_value(client, addr, tipo, func, scale)
                if value is not None:
                    row[name] = value

            # Guarda toda la fila en DB
            save_row_to_db(row)
            print(f"[OK] {ts} ⇒ {len(row)-1} campos actualizados")

        except Exception as e:
            print("[ERR] Ciclo poller:", e)

        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()

