from fastapi import FastAPI
from pydantic import BaseModel
from datetime import datetime
import uvicorn

app = FastAPI()

# This is our temporary in-memory database list
VEHICLE_DATABASE = []

class VehicleAudit(BaseModel):
    track_id: int
    reconciled_id: str
    confidence: float
    gate_id: str = "GATE_NORTH_01"

# 1. THE SENDER ROUTE (What your AI talks to)
@app.post("/log-vehicle")
async def log_vehicle(data: VehicleAudit):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Save the record into our memory list
    record = {
        "timestamp": timestamp,
        "gate_id": data.gate_id,
        "track_id": data.track_id,
        "vehicle_id": data.reconciled_id,
        "confidence": f"{data.confidence * 100:.1f}%"
    }
    VEHICLE_DATABASE.append(record)
    
    print(f"[+] Logged: {data.reconciled_id}")
    return {"status": "success", "reconciled": data.reconciled_id}

# 2. NEW: THE VIEWING ROUTE (What you open in your browser!)
@app.get("/show-audit")
async def show_audit():
    # This returns the entire list of tracked vehicles as a clean web page
    return {
        "total_vehicles_audited": len(VEHICLE_DATABASE),
        "audit_log": VEHICLE_DATABASE
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)