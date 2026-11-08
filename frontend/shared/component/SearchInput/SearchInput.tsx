"use client";
import { SearchField } from "../../ui/SearchField";
export interface SearchInputProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  onSubmit?: () => void;
  disabled?: boolean;
  descriptionId?: string;
  placeholder?: string;
}
export function SearchInput({
  disabled,
  descriptionId,
  onSubmit,
  ...props
}: SearchInputProps) {
  return (
    <SearchField
      {...props}
      onSubmit={onSubmit ? () => onSubmit() : undefined}
      isDisabled={disabled}
      aria-describedby={descriptionId}
    />
  );
}
