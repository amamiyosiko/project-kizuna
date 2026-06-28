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
  ticket_id?: number;
  message_id?: number;
  ticket_message_id?: number;
  store_id?: number;
  file_name: string;
  content_type?: string;
  file_size?: number;
  bucket: string;
  object_key: string;
  status?: string;
  file_url?: string;
  can_preview?: boolean;
  created_at?: string;
};

export type PresignUploadResponse = {
  upload_url: string;
  bucket: string;
  object_key: string;
  file_url?: string;
  expires_seconds: number;
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

export type TicketStats = {
  total: number;
  new: number;
  open: number;
  processing: number;
  waiting_customer: number;
  waiting_platform: number;
  resolved: number;
  closed: number;
  p1: number;
  p2: number;
  high_risk: number;
  today_created: number;
};

export type TicketAIReply = {
  ticket_id: number;
  source_message_id: number;
  category: string;
  detected_intent?: string;
  risk_level: string;
  confidence_score: number;
  recommended_action?: string;
  auto_reply_allowed: boolean;
  reason?: string;
  tone: string;
  provider: string;
  model?: string;
  fallback_used?: boolean;
  reply_text: string;
  source_excerpt?: string;
};


export type AmazonStoreStatus = {
  id: number;
  store_name: string;
  store_code: string;
  marketplace?: string;
  seller_id?: string;
  status?: string;
  seller_id_ready: boolean;
};

export type AmazonCredentialStatus = {
  lwa_client_id: boolean;
  lwa_client_secret: boolean;
  refresh_token: boolean;
  marketplace_id: boolean;
  endpoint_region: string;
};

export type AmazonStatus = {
  stage: string;
  mode: string;
  auto_sync_enabled: boolean;
  ready_for_next_stage: boolean;
  credentials: AmazonCredentialStatus;
  stores: AmazonStoreStatus[];
  missing_items: string[];
  next_step?: string;
};

export type AmazonManualImportResponse = {
  success: boolean;
  ticket: Ticket;
  message: string;
};
