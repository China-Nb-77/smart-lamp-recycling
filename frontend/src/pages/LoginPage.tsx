import { useState, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { authApi } from '../api/auth';
import { setUserSession } from '../auth/session';
import { ErrorState } from '../components/feedback/ErrorState';

export function LoginPage() {
  const navigate = useNavigate();
  const [account, setAccount] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError('');
    try {
      const payload = await authApi.login({ account, password });
      setUserSession(payload.token, payload.refresh_token, payload.user);
      navigate('/');
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : '登录失败');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="auth-page">
      <section className="payment-card auth-card">
        <div className="payment-card__header">
          <div>
            <strong>用户登录</strong>
            <p>登录后可提交回收申请并查看个人订单</p>
          </div>
        </div>

        {error ? <ErrorState title="登录失败" description={error} /> : null}

        <form className="payment-form auth-form" onSubmit={handleSubmit}>
          <label>
            <span>账号 / 手机 / 邮箱</span>
            <input value={account} onChange={(e) => setAccount(e.target.value)} required />
          </label>
          <label>
            <span>密码</span>
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
          </label>
          <button type="submit" className="primary-button payment-form__submit" disabled={submitting}>
            {submitting ? '登录中...' : '登录'}
          </button>
        </form>

        <div className="auth-links">
          <span>还没有账号？</span>
          <Link to="/register">去注册</Link>
        </div>
      </section>
    </main>
  );
}
