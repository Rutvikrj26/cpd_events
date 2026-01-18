# Platform User Workflows

## Attendee Workflows

| Workflow | Steps |
|----------|-------|
| **Sign Up** | Landing → Sign up → Email verification → Profile setup (name, credentials) → Certificates linked (if any) |
| **Attend Event** | Receive invite email → Click Zoom link → Attend → Auto-logged |
| **Claim Certificate** | Receive cert email → View/download → Auto-added to dashboard |
| **Retroactive Claim** | Sign up with email → Onboarding shows "Found X certificates" → Auto-linked |
| **View Dashboard** | Login → See all certificates → Filter by date, org, CPD type |
| **Share/Verify Certificate** | Get shareable link → Public verification page (if privacy enabled) |
| **Download Certificate** | Dashboard → Select cert → Download PDF |
| **Track CPD Credits** | Dashboard → CPD page → View by type/period → Progress bars (if requirements set) |
| **Configure CPD Requirements** | Settings → CPD → Add annual requirements → Track progress |
| **Watch Recording** | Past event → Recordings tab → Watch video → Progress tracked |
| **Complete Learning Module** | Event → Learning dashboard → Watch content → Complete assignments |
| **Submit Assignment** | Learning → Assignment → Upload/enter submission → Await grade |
| **Join Waitlist** | Event full → "Join Waitlist" → See position → Notified if spot opens |

---

## Organizer Workflows

| Workflow | Steps |
|----------|-------|
| **Upgrade to Organizer** | Attendee dashboard → "Become Organizer" → Select plan → Payment → Onboarding |
| **Connect Zoom** | Settings → Integrations → Zoom OAuth → Authorize → Connected |
| **Reconnect Zoom** | Settings → Integrations → See "Expired" → Reconnect → Reauthorize |
| **Create Single Event** | New event → Title, date/time, CPD credits → Generate Zoom → Publish |
| **Create Multi-Session Event** | New event → Multi-session type → Add sessions → Configure attendance rules |
| **Add Learning Modules** | Event → Modules tab → Add modules → Add content → Configure release |
| **Create Assignment** | Event → Assignments → New → Configure submission/grading → Publish |
| **Grade Submission** | Event → Assignments → Submissions → Review → Score/feedback → Approve/Reject |
| **Invite Attendees** | Event → Registrations → Add emails / Import CSV / Use contact list |
| **Send Reminders** | Event → Send reminder (manual) or configured automatic reminders |
| **Monitor Live Event** | Event dashboard → Live tab → See join/leave in real-time |
| **Review Attendance** | Event (post) → Attendance tab → Review eligibility → Manual overrides |
| **Manage Waitlist** | Event → Registrations → Waitlist tab → Promote or configure auto-promote |
| **Publish Recording** | Event → Recordings tab → Set access level → Publish |
| **Issue Certificates** | Event → Certificates tab → Select template → Preview → Issue |
| **Revoke Certificate** | Certificate → Revoke → Enter reason → Confirm → Attendee notified |
| **Duplicate Event** | Event → More → Duplicate → Adjust date/title → Save as draft |
| **Manage Templates** | Templates → Upload/edit designs → Version history available |
| **Manage Contacts** | Contacts → Create lists → Import CSV (with column mapping) |
| **View Reports** | Reports → Date range → View stats/charts → Export |
| **Downgrade Account** | Settings → Account → Downgrade → Confirm → Events archived (read-only) |

---

## Account & Settings Workflows

| Workflow | Steps |
|----------|-------|
| **Edit Profile** | Settings → Profile → Update name, credentials, photo |
| **Edit Organizer Profile** | Settings → Profile → Logo, website, bio → Toggle public visibility |
| **Configure CPD Requirements** | Settings → CPD → Add credit types → Set annual targets |
| **Change Password** | Settings → Security → Current + new password |
| **Manage Email Preferences** | Settings → Notifications → Toggle by category |
| **Disconnect Zoom** | Settings → Integrations → Disconnect (warning shown) |
| **Export Data** | Settings → Account → Export → Wait for email → Download ZIP |
| **Downgrade to Attendee** | Settings → Account → Downgrade → Confirm (events become read-only) |
| **Delete Account** | Settings → Account → Delete → Type "DELETE" → Confirm |

---

## Billing Workflows

| Workflow | Steps |
|----------|-------|
| **Start Trial** | Upgrade to organizer → 14-day trial starts → Banner shows countdown |
| **Add Payment Method** | Settings → Subscription → Add card → Stripe form |
| **Change Plan** | Settings → Subscription → Change plan → Confirm → Prorated |
| **Payment Failed** | Banner appears → Update payment → Retry charge |
| **Cancel Subscription** | Settings → Subscription → Cancel → Confirm → Grace period → Read-only |
| **Reactivate** | Settings → Subscription → Reactivate → Select plan → Full access restored |

---

## Edge Case Resolutions

| Scenario | Resolution |
|----------|------------|
| **Attendee joins without invite** | Captured in attendance if they match by email; unmatched shown separately for manual matching |
| **Attendee joins late / leaves early** | Minimum attendance threshold (default 80%) determines certificate eligibility; organizer can override |
| **Organizer cancels event** | All registrants notified via email; Zoom meeting deleted; event marked cancelled |
| **Attendee disputes attendance** | Organizer manually marks attendance via Attendance tab override |
| **Certificate correction needed** | Revoke certificate (with reason) → Reissue with corrections; attendee notified of both |
| **Zoom connection expires** | Warning banner on dashboard; affected events listed; one-click reconnect |
| **Payment fails** | 7-day grace period; daily email reminders; banner on all pages |
| **Subscription cancelled** | Read-only access to existing events; cannot create new; can export data |
| **Guest registers, later creates account** | Certificates auto-linked during onboarding; shown "Found X certificates" |
| **Waitlist spot opens** | If auto-promote: next person promoted + notified; if manual: organizer notified |
| **Recording not available** | Different access level messages based on why (didn't attend, no certificate, etc.) |
| **Assignment past due** | Late submissions accepted if configured; penalty applied to score |
| **Organizer downgrades** | Must have no active events; existing events archived; certificates remain valid |
