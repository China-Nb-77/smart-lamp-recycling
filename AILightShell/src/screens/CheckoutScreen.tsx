import React, {useState} from 'react';
import {
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import SectionCard from '../components/SectionCard';
import {shellTheme} from '../config/theme';
import {createOrderFlow, createPrepay, mockNotify} from '../services/api';

export default function CheckoutScreen() {
  const [orderBundle, setOrderBundle] = useState<any>(null);
  const [prepayResult, setPrepayResult] = useState<any>(null);
  const [notifyResult, setNotifyResult] = useState<any>(null);
  const [error, setError] = useState('');

  const handleCreateOrder = async () => {
    setError('');
    try {
      const result = await createOrderFlow();
      setOrderBundle(result);
      setPrepayResult(null);
      setNotifyResult(null);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : '创建订单失败');
    }
  };

  const handlePrepay = async () => {
    if (!orderBundle?.order?.order_id) {
      setError('请先创建订单');
      return;
    }

    setError('');
    try {
      const result = await createPrepay(orderBundle.order.order_id);
      setPrepayResult(result);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : '预下单失败');
    }
  };

  const handleNotify = async () => {
    if (!orderBundle?.order?.order_id) {
      setError('请先创建订单');
      return;
    }

    setError('');
    try {
      const result = await mockNotify(orderBundle.order.order_id);
      setNotifyResult(result);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : '支付通知失败');
    }
  };

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <SectionCard
        subtitle="原生页直接串联 quote、create_order、pay/prepay 与 wechat/notify，便于验证支付二维码主链路。"
        title="主链路联调">
        <View style={styles.buttonRow}>
          <Pressable onPress={handleCreateOrder} style={styles.primaryButton}>
            <Text style={styles.primaryButtonText}>1. 创建订单</Text>
          </Pressable>
          <Pressable onPress={handlePrepay} style={styles.secondaryButton}>
            <Text style={styles.secondaryButtonText}>2. 生成支付参数</Text>
          </Pressable>
          <Pressable onPress={handleNotify} style={styles.secondaryButton}>
            <Text style={styles.secondaryButtonText}>3. 模拟支付完成</Text>
          </Pressable>
        </View>
        {error ? <Text style={styles.errorText}>{error}</Text> : null}
      </SectionCard>

      {orderBundle ? (
        <SectionCard title="订单结果">
          <Text style={styles.codeBlock}>{JSON.stringify(orderBundle, null, 2)}</Text>
        </SectionCard>
      ) : null}

      {prepayResult ? (
        <SectionCard title="二维码 / 支付参数">
          <Text style={styles.codeBlock}>{JSON.stringify(prepayResult, null, 2)}</Text>
        </SectionCard>
      ) : null}

      {notifyResult ? (
        <SectionCard title="支付回调结果">
          <Text style={styles.codeBlock}>{JSON.stringify(notifyResult, null, 2)}</Text>
        </SectionCard>
      ) : null}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    padding: 16,
    gap: 16,
  },
  buttonRow: {
    gap: 12,
  },
  primaryButton: {
    minHeight: 48,
    borderRadius: 16,
    backgroundColor: shellTheme.colors.primary,
    alignItems: 'center',
    justifyContent: 'center',
  },
  primaryButtonText: {
    color: '#fff',
    fontWeight: '700',
  },
  secondaryButton: {
    minHeight: 48,
    borderRadius: 16,
    backgroundColor: shellTheme.colors.primarySoft,
    alignItems: 'center',
    justifyContent: 'center',
  },
  secondaryButtonText: {
    color: shellTheme.colors.primary,
    fontWeight: '700',
  },
  errorText: {
    color: shellTheme.colors.danger,
  },
  codeBlock: {
    color: shellTheme.colors.text,
    fontFamily: 'monospace',
  },
});
