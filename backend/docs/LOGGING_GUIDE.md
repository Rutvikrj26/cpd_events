# Logging Best Practices

## Overview

The CPD Events backend uses **structured JSON logging** in production for easy parsing and analysis. Logs are written to stdout/stderr and can be collected by GCP Cloud Logging, Sentry, or other log aggregation tools.

## Log Levels

Use the appropriate log level for your messages:

| Level | When to Use | Examples |
|-------|-------------|----------|
| **DEBUG** | Detailed diagnostic info (disabled in production) | Variable values, function entry/exit, loop iterations |
| **INFO** | General informational messages about normal operations | User logged in, event created, email sent, task completed |
| **WARNING** | Something unexpected but handled gracefully | Deprecated API usage, retry attempts, fallback to defaults |
| **ERROR** | Serious problem that prevented an operation | Failed API calls, database errors, caught exceptions |
| **CRITICAL** | System failure requiring immediate attention | Uncaught exceptions, data corruption, service unavailable |

## Usage Examples

### ✅ GOOD Logging

```python
import logging

logger = logging.getLogger(__name__)  # Use module-specific logger

# Include context with 'extra' parameter for structured logging
logger.info(
    "Event created successfully",
    extra={
        "event_uuid": str(event.uuid),
        "event_title": event.title,
        "organizer_id": event.organizer_id,
        "event_type": event.event_type,
        "capacity": event.capacity
    }
)

# Log errors with exception info
try:
    send_verification_email(user.email, token)
except Exception as e:
    logger.error(
        "Failed to send verification email",
        extra={
            "user_uuid": str(user.uuid),
            "user_email": user.email,
            "error_type": type(e).__name__,
            "error_message": str(e)
        },
        exc_info=True  # Include full stack trace
    )
    # Handle the error appropriately

# Log warnings for non-critical issues
if attempt_count >= 3:
    logger.warning(
        "User exceeded login attempts",
        extra={
            "user_email": email,
            "attempt_count": attempt_count,
            "ip_address": request.META.get('REMOTE_ADDR')
        }
    )
```

### ❌ BAD Logging

```python
# ❌ Don't use print() statements
print("DEBUG: User logged in")

# ❌ Don't log sensitive data
logger.info(f"User password: {password}")  # NEVER!
logger.info(f"Credit card: {card_number}")  # NEVER!
logger.info(f"API key: {api_key}")  # NEVER!

# ❌ Don't use generic messages
logger.error("Error occurred")  # Not helpful!
logger.warning("Something went wrong")  # Too vague!

# ❌ Don't log in tight loops (performance killer)
for item in million_items:
    logger.debug(f"Processing {item}")  # Will kill performance!

# ❌ Don't concatenate strings in logs
logger.info("User " + user.email + " created event " + event.title)  # Use extra dict instead

# ❌ Don't log at wrong level
logger.error("User logged in")  # Should be INFO
logger.info("Database connection failed")  # Should be ERROR
```

## Sensitive Data Rules

### NEVER Log:
- ❌ Passwords (plain text or hashed)
- ❌ API keys / tokens / secrets
- ❌ Credit card numbers (full or partial)
- ❌ Bank account numbers
- ❌ Stripe secrets / webhook secrets
- ❌ Full session data
- ❌ Encryption keys
- ❌ Social Security Numbers
- ❌ Personal health information
- ❌ Private messages content
- ❌ JWT tokens (full token)

### Safe to Log:
- ✅ UUIDs (user_uuid, event_uuid, order_uuid)
- ✅ Email addresses (for admin debugging)
- ✅ Timestamps
- ✅ HTTP status codes
- ✅ Error messages (sanitized)
- ✅ Request IDs
- ✅ IP addresses (for security monitoring)
- ✅ User agent strings
- ✅ Enum values (status, type, category)

### Conditional Logging (Development Only):
```python
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

# Only log sensitive URLs in development
logger.info(
    "Password reset link generated",
    extra={
        "user_uuid": str(user.uuid),
        "user_email": user.email,
        "reset_url": reset_url if settings.DEBUG else "[REDACTED]"
    }
)
```

## Structured Logging Format

In production, logs are output as JSON for easy parsing:

```json
{
  "asctime": "2026-01-19T10:30:45",
  "name": "accounts.views",
  "levelname": "INFO",
  "message": "User logged in successfully",
  "pathname": "/app/accounts/views.py",
  "lineno": 145,
  "user_uuid": "abc-123",
  "user_email": "user@example.com",
  "ip_address": "192.168.1.1"
}
```

This allows for:
- Easy searching by field (e.g., all logs for user_uuid)
- Aggregation and metrics (e.g., count of errors by error_type)
- Alerting based on specific conditions
- Integration with log analysis tools (GCP Logging, Datadog, Splunk)

## Per-App Loggers

Use module-specific loggers for better log organization:

```python
# In accounts/views.py
logger = logging.getLogger(__name__)  # Creates 'accounts.views' logger

# In events/services.py
logger = logging.getLogger(__name__)  # Creates 'events.services' logger

# In billing/webhooks.py
logger = logging.getLogger(__name__)  # Creates 'billing.webhooks' logger
```

This allows filtering logs by app:
```bash
# View only billing-related logs
gcloud logging read 'jsonPayload.name=~"billing"' --limit=100

# View only error logs from accounts app
gcloud logging read 'severity>=ERROR AND jsonPayload.name=~"accounts"' --limit=50
```

## Configuration

### Development (.env.dev)
```bash
LOG_LEVEL=DEBUG           # Show all logs including debug
DB_LOG_LEVEL=WARNING      # Don't spam with SQL queries
```

### Production (.env.prod)
```bash
LOG_LEVEL=INFO            # Production default
DB_LOG_LEVEL=WARNING      # Only log slow/problematic queries
```

### Temporary Debug Mode (Production)
If you need to debug a production issue:
```bash
LOG_LEVEL=DEBUG           # Temporarily enable debug logs
DB_LOG_LEVEL=DEBUG        # See all SQL queries
```

**⚠️ WARNING:** Remember to revert to INFO after debugging! DEBUG logs can contain sensitive data and create huge log volumes.

## Common Patterns

### API Request/Response Logging
```python
logger.info(
    "API request received",
    extra={
        "method": request.method,
        "path": request.path,
        "user_uuid": str(request.user.uuid) if request.user.is_authenticated else "anonymous",
        "ip_address": request.META.get('REMOTE_ADDR'),
        "user_agent": request.META.get('HTTP_USER_AGENT', '')[:200]
    }
)
```

### Database Operation Logging
```python
logger.info(
    "Database record created",
    extra={
        "model": "Event",
        "record_uuid": str(event.uuid),
        "created_by": str(request.user.uuid)
    }
)
```

### External API Call Logging
```python
logger.info(
    "Calling Stripe API",
    extra={
        "endpoint": "/v1/checkout/sessions",
        "method": "POST",
        "request_id": stripe_request_id
    }
)
```

### Background Task Logging
```python
logger.info(
    "Background task started",
    extra={
        "task_name": "send_course_enrollment_confirmation",
        "task_id": task_id,
        "args": {"enrollment_id": enrollment_id}
    }
)
```

## Viewing Logs

### Local Development
```bash
# View real-time logs
python manage.py runserver

# Logs appear in terminal with JSON formatting
```

### GCP Cloud Run (Production)
```bash
# View recent logs
gcloud run services logs read backend --limit=100

# Follow logs in real-time
gcloud run services logs tail backend

# Filter by severity
gcloud logging read 'severity>=ERROR' --limit=50

# Filter by specific field
gcloud logging read 'jsonPayload.user_uuid="abc-123"' --limit=50

# Export logs to BigQuery for analysis
gcloud logging sinks create bigquery-export \
  bigquery.googleapis.com/projects/PROJECT_ID/datasets/logs_dataset
```

## Performance Considerations

1. **Don't log in tight loops:**
   ```python
   # ❌ BAD: Logs thousands of times
   for item in items:
       logger.debug(f"Processing {item}")
   
   # ✅ GOOD: Log summary only
   logger.info(f"Processing {len(items)} items")
   # ... process items ...
   logger.info(f"Completed processing {len(items)} items")
   ```

2. **Use lazy string formatting:**
   ```python
   # ❌ BAD: String formatted even if DEBUG disabled
   logger.debug("User: " + str(user) + " did something")
   
   # ✅ GOOD: Only formatted if log level enabled
   logger.debug("User: %s did something", user)
   ```

3. **Conditional expensive operations:**
   ```python
   # ❌ BAD: Expensive serialization even if not logged
   logger.debug(f"Full data: {json.dumps(huge_object)}")
   
   # ✅ GOOD: Only serialize if DEBUG enabled
   if logger.isEnabledFor(logging.DEBUG):
       logger.debug(f"Full data: {json.dumps(huge_object)}")
   ```

## Alerting

Configure alerts in Sentry or GCP Monitoring for:

- **ERROR or CRITICAL logs** → Immediate notification
- **High rate of WARNING logs** → Alert if > 100/min
- **Specific error patterns** → Alert on "Database connection failed"
- **Slow operations** → Alert if response time > 5s

## Troubleshooting

### Logs not appearing?
1. Check LOG_LEVEL is not too restrictive (should be INFO or DEBUG)
2. Verify logger name is correct (`logger = logging.getLogger(__name__)`)
3. Check if logs are being filtered by handler configuration
4. Ensure `propagate=True` if you want logs to bubble up to parent loggers

### Too many logs?
1. Increase LOG_LEVEL to WARNING or ERROR
2. Disable debug logging for noisy modules
3. Use log sampling for high-volume events

### Logs missing context?
1. Always use `extra={}` parameter to add structured data
2. Include request_id for request tracing
3. Add user_uuid to every log where possible

---

## Summary

✅ **DO:**
- Use structured logging with `extra={}` parameter
- Include relevant context (UUIDs, user info, errors)
- Use appropriate log levels
- Sanitize sensitive data
- Log errors with `exc_info=True`

❌ **DON'T:**
- Use `print()` statements
- Log passwords, tokens, or secrets
- Log in tight loops
- Use generic error messages
- Concatenate strings in log messages

For questions or issues, contact the development team.

**Last Updated:** January 19, 2026
