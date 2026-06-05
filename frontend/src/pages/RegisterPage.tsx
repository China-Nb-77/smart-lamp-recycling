import { useState, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { authApi } from '../api/auth';
import { setUserSession } from '../auth/session';
import { ErrorState } from '../components/feedback/ErrorState';

export function RegisterPage() {
  const navigate = useNavigate();
  const [form, setForm] = useState({
    username: '',
    displayName: '',
    phone: '',
    email: '',
    password: '',
  });
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError('');
    try {
      const payload = await authApi.register(form);
      setUserSession(payload.token, payload.refresh_token, payload.user);
      navigate('/');
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : '注册失败');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="auth-page">
      <section className="payment-card auth-card">
        <div className="payment-card__header">
          <div>
            <strong>用户注册</strong>
            <p>创建账号后可保存登录态与个人回收记录</p>
          </div>
        </div>

        {error ? <ErrorState title="注册失败" description={error} /> : null}

        <form className="payment-form auth-form" onSubmit={handleSubmit}>
          <label>
            <span>用户名</span>
            <input value={form.username} onChange={(e) => setForm((s) => ({ ...s, username: e.target.value }))} required />
          </label>
          <label>
            <span>昵称</span>
            <input value={form.displayName} onChange={(e) => setForm((s) => ({ ...s, displayName: e.target.value }))} />
          </label>
          <label>
            <span>手机号</span>
            <input value={form.phone} onChange={(e) => setForm((s) => ({ ...s, phone: e.target.value }))} />
          </label>
          <label>
            <span>邮箱</span>
            <input value={form.email} onChange={(e) => setForm((s) => ({ ...s, email: e.target.value }))} />
          </label>
          <label className="payment-form__wide">
            <span>密码</span>
            <input type="password" value={form.password} onChange={(e) => setForm((s) => ({ ...s, password: e.target.value }))} required />
          </label>
          <button type="submit" className="primary-button payment-form__submit" disabled={submitting}>
            {submitting ? '注册中...' : '注册并登录'}
          </button>
        </form>

        <div className="auth-links">
          <span>已有账号？</span>
          <Link to="/login">去登录</Link>
        </div>
      </section>
    </main>
  );
}
