# XQsim Library インターフェース開発 引き継ぎ資料

**作成日**: 2024年12月31日  
**最終更新**: 2026年1月1日  
**目的**: XQsim Patch Trace API の開発状況と成果の引き継ぎ

---

## 1. プロジェクト概要

### 目的
XQsimをライブラリとして使用し、QASMを入力として受け取り、パッチ情報をJSONで返すAPIを構築する。

### 構成ファイル
```
XQsim_library/
├── src/
│   ├── api_server.py            # FastAPI サーバー
│   ├── patch_trace_backend.py   # バックエンドロジック
│   ├── run_tests.py             # テストスクリプト v1
│   ├── run_tests_v2.py          # テストスクリプト v2
│   ├── run_tests_v3_complex.py  # テストスクリプト v3（複雑回路）
│   └── XQ-simulator/            # XQsim本体
├── docs/
│   ├── API_OUTPUT_FORMAT.md     # ★ フロントエンド向け出力仕様書
│   └── types/xqsim.d.ts         # ★ TypeScript型定義
├── test_results_v2/             # テスト結果
├── Dockerfile
├── docker-compose.yml
└── README_API.md                # API ドキュメント
```

---

## 2. 現在の状態 ✅ 完成

### 動作するもの
- ✅ Dockerコンテナのビルドと起動
- ✅ FastAPI サーバー (`/health`, `/trace` エンドポイント)
- ✅ QASMのコンパイル（transpile → qisa_compile → assemble）
- ✅ シミュレーションの実行と**正常終了**
- ✅ パッチ状態の時系列トレース出力（JSON）
- ✅ 排他制御（同時実行防止）
- ✅ タイムアウト処理
- ✅ 入力検証

### テスト結果サマリー

#### v1テスト（基本回路）
| テスト | 結果 | 備考 |
|--------|------|------|
| 1量子ビット H | ❌ | CNOTなしは非対応 |
| 2量子ビット Bell | ✅ | 17,672サイクル |
| 3量子ビット GHZ | ✅ | 29,014サイクル |

#### v2テスト（CNOT含む回路）
| テスト | 結果 | サイクル | イベント |
|--------|------|---------|---------|
| CNOTのみ | ✅ | 17,672 | 2 |
| H + CNOT | ✅ | 17,672 | 2 |
| X + CNOT | ✅ | 17,672 | 2 |
| Z + CNOT | ✅ | 17,672 | 2 |
| H両方 + CNOT | ✅ | 17,672 | 2 |
| SWAP (CNOT×3) | ❌ | - | 非対応 |
| 3q線形 | ✅ | 29,014 | 5 |
| 3qファンアウト | ✅ | 29,014 | 5 |

**成功率: 7/8 (87.5%)**

---

## 3. 修正済みの内容

### xq_simulator.py（XQsim本体）
1. **AttributeError修正** (170行目, 356行目)
   - `self.emulate` → `self.skip_pqsim` に修正
   - XQsim本体のバグ

### api_server.py
1. **Ray初期化をlifespanに移動**
   - プロセス起動時に1回だけ初期化
   
2. **排他制御（グローバルロック）**
   - `/trace` は同時に1リクエストのみ実行
   - 実行中は429エラーを返却

3. **タイムアウト処理**
   - 環境変数 `XQSIM_TRACE_TIMEOUT_SECONDS` で設定可能

4. **入力検証**
   - QASMサイズ上限
   - 量子ビット数上限
   - 回路深度上限

### patch_trace_backend.py
1. **sys.exit()インターセプト**
   - XQsim内部のsys.exit()をキャッチしてRuntimeErrorに変換

2. **安定性チェック関数の実装**
   - `_check_system_stable()`: シミュレーション終了判定の補助

3. **monkeypatch による終了条件修正**
   - `qif.done`, `lmu.done` の強制設定

4. **アーティファクト管理**
   - 一時ファイルを `src/quantum_circuits/` に生成
   - 終了後にクリーンアップ

---

## 4. API仕様

### エンドポイント

```
POST /trace
Content-Type: application/json

{
  "qasm": "OPENQASM 2.0; ...",
  "config": "example_cmos_d5"
}
```

### レスポンス構造

```json
{
  "result": {
    "meta": {
      "version": 3,
      "total_cycles": 17672,
      "elapsed_seconds": 514.11,
      "termination_reason": "normal",
      "patch_grid": { "rows": 3, "cols": 4 },
      "num_patches": 12
    },
    "input": { "qasm": "...", "num_qasm_qubits": 2 },
    "compiled": { "qisa": [...], "qbin_name": "..." },
    "patch": {
      "initial": [...],   // 初期パッチ状態
      "events": [...]     // 時系列イベント ★フロントエンド用
    }
  }
}
```

詳細は `docs/API_OUTPUT_FORMAT.md` を参照。

---

## 5. 判明した制限事項 ⚠️

### XQsimの制約

| 制約 | 詳細 |
|------|------|
| **CNOTが必須** | 単一量子ビット操作のみの回路は `invalid pchpp` エラー |
| **最小3量子ビット** | 2量子ビット以下は自動パディング |
| **SWAPパターン非対応** | 同じ量子ビット間で複数CNOTは失敗 |
| **回転ゲートは遅い** | `cu1`, `rz`, `ry` 等はTゲートに分解され時間爆発 |

### 実用的な回路パターン

✅ **動作する回路**:
- H + CNOT（Bell状態）
- H + CNOT×n（GHZ状態）
- X/Z + CNOT
- 連鎖エンタングルメント
- ファンアウト

❌ **動作しない回路**:
- Hのみ（CNOTなし）
- SWAP（CNOT×3で同じペア）
- QFT（回転ゲート多数）
- 複雑なGrover/VQE/QAOA

---

## 6. 実行方法

### Docker起動

```bash
docker-compose build --no-cache
docker-compose up -d
```

### APIテスト

```bash
# ヘルスチェック
curl http://localhost:8000/health

# トレース実行
docker-compose exec xqsim-backend python /app/src/run_tests_v2.py
```

### 結果取得

```bash
docker cp xqsim_library-xqsim-backend-1:/app/test_results_v2 ./test_results_v2
```

---

## 7. フロントエンド連携

### ドキュメント

| ファイル | 内容 |
|---------|------|
| `docs/API_OUTPUT_FORMAT.md` | 出力フォーマット完全仕様 |
| `docs/types/xqsim.d.ts` | TypeScript型定義 |

### 主要な型

```typescript
interface PatchEvent {
  seq: number;           // イベント連番
  cycle: number;         // 発生サイクル
  inst: string;          // QISA命令名 (MERGE_INFO, SPLIT_INFO等)
  patch_delta: Patch[];  // 変化したパッチ
}

interface Patch {
  pchidx: number;
  row: number;
  col: number;
  pchtype: "zt" | "zb" | "mt" | "mb" | "m" | "x" | "awe" | "i";
  facebd: { w: string; n: string; e: string; s: string };
  cornerbd: { nw: string; ne: string; sw: string; se: string };
}
```

---

## 8. トラブルシューティング

### 429 Too Many Requests
```
Another trace operation is in progress
```
→ コンテナ再起動: `docker-compose restart xqsim-backend`

### 400 Bad Request (invalid pchpp)
```
invalid pchpp in PIU.dyndec
```
→ CNOTを含む回路に変更

### タイムアウト
```
Read timed out
```
→ 回転ゲート（cu1, rz等）を削除、または H+CNOT のみに簡略化

---

## 9. 今後の課題

### 優先度高
1. **パフォーマンス改善**: 1回路あたり5-15分は長い
2. **対応回路の拡大**: SWAP、回転ゲート対応

### 優先度中
3. **キャッシュ機能**: 同じ回路の再計算を避ける
4. **非同期処理**: ジョブキュー方式への変更

---

## 10. 参考情報

- XQsim GitHub: （元のリポジトリURL）
- XQsim README: `README.md`
- API README: `README_API.md`

---

**最終更新**: 2026年1月1日

