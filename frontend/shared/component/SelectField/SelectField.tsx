"use client";
import { Picker, PickerItem } from "../../ui/Picker";
export interface SelectOption {
  value: string;
  label: string;
}
export function SelectField({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: readonly SelectOption[];
}) {
  return (
    <Picker
      aria-label={label}
      value={value}
      onChange={(key) => {
        if (typeof key === "string") onChange(key);
      }}
    >
      {options.map((option) => (
        <PickerItem key={option.value} id={option.value}>
          {option.label}
        </PickerItem>
      ))}
    </Picker>
  );
}
