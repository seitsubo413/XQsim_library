"""
XQsim Patch Trace API Server (Interface Layer)

目的:
- 既存XQsimのコンパイラ/シミュレータを「そのまま」呼び出し、
  QASM文字列を入力としてパッチ形状の時系列(JSON)を返すAPIを提供する。

注意:
- 本ファイルは入出力(HTTP/JSON)のみを担う。
- 量子処理やシミュレーションのロジックは既存実装に委譲する。
"""

from __future__ import annotations

import logging
import traceback
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from patch_trace_backend import trace_patches_from_qasm


app = FastAPI(title="XQsim Patch Trace API", version="0.1.0")
logger = logging.getLogger("xqsim.api")


class TraceRequest(BaseModel):
    qasm: str = Field(..., description="OpenQASM 2.0 text")
    config: str = Field("example_cmos_d5", description="Config name under src/configs (without .json)")
    keep_artifacts: bool = Field(False, description="Keep intermediate artifacts (debug)")


class TraceResponse(BaseModel):
    result: Dict[str, Any]


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/trace", response_model=TraceResponse)
def trace(req: TraceRequest) -> TraceResponse:
    if not req.qasm or not req.qasm.strip():
        raise HTTPException(status_code=400, detail="qasm is empty")

    try:
        res = trace_patches_from_qasm(
            req.qasm,
            config_name=req.config,
            skip_pqsim=True,
            keep_artifacts=req.keep_artifacts,
        )
        return TraceResponse(result=res)
    except FileNotFoundError as e:
        # e.g., missing config file
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Interface-layer: log full traceback for debugging.
        tb = traceback.format_exc()
        logger.error("Unhandled exception in /trace: %s\n%s", repr(e), tb)
        # Don't leak huge tracebacks to clients by default; surface message.
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


