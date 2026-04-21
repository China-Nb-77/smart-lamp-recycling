const oneDay = 1000 * 60 * 60 * 24;

export function formatTimeLabel(value: string) {
  try {
    return new Intl.DateTimeFormat('zh-CN', {
      month: 'numeric',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }).format(new Date(value));
  } catch {
    return value;
  }
}

export function groupTimeLabel(value: string) {
  const updated = new Date(value).getTime();
  const now = Date.now();
  const diff = now - updated;

  if (diff < oneDay && new Date(value).getDate() === new Date().getDate()) {
    return '今天';
  }

  if (diff < oneDay * 2) {
    return '昨天';
  }

  if (diff < oneDay * 7) {
    return '7天内';
  }

  if (diff < oneDay * 30) {
    return '30天内';
  }

  return '更早';
}

export function formatRelativeDate(value: string) {
  try {
    return new Intl.DateTimeFormat('zh-CN', {
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }).format(new Date(value));
  } catch {
    return value;
  }
}
