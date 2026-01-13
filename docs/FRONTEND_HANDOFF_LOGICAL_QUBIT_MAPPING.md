# フロントエンド引き継ぎ: 論理キュービット-パッチ対応マッピング

**作成日**: 2026年1月8日  
**対象**: フロントエンドチーム  
**ステータス**: 実装完了・利用可能

---

## 1. 概要

### 1.1 追加された機能

API レスポンスの JSON に新しいフィールド `logical_qubit_mapping` が追加されました。
これにより、**どのパッチがどの論理キュービットに対応するか**を取得できます。

### 1.2 ユースケース

- パッチをクリック → 「これは q[2] です」と表示
- 論理キュービット q[n] を選択 → 対応するパッチをハイライト
- アンシラパッチと データパッチを視覚的に区別

---

## 2. データ構造

### 2.1 レスポンス内の位置

```json
{
  "meta": { ... },
  "input": { ... },
  "compiled": { ... },
  "patch": { ... },
  "logical_qubit_mapping": [   // ← 新規追加
    { ... },
    { ... }
  ]
}
```

### 2.2 フィールド定義

| フィールド | 型 | 説明 |
|-----------|------|------|
| `lq_idx` | `number` | 内部論理キュービットインデックス（0始まり） |
| `role` | `string` | キュービットの役割（後述） |
| `qubit_index` | `number?` | ユーザー視点のキュービット番号（`q[n]` の n）。role が `data` または `padding` の場合のみ存在 |
| `description` | `string` | 人間が読める説明文 |
| `patch_indices` | `number[]` | 使用するパッチのインデックス（pchidx）。アンシラは2パッチ使用 |
| `patch_coords` | `[number, number][]` | パッチの `[row, col]` 座標の配列 |
| `pchtype` | `string` | パッチタイプ（`zt`, `m`, `x` など） |

### 2.3 role の種類

| role | 説明 | qubit_index |
|------|------|-------------|
| `z_ancilla` | Zタイプ アンシラ（マジック状態用） | なし |
| `m_ancilla` | Mタイプ アンシラ（ゼロ状態用） | なし |
| `data` | ユーザーの論理キュービット | あり |
| `padding` | パディング用（偶数→奇数調整、未使用） | あり |

---

## 3. 実データ例

### 3.1 サンプル: 6量子ビット回路 (`sample_6q_ladder.json`)

**入力回路**: 6量子ビット、ladder型のCXゲート

**パッチグリッド**: 3行 × 6列 = 18パッチ

```
        Col 0    Col 1    Col 2    Col 3    Col 4    Col 5
       ┌────────┬────────┬────────┬────────┬────────┬────────┐
Row 0  │  zt    │  mt    │   m    │   m    │   m    │   i    │
       │ (Z-anc)│ (M-anc)│  q[0]  │  q[2]  │  q[4]  │        │
       ├────────┼────────┼────────┼────────┼────────┼────────┤
Row 1  │  zb    │  mb    │  aw    │  ac    │  ae    │   x    │
       │ (Z-anc)│ (M-anc)│ ancilla│ ancilla│ ancilla│(padding)│
       ├────────┼────────┼────────┼────────┼────────┼────────┤
Row 2  │   i    │   i    │   m    │   m    │   m    │   i    │
       │        │        │  q[1]  │  q[3]  │  q[5]  │        │
       └────────┴────────┴────────┴────────┴────────┴────────┘
```

### 3.2 対応するJSONデータ

```json
"logical_qubit_mapping": [
  {
    "lq_idx": 0,
    "role": "z_ancilla",
    "description": "Magic state ancilla (Z-type)",
    "patch_indices": [0, 6],
    "patch_coords": [[0, 0], [1, 0]],
    "pchtype": "zt"
  },
  {
    "lq_idx": 1,
    "role": "m_ancilla",
    "description": "Zero state ancilla (M-type)",
    "patch_indices": [1, 7],
    "patch_coords": [[0, 1], [1, 1]],
    "pchtype": "mt"
  },
  {
    "lq_idx": 2,
    "role": "data",
    "qubit_index": 0,
    "description": "User qubit q[0]",
    "patch_indices": [2],
    "patch_coords": [[0, 2]],
    "pchtype": "m"
  },
  {
    "lq_idx": 3,
    "role": "data",
    "qubit_index": 1,
    "description": "User qubit q[1]",
    "patch_indices": [14],
    "patch_coords": [[2, 2]],
    "pchtype": "m"
  },
  {
    "lq_idx": 4,
    "role": "data",
    "qubit_index": 2,
    "description": "User qubit q[2]",
    "patch_indices": [3],
    "patch_coords": [[0, 3]],
    "pchtype": "m"
  },
  {
    "lq_idx": 5,
    "role": "data",
    "qubit_index": 3,
    "description": "User qubit q[3]",
    "patch_indices": [15],
    "patch_coords": [[2, 3]],
    "pchtype": "m"
  },
  {
    "lq_idx": 6,
    "role": "data",
    "qubit_index": 4,
    "description": "User qubit q[4]",
    "patch_indices": [4],
    "patch_coords": [[0, 4]],
    "pchtype": "m"
  },
  {
    "lq_idx": 7,
    "role": "data",
    "qubit_index": 5,
    "description": "User qubit q[5]",
    "patch_indices": [16],
    "patch_coords": [[2, 4]],
    "pchtype": "m"
  },
  {
    "lq_idx": 8,
    "role": "padding",
    "qubit_index": 6,
    "description": "Padding qubit (unused)",
    "patch_indices": [11],
    "patch_coords": [[1, 5]],
    "pchtype": "x"
  }
]
```

---

## 4. フロントエンド実装ガイド

### 4.1 TypeScript 型定義

```typescript
interface LogicalQubitMapping {
  lq_idx: number;
  role: 'z_ancilla' | 'm_ancilla' | 'data' | 'padding';
  qubit_index?: number;  // role が 'data' または 'padding' の場合のみ
  description: string;
  patch_indices: number[];
  patch_coords: [number, number][];
  pchtype: string;
}
```

### 4.2 逆引きマップの構築例

```typescript
// pchidx → LogicalQubitMapping の逆引きマップを構築
function buildPatchToQubitMap(
  mappings: LogicalQubitMapping[]
): Map<number, LogicalQubitMapping> {
  const map = new Map<number, LogicalQubitMapping>();
  for (const mapping of mappings) {
    for (const pchidx of mapping.patch_indices) {
      map.set(pchidx, mapping);
    }
  }
  return map;
}

// 使用例: パッチクリック時
function onPatchClick(pchidx: number) {
  const mapping = patchToQubitMap.get(pchidx);
  if (mapping) {
    if (mapping.role === 'data') {
      showTooltip(`q[${mapping.qubit_index}]`);
    } else {
      showTooltip(mapping.description);
    }
  }
}
```

### 4.3 ユーザーキュービットのみをフィルタ

```typescript
// ユーザーの論理キュービットのみを取得
const userQubits = mappings.filter(m => m.role === 'data');

// q[n] → パッチ座標のマップ
const qubitToPatch = new Map(
  userQubits.map(m => [m.qubit_index!, m.patch_coords[0]])
);
```

### 4.4 色分け表示の例

```typescript
function getPatchColor(mapping: LogicalQubitMapping | undefined): string {
  if (!mapping) return '#gray';  // 未使用パッチ
  
  switch (mapping.role) {
    case 'z_ancilla': return '#4a90d9';  // 青系
    case 'm_ancilla': return '#7b68ee';  // 紫系
    case 'data':      return '#50c878';  // 緑系
    case 'padding':   return '#d3d3d3';  // グレー
    default:          return '#gray';
  }
}
```

---

## 5. 重要な注意点

### 5.1 アンシラは2パッチを使用

- `z_ancilla` と `m_ancilla` は **2つのパッチ**（上下に隣接）を使用
- `patch_indices` と `patch_coords` に2要素が含まれる

### 5.2 パディングキュービット

- XQsim内部では論理キュービット数が奇数である必要がある
- 入力が偶数の場合、1つのパディングキュービットが自動追加される
- `role: "padding"` で識別可能
- `meta.warnings` にもパディング適用のメッセージが含まれる

### 5.3 座標系

- `patch_coords` は `[row, col]` 形式
- `row` は上から下（0が上）
- `col` は左から右（0が左）
- `patch.initial` の各パッチにも `row`, `col` フィールドがある

### 5.4 pchidx の計算

```
pchidx = row * num_cols + col
```

例: 3行6列のグリッドで `[2, 3]` の場合:
```
pchidx = 2 * 6 + 3 = 15
```

---

## 6. 関連データとの連携

### 6.1 patch.initial との関連

`logical_qubit_mapping` の `patch_indices` を使って `patch.initial` から詳細情報を取得:

```typescript
const pchidx = mapping.patch_indices[0];
const patchInfo = response.patch.initial.find(p => p.pchidx === pchidx);
// patchInfo.facebd, patchInfo.cornerbd などにアクセス可能
```

### 6.2 patch.events との関連

イベント発生時に、影響を受けた論理キュービットを特定:

```typescript
function getAffectedQubits(event: PatchEvent): LogicalQubitMapping[] {
  const affectedPchidxs = event.patch_delta.map(d => d.pchidx);
  return mappings.filter(m => 
    m.patch_indices.some(idx => affectedPchidxs.includes(idx))
  );
}
```

---

## 7. テストデータ

以下のサンプルファイルが利用可能です:

| ファイル | キュービット数 | パッチグリッド |
|----------|--------------|---------------|
| `sample_results/sample_6q_ladder.json` | 6 (+1 padding) | 3×6 |

---

## 8. 質問・フィードバック

実装で不明点があればバックエンドチームまでお問い合わせください。

- 追加のフィールドが必要な場合
- 形式の変更要望
- バグ報告

---

**変更履歴**

| 日付 | 内容 |
|------|------|
| 2026-01-08 | 初版作成。`logical_qubit_mapping` フィールドを追加 |
