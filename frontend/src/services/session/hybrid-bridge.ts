type ShellSessionPayload = {
  userName?: string;
  sessionToken?: string;
  latestOrderId?: string;
  latestOrderJson?: string;
  latestUploadJson?: string;
};

type BridgeMessage = {
  scope?: string;
  type?: string;
  payload?: unknown;
};

const shellRequestScope = 'h5-shell';

export function requestShellAction(action: string, payload?: Record<string, unknown>) {
  const message = {
    scope: shellRequestScope,
    type: 'request',
    payload: {
      action,
      ...payload,
    },
  };

  const shellWindow = window as Window &
    typeof globalThis & {
      ReactNativeWebView?: {
        postMessage: (body: string) => void;
      };
    };

  if (typeof shellWindow.ReactNativeWebView?.postMessage === 'function') {
    shellWindow.ReactNativeWebView.postMessage(JSON.stringify(message));
  }
}

export function subscribeShellMessages(
  callback: (message: BridgeMessage) => void,
) {
  const handler = (event: MessageEvent) => {
    if (typeof event.data !== 'string') {
      return;
    }

    try {
      const parsed = JSON.parse(event.data) as BridgeMessage;
      if (parsed.scope !== 'rn-shell') {
        return;
      }
      callback(parsed);
    } catch {
      // ignore invalid messages
    }
  };

  window.addEventListener('message', handler);
  return () => window.removeEventListener('message', handler);
}

export function getSeedSession() {
  const userName =
    window.localStorage.getItem('demo.profile.user_name') || '187******09';
  const sessionToken =
    window.localStorage.getItem('demo.profile.session_token') || 'web-session';
  const latestOrderId = window.localStorage.getItem('demo.latestOrderId') || '';

  return {
    userName,
    sessionToken,
    latestOrderId,
  };
}

export function parseShellSessionPayload(payload: unknown): ShellSessionPayload {
  if (!payload || typeof payload !== 'object') {
    return {};
  }

  return payload as ShellSessionPayload;
}
