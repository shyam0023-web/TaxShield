from fastapi import FastAPI
from datetime import date
from app.watchdog.timebar import calculate_timebar, TimeBarRequest, TimeBarResult

app = FastAPI(title="TaxShield API")


@app.get("/")
def home():
    return {"message": "TaxShield API is running!"}


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/api/timebar", response_model=TimeBarResult)
def timebar(
    fy: str = "2018-19", section: int = 73, notice_date: date = date(2024, 1, 15)
):
    """Check if a GST notice is time-barred"""

    request = TimeBarRequest(fy=fy, section=section, notice_date=notice_date)
    return calculate_timebar(request)
