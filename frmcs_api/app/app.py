from fastapi import FastAPI
from app.ble_manager import BLEManager
from contextlib import asynccontextmanager



ble = BLEManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # START
    print("Starting app...")

    yield

    # STOP
    print("Stopping app...")
    if ble.client and ble.client.is_connected:
        await ble.client.disconnect()


app = FastAPI(lifespan=lifespan)


@app.get("/")
def home():
    return {"message": "Hello World"}


@app.post("/train/connect")
async def connect_train():
    try:
        await ble.connect()
        return {"status": "connected"}
    
    except Exception as e:
        return {"error": str(e)}
    

@app.post("/train/speed")
async def set_speed(speed: int):
    try:
        if not ble.client or not ble.client.is_connected:
            await ble.connect()
        
        await ble.set_speed(speed)
        return {"speed": speed}
    
    except Exception as e:
        return {"error": str(e)}


@app.post("/train/disconnect")
async def disconnect_train():
    try:
        if ble.client and ble.client.is_connected:
            await ble.client.disconnect()
            return {"status": "disconnected"}
        return {"status": "already disconnected"}

    except Exception as e:
        return {"error": str(e)}


@app.get("/train/status")
async def train_status():
    if ble.client and ble.client.is_connected:
        return {"connected": True}
    
    return {"connected": False}
