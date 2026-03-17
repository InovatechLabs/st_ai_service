from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.endpoints import reports, insights

app = FastAPI(title="SafeTemp AI Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(reports.router, prefix="/reports", tags=["Relatórios"])
app.include_router(insights.router, prefix="/insights", tags=["IA Insights"])

@app.get("/")
def root():
    return {"status": "online"}