import { execFileSync } from "node:child_process";
import { createServer } from "node:net";

export function hasPortListener(output, port) {
  return output.split(/\r?\n/).some((line) => {
    const fields = line.trim().split(/\s+/);
    return (
      fields[0] === "TCP" && fields[1]?.endsWith(`:${port}`) && fields[3] === "LISTENING"
    );
  });
}

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
    const output = execFileSync("netstat.exe", ["-ano", "-p", "tcp"], {
      encoding: "utf8",
      timeout: 10000,
    });
    return hasPortListener(output, value);
  },
) {
  if (await observeListeners(port))
    throw new Error(`Dedicated port ${port} is occupied; existing server is unchanged`);
}
