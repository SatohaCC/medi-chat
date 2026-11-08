"use client";
import { ChatHeader } from "../ChatHeader";
import { ChatScreenView } from "./ChatScreenView";
import { useChatScreen } from "./useChatScreen";
export function ChatScreen() {
  const { header, ...screen } = useChatScreen();
  return <ChatScreenView {...screen} header={<ChatHeader {...header} />} />;
}
