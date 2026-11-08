"use client";
import type { ReactNode } from "react";
import { Form as UIForm } from "../../ui/Form";
export function Form({
  children,
  onSubmit,
}: {
  children: ReactNode;
  onSubmit: (data: FormData) => void;
}) {
  return (
    <UIForm
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit(new FormData(event.currentTarget));
      }}
    >
      {children}
    </UIForm>
  );
}
