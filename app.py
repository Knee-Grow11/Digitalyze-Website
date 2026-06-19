"""
Shop storefront + AI FAQ chatbot.

The chatbot answers ONLY from knowledge_base.json (a lightweight RAG approach):
the shop's real info is injected into the model prompt on every request, so the
bot stays accurate instead of making things up.

Supported LLM providers (set LLM_PROVIDER + the matching API key as env vars):
  - gemini    -> GEMINI_API_KEY     (has a free tier; good default)
  - openai    -> OPENAI_API_KEY
  - anthropic -> ANTHROPIC_API_KEY

If no key is set, the app still runs and the bot falls back to keyword matching
over the FAQ, so you can develop and demo the site before wiring in a model.
"""

import os
import json
import datetime
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
KB_PATH = os.path.join(BASE_DIR, "knowledge_base.json")

# Captured leads live in memory only. On Render's free tier the filesystem is
# wiped on restart, so for production swap this for Google Sheets or a database.
LEADS = []


def load_kb():
    """Load the knowledge base fresh each call so edits show up without a restart."""
    with open(KB_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def build_system_prompt(kb):
    """Turn the knowledge base into a grounding prompt the model must stick to."""
    shop = kb["shop"]
    policies = kb["policies"]
    faq = kb["faq"]
    products = kb["products"]

    faq_text = "\n".join(f"Q: {item['q']}\nA: {item['a']}" for item in faq)
    policy_text = "\n".join(f"- {key.replace('_', ' ').title()}: {val}"
                            for key, val in policies.items())
    product_text = "\n".join(
        f"- {p['name']} ({p['price']}): {p['description']}" for p in products
    )

    return f"""You are the customer service assistant for {shop['name']}, an online shop selling on Shopee Malaysia.
Tagline: {shop['tagline']}
Location: {shop['location']}. Operating hours: {shop['operating_hours']}.
{shop['languages']}

Use ONLY the information below to answer. If a question is not covered here, say you are not sure and offer to connect the customer to the team on WhatsApp. Never invent prices, stock, delivery dates, or policies.

Be warm, concise, and helpful. Reply in the same language the customer uses (English or Bahasa Malaysia). When relevant, gently encourage the customer to check the shop's Shopee page to buy. Keep answers short, usually 1 to 3 sentences.

=== SHOP POLICIES ===
{policy_text}

=== FREQUENTLY ASKED QUESTIONS ===
{faq_text}

=== PRODUCTS ===
{product_text}
"""


# ---------------------------------------------------------------------------
# LLM provider calls
# ---------------------------------------------------------------------------

def call_gemini(system_prompt, user_message):
    import google.generativeai as genai
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        system_instruction=system_prompt,
    )
    resp = model.generate_content(user_message)
    return resp.text.strip()


def call_openai(system_prompt, user_message):
    from openai import OpenAI
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        max_tokens=300,
        temperature=0.3,
    )
    return resp.choices[0].message.content.strip()


def call_anthropic(system_prompt, user_message):
    import anthropic
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    resp = client.messages.create(
        model="claude-3-5-haiku-20241022",
        max_tokens=300,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )
    return resp.content[0].text.strip()


def fallback_answer(kb, user_message):
    """No API key configured: keyword-match over FAQ + policies.

    This only runs before you add an LLM key. With a key, the model handles
    phrasing far better. We still make this reasonably robust so the demo looks
    good out of the box.
    """
    msg = user_message.lower()

    # Build a searchable set of (answer, weighted_keywords) from FAQ and policies.
    # Distinctive words (cash, refund, warranty) are weighted higher than shared
    # words (delivery, ship) so a question maps to the right topic.
    candidates = []
    for item in kb["faq"]:
        kws = {w: 1 for w in item["q"].lower().replace("?", "").split() if len(w) > 3}
        candidates.append((item["a"], kws))

    policy_keywords = {
        "shipping": {"ship": 2, "shipping": 2, "courier": 3, "postage": 2, "sabah": 3, "sarawak": 3, "deliver": 1, "delivery": 1},
        "returns": {"return": 3, "returns": 3, "refund": 3, "exchange": 3, "damaged": 2, "wrong": 2, "broken": 2, "policy": 1},
        "payment": {"payment": 3, "pay": 3, "cash": 3, "cod": 3, "card": 3, "banking": 3, "fpx": 3, "shopeepay": 3, "method": 2},
        "warranty": {"warranty": 3, "guarantee": 2, "defect": 3, "faulty": 3},
        "stock": {"stock": 3, "available": 3, "availability": 3, "ready": 2},
    }
    for key, kws in policy_keywords.items():
        if key in kb["policies"]:
            candidates.append((kb["policies"][key], kws))

    best = None
    best_score = 0
    for answer, kw_weights in candidates:
        score = sum(weight for word, weight in kw_weights.items() if word in msg)
        if score > best_score:
            best_score = score
            best = answer

    if best and best_score > 0:
        return best
    shop = kb["shop"]
    return (f"I'm not sure about that one, but I'd be happy to connect you with our team. "
            f"You can message us on WhatsApp and we'll help you out. "
            f"Meanwhile, browse everything on our Shopee page: {shop['shopee_url']}")


def get_bot_reply(user_message):
    kb = load_kb()
    provider = os.environ.get("LLM_PROVIDER", "").lower()
    system_prompt = build_system_prompt(kb)
    try:
        if provider == "gemini" and os.environ.get("GEMINI_API_KEY"):
            return call_gemini(system_prompt, user_message)
        if provider == "openai" and os.environ.get("OPENAI_API_KEY"):
            return call_openai(system_prompt, user_message)
        if provider == "anthropic" and os.environ.get("ANTHROPIC_API_KEY"):
            return call_anthropic(system_prompt, user_message)
    except Exception as e:
        # Never crash the chat on a provider error; degrade gracefully.
        app.logger.error(f"LLM call failed: {e}")
        return fallback_answer(kb, user_message)
    return fallback_answer(kb, user_message)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    kb = load_kb()
    return render_template("index.html", shop=kb["shop"], products=kb["products"])


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()
    if not message:
        return jsonify({"reply": "Please type a question and I'll help you out."})
    reply = get_bot_reply(message)
    return jsonify({"reply": reply})


@app.route("/lead", methods=["POST"])
def lead():
    """Capture a customer's contact details (name + phone), mirroring Mampu AI's
    lead-collection feature. Stored in memory for the demo."""
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    phone = (data.get("phone") or "").strip()
    if not name or not phone:
        return jsonify({"ok": False, "error": "Name and phone are required."}), 400
    LEADS.append({
        "name": name,
        "phone": phone,
        "note": (data.get("note") or "").strip(),
        "time": datetime.datetime.now().isoformat(timespec="seconds"),
    })
    return jsonify({"ok": True, "message": "Thanks! Our team will reach out to you soon."})


@app.route("/admin/leads")
def admin_leads():
    """A simple view of captured leads. In production, protect this behind login."""
    kb = load_kb()
    return render_template("leads.html", leads=LEADS, shop=kb["shop"])


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
