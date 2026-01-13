#!/usr/bin/env python3
"""
gate_to_event_mappingの動作確認テスト
簡単な回路でgate_to_event_mappingが正しく出力されるか確認
"""

import json
import time
import urllib.request
import urllib.error
from datetime import datetime
import os

API_URL = "http://localhost:8000"
TIMEOUT = 3600  # 1時間タイムアウト

# 簡単なテスト回路
TEST_CIRCUITS = [
    {
        "name": "test_cnot_only",
        "description": "2量子ビット: CNOTのみ（最もシンプル）",
        "qasm": """OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
creg c[2];
cx q[0],q[1];
measure q[0] -> c[0];
measure q[1] -> c[1];
"""
    },
    {
        "name": "test_h_cnot",
        "description": "2量子ビット: H + CNOT (Bell状態)",
        "qasm": """OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
creg c[2];
h q[0];
cx q[0],q[1];
measure q[0] -> c[0];
measure q[1] -> c[1];
"""
    },
    {
        "name": "test_3q_linear",
        "description": "3量子ビット: H + 2つのCNOT",
        "qasm": """OPENQASM 2.0;
include "qelib1.inc";
qreg q[3];
creg c[3];
h q[0];
cx q[0],q[1];
cx q[1],q[2];
measure q[0] -> c[0];
measure q[1] -> c[1];
measure q[2] -> c[2];
"""
    },
]


def run_trace(name: str, qasm: str) -> dict:
    """APIにトレースリクエストを送信"""
    req_data = json.dumps({"qasm": qasm}).encode("utf-8")
    req = urllib.request.Request(
        f"{API_URL}/trace",
        data=req_data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    
    start = time.time()
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            elapsed = time.time() - start
            data = json.loads(resp.read().decode("utf-8"))
            return {
                "status": "SUCCESS",
                "elapsed": elapsed,
                "data": data
            }
    except urllib.error.HTTPError as e:
        elapsed = time.time() - start
        try:
            error_body = json.loads(e.read().decode("utf-8"))
            error_detail = error_body.get("detail", str(e))
        except:
            error_detail = str(e)
        return {
            "status": "FAILED",
            "elapsed": elapsed,
            "http_status": e.code,
            "error": error_detail
        }
    except Exception as e:
        elapsed = time.time() - start
        return {
            "status": "ERROR",
            "elapsed": elapsed,
            "error": str(e)
        }


def analyze_gate_mapping(result_data: dict) -> dict:
    """gate_to_event_mappingを分析"""
    gate_mapping = result_data.get("result", {}).get("gate_to_event_mapping", [])
    compiled = result_data.get("result", {}).get("compiled", {})
    events = result_data.get("result", {}).get("patch", {}).get("events", [])
    
    analysis = {
        "has_mapping": len(gate_mapping) > 0,
        "num_gates": len(gate_mapping),
        "gates": [],
        "qisa_count": len(compiled.get("qisa", [])),
        "events_count": len(events),
    }
    
    for gate in gate_mapping:
        gate_info = {
            "gate_idx": gate.get("gate_idx"),
            "gate_type": gate.get("gate_type"),
            "gate_qubits": gate.get("gate_qubits", []),
            "ppr_type": gate.get("ppr_type"),
            "num_events": len(gate.get("events", [])),
            "events": gate.get("events", []),
        }
        analysis["gates"].append(gate_info)
    
    return analysis


def main():
    print("=" * 80)
    print("gate_to_event_mapping 動作確認テスト")
    print(f"開始時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    # 出力ディレクトリ
    output_dir = "test_results_gate_mapping"
    os.makedirs(output_dir, exist_ok=True)
    
    results = []
    
    for i, circuit in enumerate(TEST_CIRCUITS, 1):
        name = circuit["name"]
        desc = circuit["description"]
        qasm = circuit["qasm"]
        
        print(f"\n[{i}/{len(TEST_CIRCUITS)}] {name}")
        print(f"    説明: {desc}")
        print(f"    開始: {datetime.now().strftime('%H:%M:%S')}")
        print(f"    実行中...", flush=True)
        
        result = run_trace(name, qasm)
        
        if result["status"] == "SUCCESS":
            data = result["data"]["result"]
            
            # gate_to_event_mappingの分析
            analysis = analyze_gate_mapping(result["data"])
            
            print(f"    ✅ 成功! ({datetime.now().strftime('%H:%M:%S')})")
            print(f"    - 実行時間: {result['elapsed']:.1f}秒")
            print(f"    - QISA命令数: {analysis['qisa_count']}")
            print(f"    - パッチイベント数: {analysis['events_count']}")
            print(f"    - gate_to_event_mapping: {'✅ あり' if analysis['has_mapping'] else '❌ なし'}")
            
            if analysis['has_mapping']:
                print(f"    - マッピングされたゲート数: {analysis['num_gates']}")
                for gate in analysis['gates']:
                    print(f"      • ゲート[{gate['gate_idx']}]: {gate['gate_type'].upper()}{gate['gate_qubits']}")
                    print(f"        → PPRタイプ: {gate['ppr_type']}, 関連イベント数: {gate['num_events']}")
                    if gate['events']:
                        for evt in gate['events']:
                            print(f"          - {evt['inst']} @ cycle {evt['cycle']} (QISA idx: {evt['qisa_idx']})")
            else:
                print(f"    ⚠️ 警告: gate_to_event_mappingが空です")
            
            results.append({
                "name": name,
                "description": desc,
                "status": "SUCCESS",
                "elapsed_seconds": round(result['elapsed'], 2),
                "gate_mapping_analysis": analysis
            })
            
            # 結果をファイルに保存
            output_file = f"{output_dir}/{name}.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"    - 保存: {output_file}")
        else:
            print(f"    ❌ 失敗: {result.get('error', 'Unknown error')}")
            results.append({
                "name": name,
                "description": desc,
                "status": result["status"],
                "error": result.get("error"),
                "elapsed_seconds": round(result['elapsed'], 2)
            })
    
    # サマリー出力
    print("\n" + "=" * 80)
    print("テスト結果サマリー")
    print("=" * 80)
    
    success_count = sum(1 for r in results if r["status"] == "SUCCESS")
    mapping_count = sum(1 for r in results if r.get("gate_mapping_analysis", {}).get("has_mapping", False))
    
    print(f"成功: {success_count}/{len(results)}")
    print(f"gate_to_event_mappingあり: {mapping_count}/{success_count}")
    
    for r in results:
        status_icon = "✅" if r["status"] == "SUCCESS" else "❌"
        mapping_icon = "✅" if r.get("gate_mapping_analysis", {}).get("has_mapping", False) else "❌"
        print(f"  {status_icon} {r['name']}: {r['status']} (マッピング: {mapping_icon})")
    
    # サマリーをファイルに保存
    summary = {
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "test_type": "gate_mapping_verification",
        "total_tests": len(results),
        "passed": success_count,
        "failed": len(results) - success_count,
        "mapping_available": mapping_count,
        "results": results
    }
    with open(f"{output_dir}/summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"\nサマリー保存: {output_dir}/summary.json")


if __name__ == "__main__":
    main()

