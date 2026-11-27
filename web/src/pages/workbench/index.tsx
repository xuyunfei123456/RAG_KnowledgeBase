import { FormEvent, useEffect, useState } from "react";
import * as api from "../../api";
import type { Space } from "../../api";
import { AccountDrawer } from "./AccountDrawer";
import { Chat } from "./Chat";
import { Conversations } from "./Conversations";
import { Documents } from "./Documents";
import { Spaces } from "./Spaces";

export function Workbench({
  account,
  onLogout,
}: {
  account: api.Account;
  onLogout: () => void;
}) {
  const [spaces, setSpaces] = useState<Space[]>([]);
  const [current, setCurrent] = useState<Space | null>(null);
  const [spaceName, setSpaceName] = useState("");
  const [spaceError, setSpaceError] = useState("");
  const [showAccount, setShowAccount] = useState(false);
  const [creatingSpace, setCreatingSpace] = useState(false);
  const [deletingSpaceId, setDeletingSpaceId] = useState("");
  const [loggingOut, setLoggingOut] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [convStamp, setConvStamp] = useState(0);
  const [docStamp, setDocStamp] = useState(0);

  function selectSpace(space: Space | null) {
    setCurrent(space);
    setConversationId(null);
  }

  async function reload() {
    const list = await api.listSpaces();
    setSpaces(list);
    setCurrent((prev) => {
      const next = list.find((s) => s.id === prev?.id) ?? list[0] ?? null;
      if (next?.id !== prev?.id) setConversationId(null);
      return next;
    });
  }

  useEffect(() => {
    reload().catch((err) => setSpaceError(err instanceof Error ? err.message : "加载失败"));
  }, []);

  async function addSpace(e: FormEvent) {
    e.preventDefault();
    if (creatingSpace) return;
    const name = spaceName.trim();
    if (!name) return;
    setCreatingSpace(true);
    setSpaceError("");
    try {
      const space = await api.createSpace(name);
      setSpaceName("");
      setSpaces((xs) => [...xs, space]);
      selectSpace(space);
    } catch (err) {
      setSpaceError(err instanceof Error ? err.message : "创建失败");
    } finally {
      setCreatingSpace(false);
    }
  }

  async function onDeleteSpace(space: Space) {
    if (deletingSpaceId) return;
    if (!window.confirm("确定删除知识空间「" + space.name + "」？该空间下的文档也会被删掉。")) {
      return;
    }
    setDeletingSpaceId(space.id);
    setSpaceError("");
    try {
      await api.deleteSpace(space.id);
      const next = spaces.filter((s) => s.id !== space.id);
      setSpaces(next);
      if (current?.id === space.id) selectSpace(next[0] ?? null);
    } catch (err) {
      setSpaceError(err instanceof Error ? err.message : "删除失败");
    } finally {
      setDeletingSpaceId("");
    }
  }

  async function logout() {
    if (loggingOut) return;
    setLoggingOut(true);
    try {
      await api.logout();
      onLogout();
    } catch {
      setLoggingOut(false);
    }
  }

  return (
    <div className="desk">
      <header className="topbar">
        <span className="brand">知识库</span>
        <span className="top-right">
          <button type="button" className="ghost" onClick={() => setShowAccount((v) => !v)}>
            开通账号
          </button>
          <span className="who">{account.username}</span>
          <button type="button" className="ghost" disabled={loggingOut} onClick={logout}>
            {loggingOut ? "退出中" : "退出"}
          </button>
        </span>
      </header>
      <div className="cols">
        <Spaces
          spaces={spaces}
          current={current}
          spaceName={spaceName}
          error={spaceError}
          creating={creatingSpace}
          deletingId={deletingSpaceId}
          onNameChange={setSpaceName}
          onCreate={addSpace}
          onSelect={selectSpace}
          onDelete={onDeleteSpace}
        />
        <Conversations
          space={current}
          currentId={conversationId}
          stamp={convStamp}
          onSelect={setConversationId}
        />
        <Chat
          space={current}
          conversationId={conversationId}
          docStamp={docStamp}
          onConversationId={setConversationId}
          onListDirty={() => setConvStamp((n) => n + 1)}
        />
        <Documents space={current} onDocumentsChanged={() => setDocStamp((n) => n + 1)} />
      </div>
      {showAccount ? <AccountDrawer /> : null}
    </div>
  );
}
