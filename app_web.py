import os
from typing import Literal

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field, field_validator

from services.simulate import simulate

app = FastAPI()

ROUTE_MAP = {"N": "nominal", "A": "accelerated", "C": "cpi"}
FIN_MAP   = {"E": "equity", "L": "loan", "S": "leasing"}  # S = leasing

# ---------- Models ----------

class SimIn(BaseModel):
    kwp: float = Field(gt=0, le=30)
    route: Literal["N", "A", "C"]
    accounting: Literal["net_billing"] = "net_billing"
    finance_mode: Literal["E", "L", "S"]
    loan_scenario: Literal["low", "base", "high"] | None = "base"
    self_consumption: float = Field(ge=0, le=1)
    apply_urban_premium: bool = True

    @field_validator("loan_scenario", mode="before")
    def _loan_req(cls, v, info):
        # if finance_mode == "L" (loan), loan_scenario must be provided
        data = info.data
        if data.get("finance_mode") == "L" and (v is None or v == ""):
            raise ValueError("loan_scenario required for finance_mode=loan")
        return v or "base"

# ---------- API ----------

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
        # Возвращаем мягкую ошибку, чтобы фронт не падал
        return {"status": "error", "message": str(e)}

# Тестовый (legacy) эндпоинт — удобно дергать из браузера
@app.get("/api/sim")
def api_sim(
    kwp: float = 20,
    route: str = "accelerated",     # может прийти 'A'/'N'/'C' или полное название
    finance_mode: str = "equity",   # 'equity' | 'loan' | 'leasing'
    loan_scenario: str = "base",
    self_consumption: float = 0.5,
):
    # Поддержка коротких кодов маршрута
    route_full = ROUTE_MAP.get(route, route)  # если 'A'/'N'/'C' -> развернем, иначе оставим как есть
    res = simulate(
        kwp=kwp,
        route=route_full,
        accounting="net_billing",
        finance_mode=finance_mode,
        loan_scenario=loan_scenario,
        self_consumption=self_consumption,
        apply_urban_premium=True,
    )
    return {"status": "ok", **res}

# ---------- Static & Templates ----------

app.mount("/static", StaticFiles(directory="ui/static"), name="static")
templates = Jinja2Templates(directory="ui/templates")

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# Health — для Render
@app.get("/health")
def health():
    return {"status": "ok"}
