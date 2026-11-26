export type { Account, DocStatus, Document, Space } from "./types";
export { createAccount, login, logout, me } from "./auth";
export { createSpace, deleteSpace, listSpaces } from "./spaces";
export {
  deleteDocument,
  listDocuments,
  openOriginal,
  originalUrl,
  splitPageAnchor,
  uploadDocument,
} from "./documents";
