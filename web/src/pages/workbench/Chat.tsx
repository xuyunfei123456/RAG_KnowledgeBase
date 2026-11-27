import { FormEvent, KeyboardEvent, useEffect, useRef, useState } from "react";
import * as api from "../../api";
import type { ConversationDetail, Source, Space } from "../../api";

export function Chat({
  space,
  conversationId,
  docStamp,
  onConversationId,
  onListDirty,
}: {
  space: Space | null;
  conversationId: string | null;
  docStamp: number;
  onConversationId: (id: string | null) => void;
  onListDirty: () => void;
}) {
  const [conversation, setConversation] = useState<ConversationDetail | null>(null);
  const [question, setQuestion] = useState("");
  const [asking, setAsking] = useState(false);
  const [error, setError] = useState("");
  const logRef = useRef<HTMLDivElement>(null);
  const gen = useRef(0);
  const loadedId = useRef<string | null>(null);
  const spaceIdRef = useRef(space?.id);
  spaceIdRef.current = space?.id;

  useEffect(() => {
    gen.current += 1;
    const token = gen.current;
    if (!space || !conversationId) {
      setQuestion("");
      setError("");
      setAsking(false);
      setConversation(null);
      loadedId.current = null;
      return;
    }
    if (loadedId.current !== conversationId) {
      setQuestion("");
      setError("");
      setAsking(false);
    }
    api
      .getConversation(space.id, conversationId)
      .then((detail) => {
        if (token !== gen.current) return;
        loadedId.current = detail.id;
        setConversation(detail);
      })
      .catch((err) => {
        if (token !== gen.current) return;
        loadedId.current = null;
        setConversation(null);
        setError(err instanceof Error ? err.message : "加载对话失败");
      });
  }, [space?.id, conversationId, docStamp]);

  useEffect(() => {
    const el = logRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [conversation?.messages, asking]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!space || asking) return;
    const text = question.trim();
    if (!text) return;
    const spaceId = space.id;
    const token = gen.current;
    setAsking(true);
    setError("");
    try {
      const next = conversation
        ? await api.addMessage(spaceId, conversation.id, text)
        : await api.startConversation(spaceId, text);
      if (token !== gen.current || spaceIdRef.current !== spaceId) return;
      loadedId.current = next.id;
      setConversation(next);
      setQuestion("");
      onConversationId(next.id);
      onListDirty();
    } catch (err) {
      if (token !== gen.current || spaceIdRef.current !== spaceId) return;
      setError(err instanceof Error ? err.message : "提问失败");
    } finally {
      if (token === gen.current) setAsking(false);
    }
  }

  function onKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      e.currentTarget.form?.requestSubmit();
    }
  }

  function onSource(src: Source) {
    if (!space || src.deleted || !src.doc_id) return;
    api.openOriginal(space.id, src.doc_id, src.page ?? undefined);
  }

  return (
    <main className="col main">
      <div className="col-h">
        <span>{space ? space.name : "问答"}</span>
        {conversation ? (
          <button
            type="button"
            className="ghost"
            disabled={asking}
            onClick={() => onConversationId(null)}
          >
            新对话
          </button>
        ) : null}
      </div>
      {space ? (
        <>
          <div className="chat-log" ref={logRef}>
            {conversation
              ? conversation.messages.map((m) => (
                  <div key={m.id} className={"chat-msg " + m.role}>
                    <div className="chat-role">{m.role === "user" ? "问" : "答"}</div>
                    <div className="chat-body">{m.content}</div>
                    {m.role === "assistant" && m.sources && m.sources.length > 0 ? (
                      <ul className="chat-sources">
                        {m.sources.map((src, i) => (
                          <li key={m.id + "-" + i}>
                            {src.doc_id && !src.deleted ? (
                              <button type="button" className="source" onClick={() => onSource(src)}>
                                <SourceLabel src={src} />
                              </button>
                            ) : (
                              <div className="source">
                                <SourceLabel src={src} />
                              </div>
                            )}
                          </li>
                        ))}
                      </ul>
                    ) : null}
                  </div>
                ))
              : asking
                ? null
                : (
                <p className="empty">在当前空间提问，只根据这个空间的文档作答</p>
              )}
            {asking ? <p className="meta">生成中</p> : null}
          </div>
          {error ? <p className="error chat-err">{error}</p> : null}
          <form className="chat-ask" onSubmit={onSubmit}>
            <textarea
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={onKeyDown}
              placeholder="输入问题"
              maxLength={4000}
              disabled={asking}
              rows={2}
            />
            <button type="submit" className="primary" disabled={asking || !question.trim()}>
              {asking ? "生成中" : conversation ? "追问" : "提问"}
            </button>
          </form>
        </>
      ) : (
        <p className="empty">先创建一个知识空间</p>
      )}
    </main>
  );
}

function SourceLabel({ src }: { src: Source }) {
  const title = src.page && src.page > 0 ? src.filename + " 第" + src.page + "页" : src.filename;
  return (
    <>
      <div className="source-name">{src.deleted ? "原文已删除" : title}</div>
      {src.deleted ? <div className="source-gone">{title}</div> : null}
      <div className="source-snip">{src.snippet}</div>
    </>
  );
}
