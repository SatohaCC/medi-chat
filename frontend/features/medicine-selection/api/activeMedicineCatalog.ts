import type { MedicineOption } from "../model/medicine";
import type { MedicineEntry } from "../model/medicineAutocomplete";

export interface ActiveMedicineSnapshot {
  generation_id: string | null;
  groups: MedicineOption[];
  items: MedicineEntry[];
  status: "loading" | "ready" | "error";
}
export class ActiveMedicineCatalog {
  private latestRequest = 0;
  private current: ActiveMedicineSnapshot = {
    generation_id: null,
    groups: [],
    items: [],
    status: "loading",
  };
  private listeners = new Set<() => void>();
  private fetcher: typeof fetch;
  private base: string;
  constructor(fetcher: typeof fetch, base = "") {
    this.fetcher = fetcher;
    this.base = base;
  }
  get snapshot() {
    return this.current;
  }
  subscribe = (listener: () => void) => {
    this.listeners.add(listener);
    return () => {
      this.listeners.delete(listener);
    };
  };
  private publish(value: ActiveMedicineSnapshot) {
    this.current = value;
    for (const listener of this.listeners) listener();
  }
  async refresh(): Promise<void> {
    const request = ++this.latestRequest;
    try {
      for (let attempt = 0; attempt < 3; attempt++) {
        const [groupResponse, itemResponse] = await Promise.all([
          this.fetcher(`${this.base}/api/medicines`, { cache: "no-store" }),
          this.fetcher(`${this.base}/api/medicines/autocomplete`, { cache: "no-store" }),
        ]);
        if (!groupResponse.ok || !itemResponse.ok)
          throw new Error("Medicine catalogue unavailable");
        const group = (await groupResponse.json()) as {
          generation_id: string;
          items: MedicineOption[];
        };
        const compact = (await itemResponse.json()) as {
          generation_id: string;
          items: MedicineEntry[];
        };
        if (request !== this.latestRequest) return;
        if (!group.generation_id || group.generation_id !== compact.generation_id)
          continue;
        this.publish({
          generation_id: group.generation_id,
          groups: group.items,
          items: compact.items,
          status: "ready",
        });
        return;
      }
      throw new Error("Medicine generations changed during refresh");
    } catch {
      if (request === this.latestRequest)
        this.publish({ ...this.current, status: "error" });
    }
  }
}
