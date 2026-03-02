/**
 * Ballpoint Webhook Receiver — Cloudflare Worker
 *
 * Receives webhook events from the Ballpoint API, verifies the HMAC-SHA256
 * signature using the Web Crypto API, and rejects stale/replayed requests.
 *
 * Secrets (set via `wrangler secret put`):
 *   WEBHOOK_SECRET — your webhook secret (whsec_...)
 */

export default {
  async fetch(request, env) {
    if (request.method !== "POST") {
      return new Response("Method not allowed", { status: 405 });
    }

    const signature = request.headers.get("x-ballpoint-signature") || "";
    const timestamp = request.headers.get("x-ballpoint-timestamp") || "";
    const eventId = request.headers.get("x-ballpoint-event-id") || "";

    // Read raw body once (body can only be consumed once in Workers)
    const rawBody = await request.text();

    // 1. Verify signature
    const valid = await verifySignature(rawBody, timestamp, signature, env.WEBHOOK_SECRET);
    if (!valid) {
      console.log(`Rejected: invalid signature (event ${eventId})`);
      return Response.json({ error: "Invalid signature" }, { status: 400 });
    }

    // 2. Reject stale timestamps (replay protection — 5 minute window)
    //    Also reject timestamps more than 2 minutes in the future (clock skew)
    const timestampAge = Date.now() - new Date(timestamp).getTime();
    if (timestampAge > 5 * 60 * 1000 || timestampAge < -2 * 60 * 1000) {
      console.log(`Rejected: timestamp out of range (${timestamp})`);
      return Response.json({ error: "Timestamp out of range" }, { status: 400 });
    }

    // 3. Deduplicate on eventId to handle at-least-once delivery.
    //    Recommended: store event IDs in KV with expirationTtl.
    //
    //    const seen = await env.WEBHOOK_EVENTS.get(eventId);
    //    if (seen) {
    //      return Response.json({ received: true, duplicate: true }, { status: 200 });
    //    }
    //    await env.WEBHOOK_EVENTS.put(eventId, "1", { expirationTtl: 86400 });
    //
    //    For strong consistency, use Durable Objects instead of KV.

    // 4. Parse and process the event
    const payload = JSON.parse(rawBody);
    console.log(`Webhook received: ${payload.type} (${eventId})`);

    const orderId = payload.data?.order_id;
    const status = payload.data?.display_status;
    console.log(`Order ${orderId} → ${status}`);

    return Response.json({ received: true }, { status: 200 });
  },
};

async function verifySignature(body, timestamp, signature, secret) {
  const encoder = new TextEncoder();

  const key = await crypto.subtle.importKey(
    "raw",
    encoder.encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"]
  );

  const data = encoder.encode(timestamp + body);
  const sig = await crypto.subtle.sign("HMAC", key, data);
  const expected = Array.from(new Uint8Array(sig))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");

  const received = signature.replace("sha256=", "");

  // Constant-length comparison (not truly constant-time in JS,
  // but sufficient for webhook verification)
  if (expected.length !== received.length) return false;
  let mismatch = 0;
  for (let i = 0; i < expected.length; i++) {
    mismatch |= expected.charCodeAt(i) ^ received.charCodeAt(i);
  }
  return mismatch === 0;
}
