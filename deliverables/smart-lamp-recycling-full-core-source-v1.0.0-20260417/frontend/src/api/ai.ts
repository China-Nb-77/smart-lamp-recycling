import type { LampTypeClassificationResponse } from '../types/vision';

const aiBaseUrl = import.meta.env.VITE_VISION_API_BASE_URL || '/vision-api';

export async function classifyLamp(imageFile: File) {
  const formData = new FormData();
  formData.append('file', imageFile);

  try {
    const response = await fetch(`${aiBaseUrl}/classify`, {
      method: 'POST',
      body: formData,
    });
    return (await response.json()) as LampTypeClassificationResponse;
  } catch {
    return {
      success: false,
      lamp_type: '',
      confidence: 0,
    } as LampTypeClassificationResponse;
  }
}
