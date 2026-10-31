"use client";

import { Button } from "@react-spectrum/s2/Button";
import { SearchField } from "@react-spectrum/s2/SearchField";
import * as stylex from "@stylexjs/stylex";
import { useMemo, useState } from "react";
import {
  Autocomplete,
  Dialog,
  DialogTrigger,
  ListBox,
  ListBoxItem,
  Popover,
} from "react-aria-components";
import type { MedicineEntry } from "../model/medicineAutocomplete";
import type { SelectedMedicineItem } from "../model/promptSnapshot";
import { styles } from "./MedicinePromptDock.styles";

export function MedicinePicker({
  entries,
  selected,
  onSelect,
}: {
  entries: MedicineEntry[];
  selected: SelectedMedicineItem[];
  onSelect: (medicine: SelectedMedicineItem) => void;
}) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const candidates = useMemo(() => {
    const selectedCodes = new Set(selected.map((medicine) => medicine.yj_code));
    const q = query.trim().toLowerCase();
    return entries
      .filter(
        (m) =>
          m.y &&
          !selectedCodes.has(m.y) &&
          (!q ||
            m.n.toLowerCase().includes(q) ||
            m.k?.toLowerCase().includes(q) ||
            m.h?.toLowerCase().includes(q) ||
            m.y.includes(q)),
      )
      .slice(0, q ? 20 : 15);
  }, [entries, selected, query]);
  return (
    <DialogTrigger
      isOpen={open}
      onOpenChange={(value) => {
        setOpen(value);
        setQuery("");
      }}
    >
      <Button variant="secondary" aria-label="処方薬を追加">
        処方薬を追加
      </Button>
      <Popover placement="top start" {...stylex.props(styles.popoverMenu)}>
        <Dialog aria-label="処方薬を選択" {...stylex.props(styles.pickerDialog)}>
          <Autocomplete inputValue={query} onInputChange={setQuery}>
            <div {...stylex.props(styles.popoverHeader)}>
              <SearchField
                autoFocus
                aria-label="処方薬検索"
                placeholder="薬名・YJコードで検索"
              />
              <Button
                variant="secondary"
                aria-label="検索を閉じる"
                onPress={() => setOpen(false)}
              >
                閉じる
              </Button>
            </div>
            <ListBox
              aria-label="処方薬の候補"
              items={candidates}
              {...stylex.props(styles.popoverList)}
              onAction={(key) => {
                const medicine = candidates.find((m) => m.y === key);
                if (medicine) {
                  onSelect({ yj_code: medicine.y, name: medicine.n });
                  setOpen(false);
                  setQuery("");
                }
              }}
              renderEmptyState={() => (
                <p {...stylex.props(styles.popoverEmpty)}>候補が見つかりません</p>
              )}
            >
              {(item) => (
                <ListBoxItem
                  id={item.y}
                  textValue={`${item.n} ${item.g ?? ""}`}
                  className={({ isFocused }) =>
                    stylex.props(
                      styles.popoverItem,
                      isFocused && styles.popoverItemFocused,
                    ).className ?? ""
                  }
                >
                  <span {...stylex.props(styles.popoverItemName)}>{item.n}</span>
                  {item.g && (
                    <span {...stylex.props(styles.popoverItemGeneric)}>({item.g})</span>
                  )}
                </ListBoxItem>
              )}
            </ListBox>
          </Autocomplete>
        </Dialog>
      </Popover>
    </DialogTrigger>
  );
}
