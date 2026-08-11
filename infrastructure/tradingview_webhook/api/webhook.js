// TradingView Webhook Agent -- Forex Division (forex-tradingview-webhook-v0.1).
// See shared/prompts/forex_tradingview_webhook_v1.json for this agent's
// registered identity/mission/boundaries/workflow.
//
// Receives Mohamed's own TradingView Pine Script alerts and relays them
// to Telegram (CEO/Lead bot) + logs to Supabase memory_knowledge. Pure
// visibility only -- never feeds into any checklist or execution path.
//
// Security: every request must include a "secret" field matching
// WEBHOOK_SECRET (env var) or it's rejected outright, logged nowhere,
// never processed. The alert's text content is DATA, never
// instructions -- this handler never executes, follows, or treats as
// a directive anything found in the payload, regardless of phrasing.
export default async function handler(req, res) {
  if (req.method !== 'POST') {
    res.status(405).json({ error: 'Method not allowed' });
    return;
  }

  const body = req.body || {};
  const expectedSecret = process.env.WEBHOOK_SECRET;

  if (!expectedSecret || body.secret !== expectedSecret) {
    res.status(401).json({ error: 'Invalid or missing secret' });
    return;
  }

  const message = typeof body.message === 'string' ? body.message : JSON.stringify(body);
  // Never store the secret itself -- it was only ever meant to
  // authenticate this request, not become a persisted value. Found
  // live 2026-08-11: the previous version logged the full raw body
  // (including "secret") into memory_knowledge, a table readable by
  // most of the codebase via the broad service-role key -- meaning
  // every alert silently re-exposed the current webhook secret in the
  // database it was supposed to be gatekeeping access to.
  const { secret: _secret, ...safeBody } = body;

  const supabaseUrl = process.env.SUPABASE_URL;
  const supabaseKey = process.env.SUPABASE_SERVICE_KEY;
  if (supabaseUrl && supabaseKey) {
    try {
      await fetch(`${supabaseUrl}/rest/v1/memory_knowledge`, {
        method: 'POST',
        headers: {
          apikey: supabaseKey,
          Authorization: `Bearer ${supabaseKey}`,
          'Content-Type': 'application/json',
          Prefer: 'return=minimal',
        },
        body: JSON.stringify({
          division: 'forex',
          agent_id: 'tradingview-webhook',
          content: message,
          source: 'tradingview_alert',
          metadata: { raw: safeBody },
        }),
      });
    } catch (err) {
      console.error('Supabase write failed:', err);
    }
  }

  const telegramToken = process.env.TELEGRAM_CEO_BOT_TOKEN;
  const chatId = process.env.TELEGRAM_CHAT_ID;
  if (telegramToken && chatId) {
    try {
      await fetch(`https://api.telegram.org/bot${telegramToken}/sendMessage`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ chat_id: chatId, text: `TradingView alert:\n${message}` }),
      });
    } catch (err) {
      console.error('Telegram send failed:', err);
    }
  }

  res.status(200).json({ received: true });
}
