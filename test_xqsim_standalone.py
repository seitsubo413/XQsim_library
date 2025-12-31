#!/usr/bin/env python3
"""
XQsim単体テスト（インターフェースなし）

qft_n2.qasmを使ってXQsimを直接実行し、
シミュレーションが正常に終了するか確認します。
"""

import os
import sys

# パス設定
curr_path = os.path.abspath(__file__)
curr_dir = os.path.dirname(curr_path)
src_dir = os.path.join(curr_dir, "src")
sim_dir = os.path.join(src_dir, "XQ-simulator")
comp_dir = os.path.join(src_dir, "compiler")

sys.path.insert(0, src_dir)
sys.path.insert(0, sim_dir)
sys.path.insert(0, comp_dir)

# Ray初期化（ダッシュボード無効）
os.environ["RAY_DISABLE_DASHBOARD"] = "1"
os.environ["RAY_DASHBOARD_ENABLED"] = "0"
os.environ["RAY_USAGE_STATS_ENABLED"] = "0"

import ray
if not ray.is_initialized():
    ray.init(
        ignore_reinit_error=True,
        include_dashboard=False,
        log_to_driver=False,
        num_cpus=1,
        object_store_memory=512 * 1024 * 1024,
        _plasma_directory="/dev/shm",
        _temp_dir="/tmp/ray",
    )

from gsc_compiler import gsc_compiler
from xq_simulator import xq_simulator

def main():
    print("=" * 60)
    print("XQsim 単体テスト（インターフェースなし）")
    print("=" * 60)
    
    # 1) コンパイル
    # XQsimの制約に合わせて3量子ビット版を使用
    # qft_n2.qasmを3量子ビットにパディングしてコンパイル
    qbin_name = "qft_n3_standalone"
    print(f"\n1) コンパイル: {qbin_name}")
    
    # 3量子ビット版のQASMを作成
    qasm_3q = """OPENQASM 2.0;
include "qelib1.inc";
qreg q[3];
creg meas[2];
h q[1];
cp(pi/2) q[0],q[1];
h q[0];
barrier q[0],q[1];
measure q[0] -> meas[0];
measure q[1] -> meas[1];
"""
    qasm_path = os.path.join(src_dir, "quantum_circuits", "open_qasm", f"{qbin_name}.qasm")
    os.makedirs(os.path.dirname(qasm_path), exist_ok=True)
    with open(qasm_path, "w") as f:
        f.write(qasm_3q)
    print(f"   3量子ビット版QASMを作成: {qasm_path}")
    
    compiler = gsc_compiler()
    compiler.setup(
        qc_name=qbin_name,
        compile_mode=["transpile", "qisa_compile", "assemble"]
    )
    compiler.run()
    print("   コンパイル完了")
    
    # 2) シミュレータ設定
    print("\n2) シミュレータ設定")
    # XQsimの制約: num_lq % 2 == 1 または num_lq == 2
    # qft_n3_standalone = 3 qubits → num_lq = 3 + 2 = 5 (奇数なのでOK)
    num_lq = 3 + 2  # 3量子ビット + 2 = 5
    
    sim = xq_simulator()
    sim.setup(
        config="example_cmos_d5",
        qbin=qbin_name,  # qft_n3_standalone
        num_lq=num_lq,
        skip_pqsim=True,  # 物理シミュレーションをスキップ
        num_shots=1,
        dump=False,
        regen=True,
        debug=False,
    )
    
    # emulate属性を設定
    if not hasattr(sim, "emulate"):
        sim.emulate = True
    
    print(f"   num_lq={num_lq}, skip_pqsim=True")
    
    # 3) シミュレーション実行
    print("\n3) シミュレーション実行")
    print("   サイクルごとの状態を監視...")
    
    max_cycles = 100000
    log_interval = 1000
    
    try:
        while not sim.sim_done:
            sim.run_cycle_transfer()
            sim.run_cycle_update()
            sim.run_cycle_tick()
            
            if sim.cycle % log_interval == 0:
                print(f"\n   Cycle {sim.cycle}:")
                print(f"     qif.done={sim.qif.done}, qid.done={sim.qid.done}")
                print(f"     pdu.state={sim.pdu.state}, piu.state={sim.piu.state}")
                print(f"     psu.pchinfo_full={sim.psu.pchinfo_full}")
                
                # PSU srmem状態
                pchinfo_srmem = sim.psu.pchinfo_srmem
                db = pchinfo_srmem.double_buffer
                print(f"     PSU.srmem.double_buffer: [0].state={db[0].state}, [1].state={db[1].state}")
                
                print(f"     sim_done={sim.sim_done}")
            
            if sim.cycle >= max_cycles:
                print(f"\n   警告: {max_cycles}サイクルに達しました。中断します。")
                break
        
        if sim.sim_done:
            print(f"\n✓ シミュレーション正常終了! 総サイクル数: {sim.cycle}")
        else:
            print(f"\n✗ シミュレーション未完了。現在のサイクル: {sim.cycle}")
            
    except Exception as e:
        print(f"\n✗ エラー発生: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    print("\n" + "=" * 60)
    print("テスト完了")
    print("=" * 60)
    return 0

if __name__ == "__main__":
    sys.exit(main())

