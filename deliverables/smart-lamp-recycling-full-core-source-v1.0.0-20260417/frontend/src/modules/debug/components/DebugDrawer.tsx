import { useMemo, useState } from 'react';
import { FlaskConical, X } from 'lucide-react';
import { debugEndpoints } from '../../../services/api/debug-catalog';
import { request } from '../../../services/api/client';

type DebugDrawerProps = {
  open: boolean;
  onClose: () => void;
};

type EndpointLog = {
  requestPath: string;
  requestBody?: unknown;
  response?: unknown;
  error?: string;
};

export function DebugDrawer({ open, onClose }: DebugDrawerProps) {
  const initialValues = useMemo(
    () =>
      Object.fromEntries(
        debugEndpoints.map((endpoint) => [
          endpoint.id,
          Object.fromEntries(endpoint.fields.map((field) => [field.key, ''])),
        ]),
      ) as Record<string, Record<string, string>>,
    [],
  );
  const [valuesById, setValuesById] = useState(initialValues);
  const [logs, setLogs] = useState<Record<string, EndpointLog>>({});
  const [loadingId, setLoadingId] = useState('');

  if (!open) {
    return null;
  }

  return (
    <div className="debug-drawer">
      <div className="debug-drawer__backdrop" onClick={onClose} />
      <aside className="debug-drawer__panel">
        <div className="debug-drawer__header">
          <div>
            <strong>Debug Drawer</strong>
            <p>手动触发所有已扫描到的真实接口</p>
          </div>
          <button type="button" className="icon-button" onClick={onClose}>
            <X size={20} />
          </button>
        </div>
        <div className="debug-drawer__list">
          {debugEndpoints.map((endpoint) => {
            const endpointValues = valuesById[endpoint.id] || {};
            const log = logs[endpoint.id];

            return (
              <section key={endpoint.id} className="debug-card">
                <div className="debug-card__head">
                  <span>
                    <FlaskConical size={16} />
                    {endpoint.title}
                  </span>
                  <code>{endpoint.pathTemplate}</code>
                </div>
                <div className="debug-card__fields">
                  {endpoint.fields.map((field) =>
                    field.kind === 'textarea' ? (
                      <label key={field.key}>
                        <span>{field.label}</span>
                        <textarea
                          rows={3}
                          value={endpointValues[field.key] || ''}
                          placeholder={field.placeholder}
                          onChange={(event) =>
                            setValuesById((current) => ({
                              ...current,
                              [endpoint.id]: {
                                ...current[endpoint.id],
                                [field.key]: event.target.value,
                              },
                            }))
                          }
                        />
                      </label>
                    ) : (
                      <label key={field.key}>
                        <span>{field.label}</span>
                        <input
                          value={endpointValues[field.key] || ''}
                          placeholder={field.placeholder}
                          onChange={(event) =>
                            setValuesById((current) => ({
                              ...current,
                              [endpoint.id]: {
                                ...current[endpoint.id],
                                [field.key]: event.target.value,
                              },
                            }))
                          }
                        />
                      </label>
                    ),
                  )}
                </div>
                <button
                  type="button"
                  className="primary-button primary-button--compact"
                  disabled={loadingId === endpoint.id}
                  onClick={async () => {
                    const path = endpoint.buildPath(endpointValues);
                    const body = endpoint.buildBody?.(endpointValues);
                    setLoadingId(endpoint.id);
                    try {
                      const response = await request<unknown>(path, {
                        method: endpoint.method,
                        body,
                      });
                      setLogs((current) => ({
                        ...current,
                        [endpoint.id]: {
                          requestPath: path,
                          requestBody: body,
                          response,
                        },
                      }));
                    } catch (error) {
                      setLogs((current) => ({
                        ...current,
                        [endpoint.id]: {
                          requestPath: path,
                          requestBody: body,
                          error: error instanceof Error ? error.message : '执行失败',
                        },
                      }));
                    } finally {
                      setLoadingId('');
                    }
                  }}
                >
                  {loadingId === endpoint.id ? '执行中...' : '执行'}
                </button>
                {log ? (
                  <div className="debug-card__result">
                    <div>
                      <span>Request</span>
                      <pre>{JSON.stringify({ path: log.requestPath, body: log.requestBody }, null, 2)}</pre>
                    </div>
                    <div>
                      <span>{log.error ? 'Error' : 'Response'}</span>
                      <pre>
                        {log.error
                          ? log.error
                          : JSON.stringify(log.response ?? {}, null, 2)}
                      </pre>
                    </div>
                  </div>
                ) : null}
              </section>
            );
          })}
        </div>
      </aside>
    </div>
  );
}
