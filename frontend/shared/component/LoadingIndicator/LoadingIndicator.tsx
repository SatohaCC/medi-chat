"use client";
import { aiLogo, PixelLoader } from "../../ui/Loader";
export function LoadingIndicator({
  size = 28,
  color,
}: {
  size?: number;
  color?: string;
}) {
  return <PixelLoader size={size} isPlaying icon={aiLogo} color={color} />;
}
