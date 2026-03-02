/**
 * Ballpoint Webhook Receiver — AWS Lambda
 *
 * Receives webhook events from the Ballpoint API, verifies the HMAC-SHA256
 * signature, checks for replay attacks, and returns 200.
 *
 * Environment variables:
 *   WEBHOOK_SECRET — your webhook secret (whsec_...)
 *
 * API Gateway configuration:
 *   - Use a Lambda proxy integration
 *   - The event.body is a string (raw body) when using proxy integration
 *   - If using REST API (not HTTP API), you may need to enable "binary media
 *     types" or a mapping template to pass the raw body through. HTTP API
 *     (v2) passes the body as a string by default.
 */

const crypto = require("crypto");

const WEBHOOK_SECRET = process.env.WEBHOOK_SECRET || "";

exports.handler = async (event) => {
  // Extract headers (API Gateway lowercases them)
  const headers = event.headers || {};
  const signature = headers["x-ballpoint-signature"] || "";
  const timestamp = headers["x-ballpoint-timestamp"] || "";
  const eventId = headers["x-ballpoint-event-id"] || "";

  // Raw body — API Gateway proxy integration provides this as a string.
  // API Gateway may base64-encode the body depending on content type config.
  let rawBody = event.body || "";
  if (event.isBase64Encoded) {
    rawBody = Buffer.from(rawBody, "base64").toString("utf-8");
  }

  // 1. Verify signature
  if (!verifySignature(rawBody, timestamp, signature, WEBHOOK_SECRET)) {
    console.warn(`Rejected: invalid signature (event ${eventId})`);
    return { statusCode: 400, body: JSON.stringify({ error: "Invalid signature" }) };
  }

  // 2. Reject stale timestamps (replay protection — 5 minute window)
  //    Also reject timestamps more than 2 minutes in the future (clock skew)
  const timestampAge = Date.now() - new Date(timestamp).getTime();
  if (timestampAge > 5 * 60 * 1000 || timestampAge < -2 * 60 * 1000) {
    console.warn(`Rejected: timestamp out of range (${timestamp})`);
    return { statusCode: 400, body: JSON.stringify({ error: "Timestamp out of range" }) };
  }

  // 3. Deduplicate on eventId to handle at-least-once delivery.
  //    Uses DynamoDB conditional put with a 24-hour TTL.
  const { DynamoDBClient, PutItemCommand } = require("@aws-sdk/client-dynamodb");
  const ddb = new DynamoDBClient({});
  try {
    await ddb.send(new PutItemCommand({
      TableName: "webhook-events",
      Item: {
        eventId: { S: eventId },
        ttl: { N: String(Math.floor(Date.now() / 1000) + 86400) },
      },
      ConditionExpression: "attribute_not_exists(eventId)",
    }));
  } catch (e) {
    if (e.name === "ConditionalCheckFailedException") {
      return { statusCode: 200, body: JSON.stringify({ received: true, duplicate: true }) };
    }
    throw e;
  }
  //    Alternative: ElastiCache/Redis with SETNX and TTL.

  // 4. Parse and process the event
  const payload = JSON.parse(rawBody);
  console.log(`Webhook received: ${payload.type} (${eventId})`);

  const orderId = payload.data?.order_id;
  const status = payload.data?.display_status;
  const userId = payload.data?.external_user_id;
  console.log(`Order ${orderId} → ${status} (user: ${userId})`);

  return {
    statusCode: 200,
    body: JSON.stringify({ received: true }),
  };
};

function verifySignature(body, timestamp, signature, secret) {
  const expected = crypto
    .createHmac("sha256", secret)
    .update(timestamp + body)
    .digest("hex");
  const received = signature.replace("sha256=", "");
  try {
    return crypto.timingSafeEqual(
      Buffer.from(expected, "hex"),
      Buffer.from(received, "hex")
    );
  } catch {
    return false;
  }
}
