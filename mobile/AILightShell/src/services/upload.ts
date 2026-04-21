import {launchImageLibrary} from 'react-native-image-picker';
import {UPLOAD_ENDPOINT} from '../config/env';
import {saveLatestUpload} from '../store/session';

export async function chooseAndUploadImage() {
  const result = await launchImageLibrary({
    mediaType: 'photo',
    selectionLimit: 1,
    quality: 0.7,
    maxWidth: 1600,
    maxHeight: 1600,
    includeBase64: false,
  });

  if (result.didCancel) {
    return null;
  }

  if (result.errorMessage) {
    throw new Error(result.errorMessage);
  }

  const asset = result.assets?.[0];
  if (!asset?.uri || !asset.fileName || !asset.type) {
    throw new Error('未获取到有效图片资源');
  }

  const formData = new FormData();
  formData.append('file', {
    uri: asset.uri,
    name: asset.fileName,
    type: asset.type,
  } as never);

  let uploadPayload: unknown = null;
  try {
    const response = await fetch(UPLOAD_ENDPOINT, {
      method: 'POST',
      body: formData,
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload?.message || '上传失败');
    }
    uploadPayload = payload?.data ?? payload;
  } catch (error) {
    uploadPayload = {
      success: false,
      message:
        error instanceof Error ? error.message : '上传接口暂不可用，请检查 UPLOAD_ENDPOINT',
    };
  }

  const uploadResult = {
    local: {
      uri: asset.uri,
      fileName: asset.fileName,
      fileSize: asset.fileSize,
      type: asset.type,
    },
    remote: uploadPayload,
  };

  await saveLatestUpload(uploadResult);
  return uploadResult;
}
