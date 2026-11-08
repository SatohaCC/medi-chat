import * as stylex from "@stylexjs/stylex";
import { useState } from "react";
import { ActionButton as Button } from "../../../../shared/component/ActionButton";
import type { JevResponseData } from "../../model/jev";
import { styles } from "./JevResponseInspector.styles";

function CopyJsonButton({ data }: { data: unknown }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(JSON.stringify(data, null, 2));
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // ignore
    }
  };

  return (
    <Button
      appearance="compact"
      tone={copied ? "positive" : "neutral"}
      onActivate={handleCopy}
    >
      {copied ? "✓ コピー完了" : "JSONをコピー"}
    </Button>
  );
}

export function JevRawData({ response }: { response: JevResponseData }) {
  return (
    <div {...stylex.props(styles.rawContainer)}>
      <div {...stylex.props(styles.rawHeader)}>
        <span>判定APIの詳細データ (JSON)</span>
        <CopyJsonButton data={response} />
      </div>
      <pre {...stylex.props(styles.rawCode)}>
        <code>{JSON.stringify(response, null, 2)}</code>
      </pre>
    </div>
  );
}
