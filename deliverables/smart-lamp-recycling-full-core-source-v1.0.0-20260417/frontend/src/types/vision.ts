export type VisionFollowUpOption = {
  value: string;
  label: string;
};

export type VisionFollowUpQuestion = {
  id: 'install_type' | 'budget_level' | 'material' | 'space';
  question: string;
  options: VisionFollowUpOption[];
};

export type VisionSimilarItem = {
  rank: number;
  sku_id: string;
  title: string;
  similarity_score: number;
  base_price: number;
  material: string;
  size_band: string;
  craft: string;
  risk_level: string;
  metadata: Record<string, unknown>;
};

export type VisionQuoteLineItem = {
  detection_index: number;
  matched_sku_id: string;
  title: string;
  base_price: number;
  final_quote: number;
  similarity_score: number;
  detection_confidence: number;
  matched_product: VisionSimilarItem;
  topk_similar_items: VisionSimilarItem[];
  breakdown: Record<string, unknown>;
  price_composition: Record<string, unknown>;
};

export type VisionQuotePayload = {
  image_path: string;
  detection_backend: string;
  embedding_backend: string;
  retrieval_backend: string;
  currency: string;
  total_quote: number;
  price_summary: {
    line_item_count: number;
    subtotal_before_residual: number;
    residual_total: number;
    total_quote: number;
    currency: string;
  };
  detection_summary: {
    backend: string;
    used_fallback: boolean;
    notes: string[];
    detections: Array<{
      detection_index: number;
      bbox_xyxy: number[];
      confidence: number;
      label: string;
      area_ratio: number;
      crop_path?: string;
    }>;
  };
  line_items: VisionQuoteLineItem[];
};

export type VisionQuoteResponse = {
  quote: VisionQuotePayload;
  summary: {
    recognized_type: string;
    matched_sku_id: string;
    matched_title: string;
    recycle_quote: number;
    currency: string;
    detection_backend: string;
    explanation?: string;
    lamp_type_label?: string;
    lamp_type_score?: number;
    lamp_type_backend?: string;
    lamp_type_model_id?: string;
  };
  follow_up_questions: VisionFollowUpQuestion[];
  upload?: {
    filename: string;
    stored_path: string;
    size_bytes: number;
  };
};

export type VisionPreferences = {
  install_type: string;
  budget_level: string;
  material: string;
  space?: string;
};

export type VisionRecommendation = {
  sku_id: string;
  title: string;
  image_path?: string;
  image_missing?: boolean;
  visual_style: string;
  material: string;
  size_band: string;
  craft: string;
  base_price: number;
  fit_score: number;
  recommendation_reasons: string[];
};

export type VisionRecommendationResponse = {
  session_id?: string;
  reference: {
    sku_id: string;
    title: string;
    visual_style: string;
    material: string;
    size_band: string;
    craft: string;
    base_price: number;
  };
  preferences: VisionPreferences;
  space?: string;
  selection_api?: {
    path: string;
    method: string;
  };
  recommendations: VisionRecommendation[];
};

export type LampTypeClassificationResponse = {
  success: boolean;
  lamp_type: string;
  confidence: number;
  label?: string;
  score?: number;
  candidates?: Array<{
    label: string;
    score: number;
  }>;
  model_id?: string;
  backend?: string;
  image_path?: string;
  upload?: {
    filename: string;
    stored_path: string;
    size_bytes: number;
  };
};
