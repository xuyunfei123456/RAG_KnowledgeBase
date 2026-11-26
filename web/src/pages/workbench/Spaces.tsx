import { FormEvent } from "react";
import type { Space } from "../../api";

export function Spaces({
  spaces,
  current,
  spaceName,
  error,
  creating,
  deletingId,
  onNameChange,
  onCreate,
  onSelect,
  onDelete,
}: {
  spaces: Space[];
  current: Space | null;
  spaceName: string;
  error: string;
  creating: boolean;
  deletingId: string;
  onNameChange: (name: string) => void;
  onCreate: (e: FormEvent) => void;
  onSelect: (space: Space) => void;
  onDelete: (space: Space) => void;
}) {
  return (
    <aside className="col space-col">
      <div className="col-h">知识空间</div>
      <form className="inline" onSubmit={onCreate}>
        <input
          value={spaceName}
          onChange={(e) => onNameChange(e.target.value)}
          placeholder="新空间名称"
          disabled={creating}
        />
        <button type="submit" className="primary" disabled={creating}>
          {creating ? "创建中" : "创建"}
        </button>
      </form>
      {error ? <p className="error space-err">{error}</p> : null}
      <ul className="list">
        {spaces.map((s) => (
          <li key={s.id} className="space-item">
            <button
              type="button"
              className={s.id === current?.id ? "row active" : "row"}
              onClick={() => onSelect(s)}
            >
              {s.name}
            </button>
            <button
              type="button"
              className="ghost"
              disabled={deletingId === s.id}
              onClick={() => onDelete(s)}
            >
              {deletingId === s.id ? "删除中" : "删除"}
            </button>
          </li>
        ))}
      </ul>
      {spaces.length === 0 ? <p className="empty">还没有知识空间</p> : null}
    </aside>
  );
}
