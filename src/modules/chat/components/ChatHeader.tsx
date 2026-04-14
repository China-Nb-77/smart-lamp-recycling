import { Menu, PlusSquare } from 'lucide-react';

type ChatHeaderProps = {
  title: string;
  onOpenHistory: () => void;
  onNewChat: () => void;
};

export function ChatHeader({
  title,
  onOpenHistory,
  onNewChat,
}: ChatHeaderProps) {
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
      <button
        type="button"
        className="icon-button"
        aria-label="新建对话"
        onClick={onNewChat}
      >
        <PlusSquare size={27} strokeWidth={2.1} />
      </button>
    </header>
  );
}
