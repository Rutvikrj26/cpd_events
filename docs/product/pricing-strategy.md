# Pricing + Tax Plan (Platform as Merchant of Record)

This plan describes the work needed to switch to platform charges (platform MoR)
and mirror Eventbrite-style tax + fee handling.

## Goals
- Platform becomes merchant of record for ticket sales.
- Stripe Tax uses platform tax registrations (organizers do not enable Stripe Tax).
- Fees and tax are calculated consistently and shown clearly to attendees.
- Organizers receive payouts via transfers, net of platform fees.
- Minimal disruption to existing payment flows.

## Non-goals
- Replacing Stripe as the payment processor.
- Changing the event creation or registration UX beyond fee/tax messaging.
- Implementing multi-currency expansion beyond CAD/USD right now.

## Current State (Snapshot)
- Destination charges only: PaymentIntent created on platform account.
- Stripe Tax Calculation called on platform account.
- Fees: service fee (platform cut), processing fee passed to attendee.
- Service fee tax handled by platform (organizer GST/HST does not affect it).
- PaymentIntent created during registration (prior to payment).

## Target State (Eventbrite-style)
- Destination charges on platform account (PaymentIntent on platform).
- Stripe Tax Calculation on platform account using platform registrations.
- Transfer to connected account after payment success.
- Platform service fee collected as application fee (or explicit split).
- Organizers do not need Stripe Tax enabled.

## Stripe Model Choice
- Use Destination Charges only:
  - Create PaymentIntent on platform account.
  - Set `transfer_data.destination` to organizer connected account.
  - Use `application_fee_amount` for platform service fee.
  - Keep Stripe Tax on platform account.

## Data + Money Flow
1) Attendee pays total (ticket + fees + tax) to platform.
2) Platform pays organizer via transfer for ticket revenue (net of platform fee).
3) Stripe processing fees are borne by platform, but passed through to attendee in price.
4) Platform remits tax collected via Stripe Tax.

## Fee + Tax Rules (Current Business Decisions)
- Pass through Stripe processing fee to attendee.
- Platform fee = service fee (percent + fixed by currency).
- Tax applies to ticket + service fee; processing fee is non-taxable.
- If organizer has GST/HST registration number, service fee tax is skipped.
- Use Stripe Tax Calculation API for totals.

## Work Plan

### 1) Product + Legal Alignment
- Confirm merchant-of-record implications (chargebacks, disputes, refunds).
- Update Terms of Service and organizer agreements.
- Update payout disclosures and tax responsibility wording.
- Decide if organizer GST/HST number still affects service-fee tax treatment.

### 2) Rollout Strategy
- Switch all events to destination charges.
- Remove direct-charge logic and config toggles.

### 3) Backend - Stripe PaymentIntent
- Update `StripePaymentService.create_payment_intent`:
  - Remove `stripe_account` param for PaymentIntent creation.
  - Add `transfer_data.destination` (connected account).
  - Use `application_fee_amount` for platform fee.
  - Ensure `on_behalf_of` is not set (unless required for receipts).
- Move Stripe Tax calculations to platform (no `stripe_account`).
- Ensure tax calculation uses the platform registrations.
- Persist:
  - `payment_intent_id`
  - `transfer_id` (if using separate transfers)
  - fee + tax breakdown on registration.

### 4) Backend - Transfers
- Decide transfer timing:
  - Create transfer after successful payment (preferred).
  - Or use `transfer_data` to auto-transfer.
- Track transfer IDs for refunds/disputes.
- Add idempotency keys for transfers.

### 5) Backend - Webhooks
- Confirm webhook routing is on platform account only.
- Update webhook handlers to:
  - Read tax/fee metadata from PaymentIntent.
  - Record transfer status (if transfer on success).
  - Handle partial refunds and reverse transfers.

### 6) Backend - Refunds + Reversals
- Update refund flow:
  - Refund on platform PaymentIntent.
  - Reverse transfer to organizer if already paid.
- Implement logic for partial refunds:
  - Proportional reversal of transfer.
  - Adjust tax if Stripe Tax supports automatic adjustments.

### 7) Backend - Tax Registration Handling
- Remove organizer requirement to enable Stripe Tax.
- Use platform tax registration for all calculations.
- Keep organizer GST/HST number only for fee tax logic (if still required).

### 8) Backend - Pricing Calculation
- Confirm fee calculation order:
  1) Ticket price
  2) Service fee
  3) Tax on ticket + service fee
  4) Processing fee grossed-up on tax-inclusive base
  5) Final tax calc including non-taxable processing fee
- Ensure totals align with Stripe Tax `amount_total`.

### 9) Frontend - Payment UX
- Update copy to clarify:
  - Platform processes payments and taxes.
  - Organizer receives payouts after payment.
- Ensure payment breakdown uses `total_amount` from backend.
- Add "Complete payment" resume path for pending payment.

### 10) Frontend - Organizer UX
- Update payout/settings pages:
  - Clarify organizer does not need Stripe Tax setup.
  - Collect GST/HST number (if still needed for service-fee tax).

### 11) Infra + Config
- Ensure Stripe keys and webhook secret are platform account keys.
- Add config flag for payment model default.
- Keep per-currency fee tfvars (CAD, USD).

### 12) Testing
- Unit tests for:
  - PaymentIntent amounts and metadata.
  - Tax calc and fee breakdowns.
  - Transfer creation and reversal logic.
- Integration tests for:
  - Paid registration flow with tax calc.
  - Refund flow (full + partial).
  - Pending payment resume.

### 13) Migration Plan
- Phase 1: move all events to destination charges.
- Phase 2: migrate existing organizers.

### 14) Monitoring + Ops
- Add dashboards for:
  - PaymentIntent success rate.
  - Transfer failures.
  - Tax calc failures.
- Add alerts for missing tax registration or transfer failures.

## Acceptance Criteria
- Attendee can complete paid registration without organizer Stripe Tax setup.
- Stripe Tax calculates and returns totals on platform account.
- Organizer receives payouts via transfers.
- Refunds reverse transfers correctly.
- Event detail page shows correct registration status (pending/confirmed).
- Fee/tax breakdown matches Stripe totals.

## Open Decisions
- Keep or remove organizer GST/HST number logic for service fee tax?
- Transfer timing (auto transfer vs post-confirm transfer)?
- Single payment model for all events or gradual toggle?
