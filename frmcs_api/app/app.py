from fastapi import FastAPI
import asyncio
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from pydantic import BaseModel
from dotenv import load_dotenv
import os

from app.lego_train import LegoTrain
from app.ble_manager import BLEManager

load_dotenv(".env.local")

# MAC
EXPRESS_MAC = os.getenv("EXPRESS_MAC")
CARGO_MAC = os.getenv("CARGO_MAC")

express = LegoTrain("Express", EXPRESS_MAC, 0)
cargo = LegoTrain("Cargo", CARGO_MAC, 20)

# TWARDY REJESTR POŁĄCZEŃ - Musi być tutaj, na górze!
connected_flags = {
    "express": False,
    "cargo": False
}


class SpeedRequest(BaseModel):
    speed: int


class LightRequest(BaseModel):
    brightness: int


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting app...")
    yield
    print("Stopping app...")

    # Odpinamy Express przy wyłączaniu serwera
    if express.client:
        await express.disconnect()

    # Odpinamy Cargo przy wyłączaniu serwera
    if cargo.client:
        await cargo.disconnect()


app = FastAPI(lifespan=lifespan)

cors_origins = os.getenv("CORS_ORIGINS", "").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def home():
    return {"status": "success", "message": "FRMCS API"}


# --- CONNECT ---
@app.post("/express/connect")
async def connect_express():
    try:
        await express.connect()
        await asyncio.sleep(1)
        connected_flags["express"] = True  # Zaznaczamy w słowniku
        return {"status": "success", "message": "express connected"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/cargo/connect")
async def connect_cargo():
    try:
        await cargo.connect()
        await asyncio.sleep(1)
        connected_flags["cargo"] = True  # Zaznaczamy w słowniku
        return {"status": "success", "message": "cargo connected"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# --- SPEED ---
@app.post("/express/speed")
async def express_speed(req: SpeedRequest):
    try:
        print("Incoming speed:", req.speed)
        if not connected_flags["express"]:
            await express.connect()
            connected_flags["express"] = True

        await express.send_speed(req.speed)
        return {"status": "success", "speed": req.speed}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/cargo/speed")
async def cargo_speed(req: SpeedRequest):
    try:
        print("Incoming speed:", req.speed)
        if not connected_flags["cargo"]:
            await cargo.connect()
            connected_flags["cargo"] = True

        await cargo.send_speed(req.speed)
        return {"status": "success", "speed": req.speed}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# --- STOP ---
@app.post("/express/stop")
async def express_stop():
    try:
        await express.stop()
        return {"status": "success", "message": "express stopped"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/cargo/stop")
async def cargo_stop():
    try:
        await cargo.stop()
        return {"status": "success", "message": "cargo stopped"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# --- DISCONNECT ---
@app.post("/express/disconnect")
async def express_disconnect():
    try:
        connected_flags["express"] = False  # Blokada w UI od razu
        if express.client:
            try:
                await express.stop()
                await express.disconnect()
            except Exception as hw_error:
                print(f"Zignorowano błąd sprzętowy (Express już rozłączony?): {hw_error}")

        return {"status": "success", "message": "express disconnected"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/cargo/disconnect")
async def cargo_disconnect():
    try:
        connected_flags["cargo"] = False  # Blokada w UI od razu
        if cargo.client:
            try:
                await cargo.stop()
                await cargo.disconnect()
            except Exception as hw_error:
                print(f"Zignorowano błąd sprzętowy (Cargo już rozłączony?): {hw_error}")

        return {"status": "success", "message": "cargo disconnected"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# --- LIGHTS ---
@app.post("/express/light")
async def express_light(req: LightRequest):
    return await express.set_light(req.brightness)


# --- STATUS ---
@app.get("/status")
async def status():
    try:
        # Sprawdzamy co twierdzi moduł Expressu
        express_hw = False
        if express.client:
            hw_val = getattr(express.client, 'is_connected', False)
            if callable(hw_val):
                res = hw_val()
                express_hw = await res if asyncio.iscoroutine(res) else res
            else:
                express_hw = hw_val

        # Ostateczny stan: Prawda TYLKO gdy moduł twierdzi, że jest połączony, ORAZ kliknęliśmy "Connect"
        final_express_conn = bool(express_hw) and connected_flags["express"]

        # Sprawdzamy co twierdzi moduł Cargo
        cargo_hw = False
        if cargo.client:
            hw_val = getattr(cargo.client, 'is_connected', False)
            if callable(hw_val):
                res = hw_val()
                cargo_hw = await res if asyncio.iscoroutine(res) else res
            else:
                cargo_hw = hw_val

        final_cargo_conn = bool(cargo_hw) and connected_flags["cargo"]

        return {
            "status": "success",
            "data": {
                "express": {
                    "speed": getattr(express, "speed", 0),
                    "connected": final_express_conn,
                    "light": getattr(express, "light_on", False)
                },
                "cargo": {
                    "speed": getattr(cargo, "speed", 0),
                    "connected": final_cargo_conn
                }
            }
        }
    except Exception as e:
        print(f"Błąd statusu: {e}")
        return {"status": "error", "message": str(e)}
