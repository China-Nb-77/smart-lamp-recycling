import { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { api } from '../services/api/endpoints';
import type { QrErrorResponse } from '../types/api';
import { ErrorState } from '../components/feedback/ErrorState';
import { LoadingState } from '../components/feedback/LoadingState';

export function QrErrorPage() {
  const [searchParams] = useSearchParams();
  const code = searchParams.get('code') || '404';
  const [payload, setPayload] = useState<QrErrorResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let disposed = false;

    void api
      .getQrError(code)
      .then((result) => {
        if (!disposed) {
          setPayload(result);
          setLoading(false);
        }
      })
      .catch(() => {
        if (!disposed) {
          setPayload({
            trace_id: '',
            error_code: code,
            message: '二维码错误信息获取失败',
            suggestion: '请返回首页后重新执行二维码生成或扫码流程',
          });
          setLoading(false);
        }
      });

    return () => {
      disposed = true;
    };
  }, [code]);

  return (
    <main className="page-shell">
      <div className="feedback-page">
        <div className="order-header">
          <Link className="icon-button" to="/">
            <ArrowLeft size={22} />
          </Link>
          <strong>二维码错误</strong>
          <span />
        </div>
        {loading ? (
          <section className="order-page__state">
            <LoadingState label="正在加载错误说明..." />
          </section>
        ) : (
          <ErrorState
            title={payload?.error_code || code}
            description={payload?.message || '二维码错误'}
            action={
              <div className="feedback-actions">
                <Link className="secondary-button" to="/">
                  返回首页
                </Link>
              </div>
            }
          />
        )}
        {payload?.suggestion ? <p className="order-error-tip">{payload.suggestion}</p> : null}
      </div>
    </main>
  );
}
