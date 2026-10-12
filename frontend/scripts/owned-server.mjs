import { execFileSync } from "node:child_process";
import { createServer } from "node:net";

export async function ensurePortAvailable(port) {
  const probe = createServer();
  await new Promise((done, reject) => {
    probe.once("error", () =>
      reject(
        new Error(`Dedicated port ${port} is occupied; existing server is unchanged`),
      ),
    );
    probe.listen(port, "127.0.0.1", () => probe.close(done));
  });
}

// Call only after the test-owned child has exited. TIME_WAIT is not a server.
export async function ensureOwnedRestartPortAvailable(
  port,
  observeListeners = async (value) => {
    if (process.platform !== "win32") {
      await ensurePortAvailable(value);
      return false;
    }
    if (!Number.isSafeInteger(value) || value < 1 || value > 65535)
      throw new Error("Invalid dedicated port");
    const output = execFileSync(
      "powershell.exe",
      [
        "-NoProfile",
        "-NonInteractive",
        "-Command",
        `$ErrorActionPreference='Stop'; $connections = @(Get-NetTCPConnection -State Listen -LocalPort ${value} -ErrorAction SilentlyContinue); if ($connections.Count -gt 0) { 'occupied' } else { 'available' }`,
      ],
      { encoding: "utf8", timeout: 10000 },
    );
    if (!["occupied", "available"].includes(output.trim()))
      throw new Error("Cannot verify dedicated restart port");
    return output.trim() === "occupied";
  },
) {
  if (await observeListeners(port))
    throw new Error(`Dedicated port ${port} is occupied; existing server is unchanged`);
}
