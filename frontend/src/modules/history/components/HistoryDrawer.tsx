import { MoreHorizontal, Trash2 } from 'lucide-react';
import type { ChatSession } from '../../../types/chat';
import { groupTimeLabel } from '../../../utils/date';

type HistoryDrawerProps = {
  open: boolean;
  sessions: ChatSession[];
  currentSessionId: string;
  userLabel: string;
  onClose: () => void;
  onSelect: (sessionId: string) => void;
  onNewChat: () => void;
  onDelete: (sessionId: string) => void;
};

export function HistoryDrawer({
  open,
  sessions,
  currentSessionId,
  userLabel,
  onClose,
  onSelect,
  onNewChat,
  onDelete,
}: HistoryDrawerProps) {
  const groups = sessions.reduce<Record<string, ChatSession[]>>((bucket, session) => {
    const label = groupTimeLabel(session.updated_at);
    bucket[label] = bucket[label] || [];
    bucket[label].push(session);
    return bucket;
  }, {});

  const labels = ['今天', '昨天', '7天内', '30天内', '更早'].filter(
    (label) => groups[label]?.length,
  );

  return (
    <>
      <div
        className={`drawer-backdrop ${open ? 'drawer-backdrop--open' : ''}`}
        onClick={onClose}
      />
      <aside className={`history-drawer ${open ? 'history-drawer--open' : ''}`}>
        <div className="history-drawer__content">
          <button
            type="button"
            className="secondary-button history-drawer__new"
            onClick={onNewChat}
          >
            新建对话
          </button>
          <div className="history-drawer__groups">
            {labels.map((label) => (
              <section key={label}>
                <h2>{label}</h2>
                <ul>
                  {groups[label].map((session) => (
                    <li key={session.id}>
                      <button
                        type="button"
                        className={`history-session ${
                          session.id === currentSessionId ? 'history-session--active' : ''
                        }`}
                        onClick={() => onSelect(session.id)}
                      >
                        <span>{session.title}</span>
                      </button>
                      <button
                        type="button"
                        className="history-delete"
                        aria-label={`删除 ${session.title}`}
                        onClick={() => onDelete(session.id)}
                      >
                        <Trash2 size={16} />
                      </button>
                    </li>
                  ))}
                </ul>
              </section>
            ))}
          </div>
        </div>
        <footer className="history-drawer__footer">
          <div className="history-user">
            <div className="history-user__avatar" aria-hidden="true">
              <span />
            </div>
            <strong>{userLabel}</strong>
          </div>
          <button
            type="button"
            className="icon-button icon-button--small"
            aria-label="更多操作"
            title="后端暂无更多用户接口，保留占位"
            disabled
          >
            <MoreHorizontal size={20} />
          </button>
        </footer>
      </aside>
    </>
  );
}
