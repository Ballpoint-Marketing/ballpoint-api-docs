/**
 * Ballpoint API Integration Example
 *
 * A minimal Express server that:
 *   1. Creates orders via the Ballpoint API
 *   2. Receives and verifies webhook events
 *   3. Tracks order status in memory
 *   4. Serves a simple dashboard
 *
 * Usage:
 *   BALLPOINT_API_KEY=pk_test_... WEBHOOK_SECRET=whsec_... npm start
 *   Open http://localhost:3000
 */

const express = require("express");
const crypto = require("crypto");
const { v4: uuidv4 } = require("uuid");

const app = express();
const PORT = process.env.PORT || 3000;

// --- Configuration ---

const BALLPOINT_BASE = process.env.BALLPOINT_BASE || "https://api.ballpointmarketing.com";
const API_KEY = process.env.BALLPOINT_API_KEY || "";
const WEBHOOK_SECRET = process.env.WEBHOOK_SECRET || "";

if (!API_KEY) {
  console.error("Set BALLPOINT_API_KEY (e.g. pk_test_...) before starting.");
  process.exit(1);
}

// --- In-memory order store (use a database in production) ---

const orders = new Map(); // order_id → { status, events[], createdAt }

// --- 1. Create an Order ---

app.post("/create-order", express.json(), async (req, res) => {
  const { campaign_id, product_type, postage_type, piece_count, envelope_style } = req.body;

  const idempotencyKey = uuidv4();

  const payload = {
    campaign_id: campaign_id || "camp_test",
    product_type: product_type || "4x6_printed",
    postage_type: postage_type || "first_class",
    piece_count: piece_count || 10,
  };
  if (envelope_style) payload.envelope_style = envelope_style;

  try {
    const response = await fetch(`${BALLPOINT_BASE}/v1/billing/orders`, {
      method: "POST",
      headers: {
        "X-Partner-Key": API_KEY,
        "Idempotency-Key": idempotencyKey,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });

    const data = await response.json();

    if (response.ok) {
      orders.set(data.order_id, {
        status: data.status,
        productType: payload.product_type,
        pieceCount: payload.piece_count,
        billing: data.billing,
        events: [],
        createdAt: new Date().toISOString(),
      });
    }

    res.status(response.status).json(data);
  } catch (err) {
    // Network error — safe to retry with the SAME idempotency key.
    // If the original request succeeded, you'll get the cached response.
    res.status(502).json({
      error: "Network error calling Ballpoint API",
      message: err.message,
      retryable: true,
      idempotency_key: idempotencyKey,
    });
  }
});

// --- 2. Receive Webhooks ---

// Webhook handler MUST use raw body for signature verification.
// express.json() would parse it before we can verify — use raw buffer instead.
app.post("/webhooks/ballpoint", express.raw({ type: "application/json" }), (req, res) => {
  const signature = req.headers["x-ballpoint-signature"] || "";
  const timestamp = req.headers["x-ballpoint-timestamp"] || "";
  const eventId = req.headers["x-ballpoint-event-id"] || "";

  // Step 1: Verify signature
  if (WEBHOOK_SECRET && !verifySignature(req.body, timestamp, signature, WEBHOOK_SECRET)) {
    console.warn(`Webhook rejected: invalid signature (event ${eventId})`);
    return res.status(400).json({ error: "Invalid signature" });
  }

  // Step 2: Reject stale timestamps (replay protection)
  //         Also reject timestamps more than 2 minutes in the future (clock skew)
  const timestampAge = Date.now() - new Date(timestamp).getTime();
  if (timestampAge > 5 * 60 * 1000 || timestampAge < -2 * 60 * 1000) {
    console.warn(`Webhook rejected: timestamp out of range (${timestamp})`);
    return res.status(400).json({ error: "Timestamp out of range" });
  }

  // Step 3: Parse payload
  const event = JSON.parse(req.body.toString());
  console.log(`Webhook received: ${event.type} (${eventId})`);

  // Step 4: Process event (idempotently — deduplicate on eventId)
  const orderId = event.data?.order_id;
  if (orderId && orders.has(orderId)) {
    const order = orders.get(orderId);

    // Deduplicate: skip if we've already processed this event ID
    if (order.events.some((e) => e.eventId === eventId)) {
      console.log(`Duplicate event ${eventId} — skipping`);
      return res.status(200).json({ received: true, duplicate: true });
    }

    // Update status
    order.status = event.data.display_status || event.data.production_status || order.status;
    order.events.push({
      eventId,
      type: event.type,
      status: order.status,
      receivedAt: new Date().toISOString(),
    });
  }

  // Always return 200 quickly — do heavy processing async
  res.status(200).json({ received: true });
});

function verifySignature(bodyBuffer, timestamp, signature, secret) {
  const expected = crypto
    .createHmac("sha256", secret)
    .update(timestamp + bodyBuffer.toString())
    .digest("hex");
  const received = signature.replace("sha256=", "");
  return crypto.timingSafeEqual(Buffer.from(expected, "hex"), Buffer.from(received, "hex"));
}

// --- 3. Dashboard ---

app.get("/", (_req, res) => {
  const rows = [...orders.entries()]
    .sort((a, b) => b[1].createdAt.localeCompare(a[1].createdAt))
    .map(
      ([id, o]) => `
      <tr>
        <td><code>${id}</code></td>
        <td>${o.productType}</td>
        <td>${o.pieceCount}</td>
        <td><strong>${o.status}</strong></td>
        <td>${o.events.length}</td>
        <td>${o.createdAt}</td>
      </tr>`
    )
    .join("");

  res.send(`<!DOCTYPE html>
<html>
<head><title>Ballpoint Integration Example</title>
<style>
  body { font-family: system-ui; max-width: 900px; margin: 2rem auto; }
  table { border-collapse: collapse; width: 100%; }
  th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
  th { background: #f5f5f5; }
  code { background: #eee; padding: 2px 4px; border-radius: 3px; }
  form { margin: 2rem 0; padding: 1rem; background: #f9f9f9; border-radius: 8px; }
  button { padding: 8px 16px; background: #2563eb; color: white; border: none; border-radius: 4px; cursor: pointer; }
</style>
</head>
<body>
  <h1>Ballpoint Integration Example</h1>

  <form id="orderForm">
    <h3>Create Test Order</h3>
    <button type="submit">Create 10x 4x6 Printed Postcards</button>
  </form>

  <h3>Orders</h3>
  <table>
    <thead><tr><th>Order ID</th><th>Product</th><th>Pieces</th><th>Status</th><th>Events</th><th>Created</th></tr></thead>
    <tbody>${rows || "<tr><td colspan='6'>No orders yet</td></tr>"}</tbody>
  </table>

  <script>
    document.getElementById("orderForm").addEventListener("submit", async (e) => {
      e.preventDefault();
      const res = await fetch("/create-order", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ piece_count: 10 }),
      });
      const data = await res.json();
      alert(res.ok ? "Order created: " + data.order_id : "Error: " + JSON.stringify(data));
      location.reload();
    });
  </script>
</body>
</html>`);
});

// --- Start ---

app.listen(PORT, () => {
  console.log(`Ballpoint integration example running on http://localhost:${PORT}`);
  console.log(`Webhook endpoint: POST http://localhost:${PORT}/webhooks/ballpoint`);
  console.log(`API key: ${API_KEY.slice(0, 12)}...`);
});
