export type Account = { id: string; username: string };
export type Space = { id: string; name: string; lightrag_workspace: string };
export type DocStatus = "processing" | "ready" | "failed";
export type Document = {
  id: string;
  filename: string;
  kind: string;
  status: DocStatus;
  error_msg: string | null;
  created_at: string;
};
