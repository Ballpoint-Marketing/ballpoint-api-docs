# Ballpoint API — Express Integration Example

A minimal Node.js server that creates orders, receives webhooks, and displays status. Copy this as a starting point for your integration.

## Setup

```bash
npm install
```

## Run

```bash
BALLPOINT_API_KEY=pk_test_your_key_here \
WEBHOOK_SECRET=whsec_your_secret_here \
npm start
```

Open [http://localhost:3000](http://localhost:3000) to see the dashboard.

## What It Does

| Route | Purpose |
|-------|---------|
| `GET /` | Dashboard — lists orders and their current status |
| `POST /create-order` | Creates an order via the Ballpoint API |
| `POST /webhooks/ballpoint` | Receives webhook events from Ballpoint |

## Testing Webhooks Locally

Use [ngrok](https://ngrok.com) to expose your local server:

```bash
ngrok http 3000
```

Then register the ngrok URL as your webhook endpoint with Ballpoint:
`https://abc123.ngrok.io/webhooks/ballpoint`

## Key Patterns Demonstrated

**Idempotency**: Every order creation generates a unique `Idempotency-Key`. On network failure, retry with the same key — you'll never be double-charged.

**Signature verification**: The webhook handler verifies `X-Ballpoint-Signature` using HMAC-SHA256 before processing any event.

**Replay protection**: Rejects webhook payloads with timestamps older than 5 minutes or more than 2 minutes in the future.

**Deduplication**: Tracks processed `X-Ballpoint-Event-Id` values to skip duplicate deliveries.

## Files

- `server.js` — Complete integration in one file (~180 lines)
- `package.json` — Two dependencies: `express` and `uuid`
