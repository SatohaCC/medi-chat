"use client";
import * as stylex from "@stylexjs/stylex";
import { ChevronDown } from "lucide-react";
import {
  Select as AriaSelect,
  Button,
  ListBox,
  ListBoxItem,
  Popover,
  SelectValue,
} from "react-aria-components";
import { styles } from "./Select.styles";
export interface SelectOption {
  readonly value: string;
  readonly label: string;
}

export interface SelectProps {
  value: string;
  options: readonly SelectOption[];
  onValueChange: (value: string) => void;
  label: string;
  disabled?: boolean;
}
export function Select({
  value,
  options,
  onValueChange,
  label,
  disabled = false,
}: SelectProps) {
  return (
    <AriaSelect
      {...stylex.props(styles.root)}
      aria-label={label}
      value={value}
      onChange={(key) => {
        if (typeof key === "string") onValueChange(key);
      }}
      isDisabled={disabled}
    >
      <Button {...stylex.props(styles.trigger, disabled && styles.disabled)}>
        <SelectValue />
        <span {...stylex.props(styles.chevronWrapper)} aria-hidden="true">
          <ChevronDown size={13} strokeWidth={2.2} />
        </span>
      </Button>
      <Popover {...stylex.props(styles.popup)}>
        <ListBox {...stylex.props(styles.list)}>
          {options.map((option) => (
            <ListBoxItem
              id={option.value}
              key={option.value}
              textValue={option.label}
              className={({ isFocused }) =>
                stylex.props(styles.option, isFocused && styles.focused).className ?? ""
              }
            >
              {option.label}
            </ListBoxItem>
          ))}
        </ListBox>
      </Popover>
    </AriaSelect>
  );
}
