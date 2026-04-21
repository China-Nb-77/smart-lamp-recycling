export type AuthUser = {
  id: number;
  username: string;
  displayName?: string;
  realName?: string;
  role?: string;
};

const USER_TOKEN_KEY = 'ai-light.user.token';
const USER_REFRESH_TOKEN_KEY = 'ai-light.user.refresh-token';
const USER_PROFILE_KEY = 'ai-light.user.profile';
const ADMIN_TOKEN_KEY = 'ai-light.admin.token';
const ADMIN_PROFILE_KEY = 'ai-light.admin.profile';

export function getUserToken() {
  return window.localStorage.getItem(USER_TOKEN_KEY) || '';
}

export function getUserRefreshToken() {
  return window.localStorage.getItem(USER_REFRESH_TOKEN_KEY) || '';
}

export function getAdminToken() {
  return window.localStorage.getItem(ADMIN_TOKEN_KEY) || '';
}

export function setUserSession(token: string, refreshToken: string, user: AuthUser) {
  window.localStorage.setItem(USER_TOKEN_KEY, token);
  window.localStorage.setItem(USER_REFRESH_TOKEN_KEY, refreshToken);
  window.localStorage.setItem(USER_PROFILE_KEY, JSON.stringify(user));
}

export function setAdminSession(token: string, user: AuthUser) {
  window.localStorage.setItem(ADMIN_TOKEN_KEY, token);
  window.localStorage.setItem(ADMIN_PROFILE_KEY, JSON.stringify(user));
}

export function clearUserSession() {
  window.localStorage.removeItem(USER_TOKEN_KEY);
  window.localStorage.removeItem(USER_REFRESH_TOKEN_KEY);
  window.localStorage.removeItem(USER_PROFILE_KEY);
}

export function clearAdminSession() {
  window.localStorage.removeItem(ADMIN_TOKEN_KEY);
  window.localStorage.removeItem(ADMIN_PROFILE_KEY);
}

export function getStoredUser(): AuthUser | null {
  try {
    const raw = window.localStorage.getItem(USER_PROFILE_KEY);
    return raw ? (JSON.parse(raw) as AuthUser) : null;
  } catch {
    return null;
  }
}

export function getStoredAdmin(): AuthUser | null {
  try {
    const raw = window.localStorage.getItem(ADMIN_PROFILE_KEY);
    return raw ? (JSON.parse(raw) as AuthUser) : null;
  } catch {
    return null;
  }
}
