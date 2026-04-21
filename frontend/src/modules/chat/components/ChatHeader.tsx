import { useEffect, useRef, useState } from 'react';
import { Menu, MoreHorizontal } from 'lucide-react';

type ChatHeaderProps = {
  title: string;
  onOpenHistory: () => void;
  onNewChat: () => void;
  onOpenProfile: () => void;
  onOpenAdmin: () => void;
  onLogout: () => void;
};

export function ChatHeader({
  title,
  onOpenHistory,
  onNewChat,
  onOpenProfile,
  onOpenAdmin,
  onLogout,
}: ChatHeaderProps) {
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    function handleOutside(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setMenuOpen(false);
      }
    }

    function handleEscape(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        setMenuOpen(false);
      }
    }

    window.addEventListener('mousedown', handleOutside);
    window.addEventListener('keydown', handleEscape);
    return () => {
      window.removeEventListener('mousedown', handleOutside);
      window.removeEventListener('keydown', handleEscape);
    };
  }, []);

  return (
    <header className="chat-header">
      <button
        type="button"
        className="icon-button"
        aria-label="打开历史会话"
        onClick={onOpenHistory}
      >
        <Menu size={27} strokeWidth={2.3} />
      </button>

      <h1>{title}</h1>

      <div className="chat-header__menu" ref={menuRef}>
        <button
          type="button"
          className="icon-button"
          aria-label="打开用户菜单"
          onClick={() => setMenuOpen((open) => !open)}
        >
          <MoreHorizontal size={27} strokeWidth={2.1} />
        </button>

        {menuOpen ? (
          <div className="chat-header__dropdown" role="menu" aria-label="用户菜单">
            <button
              type="button"
              role="menuitem"
              onClick={() => {
                setMenuOpen(false);
                onOpenProfile();
              }}
            >
              个人中心
            </button>
            <button
              type="button"
              role="menuitem"
              onClick={() => {
                setMenuOpen(false);
                onOpenAdmin();
              }}
            >
              管理员端
            </button>
            <button
              type="button"
              role="menuitem"
              className="chat-header__danger"
              onClick={() => {
                setMenuOpen(false);
                onLogout();
              }}
            >
              退出登录
            </button>
            <button
              type="button"
              role="menuitem"
              onClick={() => {
                setMenuOpen(false);
                onNewChat();
              }}
            >
              新建对话
            </button>
          </div>
        ) : null}
      </div>
    </header>
  );
}
