import NetInfo from '@react-native-community/netinfo';
import React, {useEffect, useState} from 'react';
import {StyleSheet, Text, View} from 'react-native';
import {shellTheme} from '../config/theme';

export default function NetworkBanner() {
  const [offline, setOffline] = useState(false);

  useEffect(() => {
    const unsubscribe = NetInfo.addEventListener((state) => {
      setOffline(!(state.isConnected && state.isInternetReachable !== false));
    });

    return unsubscribe;
  }, []);

  if (!offline) {
    return null;
  }

  return (
    <View style={styles.banner}>
      <Text style={styles.text}>当前网络不可用，H5 页面与支付链路可能失败。</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  banner: {
    backgroundColor: '#fff3d6',
    paddingHorizontal: 16,
    paddingVertical: 10,
  },
  text: {
    color: shellTheme.colors.warning,
    fontSize: 13,
    fontWeight: '600',
    textAlign: 'center',
  },
});
