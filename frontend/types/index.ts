export type Store = {
  id: number;
  store_name: string;
  store_code: string;
  platform?: string;
  marketplace?: string;
  seller_id?: string;
  status?: string;
  note?: string;
  created_at?: string;
};

export type Conversation = {
  id: number;
  store_id?: number;
  subject?: string;
  status?: "open" | "processing" | "waiting_customer" | "done" | "closed" | string;
  category?: string;
  risk_level?: string;
  last_message_at?: string;
  last_reply_at?: string;
  created_at?: string;
};

export type Message = {
  id: number;
  conversation_id?: number;
  sender_type: "buyer" | "seller" | "system" | "ai" | string;
  content: string;
  original_language?: string;
  created_at?: string;
  sent_at?: string;
};

export type AIReply = {
  id: number;
  conversation_id?: number;
  message_id?: number;
  detected_category?: string;
  detected_intent?: string;
  risk_level?: string;
  ai_reply_text: string;
  final_reply_text?: string;
  confidence_score?: number;
  status?: string;
};


export type Attachment = {
  id: number;
  conversation_id?: number;
  message_id?: number;
  store_id?: number;
  file_name: string;
  content_type?: string;
  file_size?: number;
  bucket: string;
  object_key: string;
  status?: string;
  created_at?: string;
};

export type ReplyTemplate = {
  id: number;
  category?: string;
  title: string;
  content_ja: string;
  content_zh?: string;
  risk_level?: string;
  is_active?: boolean;
  created_at?: string;
  updated_at?: string;
};
