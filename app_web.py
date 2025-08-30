import os
from typing import Literal

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field, model_validator
from services.simulate import simulate

app = FastAPI()

ROUTE_MAP = {"N": "nominal", "A": "accelerated", "C": "cpi"}
FIN_MAP   = {"E": "equity",  "L": "loan",        "S": "leasing"}

# ---------- Models ----------

class SimIn(BaseModel):
    kwp: float = Field(gt=0, le=30)
    route: Literal["N", "A", "C"]
    accounting: Literal["net_billing"] = "net_billing"
    finance_mode: Literal["E", "L", "S"]
    # делаем свободным, разрулим на уровне модели
    loan_scenario: str | None = None
    self_consumption: float = Field(ge=0, le=1)
    apply_urban_premium: bool = True

    @model_validator(mode="after")
    def normalize(self):
        # Приведём loan_scenario к нормальному виду
        if self.finance_mode == "L":
            map_ = {"L": "low", "B": "base", "H": "high"}
            if self.loan_scenario is None or self.loan_scenario == "":
                self.loan_scenario = "base"
            self.loan_scenario = map_.get(self.loan_scenario, self.loan_scenario)
            if self.loan_scenario not in {"low", "base", "high"}:
                raise ValueError("loan_scenario must be low/base/high for finance_mode=loan")
        else:
            # для equity/leasing сценарий кредита не нужен
            self.loan_scenario = None
        return self

@app.post("/api/simulate")
def api_simulate(inp: SimIn):
    try:
        scenario = inp.loan_scenario or "base"  # для loan уже нормализовано, для остальных -> "base"
        res = simulate(
            kwp=inp.kwp,
            route=ROUTE_MAP[inp.route],
            accounting=inp.accounting,
            self_consumption=inp.self_consumption,
            finance_mode=FIN_MAP[inp.finance_mode],
            loan_scenario=scenario,
            apply_urban_premium=inp.apply_urban_premium,
        )
        return {"status": "ok", **res}
    except Exception as e:
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
