import { ActionButton as Button } from "../../../../shared/component/ActionButton";
import type { PendingRequest, UnsentRequest } from "../../model/chatRequestLifecycle";
export interface ChatDeliveryStatusProps {
  pending: PendingRequest | null;
  unsent: UnsentRequest[];
  restoreChoice: UnsentRequest | null;
  onCancelPending: (id: string) => void;
  onEdit: (question: UnsentRequest) => void;
  onKeepDraft: () => void;
  onReplaceDraft: () => void;
}
export function ChatDeliveryStatus({
  pending,
  unsent,
  restoreChoice,
  onCancelPending,
  onEdit,
  onKeepDraft,
  onReplaceDraft,
}: ChatDeliveryStatusProps) {
  return (
    <>
      {pending && (
        <section aria-label="未送信の保留">
          <p role="status">未送信・接続待ちの保留: {pending.content}</p>
          <p>
            {pending.context?.targets.map((medicine) => medicine.name).join("、")} /{" "}
            {pending.context?.model}
          </p>
          <Button
            appearance="secondary"
            onActivate={() => onCancelPending(pending.payload.request_id)}
          >
            保留を取消
          </Button>
        </section>
      )}
      {unsent.map((question) => (
        <section key={question.payload.request_id} aria-label="未送信の質問">
          <p>
            {question.reason === "expired"
              ? "期限切れ"
              : question.reason === "cancelled"
                ? "取消"
                : "認証により取消"}
            : {question.content}
          </p>
          <p>
            {question.context?.targets.map((medicine) => medicine.name).join("、")} /{" "}
            {question.context?.model}
          </p>
          <Button appearance="secondary" onActivate={() => onEdit(question)}>
            再編集
          </Button>
        </section>
      ))}
      {restoreChoice && (
        <section aria-label="再編集の確認">
          <p>別の質問を編集中です。</p>
          <Button appearance="secondary" onActivate={onKeepDraft}>
            現在の入力を保持
          </Button>
          <Button appearance="secondary" onActivate={onReplaceDraft}>
            元の質問に置換
          </Button>
        </section>
      )}
    </>
  );
}
