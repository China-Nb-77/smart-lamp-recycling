import { useEffect, useMemo, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { ArrowLeft, FileText, MapPinned, PackageCheck, ReceiptText } from 'lucide-react';
import { QRCodeSVG } from 'qrcode.react';
import { paymentApi } from '../services/paymentApi';
import type { ElectronicOrderResponse, QrErrorResponse } from '../types/api';
import type { AgentLogisticsMapResponse, AgentLogisticsResponse } from '../types/agent';
import { ErrorState } from '../components/feedback/ErrorState';
import { LoadingState } from '../components/feedback/LoadingState';
import { formatRelativeDate } from '../utils/date';

export function ElectronicOrderPage() {
  const { orderId = '' } = useParams();
  const [searchParams] = useSearchParams();
  const qrToken = searchParams.get('qrToken') || '';
  const [payload, setPayload] = useState<ElectronicOrderResponse | null>(null);
  const [logistics, setLogistics] = useState<AgentLogisticsResponse | null>(null);
  const [mapPayload, setMapPayload] = useState<AgentLogisticsMapResponse | null>(null);
  const [errorPayload, setErrorPayload] = useState<QrErrorResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let disposed = false;

    async function run() {
      if (!orderId || !qrToken) {
        if (!disposed) {
          setErrorPayload({
            trace_id: '',
            error_code: '404',
            message: '订单或二维码参数缺失',
            suggestion: '请重新生成二维码并重新扫码',
          });
          setLoading(false);
        }
        return;
      }

      try {
        const [order, track, trackMap] = await Promise.all([
          paymentApi.getElectronicOrder(orderId, qrToken),
          paymentApi.getLogistics(orderId),
          paymentApi.getLogisticsMap(orderId),
        ]);
        if (disposed) {
          return;
        }
        if (order.status_code !== 200 || order.code !== 'SUCCESS') {
          setPayload(order);
          setErrorPayload({
            trace_id: order.trace_id || '',
            error_code: order.code || String(order.status_code || 404),
            message: order.message || '电子货单打开失败',
            suggestion: '请重新扫码或检查订单状态',
          });
          setLoading(false);
          return;
        }
        setPayload(order);
        setLogistics(track);
        setMapPayload(trackMap);
        setLoading(false);
      } catch {
        if (!disposed) {
          setErrorPayload({
            trace_id: '',
            error_code: '404',
            message: '电子货单加载失败',
            suggestion: '请稍后重试',
          });
          setLoading(false);
        }
      }
    }

    void run();
    return () => {
      disposed = true;
    };
  }, [orderId, qrToken]);

  const qrValue = useMemo(() => {
    if (typeof window !== 'undefined') {
      return window.location.href;
    }
    return `${orderId}:${qrToken}`;
  }, [orderId, qrToken]);

  const mapSrc = useMemo(() => {
    if (!mapPayload?.nodes.length) {
      return '';
    }
    const latitudes = mapPayload.nodes.map((node) => node.lat);
    const longitudes = mapPayload.nodes.map((node) => node.lng);
    const minLat = Math.min(...latitudes) - 0.03;
    const maxLat = Math.max(...latitudes) + 0.03;
    const minLng = Math.min(...longitudes) - 0.03;
    const maxLng = Math.max(...longitudes) + 0.03;
    const last = mapPayload.nodes[mapPayload.nodes.length - 1];
    return `https://www.openstreetmap.org/export/embed.html?bbox=${minLng}%2C${minLat}%2C${maxLng}%2C${maxLat}&layer=mapnik&marker=${last.lat}%2C${last.lng}`;
  }, [mapPayload]);

  if (loading) {
    return (
      <main className="order-page">
        <div className="order-header">
          <Link className="icon-button" to="/">
            <ArrowLeft size={22} />
          </Link>
          <strong>电子货单</strong>
          <span />
        </div>
        <section className="order-page__state">
          <LoadingState label="正在加载电子货单..." />
        </section>
      </main>
    );
  }

  if (!payload || payload.status_code !== 200 || payload.code !== 'SUCCESS') {
    return (
      <main className="order-page">
        <div className="order-header">
          <Link className="icon-button" to="/">
            <ArrowLeft size={22} />
          </Link>
          <strong>电子货单</strong>
          <span />
        </div>
        <section className="order-page__state">
          <ErrorState
            title={errorPayload?.error_code || String(payload?.status_code || '404')}
            description={errorPayload?.message || payload?.message || '订单打开失败'}
          />
          {errorPayload?.suggestion ? <p className="order-error-tip">{errorPayload.suggestion}</p> : null}
        </section>
      </main>
    );
  }

  return (
    <main className="order-page">
      <div className="order-header">
        <Link className="icon-button" to="/">
          <ArrowLeft size={22} />
        </Link>
        <strong>电子货单</strong>
        <span />
      </div>

      <section className="order-summary-card">
        <div className="order-summary-card__head">
          <div>
            <span>order_id</span>
            <h1>{payload.order_id}</h1>
          </div>
          <div className="order-summary-card__status">{payload.order_basic?.status}</div>
        </div>
        <div className="order-grid">
          <div>
            <span>下单时间</span>
            <strong>
              {payload.order_basic?.created_at
                ? formatRelativeDate(payload.order_basic.created_at)
                : '--'}
            </strong>
          </div>
          <div>
            <span>支付状态</span>
            <strong>{payload.payment?.pay_status || '--'}</strong>
          </div>
          <div>
            <span>支付时间</span>
            <strong>
              {payload.payment?.paid_at ? formatRelativeDate(payload.payment.paid_at) : '--'}
            </strong>
          </div>
          <div>
            <span>运单号</span>
            <strong>{payload.waybill?.waybill_id || '--'}</strong>
          </div>
        </div>
      </section>

      <section className="order-section">
        <div className="order-section__title">
          <ReceiptText size={18} />
          <strong>商品明细</strong>
        </div>
        <div className="item-list">
          {payload.items?.map((item) => (
            <article key={`${item.sku}_${item.name}`} className="item-row">
              <div>
                <strong>{item.name}</strong>
                <p>灯具数量 x{item.qty}</p>
              </div>
              <div>
                <strong>¥{item.price}</strong>
                <p>单件价格</p>
              </div>
            </article>
          ))}
        </div>
      </section>

      <section className="order-section">
        <div className="order-section__title">
          <PackageCheck size={18} />
          <strong>物流时间线</strong>
        </div>
        <ol className="timeline-list timeline-list--page">
          {(logistics?.events || payload.timeline || []).map((event) => (
            <li key={`${event.time}_${event.event}`}>
              <span className="timeline-list__dot" />
              <div>
                <strong>{event.event}</strong>
                <time>{formatRelativeDate(event.time)}</time>
              </div>
            </li>
          ))}
        </ol>
      </section>

      {mapSrc ? (
        <section className="order-section">
          <div className="order-section__title">
            <MapPinned size={18} />
            <strong>物流地图</strong>
          </div>
          <iframe
            className="order-map"
            src={mapSrc}
            loading="lazy"
            referrerPolicy="no-referrer-when-downgrade"
            title="物流地图"
          />
          <div className="order-map__nodes">
            {(mapPayload?.nodes || []).map((node) => (
              <div key={`${node.label}_${node.lng}_${node.lat}`} className="order-map__node">
                <strong>{node.label}</strong>
                <span>
                  {node.lat.toFixed(4)}, {node.lng.toFixed(4)}
                </span>
              </div>
            ))}
          </div>
        </section>
      ) : null}

      <section className="order-section order-section--two-column">
        <div>
          <div className="order-section__title">
            <FileText size={18} />
            <strong>支付摘要</strong>
          </div>
          <div className="order-grid">
            <div>
              <span>金额</span>
              <strong>{payload.payment?.total !== undefined ? `¥${payload.payment.total}` : '--'}</strong>
            </div>
            <div>
              <span>运单状态</span>
              <strong>{payload.waybill?.status || '--'}</strong>
            </div>
          </div>
        </div>
        <div className="qr-side-card">
          <span>电子货单二维码</span>
          <QRCodeSVG value={qrValue} size={128} bgColor="transparent" fgColor="#111111" />
        </div>
      </section>
    </main>
  );
}
