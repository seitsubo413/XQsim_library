# XQsim Library Interface テスト結果レポート

**テスト日時:** 2025年12月31日 15:42:25  
**環境:** Docker (linux/amd64) + Python 3.10

---

## サマリー

| 項目 | 結果 |
|------|------|
| 合計テスト数 | 8 |
| 成功 | 7 ✅ |
| 失敗 | 1 ❌ |
| 成功率 | 87.5% |

---

## 詳細結果

### ✅ 成功したテスト

| # | テスト名 | 説明 | サイクル数 | 実行時間 | パッチ数 | イベント数 |
|---|----------|------|------------|----------|----------|------------|
| 1 | test_cnot_simple | 2量子ビット: シンプルなCNOT | 17,672 | 10分1秒 | 12 | 2 |
| 2 | test_h_cnot_2q | 2量子ビット: H + CNOT (Bell状態) | 17,672 | 8分22秒 | 12 | 2 |
| 3 | test_x_cnot_2q | 2量子ビット: X + CNOT | 17,672 | 8分52秒 | 12 | 2 |
| 4 | test_z_cnot_2q | 2量子ビット: Z + CNOT | 17,672 | 9分8秒 | 12 | 2 |
| 5 | test_h_both_cnot | 2量子ビット: 両方にH + CNOT | 17,672 | 10分3秒 | 12 | 2 |
| 6 | test_3q_linear | 3量子ビット: 線形CNOT (0→1→2) | 29,014 | 14分44秒 | 12 | 5 |
| 7 | test_3q_fan_out | 3量子ビット: ファンアウト (0→1, 0→2) | 29,014 | 15分24秒 | 12 | 5 |

### ❌ 失敗したテスト

| # | テスト名 | 説明 | 失敗理由 |
|---|----------|------|----------|
| 1 | test_swap_via_cnot | 2量子ビット: SWAP（3つのCNOT） | XQsim本体のpchpp制約エラー |

---

## 出力データ形式

各テストは以下のJSON形式でパッチ情報を出力:

```json
{
  "success": true,
  "total_cycles": 17672,
  "elapsed_seconds": 600.56,
  "patches": [
    {
      "patch_id": 0,
      "patch_type": "d",
      "qubit_id": 0,
      "role": "data",
      "coords": {"x": 4, "y": 2}
    },
    ...
  ],
  "events": [
    {
      "cycle": 1234,
      "event_type": "state_change",
      "patch_id": 0,
      "details": {...}
    },
    ...
  ]
}
```

---

## 結論

XQsimライブラリインターフェースは正常に動作しています。

- **入力:** OpenQASM 2.0形式の量子回路
- **出力:** パッチ情報（座標、状態、イベント）をJSON形式で返却
- **対応回路:** 2〜3量子ビット、基本ゲート（H, X, Z, CNOT）

失敗した1件（SWAP回路）はXQsim本体の制約によるものであり、インターフェース実装の問題ではありません。

---

## ファイル一覧

テスト結果の詳細は `test_results_v2/` フォルダに保存:

- `summary.json` - 全テストのサマリー
- `test_cnot_simple.json` - CNOTテスト詳細
- `test_h_cnot_2q.json` - Bell状態テスト詳細
- `test_x_cnot_2q.json` - X+CNOTテスト詳細
- `test_z_cnot_2q.json` - Z+CNOTテスト詳細
- `test_h_both_cnot.json` - 両方H+CNOTテスト詳細
- `test_3q_linear.json` - 3量子ビット線形テスト詳細
- `test_3q_fan_out.json` - 3量子ビットファンアウトテスト詳細

