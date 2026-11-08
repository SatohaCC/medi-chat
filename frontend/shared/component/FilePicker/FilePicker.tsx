"use client";
import { SpectrumButton } from "../../ui/Button";
import { FileTrigger } from "../../ui/FileTrigger";
export function FilePicker({
  label,
  accept,
  disabled,
  onSelect,
}: {
  label: string;
  accept: string[];
  disabled?: boolean;
  onSelect: (file: File) => void;
}) {
  return (
    <FileTrigger
      acceptedFileTypes={accept}
      onSelect={(files) => {
        const file = files?.item(0);
        if (file) onSelect(file);
      }}
    >
      <SpectrumButton variant="secondary" isDisabled={disabled} aria-label={label}>
        {label}
      </SpectrumButton>
    </FileTrigger>
  );
}
