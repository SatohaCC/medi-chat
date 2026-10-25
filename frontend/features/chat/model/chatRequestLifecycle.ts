import type { WsClientMessage, WsServerMessage } from "./chat";
import type { TransportSendResult } from "../api/chatWebSocket";
import type { PromptFieldValue } from "@react-spectrum/ai";
import type { SelectedMedicineItem } from "../../medicine-selection/model/promptSnapshot";

export interface RequestContext {
  promptSegments: PromptFieldValue["segments"];
  targets: readonly SelectedMedicineItem[];
  model: string;
}
export interface PendingRequest {
  payload: WsClientMessage;
  content: string;
  createdAt: number;
  context?: RequestContext;
}
export interface UnsentRequest extends PendingRequest {
  reason: "cancelled" | "expired" | "authentication";
}
export type SendResult =
  | { ok: true; disposition: "sent" | "queued"; requestId: string }
  | { ok: false; reason: "busy" | "queue_full" | "not_connected" | "uncertain" };
interface Callbacks {
  send: (payload: WsClientMessage) => TransportSendResult;
  start: (content: string, requestId: string) => void;
  event: (event: WsServerMessage) => void;
  abort?: (requestId: string) => boolean;
  ready?: () => boolean;
  canQueue?: () => boolean;
  now?: () => number;
  pending?: (pending: PendingRequest | null, unsent?: UnsentRequest) => void;
}

/** Synchronous request ownership shared by the hook and its model tests. */
export class ChatRequestLifecycle {
  activeId: string | null = null;
  stopping = false;
  pending: PendingRequest | null = null;
  private closed = false;
  private timer: ReturnType<typeof setTimeout> | undefined;
  private callbacks: Callbacks;
  constructor(callbacks: Callbacks) {
    this.callbacks = callbacks;
  }
  private now() {
    return this.callbacks.now?.() ?? Date.now();
  }
  send(payload: WsClientMessage, content: string, context?: RequestContext): SendResult {
    if (this.closed || this.callbacks.canQueue?.() === false)
      return { ok: false, reason: "not_connected" };
    if (this.activeId) return { ok: false, reason: "busy" };
    if (this.pending) return { ok: false, reason: "queue_full" };
    const snapshot = structuredClone({
      payload,
      content,
      context,
      createdAt: this.now(),
    });
    if (this.callbacks.ready?.() === false) return this.queue(snapshot);
    const result = this.attempt(snapshot);
    if (result === "not_open") return this.queue(snapshot);
    return result === "sent"
      ? { ok: true, disposition: "sent", requestId: payload.request_id }
      : { ok: false, reason: "uncertain" };
  }
  private queue(snapshot: PendingRequest): SendResult {
    this.pending = snapshot;
    const requestId = snapshot.payload.request_id;
    this.timer = setTimeout(
      () => {
        if (this.pending?.payload.request_id === requestId) this.invalidate("expired");
      },
      Math.max(0, 60000 - (this.now() - snapshot.createdAt)),
    );
    this.callbacks.pending?.(snapshot);
    return { ok: true, disposition: "queued", requestId };
  }
  private attempt(snapshot: PendingRequest): TransportSendResult {
    const id = snapshot.payload.request_id;
    this.activeId = id;
    const result = this.callbacks.send(snapshot.payload);
    if (result === "not_open") {
      this.activeId = null;
      return result;
    }
    this.callbacks.start(snapshot.content, id);
    if (result === "uncertain") {
      this.activeId = null;
      this.callbacks.event({ type: "aborted", request_id: id });
    }
    return result;
  }
  flush(): void {
    if (this.closed || !this.pending || this.activeId) return;
    if (this.now() - this.pending.createdAt >= 60000) {
      this.invalidate("expired");
      return;
    }
    if (this.callbacks.canQueue?.() === false) {
      this.invalidate("authentication");
      return;
    }
    if (this.callbacks.ready?.() === false) return;
    const snapshot = this.pending;
    this.pending = null;
    const result = this.attempt(snapshot);
    if (result === "not_open") {
      this.pending = snapshot;
      return;
    }
    clearTimeout(this.timer);
    this.callbacks.pending?.(null);
  }
  private invalidate(reason: UnsentRequest["reason"]): void {
    if (!this.pending) return;
    const snapshot = this.pending;
    this.pending = null;
    clearTimeout(this.timer);
    this.callbacks.pending?.(null, { ...snapshot, reason });
  }
  cancelPending(requestId: string): void {
    if (this.pending?.payload.request_id === requestId) this.invalidate("cancelled");
  }
  authenticationExpired(): void {
    this.disconnected();
    this.invalidate("authentication");
  }
  receive(event: WsServerMessage): void {
    if (
      !this.activeId ||
      !("request_id" in event) ||
      event.request_id !== this.activeId ||
      event.type === "control_error"
    )
      return;
    if (["text_done", "error", "aborted"].includes(event.type)) {
      this.activeId = null;
      this.stopping = false;
    }
    this.callbacks.event(event);
  }
  abort(): boolean {
    if (!this.activeId || this.stopping) return false;
    if (!this.callbacks.abort?.(this.activeId)) return false;
    this.stopping = true;
    return true;
  }
  disconnected(): void {
    this.activeId = null;
    this.stopping = false;
  }
  dispose(): void {
    this.closed = true;
    this.disconnected();
    this.pending = null;
    clearTimeout(this.timer);
  }
}
