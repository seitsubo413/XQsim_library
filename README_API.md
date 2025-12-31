# XQsim Patch Trace API

XQsimを使用して、QASM回路からパッチ形状の時系列情報をJSON形式で取得するAPIです。

## 概要

このAPIは、既存のXQsim（量子制御プロセッサシミュレータ）をラップし、以下の機能を提供します：

- **入力**: OpenQASM 2.0形式の量子回路
- **出力**: パッチ形状の時系列情報（JSON）

```
QASM → コンパイル → シミュレーション → パッチ情報JSON
```

## クイックスタート

### 1. Docker でビルド・起動

```bash
docker-compose build xqsim-backend
docker-compose up -d xqsim-backend
```

### 2. ヘルスチェック

```bash
curl http://localhost:8000/health
```

レスポンス例：
```json
{
  "status": "ok",
  "trace_in_progress": false,
  "limits": {
    "max_qasm_size_bytes": 1048576,
    "max_qubits": 20,
    "max_depth": 1000,
    "max_instructions": 10000,
    "trace_timeout_seconds": 300
  }
}
```

### 3. パッチトレースの取得

```bash
curl -X POST http://localhost:8000/trace \
  -H "Content-Type: application/json" \
  -d '{
    "qasm": "OPENQASM 2.0;\ninclude \"qelib1.inc\";\nqreg q[2];\ncreg c[2];\nh q[0];\ncx q[0],q[1];\nmeasure q[0] -> c[0];\nmeasure q[1] -> c[1];",
    "config": "example_cmos_d5"
  }'
```

## API エンドポイント

### `GET /health`

ヘルスチェック。現在の状態と制限値を返します。

### `POST /trace`

QASMからパッチトレースを生成します。

#### リクエストボディ

| フィールド | 型 | 必須 | デフォルト | 説明 |
|-----------|------|------|-----------|------|
| `qasm` | string | ✅ | - | OpenQASM 2.0形式の量子回路 |
| `config` | string | - | `example_cmos_d5` | 設定ファイル名（`src/configs/`配下、`.json`なし） |
| `keep_artifacts` | bool | - | `false` | 中間ファイルを残すか |
| `debug_logging` | bool | - | `false` | 詳細ログを有効化 |

#### レスポンス

```json
{
  "result": {
    "meta": {
      "version": 3,
      "config": "example_cmos_d5",
      "block_type": "Distillation",
      "code_distance": 5,
      "patch_grid": { "rows": 3, "cols": 3 },
      "num_patches": 9,
      "total_cycles": 12345,
      "elapsed_seconds": 1.23,
      "termination_reason": "normal",
      "forced_terminations": [],
      "warnings": []
    },
    "input": {
      "qasm": "...",
      "num_qasm_qubits": 2,
      "num_compile_qubits": 3,
      "padding_applied": true
    },
    "compiled": {
      "clifford_t_qasm": "...",
      "clifford_t_qasm_padded": "...",
      "qisa": ["..."],
      "qbin_name": "api_xxx_n3"
    },
    "patch": {
      "initial": [...],
      "events": [...]
    }
  }
}
```

#### エラーレスポンス

| ステータスコード | 説明 |
|-----------------|------|
| 400 | 無効な入力（QASM構文エラー、制限超過、シミュレーションエラー） |
| 429 | 別のトレースが実行中 |
| 504 | タイムアウト |
| 500 | 内部エラー |

## 設定

### 環境変数

| 変数 | 説明 | デフォルト |
|------|------|-----------|
| `XQSIM_MAX_QASM_SIZE_BYTES` | QASMの最大サイズ（バイト） | `1048576` (1MB) |
| `XQSIM_MAX_QUBITS` | 最大qubit数 | `20` |
| `XQSIM_MAX_DEPTH` | 最大回路深さ | `1000` |
| `XQSIM_MAX_INSTRUCTIONS` | 最大命令数 | `10000` |
| `XQSIM_TRACE_TIMEOUT_SECONDS` | タイムアウト（秒） | `300` |
| `XQSIM_RAY_OBJECT_STORE_MB` | Rayオブジェクトストアサイズ（MB） | `256` |
| `XQSIM_RAY_NUM_CPUS` | Ray使用CPU数 | `1` |
| `XQSIM_ARTIFACT_ROOT` | 生成ファイルの場所 | `src/quantum_circuits`（コンパイラと同じ） |
| `XQSIM_DEBUG_LOG_INTERVAL` | デバッグログ間隔（サイクル） | `1000` |

### 利用可能な設定ファイル

`src/configs/` 配下の設定ファイル：

| 設定名 | 説明 |
|--------|------|
| `example_cmos_d5` | 例: CMOS, code distance 5 |
| `example_rsfq_d5` | 例: RSFQ, code distance 5 |
| `current_300K_CMOS` | 現在の300K CMOS |
| `nearfuture_4K_CMOS` | 近い将来の4K CMOS |
| `nearfuture_4K_CMOS_Vopt` | 近い将来の4K CMOS (電圧最適化) |
| `nearfuture_4K_RSFQ` | 近い将来の4K RSFQ |
| `future_4K_ERSFQ` | 将来の4K ERSFQ |

## 運用上の注意

### 並列実行の制限

- **トレース処理は直列化されます**（同時に1つのリクエストのみ実行可能）
- 実行中に別のリクエストが来ると `429 Too Many Requests` を返します
- `uvicorn --workers 1` での運用を推奨

### リソース使用

- シミュレーションはCPU集約的です
- 大きな回路はメモリを多く消費します
- タイムアウト（デフォルト5分）で強制終了します

### 既知の制限

1. **qubit数は奇数が推奨**: 偶数の場合、内部で1qubitパディングされます
2. **一部の回路は非対応**: 特定のゲート構成で `invalid pchpp` エラーが発生する場合があります
3. **シミュレーション時間**: 複雑な回路は長時間かかる場合があります

## ファイル構成

```
XQsim_library/
├── src/
│   ├── api_server.py           # FastAPI サーバー
│   ├── patch_trace_backend.py  # パッチトレースロジック
│   ├── XQ-simulator/           # XQsim本体（変更しない）
│   ├── compiler/               # コンパイラ（変更しない）
│   └── configs/                # 設定ファイル
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── README.md                   # XQsim本体のREADME
└── README_API.md               # このファイル
```

## 開発・デバッグ

### ローカル実行

```bash
cd src
uvicorn api_server:app --host 0.0.0.0 --port 8000 --reload
```

### ログ確認

```bash
docker-compose logs -f xqsim-backend
```

### デバッグモード

リクエストに `"debug_logging": true` を含めると、詳細なサイクル情報がログに出力されます。

## トラブルシューティング

### 429 Too Many Requests

別のトレースが実行中です。完了を待つか、コンテナを再起動してください。

```bash
docker-compose restart xqsim-backend
```

### 504 Gateway Timeout

シミュレーションがタイムアウトしました。回路が複雑すぎるか、シミュレーションが終了しない問題が発生しています。

### シミュレーションが終了しない

XQsim本体の既知の問題です。一部の回路で発生します。タイムアウト（デフォルト5分）で強制終了されます。

## バージョン履歴

### v0.3.0
- トレース処理の直列化（429エラー対応）
- wall clockタイムアウト追加
- 入力制限（QASM サイズ、qubit数、深さ）
- `_check_system_stable()` の堅牢化
- numpy の安全インポート
- 生成ファイルのデフォルト場所を `/tmp` に変更

### v0.2.0
- Ray初期化をAPI起動時に1回だけに変更
- `/dev/shm` フォールバック追加
- デバッグログをデフォルト無効に
- JSON正規化の改善
- パディング情報の明示化

### v0.1.0
- 初期リリース

## 関連ドキュメント

- [XQsim本体のREADME](./README.md)
- [引き継ぎ資料](./HANDOVER.md)

## ライセンス

XQsim本体のライセンスに準拠します。

