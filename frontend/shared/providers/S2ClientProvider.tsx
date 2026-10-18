"use client";

import "@react-spectrum/s2/page.css";
import { Provider } from "@react-spectrum/s2/Provider";
import type { ReactNode } from "react";

export function S2ClientProvider({ children }: { children: ReactNode }) {
  return (
    <Provider locale="ja-JP" colorScheme="light">
      {children}
    </Provider>
  );
}
