import request from './request';

export type RecommendRequest = {
  user_input: string;
  limit?: number;
};

export type RecommendResponse = {
  intent: {
    room: string;
    brightness: string;
    budget: string;
    style: string;
  };
  keyword: string;
  recommendations: Array<{
    title: string;
    price: number;
    image: string;
    link: string;
  }>;
};

export const recommendApi = {
  recommend(payload: RecommendRequest) {
    return request.post('/recommend', payload).then((res) => res.data as RecommendResponse);
  },
};
