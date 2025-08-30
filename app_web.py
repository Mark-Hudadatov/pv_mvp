import os
from typing import Literal, Optional

from fastapi import FastAPI, Request, HTTPException, Query
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field, validator

from services.simulate import simulate

app = FastAPI()

# Short -> long maps for UI
ROUTE_MAP = {"N": "nominal", "A": "accelerated", "C": "cpi"}
FIN_MAP   = {"E": "equity", "L": "loan", "S": "leasing"}  # S = leasing

# ---------- Pydantic input for POST /api/simulate ----------
class SimIn(BaseModel):
    kwp: float = Field(gt=0, le=30)
    route: Literal["N", "A", "C"]
    accounting: Literal["net_billing"] = "net_billing"
    finance_mode: Literal["E", "L", "S"]
    loan_scenario: Optional[Literal["low", "base", "high"]] = "base"
    self_consumption: float = Field(ge=0, le=1)
    apply_urban_premium: bool = True

    @validator("loan_scenario", always=True)
    def _loan_req(cls, v, values):
        if values.get("finance_mode") == "L" and v is None:
            raise ValueError("loan_scenario required for finance_mode=loan")
        return v

# ---------- API: main simulation (JSON) ----------
@app.post("/api/simulate")
def api_simulate(inp: SimIn):
    try:
        res = simulate(
            kwp=inp.kwp,
            route=ROUTE_MAP[inp.route],
            accounting=inp.accounting,
            self_consumption=inp.self_consumption,
            finance_mode=FIN_MAP[inp.finance_mode],
            loan_scenario=inp.loan_scenario or "base",
            apply_urban_premium=inp.apply_urban_premium,
        )
        return {"status": "ok", **res}
    except Exception as e:
        # Возвращаем безопасный ответ вместо 500
        return {"status": "error", "message": str(e)}

# ---------- Static + templates ----------
app.mount("/static", StaticFiles(directory="ui/static"), name="static")
templates = Jinja2Templates(directory="ui/templates")

# ---------- UI ----------
@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# ---------- Lightweight test endpoint ----------
# Принимаем kWp из query (как в твоём URL) и маппим на kwp
@app.get("/api/sim")
def api_sim(
    kWp: float = Query(20, alias="kWp"),                 # совместимость с kWp
    route: str = "accelerated",
    finance_mode: str = "equity",
    loan_scenario: str = "base",
    self_consumption: float = 0.5,
):
    # Нормализуем route: допускаем "N/A/C" и полные имена
    route_norm = ROUTE_MAP.get(route, route)  # если уже полное имя, просто пройдёт дальше

    try:
        res = simulate(
            kwp=kWp,
            route=route_norm,
            accounting="net_billing",
            finance_mode=finance_mode,
            loan_scenario=loan_scenario,
            self_consumption=self_consumption,
            apply_urban_premium=True,
        )
        return {
            "metrics": res["metrics"],
            "years": res["years"],
            "cashflow": res["cashflow"],
        }
    except Exception as e:
        # возвращаем 400 вместо 500, чтобы на фронте было проще отловить
        raise HTTPException(status_code=400, detail=str(e))

# ---------- health ----------
@app.get("/health")
def health():
    return {"status": "ok"}
