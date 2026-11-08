"use client";
import * as stylex from "@stylexjs/stylex";
import { AriaButton } from "../../ui/Button";
import { Tag, TagGroup, TagList } from "../../ui/Tag";
import { styles } from "./RemovableTags.styles";
export interface RemovableTag {
  id: string;
  label: string;
}
export function RemovableTags({
  label,
  items,
  onRemove,
  tone = "accent",
  removeLabel,
}: {
  label: string;
  items: readonly RemovableTag[];
  onRemove: (id: string) => void;
  tone?: "accent" | "positive";
  removeLabel: (label: string) => string;
}) {
  return (
    <TagGroup
      aria-label={label}
      onRemove={(keys) => {
        for (const key of keys) onRemove(String(key));
      }}
    >
      <TagList {...stylex.props(styles.tagList)}>
        {items.map((item) => (
          <Tag
            key={item.id}
            id={item.id}
            textValue={item.label}
            className={({ isFocusVisible }) =>
              stylex.props(
                styles.chip,
                tone === "positive" && styles.additionalChip,
                isFocusVisible && styles.chipFocused,
              ).className ?? ""
            }
          >
            <span title={item.label}>{item.label}</span>
            <AriaButton
              slot="remove"
              aria-label={removeLabel(item.label)}
              {...stylex.props(styles.chipRemoveBtn)}
            >
              ×
            </AriaButton>
          </Tag>
        ))}
      </TagList>
    </TagGroup>
  );
}
