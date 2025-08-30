import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from services.simulate import simulate

app = FastAPI()

app.mount("/static", StaticFiles(directory="ui/static"), name="static")
templates = Jinja2Templates(directory="ui/templates")

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/sim")
def api_sim(kWp: float = 20, route: str = "accelerated",
            finance_mode: str = "equity", loan_scenario: str = "base",
            self_consumption: float = 0.5):
    res = simulate(kWp=kWp, route=route, accounting="net_billing",
                   finance_mode=finance_mode, loan_scenario=loan_scenario,
                   self_consumption=self_consumption, apply_urban_premium=True)
    return {
        "metrics": res["metrics"],
        "years": res["years"],
        "cashflow": res["cashflow"]
    }

@app.get("/health")
def health():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("app_web:app", host="0.0.0.0", port=port, reload=True)
