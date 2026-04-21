import type { ChatSession } from '../../../types/chat';
import { readJson, writeJson } from '../../../services/storage/local-store';
import { createId } from '../../../utils/text';

const SESSION_STORAGE_KEY = 'ai-light.chat.sessions';
const CURRENT_SESSION_STORAGE_KEY = 'ai-light.chat.current-session';

export function createEmptySession(): ChatSession {
  const now = new Date().toISOString();

  return {
    id: createId('session'),
    title: '新对话',
    created_at: now,
    updated_at: now,
    messages: [],
  };
}

export function loadSessions(): ChatSession[] {
  return readJson<ChatSession[]>(SESSION_STORAGE_KEY, []);
}

export function saveSessions(sessions: ChatSession[]) {
  writeJson(SESSION_STORAGE_KEY, sessions);
}

export function getCurrentSessionId() {
  return window.localStorage.getItem(CURRENT_SESSION_STORAGE_KEY) || '';
}

export function setCurrentSessionId(sessionId: string) {
  window.localStorage.setItem(CURRENT_SESSION_STORAGE_KEY, sessionId);
}

export function ensureSessionCollection() {
  const sessions = loadSessions();
  if (sessions.length > 0) {
    return sessions;
  }

  const initial = createEmptySession();
  saveSessions([initial]);
  setCurrentSessionId(initial.id);
  return [initial];
}

export function upsertSession(collection: ChatSession[], nextSession: ChatSession) {
  const next = collection.some((session) => session.id === nextSession.id)
    ? collection.map((session) => (session.id === nextSession.id ? nextSession : session))
    : [nextSession, ...collection];

  return next.sort((left, right) =>
    right.updated_at.localeCompare(left.updated_at),
  );
}

export function removeSession(collection: ChatSession[], sessionId: string) {
  const filtered = collection.filter((session) => session.id !== sessionId);
  return filtered.length > 0 ? filtered : [createEmptySession()];
}
