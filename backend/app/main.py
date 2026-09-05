from fastapi import FastAPI
from sqlalchemy import text
from app.database import Base, engine
from app.models import Customer, Payment
from .database import engine
from app.models import (
    Customer,
    Payment,
    RecoveryAction,
    RecoveryOutcome,
    AuditLog
)
from app.routes.customers import router as customer_router
from app.routes.payments import router as payment_router
from app.routes.recovery import router as recovery_router
from fastapi.middleware.cors import CORSMiddleware

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="RecoverAI",
    description="AI-Powered Revenue Recovery Agent",
    version="1.0.0"
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(customer_router)
app.include_router(payment_router)
app.include_router(recovery_router)

@app.get("/")
def root():
    return {
        "name": "RecoverAI",
        "message": "Revenue Recovery Agent is running",
        "status": "online"
    }


@app.get("/health")
def health():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

        return {
            "status": "healthy",
            "database": "connected"
        }

    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e)
        }