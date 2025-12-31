"""
XQsim Patch Trace API Server (Interface Layer)

目的:
- 既存XQsimのコンパイラ/シミュレータを「そのまま」呼び出し、
  QASM文字列を入力としてパッチ形状の時系列(JSON)を返すAPIを提供する。

注意:
- 本ファイルは入出力(HTTP/JSON)のみを担う。
- 量子処理やシミュレーションのロジックは既存実装に委譲する。

重要な運用制約:
- trace処理は直列化される（同時実行は429エラー）
- uvicorn --workers 1 での運用を推奨
- sys.exitのインターセプトはプロセス全体に影響するため、並列実行は危険
"""

from __future__ import annotations

import logging
import os
import signal
import threading
import time
import traceback
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator


logger = logging.getLogger("xqsim.api")

# ============================================================================
# 直列化のためのグローバルmutex
# ============================================================================
_trace_lock = threading.Lock()
_trace_in_progress = False
_trace_start_time: Optional[float] = None

# 環境変数で設定可能なパラメータ
MAX_QASM_SIZE_BYTES = int(os.environ.get("XQSIM_MAX_QASM_SIZE_BYTES", str(1024 * 1024)))  # 1MB
MAX_QUBITS = int(os.environ.get("XQSIM_MAX_QUBITS", "20"))
MAX_DEPTH = int(os.environ.get("XQSIM_MAX_DEPTH", "1000"))
MAX_INSTRUCTIONS = int(os.environ.get("XQSIM_MAX_INSTRUCTIONS", "10000"))
TRACE_TIMEOUT_SECONDS = int(os.environ.get("XQSIM_TRACE_TIMEOUT_SECONDS", "300"))  # 5分


def _init_ray_once() -> None:
    """
    Rayをプロセス起動時に1回だけ初期化する。
    
    重要:
    - 関数呼び出し毎にray.init()するとメモリ/オブジェクトストアが積み上がる
    - /dev/shmの存在確認とフォールバックを実装
    - object_store_memoryを環境変数で調整可能に
    """
    import ray
    
    if ray.is_initialized():
        logger.info("Ray already initialized, skipping")
        return
    
    # 環境変数でRay設定を調整可能に
    os.environ.setdefault("RAY_DISABLE_DASHBOARD", "1")
    os.environ.setdefault("RAY_DASHBOARD_ENABLED", "0")
    os.environ.setdefault("RAY_USAGE_STATS_ENABLED", "0")
    
    # object_store_memoryを環境変数から取得（デフォルト: 256MB）
    object_store_mb = int(os.environ.get("XQSIM_RAY_OBJECT_STORE_MB", "256"))
    object_store_memory = object_store_mb * 1024 * 1024
    
    # /dev/shmの存在確認とフォールバック
    plasma_dir = "/dev/shm"
    if not os.path.exists(plasma_dir):
        plasma_dir = "/tmp/ray_plasma"
        os.makedirs(plasma_dir, exist_ok=True)
        logger.warning(f"/dev/shm not found, falling back to {plasma_dir}")
    else:
        # /dev/shmの空き容量確認
        try:
            stat = os.statvfs(plasma_dir)
            available_mb = (stat.f_bavail * stat.f_frsize) / (1024 * 1024)
            if available_mb < object_store_mb * 1.5:
                plasma_dir = "/tmp/ray_plasma"
                os.makedirs(plasma_dir, exist_ok=True)
                logger.warning(
                    f"/dev/shm has only {available_mb:.0f}MB available, "
                    f"falling back to {plasma_dir}"
                )
        except Exception as e:
            logger.warning(f"Failed to check /dev/shm capacity: {e}")
    
    try:
        ray.init(
            ignore_reinit_error=True,
            include_dashboard=False,
            log_to_driver=False,
            num_cpus=int(os.environ.get("XQSIM_RAY_NUM_CPUS", "1")),
            object_store_memory=object_store_memory,
            _plasma_directory=plasma_dir,
            _temp_dir="/tmp/ray",
        )
        logger.info(
            f"Ray initialized: object_store={object_store_mb}MB, "
            f"plasma_dir={plasma_dir}"
        )
    except Exception as e:
        logger.error(f"Failed to initialize Ray: {e}")
        raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPIのライフスパン管理。
    アプリケーション起動時にRayを初期化し、終了時にシャットダウンする。
    """
    # 起動時
    logger.info("Starting XQsim API server...")
    _init_ray_once()
    logger.info(f"Configuration: MAX_QASM_SIZE={MAX_QASM_SIZE_BYTES}B, "
                f"MAX_QUBITS={MAX_QUBITS}, MAX_DEPTH={MAX_DEPTH}, "
                f"TRACE_TIMEOUT={TRACE_TIMEOUT_SECONDS}s")
    yield
    # 終了時
    logger.info("Shutting down XQsim API server...")
    global _trace_in_progress
    if _trace_in_progress:
        logger.warning("Trace operation in progress during shutdown, may be interrupted")
    try:
        import ray
        if ray.is_initialized():
            ray.shutdown()
            logger.info("Ray shutdown completed")
    except Exception as e:
        logger.warning(f"Ray shutdown failed: {e}")


app = FastAPI(
    title="XQsim Patch Trace API",
    version="0.3.0",
    lifespan=lifespan,
)


class TraceRequest(BaseModel):
    qasm: str = Field(..., description="OpenQASM 2.0 text")
    config: str = Field(
        "example_cmos_d5",
        description="Config name under src/configs (without .json)"
    )
    keep_artifacts: bool = Field(False, description="Keep intermediate artifacts (debug)")
    debug_logging: bool = Field(False, description="Enable verbose debug logging")
    
    @validator("qasm")
    def validate_qasm_size(cls, v):
        if len(v.encode("utf-8")) > MAX_QASM_SIZE_BYTES:
            raise ValueError(
                f"QASM size exceeds limit: {len(v.encode('utf-8'))} bytes > {MAX_QASM_SIZE_BYTES} bytes"
            )
        return v


class TraceResponse(BaseModel):
    result: Dict[str, Any]


class ErrorResponse(BaseModel):
    detail: str


def _validate_circuit_limits(qc) -> None:
    """
    回路の制限をチェックする。
    
    Raises:
        ValueError: 制限を超えた場合
    """
    num_qubits = qc.num_qubits
    if num_qubits > MAX_QUBITS:
        raise ValueError(f"Number of qubits exceeds limit: {num_qubits} > {MAX_QUBITS}")
    
    depth = qc.depth()
    if depth > MAX_DEPTH:
        raise ValueError(f"Circuit depth exceeds limit: {depth} > {MAX_DEPTH}")
    
    num_instructions = len(qc.data)
    if num_instructions > MAX_INSTRUCTIONS:
        raise ValueError(f"Number of instructions exceeds limit: {num_instructions} > {MAX_INSTRUCTIONS}")


@app.get("/health")
def health() -> Dict[str, Any]:
    """ヘルスチェック。trace実行中かどうかも返す。"""
    return {
        "status": "ok",
        "trace_in_progress": _trace_in_progress,
        "limits": {
            "max_qasm_size_bytes": MAX_QASM_SIZE_BYTES,
            "max_qubits": MAX_QUBITS,
            "max_depth": MAX_DEPTH,
            "max_instructions": MAX_INSTRUCTIONS,
            "trace_timeout_seconds": TRACE_TIMEOUT_SECONDS,
        }
    }


@app.post(
    "/trace",
    response_model=TraceResponse,
    responses={
        429: {"model": ErrorResponse, "description": "Trace already in progress"},
        400: {"model": ErrorResponse, "description": "Invalid input or simulation error"},
        504: {"model": ErrorResponse, "description": "Trace timeout"},
    }
)
def trace(req: TraceRequest) -> TraceResponse:
    """
    QASMからパッチトレースを生成する。
    
    重要な制約:
    - このエンドポイントは直列化される（同時に1つのリクエストのみ実行可能）
    - 実行中に別のリクエストが来ると429エラーを返す
    - タイムアウトを超えると504エラーを返す
    """
    global _trace_in_progress, _trace_start_time
    
    if not req.qasm or not req.qasm.strip():
        raise HTTPException(status_code=400, detail="qasm is empty")

    # 直列化: 既に実行中なら429を返す
    acquired = _trace_lock.acquire(blocking=False)
    if not acquired:
        raise HTTPException(
            status_code=429,
            detail="Another trace operation is in progress. Please try again later."
        )
    
    try:
        _trace_in_progress = True
        _trace_start_time = time.time()
        
        # 遅延インポート（Ray初期化後に行う）
        from patch_trace_backend import trace_patches_from_qasm
        import importlib
        qiskit = importlib.import_module("qiskit")
        QuantumCircuit = qiskit.QuantumCircuit
        
        # QASMをパースして制限をチェック
        try:
            qc = QuantumCircuit.from_qasm_str(req.qasm)
            _validate_circuit_limits(qc)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid QASM: {e}")
        
        # タイムアウト付きでtrace実行
        res = trace_patches_from_qasm(
            req.qasm,
            config_name=req.config,
            skip_pqsim=True,
            keep_artifacts=req.keep_artifacts,
            debug_logging=req.debug_logging,
            timeout_seconds=TRACE_TIMEOUT_SECONDS,
        )
        
        # タイムアウトチェック
        elapsed = time.time() - _trace_start_time
        if elapsed > TRACE_TIMEOUT_SECONDS:
            raise HTTPException(
                status_code=504,
                detail=f"Trace operation timed out after {elapsed:.1f} seconds"
            )
        
        return TraceResponse(result=res)
        
    except HTTPException:
        raise
    except FileNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except TimeoutError as e:
        raise HTTPException(status_code=504, detail=f"Trace timeout: {e}")
    except RuntimeError as e:
        tb = traceback.format_exc()
        logger.error("Simulation error in /trace: %s\n%s", repr(e), tb)
        raise HTTPException(status_code=400, detail=f"Simulation error: {e}")
    except Exception as e:
        tb = traceback.format_exc()
        logger.error("Unhandled exception in /trace: %s\n%s", repr(e), tb)
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")
    finally:
        _trace_in_progress = False
        _trace_start_time = None
        _trace_lock.release()
