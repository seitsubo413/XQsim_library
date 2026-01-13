/**
 * XQsim Patch Trace API TypeScript型定義
 * 
 * 使用方法:
 * このファイルをフロントエンドプロジェクトにコピーして使用してください。
 * 
 * @version 0.3.0
 * @date 2025-01-06
 */

// ============================================================================
// API Request/Response Types
// ============================================================================

/**
 * GET /health レスポンス
 */
export interface HealthResponse {
  status: "ok";
  trace_in_progress: boolean;
  limits: {
    max_qasm_size_bytes: number;
    max_qubits: number;
    max_depth: number;
    max_instructions: number;
    trace_timeout_seconds: number;
  };
}

/**
 * POST /trace リクエスト
 */
export interface TraceRequest {
  /** OpenQASM 2.0形式の量子回路 (必須) */
  qasm: string;
  /** 設定名 (デフォルト: "example_cmos_d5") */
  config?: string;
  /** デバッグ用中間ファイル保持 (デフォルト: false) */
  keep_artifacts?: boolean;
  /** 詳細ログ出力 (デフォルト: false) */
  debug_logging?: boolean;
}

/**
 * POST /trace 成功レスポンス
 */
export interface TraceResponse {
  result: TraceResult;
}

/**
 * エラーレスポンス
 */
export interface ErrorResponse {
  detail: string;
}

// ============================================================================
// Result Structure
// ============================================================================

/**
 * トレース結果のメイン構造
 */
export interface TraceResult {
  /** シミュレーションのメタ情報 */
  meta: MetaInfo;
  /** 入力されたQASMの情報 */
  input: InputInfo;
  /** コンパイル結果 */
  compiled: CompiledInfo;
  /** パッチ情報 (⭐ 可視化で使用するメインデータ) */
  patch: PatchInfo;
}

/**
 * メタ情報
 */
export interface MetaInfo {
  /** API出力バージョン */
  version: number;
  /** 使用した設定名 */
  config: string;
  /** ブロックタイプ (通常 "Distillation") */
  block_type: string;
  /** 誤り訂正符号の距離 */
  code_distance: number;
  /** パッチグリッドのサイズ */
  patch_grid: {
    rows: number;
    cols: number;
  };
  /** 総パッチ数 (rows × cols) */
  num_patches: number;
  /** シミュレーション総サイクル数 */
  total_cycles: number;
  /** 実行時間（秒） */
  elapsed_seconds: number;
  /** 終了理由 */
  termination_reason: "normal" | "timeout" | "error";
  /** 強制終了メッセージ */
  forced_terminations: string[];
  /** 安定性チェック失敗メッセージ */
  stability_check_failures: string[];
  /** 警告メッセージ */
  warnings: string[];
}

/**
 * 入力情報
 */
export interface InputInfo {
  /** 元のQASM文字列 */
  qasm: string;
  /** 元の量子ビット数 */
  num_qasm_qubits: number;
  /** コンパイル時の量子ビット数（パディング後） */
  num_compile_qubits: number;
  /** パディングが適用されたか */
  padding_applied: boolean;
}

/**
 * コンパイル結果
 */
export interface CompiledInfo {
  /** Clifford+T分解後のQASM */
  clifford_t_qasm: string;
  /** パディング後のQASM */
  clifford_t_qasm_padded: string;
  /** QISA命令列（表面符号用アセンブリ） */
  qisa: string[];
  /** 生成されたバイナリ名 */
  qbin_name: string;
}

// ============================================================================
// Patch Types (⭐ 可視化で使用するメインデータ)
// ============================================================================

/**
 * パッチ情報
 */
export interface PatchInfo {
  /** 初期状態のパッチ配列 */
  initial: Patch[];
  /** 状態変化イベント配列 */
  events: PatchEvent[];
}

/**
 * パッチタイプ
 * 
 * | 値    | 説明             | 推奨色     |
 * |-------|------------------|------------|
 * | "zt"  | Z-type top       | 青系       |
 * | "zb"  | Z-type bottom    | 青系（暗め）|
 * | "mt"  | Merge top        | 緑系       |
 * | "mb"  | Merge bottom     | 緑系（暗め）|
 * | "m"   | Merge            | 緑系       |
 * | "x"   | X-type           | 赤系       |
 * | "awe" | Ancilla west-east| 黄系       |
 * | "i"   | Idle（未使用）    | グレー     |
 */
export type PatchType = "zt" | "zb" | "mt" | "mb" | "m" | "x" | "awe" | "i";

/**
 * 境界条件タイプ
 * 
 * | 値   | 説明           | 推奨表現    |
 * |------|----------------|-------------|
 * | "i"  | Idle（境界なし）| 点線 or 非表示 |
 * | "x"  | X境界          | 赤線        |
 * | "z"  | Z境界          | 青線        |
 * | "pp" | Pauli product  | 紫線        |
 * | "c"  | Corner         | 黒点        |
 * | "ze" | Z endpoint     | 青マーカー  |
 */
export type BoundaryType = "i" | "x" | "z" | "pp" | "c" | "ze";

/**
 * パッチオブジェクト
 */
export interface Patch {
  /** パッチインデックス（0から連番） */
  pchidx: number;
  /** グリッド上の行位置（0始まり） */
  row: number;
  /** グリッド上の列位置（0始まり） */
  col: number;
  /** パッチタイプ */
  pchtype: PatchType;
  /** マージ情報 */
  merged: {
    /** マージされたレジスタID */
    reg: number;
    /** マージされたメモリID */
    mem: number;
  };
  /** 4辺の境界条件 */
  facebd: {
    /** 西（左） */
    w: BoundaryType;
    /** 北（上） */
    n: BoundaryType;
    /** 東（右） */
    e: BoundaryType;
    /** 南（下） */
    s: BoundaryType;
  };
  /** 4角の境界条件 */
  cornerbd: {
    /** 北西（左上） */
    nw: BoundaryType;
    /** 北東（右上） */
    ne: BoundaryType;
    /** 南西（左下） */
    sw: BoundaryType;
    /** 南東（右下） */
    se: BoundaryType;
  };
}

/**
 * パッチ状態変化イベント
 */
export interface PatchEvent {
  /** イベント連番（0始まり） */
  seq: number;
  /** 発生サイクル番号 */
  cycle: number;
  /** 対応するQISA命令インデックス */
  qisa_idx: number;
  /** 命令名 (例: "MERGE_INFO", "SPLIT_INFO") */
  inst: string;
  /** 変化したパッチの新状態（差分のみ） */
  patch_delta: Patch[];
}

// ============================================================================
// Utility Types
// ============================================================================

/**
 * パッチタイプごとの推奨カラー
 */
export const PATCH_TYPE_COLORS: Record<PatchType, string> = {
  zt: "#3B82F6",   // blue-500
  zb: "#1E40AF",   // blue-800
  mt: "#22C55E",   // green-500
  mb: "#166534",   // green-800
  m: "#16A34A",    // green-600
  x: "#EF4444",    // red-500
  awe: "#EAB308",  // yellow-500
  i: "#9CA3AF",    // gray-400
};

/**
 * 境界条件ごとの推奨カラー
 */
export const BOUNDARY_TYPE_COLORS: Record<BoundaryType, string> = {
  i: "transparent",
  x: "#EF4444",    // red-500
  z: "#3B82F6",    // blue-500
  pp: "#A855F7",   // purple-500
  c: "#000000",    // black
  ze: "#1D4ED8",   // blue-700
};

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * 指定サイクル時点でのパッチ状態を取得
 * 
 * @param result トレース結果
 * @param targetCycle 取得したいサイクル番号
 * @returns そのサイクル時点でのパッチ配列
 */
export function getPatchStateAtCycle(result: TraceResult, targetCycle: number): Patch[] {
  // 初期状態をディープコピー
  const patches = structuredClone(result.patch.initial);
  
  // targetCycle以下のイベントを順に適用
  for (const event of result.patch.events) {
    if (event.cycle > targetCycle) break;
    
    for (const delta of event.patch_delta) {
      const idx = patches.findIndex(p => p.pchidx === delta.pchidx);
      if (idx !== -1) {
        patches[idx] = delta;
      }
    }
  }
  
  return patches;
}

/**
 * パッチインデックスから行・列位置を取得
 * 
 * @param pchidx パッチインデックス
 * @param cols 列数
 * @returns { row, col }
 */
export function getPositionFromIndex(pchidx: number, cols: number): { row: number; col: number } {
  return {
    row: Math.floor(pchidx / cols),
    col: pchidx % cols,
  };
}

/**
 * 全イベントのサイクル番号リストを取得（タイムライン用）
 * 
 * @param result トレース結果
 * @returns サイクル番号の配列（0, イベントサイクル, 最終サイクル）
 */
export function getTimelinePoints(result: TraceResult): number[] {
  const points = [0];
  for (const event of result.patch.events) {
    points.push(event.cycle);
  }
  points.push(result.meta.total_cycles);
  return [...new Set(points)].sort((a, b) => a - b);
}

