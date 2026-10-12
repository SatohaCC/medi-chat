"use client";
import * as stylex from "@stylexjs/stylex";
import type { ReactNode } from "react";
import { Tabs as AriaTabs, Tab, TabList, TabPanel } from "react-aria-components";
import { styles } from "./Tabs.styles";
export interface TabsProps {
  value: string;
  onValueChange: (value: string) => void;
  label: string;
  items: { id: string; title: ReactNode; content: ReactNode }[];
}
export function Tabs({ value, onValueChange, label, items }: TabsProps) {
  return (
    <AriaTabs
      {...stylex.props(styles.root)}
      selectedKey={value}
      onSelectionChange={(key) => onValueChange(String(key))}
    >
      <TabList aria-label={label} {...stylex.props(styles.nav)}>
        {items.map((item) => (
          <Tab
            id={item.id}
            key={item.id}
            className={({ isSelected }) =>
              stylex.props(styles.item, styles.tab, isSelected && styles.active)
                .className ?? ""
            }
          >
            {item.title}
          </Tab>
        ))}
      </TabList>
      {items.map((item) => (
        <TabPanel id={item.id} key={item.id}>
          {item.content}
        </TabPanel>
      ))}
    </AriaTabs>
  );
}
