import type { MedicineEntry } from "./medicineAutocomplete";

export interface MedicinePickerOption {
  id: string;
  label: string;
  description: string;
  entry: MedicineEntry;
}

/**
 * 医薬品の候補をピッカーの選択肢へ変換する。
 *
 * YJコードは先発・後発などの製品間で重複しうるため、選択肢のIDには
 * YJコード・製品名・位置を含める。YJコードだけをIDにすると候補一覧の
 * 収集キーが衝突し、ピッカーが候補を描画できなくなる。
 */
export function toMedicinePickerOptions(
  entries: readonly MedicineEntry[],
): MedicinePickerOption[] {
  return entries.map((entry, index) => ({
    id: `${entry.y}-${entry.n}-${index}`,
    label: entry.n,
    description: entry.g,
    entry,
  }));
}
