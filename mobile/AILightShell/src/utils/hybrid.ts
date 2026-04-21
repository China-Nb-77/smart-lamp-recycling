import {Platform} from 'react-native';
import {APP_VERSION} from '../config/env';
import {getSessionSnapshot} from '../store/session';

export async function buildInjectedBridgeScript(routePath: string) {
  const session = await getSessionSnapshot();

  return `
    (function() {
      window.localStorage.setItem('demo.profile.user_name', ${JSON.stringify(
        session.userName,
      )});
      window.localStorage.setItem('demo.profile.session_token', ${JSON.stringify(
        session.sessionToken,
      )});
      if (${JSON.stringify(session.latestOrderId)}) {
        window.localStorage.setItem('demo.latestOrderId', ${JSON.stringify(
          session.latestOrderId,
        )});
      }
      if (${JSON.stringify(session.latestOrderJson)}) {
        window.localStorage.setItem('shell.latestOrderJson', ${JSON.stringify(
          session.latestOrderJson,
        )});
      }
      if (${JSON.stringify(session.latestUploadJson)}) {
        window.localStorage.setItem('shell.latestUploadJson', ${JSON.stringify(
          session.latestUploadJson,
        )});
      }
      window.dispatchEvent(new MessageEvent('message', {
        data: JSON.stringify({
          scope: 'rn-shell',
          type: 'bridge:session',
          payload: ${JSON.stringify(session)}
        })
      }));
      window.dispatchEvent(new MessageEvent('message', {
        data: JSON.stringify({
          scope: 'rn-shell',
          type: 'bridge:device',
          payload: {
            platform: ${JSON.stringify(Platform.OS)},
            appVersion: ${JSON.stringify(APP_VERSION)},
            routePath: ${JSON.stringify(routePath)}
          }
        })
      }));
      true;
    })();
  `;
}

export function buildShellMessage(type: string, payload: Record<string, unknown>) {
  return `
    window.dispatchEvent(new MessageEvent('message', {
      data: JSON.stringify({
        scope: 'rn-shell',
        type: ${JSON.stringify(type)},
        payload: ${JSON.stringify(payload)}
      })
    }));
    true;
  `;
}
