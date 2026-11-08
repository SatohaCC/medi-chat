"use client";
import type { ReactNode } from "react";
import { Switch } from "../../ui/Switch";
export function SwitchControl({
  children,
  selected,
  onChange,
  disabled,
}: {
  children: ReactNode;
  selected: boolean;
  onChange: (value: boolean) => void;
  disabled?: boolean;
}) {
  return (
    <Switch
      isSelected={selected}
      onChange={onChange}
      isDisabled={disabled}
      size="L"
      isEmphasized
    >
      {children}
    </Switch>
  );
}
