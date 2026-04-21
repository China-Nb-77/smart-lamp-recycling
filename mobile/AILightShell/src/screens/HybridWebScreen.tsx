import NetInfo from '@react-native-community/netinfo';
import type {NativeStackNavigationProp} from '@react-navigation/native-stack';
import type {NativeStackScreenProps} from '@react-navigation/native-stack';
import {useFocusEffect, useNavigation} from '@react-navigation/native';
import React, {useCallback, useMemo, useRef, useState} from 'react';
import {ActivityIndicator, StyleSheet, View} from 'react-native';
import {WebView} from 'react-native-webview';
import type {WebViewMessageEvent} from 'react-native-webview/lib/WebViewTypes';
import type {RootStackParamList} from '../../App';
import {APP_VERSION, H5_BASE_URL} from '../config/env';
import {shellTheme} from '../config/theme';
import {chooseAndUploadImage} from '../services/upload';
import {getSessionSnapshot} from '../store/session';
import {buildInjectedBridgeScript, buildShellMessage} from '../utils/hybrid';

type Props = NativeStackScreenProps<RootStackParamList, 'Assistant'>;

export default function HybridWebScreen({route}: Props) {
  const stackNavigation =
    useNavigation<NativeStackNavigationProp<RootStackParamList>>();
  const webViewRef = useRef<WebView>(null);
  const [uri, setUri] = useState('');
  const [bridgeScript, setBridgeScript] = useState('true;');

  const routePath = route.params?.routePath || '/';

  const loadUri = useCallback(async () => {
    await getSessionSnapshot();
    setUri(`${H5_BASE_URL}${routePath}`);
    setBridgeScript(await buildInjectedBridgeScript(routePath));
  }, [routePath]);

  useFocusEffect(
    useCallback(() => {
      loadUri();
    }, [loadUri]),
  );

  const handleBridgeAction = useCallback(
    async (payload: any) => {
      const action = payload?.action;

      if (action === 'syncSession') {
        const session = await getSessionSnapshot();
        webViewRef.current?.injectJavaScript(
          buildShellMessage('bridge:session', session),
        );
        return;
      }

      if (action === 'getDeviceInfo') {
        const network = await NetInfo.fetch();
        webViewRef.current?.injectJavaScript(
          buildShellMessage('bridge:device', {
            platform: 'android',
            appVersion: APP_VERSION,
            network: network.type,
          }),
        );
        return;
      }

      if (action === 'pickImage') {
        const result = await chooseAndUploadImage();
        webViewRef.current?.injectJavaScript(
          buildShellMessage('bridge:image', {
            success: Boolean(result),
            result,
          }),
        );
        return;
      }

      if (action === 'openUploadCenter') {
        stackNavigation.navigate('UploadCenter');
        return;
      }

      if (action === 'openCheckout') {
        stackNavigation.navigate('Checkout');
      }
    },
    [stackNavigation],
  );

  const handleMessage = useCallback(
    async (event: WebViewMessageEvent) => {
      try {
        const payload = JSON.parse(event.nativeEvent.data);
        if (payload?.scope !== 'h5-shell') {
          return;
        }

        if (payload?.type === 'request') {
          await handleBridgeAction(payload.payload);
        }
      } catch {
        // ignore malformed bridge events
      }
    },
    [handleBridgeAction],
  );

  const source = useMemo(() => ({uri}), [uri]);

  if (!uri) {
    return (
      <View style={styles.loader}>
        <ActivityIndicator color={shellTheme.colors.primary} size="large" />
      </View>
    );
  }

  return (
    <WebView
      injectedJavaScript={bridgeScript}
      javaScriptEnabled
      onMessage={handleMessage}
      ref={webViewRef}
      renderLoading={() => (
        <View style={styles.loader}>
          <ActivityIndicator color={shellTheme.colors.primary} size="large" />
        </View>
      )}
      sharedCookiesEnabled
      source={source}
      startInLoadingState
      style={styles.webview}
      pullToRefreshEnabled
    />
  );
}

const styles = StyleSheet.create({
  webview: {
    flex: 1,
    backgroundColor: shellTheme.colors.background,
  },
  loader: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: shellTheme.colors.background,
  },
});
