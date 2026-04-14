import AsyncStorage from '@react-native-async-storage/async-storage';
import {
  DEFAULT_SESSION_TOKEN,
  DEFAULT_USER_NAME,
} from '../config/env';

export const STORAGE_KEYS = {
  userName: 'shell.userName',
  sessionToken: 'shell.sessionToken',
  latestOrderId: 'shell.latestOrderId',
  latestOrderJson: 'shell.latestOrderJson',
  latestUploadJson: 'shell.latestUploadJson',
};

export async function ensureSessionSeed() {
  const existingToken = await AsyncStorage.getItem(STORAGE_KEYS.sessionToken);
  const existingName = await AsyncStorage.getItem(STORAGE_KEYS.userName);

  if (!existingToken) {
    await AsyncStorage.setItem(STORAGE_KEYS.sessionToken, DEFAULT_SESSION_TOKEN);
  }

  if (!existingName) {
    await AsyncStorage.setItem(STORAGE_KEYS.userName, DEFAULT_USER_NAME);
  }
}

export async function getSessionSnapshot() {
  await ensureSessionSeed();

  const [userName, sessionToken, latestOrderId, latestOrderJson, latestUploadJson] =
    await Promise.all([
      AsyncStorage.getItem(STORAGE_KEYS.userName),
      AsyncStorage.getItem(STORAGE_KEYS.sessionToken),
      AsyncStorage.getItem(STORAGE_KEYS.latestOrderId),
      AsyncStorage.getItem(STORAGE_KEYS.latestOrderJson),
      AsyncStorage.getItem(STORAGE_KEYS.latestUploadJson),
    ]);

  return {
    userName: userName || DEFAULT_USER_NAME,
    sessionToken: sessionToken || DEFAULT_SESSION_TOKEN,
    latestOrderId: latestOrderId || '',
    latestOrderJson: latestOrderJson || '',
    latestUploadJson: latestUploadJson || '',
  };
}

export async function saveLatestOrder(order: unknown) {
  const payload = JSON.stringify(order ?? {});
  await AsyncStorage.setItem(STORAGE_KEYS.latestOrderJson, payload);

  const latestOrderId =
    typeof order === 'object' && order && 'order_id' in order
      ? String((order as {order_id?: string}).order_id || '')
      : '';

  if (latestOrderId) {
    await AsyncStorage.setItem(STORAGE_KEYS.latestOrderId, latestOrderId);
  }
}

export async function saveLatestUpload(upload: unknown) {
  await AsyncStorage.setItem(
    STORAGE_KEYS.latestUploadJson,
    JSON.stringify(upload ?? {}),
  );
}
