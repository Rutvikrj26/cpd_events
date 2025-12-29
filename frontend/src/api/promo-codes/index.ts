/**
 * Promo Codes API client
 */

import api from '../client';
import type {
  PromoCode,
  PromoCodeUsage,
  PromoCodeValidationResult,
  CreatePromoCodeRequest,
  UpdatePromoCodeRequest,
  ValidatePromoCodeRequest,
} from './types';

// ============================================================================
// Organizer Endpoints
// ============================================================================

/**
 * Get all promo codes for the current organizer
 */
export async function getPromoCodes(): Promise<PromoCode[]> {
  const response = await api.get<PromoCode[]>('/promo-codes/');
  return response.data;
}

/**
 * Get a single promo code by UUID
 */
export async function getPromoCode(uuid: string): Promise<PromoCode> {
  const response = await api.get<PromoCode>(`/promo-codes/${uuid}/`);
  return response.data;
}

/**
 * Create a new promo code
 */
export async function createPromoCode(data: CreatePromoCodeRequest): Promise<PromoCode> {
  const response = await api.post<PromoCode>('/promo-codes/', data);
  return response.data;
}

/**
 * Update a promo code
 */
export async function updatePromoCode(uuid: string, data: UpdatePromoCodeRequest): Promise<PromoCode> {
  const response = await api.patch<PromoCode>(`/promo-codes/${uuid}/`, data);
  return response.data;
}

/**
 * Delete a promo code
 */
export async function deletePromoCode(uuid: string): Promise<void> {
  await api.delete(`/promo-codes/${uuid}/`);
}

/**
 * Toggle promo code active status
 */
export async function togglePromoCodeActive(uuid: string): Promise<{ is_active: boolean; message: string }> {
  const response = await api.post<{ is_active: boolean; message: string }>(`/promo-codes/${uuid}/toggle_active/`);
  return response.data;
}

/**
 * Get usage records for a promo code
 */
export async function getPromoCodeUsages(uuid: string): Promise<PromoCodeUsage[]> {
  const response = await api.get<PromoCodeUsage[]>(`/promo-codes/${uuid}/usages/`);
  return response.data;
}

// ============================================================================
// Public Endpoints
// ============================================================================

/**
 * Validate a promo code for registration
 */
export async function validatePromoCode(data: ValidatePromoCodeRequest): Promise<PromoCodeValidationResult> {
  const response = await api.post<PromoCodeValidationResult>('/public/promo-codes/validate/', data);
  return response.data;
}
