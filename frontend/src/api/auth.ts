import request from './request';
import type { AuthUser } from '../auth/session';
import { getStoredUser } from '../auth/session';

export type RegisterPayload = {
  username: string;
  password: string;
  displayName?: string;
  phone?: string;
  email?: string;
};

export type LoginPayload = {
  account: string;
  password: string;
};

type AuthResponse = {
  token: string;
  refresh_token: string;
  user: AuthUser;
};

type DemoAuthUser = {
  password: string;
  user: AuthUser;
};

const DEMO_USERS_KEY = 'ai-light.demo.users';

function loadDemoUsers(): Record<string, DemoAuthUser> {
  try {
    const raw = window.localStorage.getItem(DEMO_USERS_KEY);
    if (!raw) {
      return {};
    }
    const parsed = JSON.parse(raw);
    return parsed && typeof parsed === 'object' ? (parsed as Record<string, DemoAuthUser>) : {};
  } catch {
    return {};
  }
}

function saveDemoUsers(users: Record<string, DemoAuthUser>) {
  window.localStorage.setItem(DEMO_USERS_KEY, JSON.stringify(users));
}

function createAuthResponse(user: AuthUser): AuthResponse {
  return {
    token: `demo-token:${user.username}:${Date.now()}`,
    refresh_token: `demo-refresh:${user.username}:${Date.now()}`,
    user,
  };
}

function normalizeAccount(value: string) {
  return value.trim().toLowerCase();
}

function buildDemoUser(account: string, displayName?: string): AuthUser {
  return {
    id: Date.now(),
    username: account,
    displayName: displayName || account,
    realName: displayName || account,
    role: 'user',
  };
}

async function withDemoFallback<T>(remoteCall: () => Promise<T>, fallback: () => T | Promise<T>) {
  try {
    return await remoteCall();
  } catch (error) {
    if (error instanceof Error) {
      const message = error.message.toLowerCase();
      if (
        message.includes('timeout') ||
        message.includes('network') ||
        message.includes('failed') ||
        message.includes('load failed')
      ) {
        return fallback();
      }
    }
    return fallback();
  }
}

export const authApi = {
  register(payload: RegisterPayload) {
    return withDemoFallback(
      () => request.post('/auth/register', payload).then((res) => res.data),
      () => {
        const account = normalizeAccount(payload.username);
        const users = loadDemoUsers();
        const user = buildDemoUser(account, payload.displayName || payload.username);
        users[account] = {
          password: payload.password,
          user,
        };
        saveDemoUsers(users);
        return createAuthResponse(user);
      },
    );
  },

  login(payload: LoginPayload) {
    return withDemoFallback(
      () => request.post('/auth/login', payload).then((res) => res.data),
      () => {
        const account = normalizeAccount(payload.account);
        const users = loadDemoUsers();
        const stored = users[account];

        if (stored) {
          if (stored.password !== payload.password) {
            throw new Error('密码错误');
          }
          return createAuthResponse(stored.user);
        }

        const user = buildDemoUser(account, payload.account);
        users[account] = {
          password: payload.password,
          user,
        };
        saveDemoUsers(users);
        return createAuthResponse(user);
      },
    );
  },

  profile() {
    return withDemoFallback(
      () => request.get('/auth/profile').then((res) => res.data),
      () => {
        const user = getStoredUser();
        if (!user) {
          throw new Error('未登录');
        }
        return user;
      },
    );
  },

  logout(refreshToken: string) {
    return withDemoFallback(
      () => request.post('/auth/logout', { refresh_token: refreshToken }).then((res) => res.data),
      () => ({ success: true }),
    );
  },
};
