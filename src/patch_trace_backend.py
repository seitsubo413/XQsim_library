#!/usr/bin/env python3
"""
XQsim Patch Trace Backend (Interface Layer)

目的:
- 既存の XQsim (compiler + simulator) のロジックを一切再実装せずに、
  外部入力(QASM) → 既存パイプライン実行 → PIU(パッチ情報)状態を観測 → JSON化
  までをつなぐ「入出力インターフェース」だけを提供します。

重要:
- XQsim本体の処理/ロジックは変更しません。
- 本ファイルは観測・整形（I/O）のみを行います。

運用上の注意:
- sys.exitのインターセプトはプロセス全体に影響する
- 並列実行は危険なため、api_server.py側で直列化すること
- uvicorn --workers 1 での運用を推奨

返すもの:
- input_qasm
- clifford_t_qasm (2A)
- qisa (全行)
- patch.initial (全パッチ)
- patch.events (PREP_INFO / MERGE_INFO / SPLIT_INFO を、PIUが受理した瞬間に差分で)
"""

from __future__ import annotations

import argparse
import importlib
import json
import logging
import os
import sys
import threading
import time
import types
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


logger = logging.getLogger("xqsim.trace")

EVENT_INSTS = {"PREP_INFO", "MERGE_INFO", "SPLIT_INFO"}

# スレッドローカルストレージでsys.exit差し替えを管理
# 注意: これは完全なスレッドセーフではない。api_server.py側で直列化すること
_exit_intercept_lock = threading.Lock()


# ============================================================================
# numpy安全インポート
# ============================================================================
_numpy_available = False
try:
    import numpy as np
    _numpy_available = True
except ImportError:
    np = None  # type: ignore


@dataclass
class TraceMetadata:
    """トレース実行のメタ情報を保持"""
    forced_terminations: List[Dict[str, Any]] = field(default_factory=list)
    cleanup_failed: bool = False
    cleanup_errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    stability_check_failures: List[Dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class PatchSnapshot:
    """A full snapshot of all patches, used to compute deltas."""
    patches: List[Dict[str, Any]]  # index aligned by pchidx


def _get_artifact_root() -> str:
    """
    生成ファイルのルートディレクトリを取得。
    
    重要: gsc_compilerは内部的に src/quantum_circuits/ を参照するため、
    このパスはコンパイラと一致させる必要がある。
    """
    curr_path = os.path.abspath(__file__)
    src_dir = os.path.dirname(curr_path)
    qc_dir = os.path.join(src_dir, "quantum_circuits")
    
    # サブディレクトリが存在することを確認
    for subdir in ["open_qasm", "transpiled", "qisa_compiled", "binary"]:
        subdir_path = os.path.join(qc_dir, subdir)
        os.makedirs(subdir_path, exist_ok=True)
    
    return qc_dir


def _make_job_name(num_qasm_qubits: int) -> str:
    """
    XQsim expects qbin name format: '{prefix}_n{N}' so it can parse N and set num_lq=N+2.
    N must be at the end.
    """
    return f"api_{uuid.uuid4().hex}_n{num_qasm_qubits}"


def _qc_paths(job_name: str) -> Tuple[str, str, str, str]:
    qc_dir = _get_artifact_root()
    qasm_path = os.path.join(qc_dir, "open_qasm", f"{job_name}.qasm")
    qtrp_path = os.path.join(qc_dir, "transpiled", f"{job_name}.qtrp")
    qisa_path = os.path.join(qc_dir, "qisa_compiled", f"{job_name}.qisa")
    qbin_path = os.path.join(qc_dir, "binary", f"{job_name}.qbin")
    return qasm_path, qtrp_path, qisa_path, qbin_path


def _ensure_parent_dir(path: str) -> None:
    parent = os.path.dirname(path)
    os.makedirs(parent, exist_ok=True)


def _to_json_safe(value: Any) -> Any:
    """
    任意の値をJSONシリアライズ可能な型に正規化する。
    numpy型、bytes、Enumなどを適切に変換。
    numpyが利用不可の場合はスキップ。
    """
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float, str)):
        return value
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    
    # numpy型の処理（numpyが利用可能な場合のみ）
    if _numpy_available and np is not None:
        if isinstance(value, np.integer):
            return int(value)
        if isinstance(value, np.floating):
            return float(value)
        if isinstance(value, np.ndarray):
            return value.tolist()
        if isinstance(value, np.bool_):
            return bool(value)
    
    # Enum処理
    if hasattr(value, "value"):
        return _to_json_safe(value.value)
    if hasattr(value, "name") and hasattr(value, "__class__"):
        return str(value.name)
    
    # コンテナ型
    if isinstance(value, dict):
        return {_to_json_safe(k): _to_json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_json_safe(v) for v in value]
    
    # フォールバック: 文字列化
    return str(value)


def _format_facebd(facebd_list: List[str]) -> Dict[str, str]:
    """
    Existing code uses order: (w, n, e, s)
    See: logical_measurement_unit.py unpacking.
    """
    if len(facebd_list) != 4:
        return {"w": "", "n": "", "e": "", "s": ""}
    w, n, e, s = facebd_list
    return {
        "w": _to_json_safe(w),
        "n": _to_json_safe(n),
        "e": _to_json_safe(e),
        "s": _to_json_safe(s),
    }


def _format_cornerbd(cornerbd_list: List[str]) -> Dict[str, str]:
    """
    Existing code uses order: (nw, ne, sw, se)
    See: physical_schedule_unit.py / pauliframe_unit.py unpacking.
    """
    if len(cornerbd_list) != 4:
        return {"nw": "", "ne": "", "sw": "", "se": ""}
    nw, ne, sw, se = cornerbd_list
    return {
        "nw": _to_json_safe(nw),
        "ne": _to_json_safe(ne),
        "sw": _to_json_safe(sw),
        "se": _to_json_safe(se),
    }


def _build_logical_qubit_mapping(
    sim: Any,
    num_qasm_qubits: int,
    num_compile_qubits: int,
) -> List[Dict[str, Any]]:
    """
    論理キュービットとパッチの対応関係を構築する。
    
    XQsimでは論理キュービットは以下のように割り当てられる:
    - lq_idx 0: Zアンシラ (magic state用)
    - lq_idx 1: Mアンシラ (zero state用)
    - lq_idx 2以降: ユーザーの論理キュービット (q[0], q[1], ...)
    
    Returns:
        論理キュービットマッピング情報のリスト
    """
    mapping: List[Dict[str, Any]] = []
    
    try:
        # patch_decode_unitからマッピングテーブルを取得
        pch_maptable = getattr(sim.pdu, "pch_maptable", None)
        if pch_maptable is None:
            return mapping
        
        num_lq = sim.param.num_lq
        num_pchcol = sim.param.num_pchcol
        num_pchrow = sim.param.num_pchrow
        
        for lq_idx in range(num_lq):
            entry: Dict[str, Any] = {
                "lq_idx": lq_idx,
            }
            
            # 役割を決定
            if lq_idx == 0:
                entry["role"] = "z_ancilla"
                entry["description"] = "Magic state ancilla (Z-type)"
            elif lq_idx == 1:
                entry["role"] = "m_ancilla"
                entry["description"] = "Zero state ancilla (M-type)"
            else:
                user_qubit_idx = lq_idx - 2
                if user_qubit_idx < num_qasm_qubits:
                    entry["role"] = "data"
                    entry["qubit_index"] = user_qubit_idx
                    entry["description"] = f"User qubit q[{user_qubit_idx}]"
                else:
                    entry["role"] = "padding"
                    entry["qubit_index"] = user_qubit_idx
                    entry["description"] = f"Padding qubit (unused)"
            
            # パッチインデックスを取得
            pch_tuple = pch_maptable[lq_idx] if lq_idx < len(pch_maptable) else (None, None)
            pchidx_1, pchidx_2 = pch_tuple
            
            if pchidx_1 is not None:
                # パッチ座標を計算 (row, col)
                row_1, col_1 = divmod(pchidx_1, num_pchcol)
                entry["patch_indices"] = [pchidx_1] if pchidx_1 == pchidx_2 else [pchidx_1, pchidx_2]
                entry["patch_coords"] = [[row_1, col_1]]
                
                if pchidx_1 != pchidx_2 and pchidx_2 is not None:
                    row_2, col_2 = divmod(pchidx_2, num_pchcol)
                    entry["patch_coords"].append([row_2, col_2])
                
                # パッチタイプを取得
                pchinfo = sim.piu.pchinfo_static_ram[pchidx_1] if pchidx_1 < len(sim.piu.pchinfo_static_ram) else {}
                entry["pchtype"] = _to_json_safe(pchinfo.get("pchtype", "unknown"))
            
            mapping.append(entry)
    
    except Exception as e:
        logger.warning(f"Failed to build logical qubit mapping: {e}")
    
    return mapping


def _take_full_patch_snapshot(sim: Any) -> PatchSnapshot:
    """
    Read PIU internal state and format it for JSON.
    This is "observation only" (no new behavior).
    """
    piu = sim.piu
    param = sim.param

    patches: List[Dict[str, Any]] = []
    for pchidx in range(param.num_pch):
        pchrow, pchcol = divmod(pchidx, param.num_pchcol)

        # static
        pchstat = piu.pchinfo_static_ram[pchidx]
        pchtype = _to_json_safe(pchstat.get("pchtype"))

        # dynamic boundary
        facebd = piu.facebd_ram[pchidx]
        cornerbd = piu.cornerbd_ram[pchidx]

        # merged flags (both, as requested)
        merged_reg = int(piu.merged_reg[pchidx]) if hasattr(piu, "merged_reg") else 0
        merged_mem = int(piu.merged_mem[pchidx]) if hasattr(piu, "merged_mem") else 0

        patches.append(
            {
                "pchidx": pchidx,
                "row": int(pchrow),
                "col": int(pchcol),
                "pchtype": pchtype,
                "merged": {"reg": merged_reg, "mem": merged_mem},
                "facebd": _format_facebd(facebd),
                "cornerbd": _format_cornerbd(cornerbd),
            }
        )
    return PatchSnapshot(patches=patches)


def _diff_patch_snapshots(
    prev: PatchSnapshot, cur: PatchSnapshot
) -> List[Dict[str, Any]]:
    """
    Compute patch deltas (only changed patches).
    This is formatting/comparison only.
    """
    deltas: List[Dict[str, Any]] = []
    for p_prev, p_cur in zip(prev.patches, cur.patches):
        if p_prev != p_cur:
            deltas.append(p_cur)
    return deltas


def _opcode_to_inst_name(param: Any, opcode_bits: Optional[str]) -> Optional[str]:
    if opcode_bits is None:
        return None
    mapping = {
        getattr(param, "PREP_INFO_opcode", None): "PREP_INFO",
        getattr(param, "MERGE_INFO_opcode", None): "MERGE_INFO",
        getattr(param, "SPLIT_INFO_opcode", None): "SPLIT_INFO",
        getattr(param, "LQI_opcode", None): "LQI",
        getattr(param, "RUN_ESM_opcode", None): "RUN_ESM",
        getattr(param, "INIT_INTMD_opcode", None): "INIT_INTMD",
        getattr(param, "MEAS_INTMD_opcode", None): "MEAS_INTMD",
        getattr(param, "PPM_INTERPRET_opcode", None): "PPM_INTERPRET",
        getattr(param, "LQM_X_opcode", None): "LQM_X",
        getattr(param, "LQM_Y_opcode", None): "LQM_Y",
        getattr(param, "LQM_Z_opcode", None): "LQM_Z",
        getattr(param, "LQM_FB_opcode", None): "LQM_FB",
    }
    return mapping.get(opcode_bits)


def _get_unit_states(sim: Any) -> Dict[str, Any]:
    """シミュレータの各ユニットの状態を取得（デバッグ/メタ情報用）"""
    return {
        "qif_done": _to_json_safe(getattr(sim.qif, "done", None)),
        "qif_all_fetched": _to_json_safe(getattr(sim.qif, "all_fetched", None)),
        "qid_done": _to_json_safe(getattr(sim.qid, "done", None)),
        "pdu_state": _to_json_safe(getattr(sim.pdu, "state", None)),
        "piu_state": _to_json_safe(getattr(sim.piu, "state", None)),
        "psu_state": _to_json_safe(getattr(sim.psu, "state", None)),
        "tcu_timebuf_empty": _to_json_safe(getattr(sim.tcu, "output_timebuf_empty", None)),
        "pfu_state": _to_json_safe(getattr(sim.pfu, "state", None)),
        "lmu_done": _to_json_safe(getattr(sim.lmu, "done", None)),
    }


def _safe_getattr(obj: Any, attr: str, default: Any = None) -> Tuple[Any, bool]:
    """
    安全に属性を取得し、取得できたかどうかも返す。
    
    Returns:
        (value, success): 値と取得成功フラグのタプル
    """
    try:
        if not hasattr(obj, attr):
            return default, False
        value = getattr(obj, attr)
        # callableの場合は呼び出さない（propertyかどうか判定が難しいため）
        return value, True
    except Exception:
        return default, False


def _check_system_stable(sim: Any, trace_meta: TraceMetadata) -> bool:
    """
    システム全体が安定状態かどうかを判定。
    
    重要:
    - 観測不能な条件はFalse（安定扱いにしない）
    - どの条件が評価不能だったかを記録
    - これは「停止して良いかの追加確認」であり、最終的にはmax_cyclesで保険
    
    Returns:
        True if system appears stable, False otherwise
    """
    conditions: Dict[str, Tuple[bool, bool]] = {}  # name -> (value, observable)
    
    # QIF: 全命令フェッチ済み
    qif_all_fetched, qif_obs = _safe_getattr(sim.qif, "all_fetched", False)
    conditions["qif_all_fetched"] = (bool(qif_all_fetched), qif_obs)
    
    # QID: バッファが空
    to_pchdec_buf, pchdec_obs = _safe_getattr(sim.qid, "to_pchdec_buf", None)
    if pchdec_obs and to_pchdec_buf is not None:
        pchdec_empty, pchdec_empty_obs = _safe_getattr(to_pchdec_buf, "empty", False)
        conditions["qid_pchdec_empty"] = (bool(pchdec_empty), pchdec_empty_obs)
    else:
        conditions["qid_pchdec_empty"] = (False, False)
    
    to_lqmeas_buf, lqmeas_obs = _safe_getattr(sim.qid, "to_lqmeas_buf", None)
    if lqmeas_obs and to_lqmeas_buf is not None:
        lqmeas_empty, lqmeas_empty_obs = _safe_getattr(to_lqmeas_buf, "empty", False)
        conditions["qid_lqmeas_empty"] = (bool(lqmeas_empty), lqmeas_empty_obs)
    else:
        conditions["qid_lqmeas_empty"] = (False, False)
    
    # PDU: 空状態
    pdu_state, pdu_obs = _safe_getattr(sim.pdu, "state", None)
    conditions["pdu_empty"] = (pdu_state == "empty", pdu_obs)
    
    # PIU: ready状態
    piu_state, piu_obs = _safe_getattr(sim.piu, "state", None)
    conditions["piu_ready"] = (piu_state == "ready", piu_obs)
    
    piu_topsu_valid, topsu_obs = _safe_getattr(sim.piu, "output_topsu_valid", True)
    conditions["piu_no_topsu_valid"] = (not bool(piu_topsu_valid), topsu_obs)
    
    piu_tolmu_valid, tolmu_obs = _safe_getattr(sim.piu, "output_tolmu_valid", True)
    conditions["piu_no_tolmu_valid"] = (not bool(piu_tolmu_valid), tolmu_obs)
    
    # PSU: ready状態でバッファ空
    psu_state, psu_state_obs = _safe_getattr(sim.psu, "state", None)
    conditions["psu_ready"] = (psu_state == "ready", psu_state_obs)
    
    psu_srmem, srmem_obs = _safe_getattr(sim.psu, "pchinfo_srmem", None)
    if srmem_obs and psu_srmem is not None:
        srmem_notempty, notempty_obs = _safe_getattr(psu_srmem, "output_notempty", True)
        conditions["psu_buf_empty"] = (not bool(srmem_notempty), notempty_obs)
    else:
        conditions["psu_buf_empty"] = (False, False)
    
    # TCU: タイムバッファ空
    tcu_empty, tcu_obs = _safe_getattr(sim.tcu, "output_timebuf_empty", False)
    conditions["tcu_empty"] = (bool(tcu_empty), tcu_obs)
    
    # PFU: ready状態
    pfu_state, pfu_obs = _safe_getattr(sim.pfu, "state", None)
    conditions["pfu_ready"] = (pfu_state == "ready", pfu_obs)
    
    # LMU: instinfo_validがFalse
    lmu_instinfo_valid, lmu_obs = _safe_getattr(sim.lmu, "instinfo_valid", True)
    conditions["lmu_no_instinfo_valid"] = (not bool(lmu_instinfo_valid), lmu_obs)
    
    # LMU: done状態
    lmu_done, lmu_done_obs = _safe_getattr(sim.lmu, "done", False)
    conditions["lmu_done"] = (bool(lmu_done), lmu_done_obs)
    
    # QXU: 測定メモリが空
    qxu_dq_meas_mem, qxu_dq_obs = _safe_getattr(sim.qxu, "dq_meas_mem", None)
    qxu_aq_meas_mem, qxu_aq_obs = _safe_getattr(sim.qxu, "aq_meas_mem", None)
    qxu_empty = not (bool(qxu_dq_meas_mem) or bool(qxu_aq_meas_mem))
    qxu_obs = qxu_dq_obs and qxu_aq_obs
    conditions["qxu_meas_mem_empty"] = (qxu_empty, qxu_obs)
    
    # 観測不能な条件を記録
    unobservable = {k: v for k, (val, obs) in conditions.items() if not obs}
    if unobservable:
        trace_meta.stability_check_failures.append({
            "cycle": sim.cycle,
            "unobservable_conditions": list(unobservable.keys()),
        })
    
    # 全条件がTrue、かつ全条件が観測可能な場合のみTrue
    all_true = all(val for val, _ in conditions.values())
    all_observable = all(obs for _, obs in conditions.values())
    
    return all_true and all_observable


@contextmanager
def _intercept_sys_exit():
    """
    sys.exitを一時的にインターセプトするコンテキストマネージャー。
    
    警告: このパターンは並行実行環境では危険。
    api_server.py側で直列化すること。
    """
    original_exit = sys.exit
    exit_info = {"called": False, "code": None}
    
    def _intercepted_exit(code=None):
        exit_info["called"] = True
        exit_info["code"] = code
        error_msg = (
            "XQsim simulation error: sys.exit() was called by the simulator. "
            "This typically occurs when there is an invalid patch Pauli product (pchpp) configuration. "
            f"Exit code: {code}"
        )
        raise RuntimeError(error_msg)
    
    with _exit_intercept_lock:
        try:
            sys.exit = _intercepted_exit
            yield exit_info
        finally:
            sys.exit = original_exit


def trace_patches_from_qasm(
    qasm_str: str,
    *,
    config_name: str = "example_cmos_d5",
    skip_pqsim: bool = True,
    num_shots: int = 1,
    keep_artifacts: bool = False,
    debug_logging: bool = False,
    max_cycles: int = 10_000_000,
    timeout_seconds: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Main entry: QASM文字列を入力として、既存XQsimを用いてパッチ時系列(JSON)を返す。

    Args:
        qasm_str: OpenQASM 2.0形式の量子回路
        config_name: 設定ファイル名（src/configs配下、.jsonなし）
        skip_pqsim: 物理量子ビットシミュレーションをスキップするか
        num_shots: シミュレーションのショット数
        keep_artifacts: 生成ファイルを残すか
        debug_logging: 詳細デバッグログを有効にするか
        max_cycles: 最大サイクル数（無限ループ防止）
        timeout_seconds: wall clockタイムアウト（秒）。Noneの場合はチェックしない
    
    Returns:
        パッチトレースを含むJSON形式の辞書
    
    Raises:
        TimeoutError: タイムアウトした場合
        RuntimeError: シミュレーションエラーの場合
    """
    start_time = time.time()
    trace_meta = TraceMetadata()
    
    # --- Path bootstrap (match XQsim style; do not modify core modules) ---
    curr_path = os.path.abspath(__file__)
    src_dir = os.path.dirname(curr_path)
    sim_dir = os.path.join(src_dir, "XQ-simulator")
    comp_dir = os.path.join(src_dir, "compiler")
    if sim_dir not in sys.path:
        sys.path.insert(0, sim_dir)
    if comp_dir not in sys.path:
        sys.path.insert(0, comp_dir)
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)

    # Import existing modules after sys.path bootstrap (no modification to their code)
    QuantumCircuit = importlib.import_module("qiskit").QuantumCircuit  # type: ignore
    gsc_mod = importlib.import_module("gsc_compiler")
    sim_mod = importlib.import_module("xq_simulator")

    gsc_compiler_cls = getattr(gsc_mod, "gsc_compiler")
    decompose_qc_to_Clifford_T_fn = getattr(gsc_mod, "decompose_qc_to_Clifford_T")
    xq_simulator_cls = getattr(sim_mod, "xq_simulator")

    # 1) Parse QASM (input)
    qc_in = QuantumCircuit.from_qasm_str(qasm_str)
    num_qasm_qubits = int(qc_in.num_qubits)

    # XQsim simulator (PIU) requires num_lq to be odd.
    num_compile_qubits = num_qasm_qubits if (num_qasm_qubits % 2 == 1) else (num_qasm_qubits + 1)
    padding_applied = num_compile_qubits != num_qasm_qubits
    
    if padding_applied:
        qc_compile = QuantumCircuit(num_compile_qubits, qc_in.num_clbits)
        qc_compile.compose(qc_in, qubits=list(range(num_qasm_qubits)), inplace=True)
        qasm_for_compile = qc_compile.qasm()
        trace_meta.warnings.append(
            f"Padding applied: original {num_qasm_qubits} qubits -> {num_compile_qubits} qubits for compilation. "
            f"The last qubit (index {num_compile_qubits - 1}) is unused."
        )
    else:
        qc_compile = qc_in
        qasm_for_compile = qasm_str

    # 2) Produce "2A" Clifford+T circuit (reuse existing function)
    qc_clifford_t = decompose_qc_to_Clifford_T_fn(qc_in)
    clifford_t_qasm = qc_clifford_t.qasm()
    
    # パディング後のClifford+Tも生成
    if padding_applied:
        qc_clifford_t_padded = decompose_qc_to_Clifford_T_fn(qc_compile)
        clifford_t_qasm_padded = qc_clifford_t_padded.qasm()
    else:
        clifford_t_qasm_padded = clifford_t_qasm

    # 3) Generate file-based artifacts using existing compiler pipeline
    job_name = _make_job_name(num_compile_qubits)
    qasm_path, qtrp_path, qisa_path, qbin_path = _qc_paths(job_name)

    _ensure_parent_dir(qasm_path)
    with open(qasm_path, "w", encoding="utf-8") as f:
        f.write(qasm_for_compile)

    compiler = gsc_compiler_cls()
    compiler.setup(
        qc_name=job_name, compile_mode=["transpile", "qisa_compile", "assemble"]
    )
    compiler.run()

    with open(qisa_path, "r", encoding="utf-8") as f:
        qisa_lines = [line.rstrip("\n") for line in f.readlines() if line.strip()]

    # 4) Run simulator cycle-by-cycle and observe PIU
    sim = xq_simulator_cls()
    num_lq = int(num_compile_qubits + 2)
    sim.setup(
        config=config_name,
        qbin=job_name,
        num_lq=num_lq,
        skip_pqsim=skip_pqsim,
        num_shots=num_shots,
        dump=False,
        regen=True,
        debug=False,
    )

    # emulate属性の設定
    if not hasattr(sim, "emulate"):
        setattr(sim, "emulate", bool(skip_pqsim))

    # --- Interface-layer workaround: ensure simulator termination ---
    _orig_qif_transfer = sim.qif.transfer
    _orig_lmu_transfer = sim.lmu.transfer
    
    def _qif_transfer_with_done_fix(self: Any) -> None:
        _orig_qif_transfer()
        try:
            qif_all_fetched, obs = _safe_getattr(self, "all_fetched", False)
            if obs and bool(qif_all_fetched):
                if _check_system_stable(sim, trace_meta):
                    if not getattr(self, "done", False):
                        trace_meta.forced_terminations.append({
                            "unit": "qif",
                            "cycle": sim.cycle,
                            "reason": "system_stable",
                            "states": _get_unit_states(sim),
                        })
                    setattr(self, "done", True)
        except Exception as e:
            logger.debug(f"QIF done fix error: {e}")

    def _lmu_transfer_with_done_fix(self: Any) -> None:
        _orig_lmu_transfer()
        try:
            state, obs = _safe_getattr(self, "state", None)
            if obs and state == "ready" and _check_system_stable(sim, trace_meta):
                if not getattr(self, "done", False):
                    trace_meta.forced_terminations.append({
                        "unit": "lmu",
                        "cycle": sim.cycle,
                        "reason": "system_stable",
                        "states": _get_unit_states(sim),
                    })
                setattr(self, "done", True)
        except Exception as e:
            logger.debug(f"LMU done fix error: {e}")

    sim.qif.transfer = types.MethodType(_qif_transfer_with_done_fix, sim.qif)
    sim.lmu.transfer = types.MethodType(_lmu_transfer_with_done_fix, sim.lmu)

    patch_initial = _take_full_patch_snapshot(sim)
    prev_snapshot = patch_initial

    events: List[Dict[str, Any]] = []
    accepted_inst_count = 0

    # デバッグログの間隔
    debug_log_interval = int(os.environ.get("XQSIM_DEBUG_LOG_INTERVAL", "1000"))
    
    # タイムアウトチェック間隔（サイクル）
    timeout_check_interval = 100

    termination_reason = "normal"

    with _intercept_sys_exit() as exit_info:
        while not sim.sim_done:
            # タイムアウトチェック
            if timeout_seconds is not None and sim.cycle % timeout_check_interval == 0:
                elapsed = time.time() - start_time
                if elapsed > timeout_seconds:
                    termination_reason = "timeout"
                    trace_meta.warnings.append(
                        f"Trace timed out after {elapsed:.1f} seconds at cycle {sim.cycle}"
                    )
                    trace_meta.forced_terminations.append({
                        "unit": "global",
                        "cycle": sim.cycle,
                        "reason": "timeout",
                        "elapsed_seconds": elapsed,
                        "states": _get_unit_states(sim),
                    })
                    raise TimeoutError(
                        f"Trace operation timed out after {elapsed:.1f} seconds"
                    )
            
            sim.run_cycle_transfer()

            # PIU acceptance moment
            accepted = bool(sim.piu.take_input) and (not bool(sim.piu.input_stall))
            if accepted:
                qisa_idx = accepted_inst_count
                accepted_inst_count += 1

                inst_name = _opcode_to_inst_name(sim.param, sim.piu.input_opcode)
                if inst_name in EVENT_INSTS:
                    cur_snapshot = _take_full_patch_snapshot(sim)
                    patch_delta = _diff_patch_snapshots(prev_snapshot, cur_snapshot)
                    prev_snapshot = cur_snapshot

                    if patch_delta:
                        events.append(
                            {
                                "seq": len(events),
                                "cycle": int(sim.cycle),
                                "qisa_idx": int(qisa_idx),
                                "inst": inst_name,
                                "patch_delta": patch_delta,
                            }
                        )

            sim.run_cycle_update()
            sim.run_cycle_tick()

            # デバッグログ（オプション）
            if debug_logging and sim.cycle % debug_log_interval == 0:
                states = _get_unit_states(sim)
                logger.info(f"Cycle {sim.cycle}: {states}")
                print(f"Cycle {sim.cycle}: sim_done={sim.sim_done}", flush=True)

            # max_cycles保険
            if sim.cycle > max_cycles:
                termination_reason = "max_cycles"
                trace_meta.warnings.append(
                    f"Simulation exceeded {max_cycles} cycles; terminated early."
                )
                trace_meta.forced_terminations.append({
                    "unit": "global",
                    "cycle": sim.cycle,
                    "reason": "max_cycles_exceeded",
                    "states": _get_unit_states(sim),
                })
                break

    # 5) Build response JSON
    elapsed_time = time.time() - start_time
    response: Dict[str, Any] = {
        "meta": {
            "version": 3,
            "config": config_name,
            "block_type": _to_json_safe(sim.param.block_type),
            "code_distance": int(sim.param.code_dist),
            "patch_grid": {
                "rows": int(sim.param.num_pchrow),
                "cols": int(sim.param.num_pchcol),
            },
            "num_patches": int(sim.param.num_pch),
            "total_cycles": int(sim.cycle),
            "elapsed_seconds": round(elapsed_time, 2),
            "termination_reason": termination_reason,
            "forced_terminations": trace_meta.forced_terminations,
            "stability_check_failures": trace_meta.stability_check_failures[:10],  # 最大10件
            "warnings": trace_meta.warnings,
        },
        "input": {
            "qasm": qasm_str,
            "num_qasm_qubits": num_qasm_qubits,
            "num_compile_qubits": int(num_compile_qubits),
            "padding_applied": padding_applied,
        },
        "compiled": {
            "clifford_t_qasm": clifford_t_qasm,
            "clifford_t_qasm_padded": clifford_t_qasm_padded if padding_applied else None,
            "qisa": qisa_lines,
            "qbin_name": job_name,
        },
        "patch": {
            "initial": patch_initial.patches,
            "events": events,
        },
        "logical_qubit_mapping": _build_logical_qubit_mapping(
            sim, num_qasm_qubits, num_compile_qubits
        ),
    }

    # 6) Cleanup artifacts unless requested otherwise
    if not keep_artifacts:
        for p in (qasm_path, qtrp_path, qisa_path, qbin_path):
            try:
                os.remove(p)
            except FileNotFoundError:
                pass
            except Exception as e:
                trace_meta.cleanup_failed = True
                trace_meta.cleanup_errors.append(f"{p}: {e}")
                logger.warning(f"Failed to cleanup {p}: {e}")
        
        if trace_meta.cleanup_failed:
            response["meta"]["cleanup_failed"] = True
            response["meta"]["cleanup_errors"] = trace_meta.cleanup_errors

    return response


def main() -> None:
    parser = argparse.ArgumentParser(
        description="XQsim patch trace backend (QASM -> JSON)"
    )
    parser.add_argument("--qasm_file", required=True, help="Path to OpenQASM 2.0 file")
    parser.add_argument(
        "--config",
        default="example_cmos_d5",
        help="Config name under src/configs (without .json)",
    )
    parser.add_argument(
        "--keep_artifacts",
        action="store_true",
        help="Keep generated qasm/qtrp/qisa/qbin files for debugging",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=None,
        help="Timeout in seconds",
    )
    parser.add_argument(
        "--out", default="-", help="Output JSON path, or '-' for stdout"
    )
    args = parser.parse_args()

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)

    with open(args.qasm_file, "r", encoding="utf-8") as f:
        qasm_str = f.read()

    res = trace_patches_from_qasm(
        qasm_str,
        config_name=args.config,
        skip_pqsim=True,
        keep_artifacts=bool(args.keep_artifacts),
        debug_logging=bool(args.debug),
        timeout_seconds=args.timeout,
    )

    out_json = json.dumps(res, ensure_ascii=False, indent=2)
    if args.out == "-":
        print(out_json)
    else:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(out_json)


if __name__ == "__main__":
    main()
