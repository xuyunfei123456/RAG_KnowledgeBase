import { useEffect, useState } from "react";
import * as api from "../../api";
import type { Conversation, Space } from "../../api";

export function Conversations({
  space,
  currentId,
  stamp,
  onSelect,
}: {
  space: Space | null;
  currentId: string | null;
  stamp: number;
  onSelect: (id: string) => void;
}) {
  const [items, setItems] = useState<Conversation[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!space) {
      setItems([]);
      setError("");
      return;
    }
    let cancelled = false;
    const spaceId = space.id;
    setError("");
    api
      .listConversations(spaceId)
      .then((list) => {
        if (!cancelled) setItems(list);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : "加载对话失败");
      });
    return () => {
      cancelled = true;
    };
  }, [space?.id, stamp]);

  return (
    <aside className="col">
      <div className="col-h">对话</div>
      {space ? (
        <>
          {error ? <p className="error space-err">{error}</p> : null}
          <ul className="list conv-list">
            {items.map((c) => (
              <li key={c.id}>
                <button
                  type="button"
                  className={c.id === currentId ? "row active conv-row" : "row conv-row"}
                  onClick={() => onSelect(c.id)}
                >
                  <span className="conv-title">{c.title}</span>
                </button>
              </li>
            ))}
          </ul>
          {items.length === 0 ? <p className="empty">还没有对话</p> : null}
        </>
      ) : (
        <p className="empty">先创建一个知识空间</p>
      )}
    </aside>
  );
}
