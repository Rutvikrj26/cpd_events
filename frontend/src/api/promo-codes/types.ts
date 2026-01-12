/**
 * Promo Code types
 */

export interface PromoCode {
  uuid: string;
  code: string;
  description: string;
  currency: string;
  discount_type: 'percentage' | 'fixed_amount';
  discount_value: string;
  max_discount_amount: string | null;
  discount_display: string;
  is_active: boolean;
  valid_from: string | null;
  valid_until: string | null;
  max_uses: number | null;
  max_uses_per_user: number;
  current_uses: number;
  uses_remaining: number | null;
  minimum_order_amount: string;
  first_time_only: boolean;
  is_valid: boolean;
  is_expired: boolean;
  events_data: Array<{ uuid: string; title: string }>;
  created_at: string;
  updated_at: string;
}

export interface PromoCodeUsage {
  uuid: string;
  promo_code_code: string;
  registration_uuid: string;
  event_title: string;
  user_email: string;
  original_price: string;
  discount_amount: string;
  final_price: string;
  created_at: string;
}

export interface PromoCodeValidationResult {
  valid: boolean;
  code?: string;
  discount_type?: 'percentage' | 'fixed_amount';
  discount_value?: string;
  discount_display?: string;
  original_price?: string;
  discount_amount?: string;
  final_price?: string;
  promo_code_uuid?: string;
  error?: string;
}

export interface CreatePromoCodeRequest {
  code: string;
  description?: string;
  currency?: string;
  discount_type: 'percentage' | 'fixed_amount';
  discount_value: number;
  max_discount_amount?: number;
  is_active?: boolean;
  valid_from?: string;
  valid_until?: string;
  max_uses?: number;
  max_uses_per_user?: number;
  minimum_order_amount?: number;
  first_time_only?: boolean;
  event_uuids?: string[];
}

export type UpdatePromoCodeRequest = Partial<CreatePromoCodeRequest>;

export interface ValidatePromoCodeRequest {
  code: string;
  event_uuid: string;
  email: string;
}
