import React, {useState} from 'react';
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import SectionCard from '../components/SectionCard';
import {shellTheme} from '../config/theme';
import {chooseAndUploadImage} from '../services/upload';

export default function UploadCenterScreen() {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState('');

  const handleUpload = async () => {
    setLoading(true);
    setError('');
    try {
      const uploadResult = await chooseAndUploadImage();
      setResult(uploadResult);
    } catch (uploadError) {
      setError(uploadError instanceof Error ? uploadError.message : '上传失败');
      setResult(null);
    } finally {
      setLoading(false);
    }
  };

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <SectionCard
        subtitle="支持相册选图、压缩和上传结果展示；上传接口默认走可配置的 UPLOAD_ENDPOINT。"
        title="图片上传链路">
        <Pressable onPress={handleUpload} style={styles.primaryButton}>
          <Text style={styles.primaryButtonText}>选择图片并上传</Text>
        </Pressable>
        {loading ? (
          <ActivityIndicator color={shellTheme.colors.primary} size="large" />
        ) : null}
        {error ? <Text style={styles.errorText}>{error}</Text> : null}
      </SectionCard>

      {result ? (
        <SectionCard title="上传结果">
          <View style={styles.resultBlock}>
            <Text style={styles.resultTitle}>本地文件</Text>
            <Text style={styles.resultText}>{JSON.stringify(result.local, null, 2)}</Text>
          </View>
          <View style={styles.resultBlock}>
            <Text style={styles.resultTitle}>接口返回</Text>
            <Text style={styles.resultText}>{JSON.stringify(result.remote, null, 2)}</Text>
          </View>
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
  primaryButton: {
    minHeight: 48,
    borderRadius: 16,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: shellTheme.colors.primary,
  },
  primaryButtonText: {
    color: '#fff',
    fontWeight: '700',
    fontSize: 15,
  },
  errorText: {
    color: shellTheme.colors.danger,
  },
  resultBlock: {
    gap: 6,
    borderRadius: 16,
    backgroundColor: shellTheme.colors.primarySoft,
    padding: 14,
  },
  resultTitle: {
    color: shellTheme.colors.text,
    fontWeight: '700',
  },
  resultText: {
    color: shellTheme.colors.text,
    fontFamily: 'monospace',
  },
});
