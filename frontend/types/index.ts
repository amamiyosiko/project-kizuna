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

export type Ticket = {
  id: number;
  ticket_no: string;
  platform?: string;
  marketplace?: string;
  store_id?: number;
  buyer_name: string;
  buyer_id?: string;
  order_no?: string;
  asin?: string;
  sku?: string;
  subject?: string;
  status?: string;
  priority?: string;
  category?: string;
  risk_level?: string;
  language?: string;
  assigned_user_id?: number;
  last_message_at?: string;
  resolved_at?: string;
  closed_at?: string;
  created_at?: string;
  updated_at?: string;
};

export type TicketMessage = {
  id: number;
  ticket_id: number;
  sender_type: "CUSTOMER" | "AGENT" | "AI" | "SYSTEM" | string;
  message_type?: string;
  content: string;
  attachment_count?: number;
  created_by?: number;
  created_at?: string;
};

export type TicketEvent = {
  id: number;
  ticket_id: number;
  event_type: string;
  title: string;
  description?: string;
  actor_type?: string;
  actor_user_id?: number;
  created_at?: string;
};
