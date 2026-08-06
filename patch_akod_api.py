import re

file_path = "/var/www/akod/app/dist/server/pages/api/lead.astro.mjs"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

new_odoo_client = '''class OdooClient {
  url;
  tenantUuid;
  webhookSecret;
  constructor() {
    this.url = process.env.TCRM_LEAD_WEBHOOK_URL || "https://akod.tcrm.online/webhook/akod/lead";
    this.tenantUuid = process.env.TCRM_TENANT_UUID || "ecfe7537-1eba-4c1d-b0c2-4d87f06dca7f";
    this.webhookSecret = process.env.TCRM_LEAD_SECRET || "e275aaaf864c976f522dd845b88828c0332c3f57a5cbab4f524a7a60e196a9e5";
  }
  async createLead(payload, options = {}) {
    const webhookUrl = this.url;
    const idempotencyKey = options.idempotencyKey || payload.idempotency_key || crypto.randomUUID();
    const correlationId = options.correlationId || payload.correlation_id || `corr_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;

    const leadPayload = {
      name: `${payload.contact_name} - ${payload.x_service_interest || "Web/Yazılım Talebi"}`,
      contact_name: payload.contact_name,
      email_from: payload.email_from,
      phone: payload.phone,
      partner_name: payload.contact_name,
      description: payload.description,
      service: payload.x_service_interest || "",
      budget: payload.x_budget_range || "",
      page_url: payload.website || "https://akod.tech",
      utm_source: payload.utm_source || "",
      utm_medium: payload.utm_medium || "",
      utm_campaign: payload.utm_campaign || ""
    };

    const rawBody = JSON.stringify(leadPayload);
    const timestamp = Math.floor(Date.now() / 1000).toString();
    const bodyHash = crypto.createHash("sha256").update(Buffer.from(rawBody, "utf8")).digest("hex");

    const canonicalPayload = [
      "v1",
      "POST",
      "/webhook/akod/lead",
      timestamp,
      this.tenantUuid,
      idempotencyKey,
      bodyHash
    ].join("\\n");

    const signature = crypto.createHmac("sha256", this.webhookSecret).update(canonicalPayload, "utf8").digest("hex");

    const resp = await fetch(webhookUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-TCRM-Signature-Version": "v1",
        "X-TCRM-Timestamp": timestamp,
        "X-TCRM-Tenant": this.tenantUuid,
        "X-TCRM-Idempotency-Key": idempotencyKey,
        "X-TCRM-Correlation-ID": correlationId,
        "X-TCRM-Signature": signature
      },
      body: rawBody
    });

    const responseText = await resp.text().catch(() => "");
    let responseData = {};
    try {
      responseData = JSON.parse(responseText);
    } catch (_) {}

    return {
      status: resp.status,
      ok: resp.ok,
      data: responseData,
      correlationId,
      idempotencyKey
    };
  }
}'''

# Replace OdooClient class in content
content = re.sub(r'class OdooClient \{[\s\S]*?\n\}', new_odoo_client, content, count=1)

# Ensure \n is properly escaped in join string
content = content.replace('.join("\n")', '.join("\\n")')

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Updated api/lead.astro.mjs successfully!")
