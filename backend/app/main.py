from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes_flights import router as flights_router
from app.api.routes_eco import router as eco_router
from app.api.routes_live import router as live_router


app = FastAPI(title="FlightGuard API")


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(flights_router, prefix="/api")
app.include_router(eco_router, prefix="/api")
app.include_router(live_router, prefix="/api")


@app.get("/")
def root():
    return {"message": "FlightGuard API is running"}


@app.get("/api/health")
def health_check():
    return {"status": "ok"}

