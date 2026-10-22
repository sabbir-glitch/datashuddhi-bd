export const REPO_URL = "https://github.com/sabbir-glitch/datashuddhi-bd";
export const LIMITATIONS_DOC_URL = `${REPO_URL}/blob/main/docs/data-detection-limitations.md`;
export const RESPONSIBLE_USE_DOC_URL = `${REPO_URL}/blob/main/docs/responsible-use.md`;
export const THREAT_MODEL_DOC_URL = `${REPO_URL}/blob/main/docs/threat-model.md`;

/** In-page sections of the landing page, in page order. `label` is the header link text. */
export const SECTIONS = [
  { id: "overview", label: "Overview" },
  { id: "how-it-works", label: "How it works" },
  { id: "detection-scope", label: "Detection scope" },
  { id: "privacy", label: "Privacy" },
] as const;
