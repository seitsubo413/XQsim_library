#!/usr/bin/env python3
"""
XQsim Patch Trace API テストスクリプト
APIサーバーが正しく動作しているか確認します
"""

import json
import requests
import sys
import time
from pathlib import Path

API_BASE_URL = "http://localhost:8000"

def wait_for_server(url, max_retries=30, delay=1):
    """APIサーバーが起動するまで待機"""
    for i in range(max_retries):
        try:
            response = requests.get(f"{url}/health", timeout=2)
            if response.status_code == 200:
                print(f"✓ APIサーバーが起動しました（{i+1}回目の試行）")
                return True
        except requests.exceptions.RequestException:
            pass
        time.sleep(delay)
    return False

def test_health():
    """ヘルスチェックエンドポイントのテスト"""
    print("=" * 60)
    print("テスト1: /health エンドポイント")
    print("=" * 60)
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        response.raise_for_status()
        result = response.json()
        print(f"✓ ステータスコード: {response.status_code}")
        print(f"✓ レスポンス: {json.dumps(result, indent=2, ensure_ascii=False)}")
        return True
    except Exception as e:
        print(f"✗ エラー: {e}")
        return False

def test_trace_simple():
    """簡単なQASMでの/traceエンドポイントのテスト"""
    print("\n" + "=" * 60)
    print("テスト2: /trace エンドポイント (簡単なQASM)")
    print("=" * 60)
    
    simple_qasm = """OPENQASM 2.0;
include "qelib1.inc";
qreg q[1];
creg meas[1];
h q[0];
measure q[0] -> meas[0];
"""
    
    payload = {
        "qasm": simple_qasm,
        "config": "example_cmos_d5"
    }
    
    try:
        print(f"送信するQASM:\n{simple_qasm}")
        print("\nリクエスト送信中（最大30分待機）...")
        response = requests.post(
            f"{API_BASE_URL}/trace",
            json=payload,
            timeout=1800  # 30分のタイムアウト（XQsimのシミュレーションは時間がかかることがある）
        )
        response.raise_for_status()
        result = response.json()
        
        print(f"✓ ステータスコード: {response.status_code}")
        print(f"\nレスポンス構造:")
        print(f"  - meta: {list(result.get('result', {}).get('meta', {}).keys())}")
        print(f"  - input: {list(result.get('result', {}).get('input', {}).keys())}")
        print(f"  - compiled: {list(result.get('result', {}).get('compiled', {}).keys())}")
        print(f"  - patch: {list(result.get('result', {}).get('patch', {}).keys())}")
        
        # パッチ情報の詳細を確認
        patch_data = result.get('result', {}).get('patch', {})
        if 'initial' in patch_data:
            print(f"\n✓ 初期パッチ数: {len(patch_data['initial'])}")
        if 'events' in patch_data:
            print(f"✓ パッチイベント数: {len(patch_data['events'])}")
            if patch_data['events']:
                print(f"  最初のイベント: {patch_data['events'][0].get('inst', 'N/A')}")
        
        # 結果をファイルに保存
        with open("test_result_simple.json", "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"\n✓ 結果を test_result_simple.json に保存しました")
        
        return True
    except requests.exceptions.Timeout:
        print("✗ タイムアウト: リクエストが5分以内に完了しませんでした")
        return False
    except requests.exceptions.HTTPError as e:
        print(f"✗ HTTPエラー: {e}")
        if hasattr(e.response, 'text'):
            print(f"  エラー詳細: {e.response.text[:500]}")
        return False
    except Exception as e:
        print(f"✗ エラー: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_trace_existing():
    """既存のQASMファイルでの/traceエンドポイントのテスト"""
    print("\n" + "=" * 60)
    print("テスト3: /trace エンドポイント (既存のQASMファイル)")
    print("=" * 60)
    
    qasm_file = Path("src/quantum_circuits/open_qasm/qft_n2.qasm")
    if not qasm_file.exists():
        print(f"✗ ファイルが見つかりません: {qasm_file}")
        return False
    
    try:
        with open(qasm_file, "r", encoding="utf-8") as f:
            qasm_content = f.read()
        
        payload = {
            "qasm": qasm_content,
            "config": "example_cmos_d5"
        }
        
        print(f"送信するQASMファイル: {qasm_file}")
        print(f"QASM内容:\n{qasm_content}")
        print("\nリクエスト送信中（最大30分待機）...")
        response = requests.post(
            f"{API_BASE_URL}/trace",
            json=payload,
            timeout=1800  # 30分のタイムアウト（XQsimのシミュレーションは時間がかかることがある）
        )
        response.raise_for_status()
        result = response.json()
        
        print(f"✓ ステータスコード: {response.status_code}")
        
        # パッチ情報の詳細を確認
        patch_data = result.get('result', {}).get('patch', {})
        if 'initial' in patch_data:
            print(f"\n✓ 初期パッチ数: {len(patch_data['initial'])}")
            if patch_data['initial']:
                first_patch = patch_data['initial'][0]
                print(f"  最初のパッチ: pchidx={first_patch.get('pchidx')}, pchtype={first_patch.get('pchtype')}")
        if 'events' in patch_data:
            print(f"✓ パッチイベント数: {len(patch_data['events'])}")
            for i, event in enumerate(patch_data['events'][:3]):  # 最初の3つを表示
                print(f"  イベント{i+1}: cycle={event.get('cycle')}, inst={event.get('inst')}, "
                      f"patch_delta数={len(event.get('patch_delta', []))}")
        
        # 結果をファイルに保存
        with open("test_result_qft.json", "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"\n✓ 結果を test_result_qft.json に保存しました")
        
        return True
    except requests.exceptions.Timeout:
        print("✗ タイムアウト: リクエストが5分以内に完了しませんでした")
        return False
    except requests.exceptions.HTTPError as e:
        print(f"✗ HTTPエラー: {e}")
        if hasattr(e.response, 'text'):
            print(f"  エラー詳細: {e.response.text[:500]}")
        return False
    except Exception as e:
        print(f"✗ エラー: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """メイン関数"""
    print("XQsim Patch Trace API テスト開始")
    print(f"API URL: {API_BASE_URL}\n")
    
    # APIサーバーが起動するまで待機
    print("APIサーバーの起動を待機中...")
    if not wait_for_server(API_BASE_URL):
        print("✗ エラー: APIサーバーが起動しませんでした")
        return 1
    
    print("")
    results = []
    
    # テスト1: ヘルスチェック
    results.append(("ヘルスチェック", test_health()))
    
    # テスト2: 簡単なQASM
    results.append(("簡単なQASM", test_trace_simple()))
    
    # テスト3: 既存のQASMファイル
    results.append(("既存のQASMファイル", test_trace_existing()))
    
    # 結果サマリー
    print("\n" + "=" * 60)
    print("テスト結果サマリー")
    print("=" * 60)
    for name, success in results:
        status = "✓ 成功" if success else "✗ 失敗"
        print(f"{name}: {status}")
    
    total = len(results)
    passed = sum(1 for _, success in results if success)
    print(f"\n合計: {passed}/{total} テストが成功しました")
    
    # すべて成功した場合は0、そうでなければ1を返す
    return 0 if passed == total else 1

if __name__ == "__main__":
    sys.exit(main())

