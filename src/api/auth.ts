import request from './request';

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

export const authApi = {
  register(payload: RegisterPayload) {
    return request.post('/auth/register', payload).then((res) => res.data);
  },
  login(payload: LoginPayload) {
    return request.post('/auth/login', payload).then((res) => res.data);
  },
  profile() {
    return request.get('/auth/profile').then((res) => res.data);
  },
  logout(refreshToken: string) {
    return request.post('/auth/logout', { refresh_token: refreshToken }).then((res) => res.data);
  },
};
