export function generateSessionTitle(question: string) {
  const cleaned = question.replace(/\s+/g, ' ').trim();
  if (!cleaned) {
    return '新对话';
  }

  return cleaned.length > 16 ? `${cleaned.slice(0, 16)}…` : cleaned;
}

export function copyText(value: string) {
  return navigator.clipboard.writeText(value);
}

export function createId(prefix: string) {
  return `${prefix}_${Math.random().toString(36).slice(2, 10)}`;
}
