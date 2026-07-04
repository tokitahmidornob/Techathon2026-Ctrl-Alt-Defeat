import asyncio
import random
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List

app = FastAPI(title="Smart Office Monitoring API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Device(BaseModel):
    id: str
    type: str
    room: str
    power_draw: float
    is_on: bool
    last_changed: datetime

ROOMS = ["Drawing Room", "Work Room 1", "Work Room 2"]
DEVICES = []
PENDING_APPROVALS = {}
ECO_LOGS = []

def init_devices():
    device_id_counter = 1
    for room in ROOMS:
        # 2 Fans (60W)
        for _ in range(2):
            DEVICES.append(Device(
                id=f"DEV-{device_id_counter:03d}",
                type="Fan",
                room=room,
                power_draw=60.0,
                is_on=False,
                last_changed=datetime.now(timezone.utc)
            ))
            device_id_counter += 1
        # 3 Lights (15W)
        for _ in range(3):
            DEVICES.append(Device(
                id=f"DEV-{device_id_counter:03d}",
                type="Light",
                room=room,
                power_draw=15.0,
                is_on=False,
                last_changed=datetime.now(timezone.utc)
            ))
            device_id_counter += 1

init_devices()

async def simulate_activity():
    while True:
        await asyncio.sleep(random.randint(10, 20))
        num_toggles = random.randint(1, 3)
        devices_to_toggle = random.sample(DEVICES, num_toggles)
        
        now = datetime.now(timezone.utc)
        for dev in devices_to_toggle:
            dev.is_on = not dev.is_on
            dev.last_changed = now
            
        # Periodically mock a >2 hour anomaly for demonstration purposes
        if random.random() < 0.15:
            active_devices = [d for d in DEVICES if d.is_on]
            if active_devices:
                anomaly_dev = random.choice(active_devices)
                anomaly_dev.last_changed = now - timedelta(hours=2, minutes=30)

async def eco_monitor():
    print("Eco-monitor task initialized and started!")
    while True:
        await asyncio.sleep(5)
        print("Checking for eco-mode timeouts...")
        now = datetime.now(timezone.utc)
        pending_count = 0
        for dev in DEVICES:
            if dev.is_on:
                if dev.id in PENDING_APPROVALS:
                    continue
                time_on = (now - dev.last_changed).total_seconds()
                if time_on > 30:
                    PENDING_APPROVALS[dev.id] = dev.dict()
                    ECO_LOGS.insert(0, f"[{now.strftime('%H:%M:%S')}] Eco-Mode Engaged: {dev.room} {dev.type} pending approval.")
                    ECO_LOGS[:] = ECO_LOGS[:50]
                    pending_count += 1
                    
        if pending_count > 0:
            print(f"Found {pending_count} new pending approval(s). Total pending: {len(PENDING_APPROVALS)}")

@app.on_event("startup")
async def startup_event():
    # asyncio.create_task(simulate_activity()) # Disabled to prevent random resets during Eco-Mode testing
    asyncio.create_task(eco_monitor())

@app.get("/api/status")
async def get_status():
    return {"devices": [dev.dict() for dev in DEVICES]}

@app.post("/api/toggle/{room_name}/{device_id}")
async def toggle_device(room_name: str, device_id: str):
    now = datetime.now(timezone.utc)
    for dev in DEVICES:
        if dev.room == room_name and dev.id == device_id:
            dev.is_on = not dev.is_on
            dev.last_changed = now
            if not dev.is_on:
                PENDING_APPROVALS.pop(device_id, None)
            state_str = "ON" if dev.is_on else "OFF"
            ECO_LOGS.insert(0, f"[{now.strftime('%H:%M:%S')}] Manual Override: {device_id} in {room_name} toggled {state_str}")
            ECO_LOGS[:] = ECO_LOGS[:50]
            return {"status": "success", "device": dev.dict()}
    return {"status": "error", "message": "Device not found"}

@app.get("/api/usage/total")
async def get_total_usage():
    total_watts = sum(dev.power_draw for dev in DEVICES if dev.is_on)
    daily_kwh = (total_watts / 1000.0) * 24
    projected_daily_cost_bdt = daily_kwh * 10.0
    return {
        "total_watts": total_watts,
        "estimated_daily_kwh": round(daily_kwh, 2),
        "projected_daily_cost_bdt": round(projected_daily_cost_bdt, 2)
    }

class EcoResolveRequest(BaseModel):
    action: str

@app.get("/api/eco/pending")
async def get_pending_approvals():
    return {"pending_approvals": list(PENDING_APPROVALS.values())}

@app.post("/api/eco/resolve/{device_id}")
async def resolve_eco(device_id: str, payload: EcoResolveRequest):
    if device_id not in PENDING_APPROVALS:
        return {"status": "error", "message": "Device not pending approval"}
    
    dev_info = PENDING_APPROVALS.pop(device_id)
    now = datetime.now(timezone.utc)
    
    if payload.action == "turn_off":
        for dev in DEVICES:
            if dev.id == device_id:
                dev.is_on = False
                dev.last_changed = now
                ECO_LOGS.insert(0, f"[{now.strftime('%H:%M:%S')}] Eco-Mode Engaged: {dev.room} {dev.type} auto-disabled to save power.")
                ECO_LOGS[:] = ECO_LOGS[:50]
                break
    elif payload.action == "ignore":
        for dev in DEVICES:
            if dev.id == device_id:
                dev.last_changed = now
                ECO_LOGS.insert(0, f"[{now.strftime('%H:%M:%S')}] Eco-Mode: Manual override to keep {dev.room} {dev.type} ON.")
                ECO_LOGS[:] = ECO_LOGS[:50]
                break
                
    return {"status": "success"}

@app.get("/api/eco/logs")
async def get_eco_logs():
    return {"logs": ECO_LOGS[:50]}

@app.get("/api/usage/rooms")
async def get_room_usage():
    usage_by_room = {room: 0.0 for room in ROOMS}
    for dev in DEVICES:
        if dev.is_on:
            usage_by_room[dev.room] += dev.power_draw
    return {"room_usage": usage_by_room}

@app.get("/api/anomalies")
async def get_anomalies():
    anomalies = []
    now = datetime.now(timezone.utc)
    for dev in DEVICES:
        if dev.is_on:
            time_on = (now - dev.last_changed).total_seconds()
            if time_on > 7200: # 2 hours in seconds
                anomalies.append({
                    "device": dev.dict(),
                    "hours_on": round(time_on / 3600, 2)
                })
    return {"anomalies": anomalies}
