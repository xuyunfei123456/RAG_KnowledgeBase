import { awaitable, parse } from "./client";
import type { Conversation, ConversationDetail } from "./types";

export function listConversations(spaceId: string) {
  return parse<Conversation[]>(awaitable(`/api/spaces/${spaceId}/conversations`));
}

export function getConversation(spaceId: string, conversationId: string) {
  return parse<ConversationDetail>(
    awaitable(`/api/spaces/${spaceId}/conversations/${conversationId}`),
  );
}

function ask(spaceId: string, path: string, question: string) {
  return parse<ConversationDetail>(
    awaitable(`/api/spaces/${spaceId}/conversations${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    }),
  );
}

export function startConversation(spaceId: string, question: string) {
  return ask(spaceId, "", question);
}

export function addMessage(spaceId: string, conversationId: string, question: string) {
  return ask(spaceId, `/${conversationId}/messages`, question);
}
