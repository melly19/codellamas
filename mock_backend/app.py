import asyncio
import json
from pathlib import Path
from typing import List, Literal, Optional

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict


class GenerateRequest(BaseModel):
    # Only allow these fields (no extras)
    model_config = ConfigDict(extra="forbid")
    topic: str
    code_smells: List[str]
    mode: Optional[Literal["single", "multi"]] = None


app = FastAPI()

# Helpful for local dev / VS Code extension webviews
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

RESPONSE_PATH = Path(__file__).with_name("generate_result.json")


@app.get("/")
async def root():
    return {"status": "ok", "mock": True}


@app.post("/generate")
async def generate(_: GenerateRequest):
    # Simulate backend latency
    await asyncio.sleep(1)

    # Always return the same payload
    return json.loads(RESPONSE_PATH.read_text(encoding="utf-8"))


if __name__ == "__main__":
    # Hard-coded host and port; run the already-imported `app` object
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=False)


