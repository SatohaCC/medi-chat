"use client";

import * as stylex from "@stylexjs/stylex";
import { useState } from "react";
import { Autocomplete } from "../../ui/Autocomplete";
import { SpectrumButton as Button } from "../../ui/Button";
import { Dialog, DialogTrigger } from "../../ui/Dialog";
import { ListBox, ListBoxItem } from "../../ui/ListBox";
import { Popover } from "../../ui/Popover";
import { SearchField } from "../../ui/SearchField";
import { styles } from "./SearchablePicker.styles";
export interface SearchableOption {
  id: string;
  label: string;
  description?: string;
}
export function SearchablePicker({
  items,
  query,
  onQueryChange,
  onSelect,
  buttonLabel,
  dialogLabel,
  searchLabel,
  searchAccessibleLabel,
  placeholder,
  closeLabel,
  closeText,
  listLabel,
  emptyText,
}: {
  items: SearchableOption[];
  query: string;
  onQueryChange: (query: string) => void;
  onSelect: (id: string) => void;
  buttonLabel: string;
  dialogLabel: string;
  searchLabel: string;
  searchAccessibleLabel: string;
  placeholder: string;
  closeLabel: string;
  closeText: string;
  listLabel: string;
  emptyText: string;
}) {
  const [open, setOpen] = useState(false);
  const setQuery = onQueryChange;
  return (
    <DialogTrigger
      isOpen={open}
      onOpenChange={(value) => {
        setOpen(value);
        setQuery("");
      }}
    >
      <Button variant="secondary" aria-label={buttonLabel}>
        {buttonLabel}
      </Button>
      <Popover placement="top start" {...stylex.props(styles.popoverMenu)}>
        <Dialog aria-label={dialogLabel} {...stylex.props(styles.pickerDialog)}>
          <Autocomplete inputValue={query} onInputChange={setQuery}>
            <div {...stylex.props(styles.popoverHeader)}>
              <SearchField
                autoFocus
                label={searchLabel}
                aria-label={searchAccessibleLabel}
                placeholder={placeholder}
              />
              <Button
                variant="secondary"
                aria-label={closeLabel}
                onPress={() => setOpen(false)}
              >
                {closeText}
              </Button>
            </div>
            <ListBox
              aria-label={listLabel}
              items={items}
              {...stylex.props(styles.popoverList)}
              onAction={(key) => {
                const item = items.find((item) => item.id === key);
                if (item) {
                  onSelect(item.id);
                  setOpen(false);
                  setQuery("");
                }
              }}
              renderEmptyState={() => (
                <p {...stylex.props(styles.popoverEmpty)}>{emptyText}</p>
              )}
            >
              {(item) => (
                <ListBoxItem
                  id={item.id}
                  textValue={`${item.label} ${item.description ?? ""}`}
                  className={({ isFocused }) =>
                    stylex.props(
                      styles.popoverItem,
                      isFocused && styles.popoverItemFocused,
                    ).className ?? ""
                  }
                >
                  <span {...stylex.props(styles.popoverItemName)}>{item.label}</span>
                  {item.description && (
                    <span {...stylex.props(styles.popoverItemGeneric)}>
                      ({item.description})
                    </span>
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
