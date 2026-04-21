import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { authApi } from '../api/auth';
import { clearUserSession, getStoredUser, getUserRefreshToken } from '../auth/session';
import { ErrorState } from '../components/feedback/ErrorState';

const SONG_ORDER_CACHE_KEY = 'ai-light.song.order-cache';

export function ProfilePage() {
  const [profile, setProfile] = useState(getStoredUser());
  const [error, setError] = useState('');
  const [orders, setOrders] = useState<string[]>([]);

  useEffect(() => {
    void authApi.profile()
      .then((payload) => setProfile(payload))
      .catch((requestError) => {
        setError(requestError instanceof Error ? requestError.message : '加载个人信息失败');
      });

    try {
      const cache = JSON.parse(window.localStorage.getItem(SONG_ORDER_CACHE_KEY) || '{}');
      setOrders(Object.keys(cache));
    } catch {
      setOrders([]);
    }
  }, []);

  return (
    <main className="auth-page">
      <section className="payment-card auth-card">
        <div className="payment-card__header">
          <div>
            <strong>个人中心</strong>
            <p>查看账号信息与最近回收订单</p>
          </div>
          <button
            type="button"
            className="secondary-pill"
            onClick={() => {
              clearUserSession();
              void authApi.logout(getUserRefreshToken()).catch(() => null);
              window.location.href = '/login';
            }}
          >
            退出登录
          </button>
        </div>

        {error ? <ErrorState title="加载失败" description={error} /> : null}

        <div className="admin-grid">
          <article className="admin-card">
            <span className="admin-card__label">用户名</span>
            <strong>{profile?.username || '--'}</strong>
          </article>
          <article className="admin-card">
            <span className="admin-card__label">昵称</span>
            <strong>{profile?.displayName || profile?.realName || '--'}</strong>
          </article>
        </div>

        <section className="admin-card">
          <div className="payment-card__header">
            <div>
              <strong>我的回收订单</strong>
              <p>基于当前浏览器缓存展示最近联调订单</p>
            </div>
          </div>
          {orders.length === 0 ? (
            <p className="admin-empty">暂无订单记录</p>
          ) : (
            <div className="admin-list">
              {orders.map((orderId) => (
                <Link key={orderId} to={`/payment/orders/${encodeURIComponent(orderId)}`} className="admin-list__item">
                  <strong>{orderId}</strong>
                  <span>查看订单详情</span>
                </Link>
              ))}
            </div>
          )}
        </section>
      </section>
    </main>
  );
}
