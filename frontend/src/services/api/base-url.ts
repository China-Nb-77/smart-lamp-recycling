function normalizeBaseUrl(rawValue: string | undefined, fallback: string) {
  const value = String(rawValue || fallback).trim();
  if (!value) {
    return fallback;
  }
  if (value === '/') {
    return '';
  }
  return value.endsWith('/') ? value.slice(0, -1) : value;
}

export function resolveRequestUrl(baseUrl: string, path: string) {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  if (!baseUrl) {
    return normalizedPath;
  }
  return `${baseUrl}${normalizedPath}`;
}

// 强制使用公网 IP 作为默认值
const configuredApiBaseUrl = normalizeBaseUrl(import.meta.env.VITE_API_BASE_URL, 'http://114.215.177.52:8000');

export const apiBaseUrl = configuredApiBaseUrl;
export const legacyApiBaseUrl = normalizeBaseUrl(
  import.meta.env.VITE_LEGACY_API_BASE_URL,
  configuredApiBaseUrl || '/api',
);
export const visionBaseUrl = normalizeBaseUrl(
  import.meta.env.VITE_VISION_API_BASE_URL,
  'http://114.215.177.52:8000',
);
export const paymentBaseUrl = normalizeBaseUrl(
  import.meta.env.VITE_PAYMENT_API_BASE_URL,
  'http://114.215.177.52:8000',
);
