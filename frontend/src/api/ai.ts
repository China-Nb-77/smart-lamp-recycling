import type { LampTypeClassificationResponse } from '../types/vision';
import { visionBaseUrl } from '../services/api/base-url';

export async function classifyLamp(imageFile: File) {
  const formData = new FormData();
  formData.append('file', imageFile);

  try {
    const response = await fetch(`${visionBaseUrl}/classify`, {
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
