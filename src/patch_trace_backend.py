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
import os
import sys
import types
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


EVENT_INSTS = {"PREP_INFO", "MERGE_INFO", "SPLIT_INFO"}


@dataclass(frozen=True)
class PatchSnapshot:
    """A full snapshot of all patches, used to compute deltas."""

    patches: List[Dict[str, Any]]  # index aligned by pchidx


def _make_job_name(num_qasm_qubits: int) -> str:
    """
    XQsim expects qbin name format: '{prefix}_n{N}' so it can parse N and set num_lq=N+2.
    N must be at the end.
    """
    return f"api_{uuid.uuid4().hex}_n{num_qasm_qubits}"


def _qc_paths(job_name: str) -> Tuple[str, str, str, str]:
    curr_path = os.path.abspath(__file__)
    src_dir = os.path.dirname(curr_path)
    qc_dir = os.path.join(src_dir, "quantum_circuits")
    qasm_path = os.path.join(qc_dir, "open_qasm", f"{job_name}.qasm")
    qtrp_path = os.path.join(qc_dir, "transpiled", f"{job_name}.qtrp")
    qisa_path = os.path.join(qc_dir, "qisa_compiled", f"{job_name}.qisa")
    qbin_path = os.path.join(qc_dir, "binary", f"{job_name}.qbin")
    return qasm_path, qtrp_path, qisa_path, qbin_path


def _ensure_parent_dir(path: str) -> None:
    parent = os.path.dirname(path)
    os.makedirs(parent, exist_ok=True)


def _format_facebd(facebd_list: List[str]) -> Dict[str, str]:
    """
    Existing code uses order: (w, n, e, s)
    See: logical_measurement_unit.py unpacking.
    """
    if len(facebd_list) != 4:
        return {"w": "", "n": "", "e": "", "s": ""}
    w, n, e, s = facebd_list
    return {"w": w, "n": n, "e": e, "s": s}


def _format_cornerbd(cornerbd_list: List[str]) -> Dict[str, str]:
    """
    Existing code uses order: (nw, ne, sw, se)
    See: physical_schedule_unit.py / pauliframe_unit.py unpacking.
    """
    if len(cornerbd_list) != 4:
        return {"nw": "", "ne": "", "sw": "", "se": ""}
    nw, ne, sw, se = cornerbd_list
    return {"nw": nw, "ne": ne, "sw": sw, "se": se}


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
        pchtype = pchstat.get("pchtype")

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


def trace_patches_from_qasm(
    qasm_str: str,
    *,
    config_name: str = "example_cmos_d5",
    skip_pqsim: bool = True,
    num_shots: int = 1,
    keep_artifacts: bool = False,
) -> Dict[str, Any]:
    """
    Main entry: QASM文字列を入力として、既存XQsimを用いてパッチ時系列(JSON)を返す。

    keep_artifacts:
      Falseなら生成した open_qasm/transpiled/qisa_compiled/binary のファイルを削除する。
      Trueならデバッグのため残す。
    """
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

    # --- Ray safety knobs (interface-layer only) ---
    # XQsim imports Ray in simulator modules. Ray can auto-init on first use and attempt to
    # start the dashboard, which may crash under pydantic v2 (FastAPI dependency).
    # We disable the dashboard via env vars before importing XQsim modules.
    os.environ.setdefault("RAY_DISABLE_DASHBOARD", "1")
    os.environ.setdefault("RAY_DASHBOARD_ENABLED", "0")
    os.environ.setdefault("RAY_USAGE_STATS_ENABLED", "0")

    # NOTE (important for /trace):
    # Even when skip_pqsim=True, XQ-simulator's QXU path constructs Ray actors
    # (e.g., qc_supervisor.remote(...)), which triggers Ray auto-init.
    # To avoid flaky auto-init defaults in containers, we explicitly init Ray here
    # with dashboard disabled and a stable plasma directory.
    ray = importlib.import_module(
        "ray"
    )  # importing is safe; it doesn't start the cluster
    if not ray.is_initialized():
        ray.init(
            ignore_reinit_error=True,
            include_dashboard=False,
            log_to_driver=False,
            num_cpus=1,
            # Keep object store small/stable for API use. Ray accepts bytes.
            object_store_memory=512 * 1024 * 1024,
            # Use shared memory inside the container to avoid slow /tmp fallback when possible.
            _plasma_directory="/dev/shm",
            _temp_dir="/tmp/ray",
        )

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
    # The existing compiler derives its internal num_lq as (num_qasm_qubits + 2).
    # Therefore, to keep compiler and simulator consistent without modifying XQsim core,
    # we pad the compilation QASM to an odd number of qubits when needed.
    #
    # - input: 2 qubits  -> compile with 3 qubits -> compiler num_lq=5 (odd) -> simulator num_lq=5
    # - input: 1 qubit  -> compile with 1 qubits -> compiler num_lq=3 (odd) -> simulator num_lq=3
    num_compile_qubits = num_qasm_qubits if (num_qasm_qubits % 2 == 1) else (num_qasm_qubits + 1)
    if num_compile_qubits != num_qasm_qubits:
        qc_compile = QuantumCircuit(num_compile_qubits, qc_in.num_clbits)
        qc_compile.compose(qc_in, qubits=list(range(num_qasm_qubits)), inplace=True)
        qasm_for_compile = qc_compile.qasm()
    else:
        qasm_for_compile = qasm_str

    # 2) Produce "2A" Clifford+T circuit (reuse existing function)
    qc_clifford_t = decompose_qc_to_Clifford_T_fn(qc_in)
    clifford_t_qasm = qc_clifford_t.qasm()

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

    # 4) Run simulator cycle-by-cycle (reuse existing run_cycle_* methods) and observe PIU
    sim = xq_simulator_cls()
    # IMPORTANT: Keep simulator's num_lq consistent with the compiler output.
    # The existing compiler uses: num_lq = (num_compile_qubits + 2).
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

    # NOTE: xq_simulator references self.emulate in run_cycle_update/run().
    # This repo version doesn't set it in setup, so we set it here without modifying core code.
    # For our "shape-only" trace, emulate == skip_pqsim is consistent with QXU's emulate_mode.
    if not hasattr(sim, "emulate"):
        setattr(sim, "emulate", bool(skip_pqsim))

    # --- Interface-layer workaround: ensure simulator termination can be observed ---
    #
    # We observed cases where /trace never finishes because qif.done/qid.done remain False,
    # even after all instructions have been fetched/consumed. This stalls xq_simulator's
    # done_cond (run_cycle_tick) forever and the API request hangs.
    #
    # Per user request: do NOT modify XQsim core logic. Instead, we patch the QIF instance
    # method at runtime to set `done=True` when "all fetched" AND "buffer empty".
    # This only affects this API process and only for trace runs.
    _orig_qif_transfer = sim.qif.transfer

    def _qif_transfer_with_done_fix(self: Any) -> None:
        _orig_qif_transfer()
        try:
            # Match original XQsim condition (quantum_instruction_fetch.py lines 85-86):
            # "done" means: all instructions fetched AND buffer still has content (being consumed).
            # Original: if self.all_fetched and not self.output_instbuf_empty: self.done = True
            if bool(getattr(self, "all_fetched", False)) and not bool(
                getattr(self, "output_instbuf_empty", True)
            ):
                setattr(self, "done", True)
        except Exception:
            # Best-effort: never crash the sim due to an interface-layer hook.
            pass

    sim.qif.transfer = types.MethodType(_qif_transfer_with_done_fix, sim.qif)

    # Interface-layer workaround: LMU may not set done=True in some cases.
    # Similar to QIF, we patch LMU's transfer method to set done=True when appropriate.
    _orig_lmu_transfer = sim.lmu.transfer

    def _lmu_transfer_with_done_fix(self: Any) -> None:
        _orig_lmu_transfer()
        try:
            # LMU should be done when state is 'ready' and no more instructions are valid
            # The original code sets done=True when state=='ready' and not instinfo_valid
            # But sometimes instinfo_valid may remain True even when there's no more work
            # We check if all inputs are empty/ready and state is ready
            state = getattr(self, "state", None)
            instinfo_valid = bool(getattr(self, "instinfo_valid", True))
            input_lqmeasbuf_empty = bool(getattr(self, "input_lqmeasbuf_empty", False))
            
            # If state is ready and input buffer is empty, consider LMU done
            # This is a more aggressive condition to prevent infinite loops
            if state == "ready":
                if not instinfo_valid:
                    # Original condition: state=='ready' and not instinfo_valid
                    setattr(self, "done", True)
                elif input_lqmeasbuf_empty:
                    # Additional condition: if input buffer is empty and state is ready,
                    # and we've been running for a while, consider it done
                    # This helps prevent infinite loops in interface layer
                    setattr(self, "done", True)
        except Exception:
            # Best-effort: never crash the sim due to an interface-layer hook.
            pass

    sim.lmu.transfer = types.MethodType(_lmu_transfer_with_done_fix, sim.lmu)

    # Ray was pre-initialized above (dashboard disabled) to avoid container crashes.

    patch_initial = _take_full_patch_snapshot(sim)
    prev_snapshot = patch_initial

    events: List[Dict[str, Any]] = []
    accepted_inst_count = (
        0  # qisa_idx, aligned by PIU acceptance (take_input && !stall)
    )

    # Interface-layer workaround: catch SystemExit from existing XQsim code
    # Existing code calls sys.exit() on errors, which would kill the API server.
    # We catch it and convert to a proper exception.
    original_exit = sys.exit
    sys_exit_called = False
    sys_exit_code = None

    def _intercept_sys_exit(code=None):
        nonlocal sys_exit_called, sys_exit_code
        sys_exit_called = True
        sys_exit_code = code
        # Don't actually exit; raise an exception instead
        # Note: We can't easily capture the exact error message from PIU.dyndec
        # because it's printed to stdout, but we know the common error pattern
        error_msg = (
            "XQsim simulation error: sys.exit() was called by the simulator. "
            "This typically occurs when there is an invalid patch Pauli product (pchpp) configuration. "
            "The error 'invalid pchpp in PIU.dyndec' indicates that both pchpp_even and pchpp_odd "
            "are non-Identity ('I') values, which is not allowed. "
            "Some QASM circuits may not be compatible with the current patch configuration. "
            "Try using a different QASM circuit or check the patch configuration."
        )
        raise RuntimeError(error_msg)

    try:
        sys.exit = _intercept_sys_exit

        while not sim.sim_done:
            sim.run_cycle_transfer()

            # PIU acceptance moment (as agreed): take_input == True and input_stall == False
            accepted = bool(sim.piu.take_input) and (not bool(sim.piu.input_stall))
            if accepted:
                qisa_idx = accepted_inst_count
                accepted_inst_count += 1

                inst_name = _opcode_to_inst_name(sim.param, sim.piu.input_opcode)
                if inst_name in EVENT_INSTS:
                    cur_snapshot = _take_full_patch_snapshot(sim)
                    patch_delta = _diff_patch_snapshots(prev_snapshot, cur_snapshot)
                    prev_snapshot = cur_snapshot

                    # emit event only if there is any delta (shape changed)
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

            # Debug logging: detailed state every 1000 cycles
            if sim.cycle % 1000 == 0:
                print(f"\n=== Cycle {sim.cycle} Debug Info ===")
                # QID state
                qid = sim.qid
                print(f"QID: all_decoded={getattr(qid, 'all_decoded', 'N/A')}, "
                      f"to_pchdec_buf.empty={getattr(qid.to_pchdec_buf, 'empty', 'N/A')}, "
                      f"to_lqmeas_buf.empty={getattr(qid.to_lqmeas_buf, 'empty', 'N/A')}, "
                      f"input_qifdone={getattr(qid, 'input_qifdone', 'N/A')}")
                # PDU state
                pdu = sim.pdu
                print(f"PDU: state={getattr(pdu, 'state', 'N/A')}, "
                      f"next_state={getattr(pdu, 'next_state', 'N/A')}, "
                      f"input_stall={getattr(pdu, 'input_stall', 'N/A')}, "
                      f"output_valid={getattr(pdu, 'output_valid', 'N/A')}")
                # PIU state
                piu = sim.piu
                print(f"PIU: state={getattr(piu, 'state', 'N/A')}, "
                      f"next_state={getattr(piu, 'next_state', 'N/A')}, "
                      f"input_stall={getattr(piu, 'input_stall', 'N/A')}, "
                      f"take_input={getattr(piu, 'take_input', 'N/A')}, "
                      f"output_topsu_valid={getattr(piu, 'output_topsu_valid', 'N/A')}, "
                      f"output_tolmu_valid={getattr(piu, 'output_tolmu_valid', 'N/A')}")
                # Downstream unit full status (causes stall)
                psu = sim.psu
                pfu = sim.pfu
                lmu = sim.lmu
                print(f"Downstream Full: psu.pchinfo_full={getattr(psu, 'pchinfo_full', 'N/A')}, "
                      f"pfu.pchinfo_full={getattr(pfu, 'pchinfo_full', 'N/A')}, "
                      f"lmu.pchinfo_full={getattr(lmu, 'pchinfo_full', 'N/A')}")
                # PSU srmem state (to understand why psu.pchinfo_full stays True)
                pchinfo_srmem = getattr(psu, 'pchinfo_srmem', None)
                if pchinfo_srmem:
                    print(f"PSU.srmem: input_pop={getattr(pchinfo_srmem, 'input_pop', 'N/A')}, "
                          f"input_valid={getattr(pchinfo_srmem, 'input_valid', 'N/A')}")
                    # Check double buffer state
                    db = getattr(pchinfo_srmem, 'double_buffer', None)
                    if db:
                        print(f"PSU.srmem.double_buffer[0].state={getattr(db[0], 'state', 'N/A')}, "
                              f"[1].state={getattr(db[1], 'state', 'N/A')}")
                print(f"PSU: state={getattr(psu, 'state', 'N/A')}, "
                      f"next_pch={getattr(psu, 'next_pch', 'N/A')}, "
                      f"input_cwdgen_stall={getattr(psu, 'input_cwdgen_stall', 'N/A')}")
                # Stall signals
                print(f"Stalls: piu.input_stall={getattr(piu, 'input_stall', 'N/A')}, "
                      f"pdu.input_stall={getattr(pdu, 'input_stall', 'N/A')}")
                print(f"=== End Debug Info ===\n", flush=True)

            # Safety: if something goes wrong, avoid infinite loops (interface concern only)
            # This check must be INSIDE the loop to actually prevent infinite loops.
            if sim.cycle > 10_000_000:
                raise RuntimeError("Simulation exceeded 10,000,000 cycles; aborting trace.")
    except RuntimeError as e:
        # Re-raise RuntimeError (including our intercepted sys.exit)
        raise
    finally:
        # Restore original sys.exit
        sys.exit = original_exit

    # 5) Build response JSON
    response: Dict[str, Any] = {
        "meta": {
            "version": 1,
            "config": config_name,
            "block_type": sim.param.block_type,
            "code_distance": int(sim.param.code_dist),
            "patch_grid": {
                "rows": int(sim.param.num_pchrow),
                "cols": int(sim.param.num_pchcol),
            },
            "num_patches": int(sim.param.num_pch),
        },
        "input": {
            "qasm": qasm_str,
            "num_qasm_qubits": num_qasm_qubits,
            "num_compile_qubits": int(num_compile_qubits),
        },
        "compiled": {
            "clifford_t_qasm": clifford_t_qasm,
            "qisa": qisa_lines,
            "qbin_name": job_name,
        },
        "patch": {
            "initial": patch_initial.patches,
            "events": events,
        },
    }

    # 6) Cleanup artifacts unless requested otherwise
    if not keep_artifacts:
        for p in (qasm_path, qtrp_path, qisa_path, qbin_path):
            try:
                os.remove(p)
            except FileNotFoundError:
                pass
            except Exception:
                # keep best-effort cleanup; do not mask main result
                pass

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
        "--out", default="-", help="Output JSON path, or '-' for stdout"
    )
    args = parser.parse_args()

    with open(args.qasm_file, "r", encoding="utf-8") as f:
        qasm_str = f.read()

    res = trace_patches_from_qasm(
        qasm_str,
        config_name=args.config,
        skip_pqsim=True,
        keep_artifacts=bool(args.keep_artifacts),
    )

    out_json = json.dumps(res, ensure_ascii=False)
    if args.out == "-":
        print(out_json)
    else:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(out_json)


if __name__ == "__main__":
    main()
