"""ScopeLeak web app: one screen, local inference.

    .venv/Scripts/python -m uvicorn app:app --port 8000
"""
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from core import classifier, evidence, llm, parser

ROOT = Path(__file__).parent
EXAMPLE = ROOT / "eval" / "scenarios" / "website"

app = FastAPI(title="ScopeLeak")
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")


@app.get("/")
def index():
    return FileResponse(ROOT / "static" / "index.html")


@app.get("/api/status")
def status():
    """Which model is configured and whether the server actually has it.
    The endpoint URL and API key stay on the server."""
    config = llm.load_config()
    try:
        available = llm.list_models(config)
    except Exception as exc:
        return {"model": config["model"], "ready": False,
                "error": f"Cannot reach the model server: {exc}"}
    if config["model"] not in available:
        return {"model": config["model"], "ready": False,
                "error": f"Model {config['model']} is not installed. "
                         f"Run: ollama pull {config['model']}"}
    return {"model": config["model"], "ready": True, "local": "localhost" in config["base_url"]}


@app.get("/api/example")
def example():
    return {"agreement": (EXAMPLE / "contract.txt").read_text(encoding="utf-8"),
            "message": "Great work on the website so far! Could we also add a reserved area "
                       "where our customers can log in and download their invoices? "
                       "And the button colours should be our brand green."}


@app.post("/api/analyze")
def analyze(message: str = Form(...), agreement: str = Form(""),
            agreement_file: UploadFile | None = File(None)):
    if agreement_file and agreement_file.filename:
        agreement = parser.extract_text(agreement_file.filename, agreement_file.file.read())
    if not agreement.strip() or not message.strip():
        raise HTTPException(400, "Both the agreement and the client message are needed.")
    try:
        items = classifier.classify(agreement, message)
    except Exception as exc:
        raise HTTPException(502, f"The model did not answer: {exc}")
    return {"model": llm.load_config()["model"],
            "lines": evidence.number_lines(agreement),
            "requests": items}
