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

export type Source = {
  filename: string;
  snippet: string;
  doc_id: string | null;
  page: number | null;
  deleted: boolean;
};

export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources: Source[] | null;
  created_at: string;
};

export type Conversation = {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
};

export type ConversationDetail = Conversation & {
  messages: ChatMessage[];
};
