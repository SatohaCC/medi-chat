export interface MedicineOption {
  generic_name: string;
  brand_names: string[];
  yj_codes: string[];
  document_ids: string[];
  matched_aliases: string[];
}

export interface CustomMedicine {
  name: string;
  yj_code: string;
}

export type MedicineCatalogStatus = "loading" | "ready" | "error";
