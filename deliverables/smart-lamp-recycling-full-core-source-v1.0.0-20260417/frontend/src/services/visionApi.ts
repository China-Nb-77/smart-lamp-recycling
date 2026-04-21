import { ApiError, extractErrorMessage } from './api/client';
import type {
  LampTypeClassificationResponse,
  VisionPreferences,
  VisionQuoteResponse,
  VisionRecommendationResponse,
} from '../types/vision';

const visionBaseUrl = import.meta.env.VITE_VISION_API_BASE_URL || '/vision-api';

export function buildVisionImageUrl(imagePath?: string) {
  if (!imagePath) {
    return '';
  }
  return `${visionBaseUrl}/catalog-image?path=${encodeURIComponent(imagePath)}`;
}

async function parseResponse<T>(response: Response): Promise<T> {
  const contentType = response.headers.get('content-type') || '';
  const payload = contentType.includes('application/json')
    ? await response.json()
    : await response.text();

  if (!response.ok) {
    throw new ApiError(extractErrorMessage(payload), response.status, payload);
  }

  return payload as T;
}

export const visionApi = {
  async classifyLamp(file: File) {
    const form = new FormData();
    form.append('file', file);

    const response = await fetch(`${visionBaseUrl}/classify`, {
      method: 'POST',
      body: form,
    });
    return parseResponse<LampTypeClassificationResponse>(response);
  },

  async uploadQuote(file: File, topk = 3) {
    const form = new FormData();
    form.append('file', file);
    form.append('topk', String(topk));

    const response = await fetch(`${visionBaseUrl}/quote-upload`, {
      method: 'POST',
      body: form,
    });
    return parseResponse<VisionQuoteResponse>(response);
  },

  async recommend(referenceSkuId: string, preferences: VisionPreferences, limit = 3) {
    const response = await fetch(`${visionBaseUrl}/recommend`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        reference_sku_id: referenceSkuId,
        preferences,
        limit,
      }),
    });
    return parseResponse<VisionRecommendationResponse>(response);
  },
};
