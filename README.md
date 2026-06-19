# Shopee Shop + AI FAQ Chatbot

A storefront website for a Shopee shop with a built-in AI assistant that answers
customer questions (shipping, returns, stock, products) using **only your shop's
real information** — a lightweight RAG approach that keeps the bot accurate
instead of making things up. When it can't answer, it hands the customer off to
WhatsApp, just like a real customer-service flow.

Built with Flask. Designed to deploy on Render's free tier.

---

## What's inside

| File | What it does |
|------|--------------|
| `app.py` | Flask server: homepage, `/chat` (the AI endpoint), `/lead` (captures contacts), `/admin/leads` |
| `knowledge_base.json` | **Your shop's info** — edit this with your real FAQ, policies, and products |
| `templates/index.html` | The storefront homepage + chat widget |
| `templates/leads.html` | A simple page to view captured leads |
| `static/style.css` | All styling |
| `static/chat.js` | Chat widget behaviour |
| `static/product*.svg` | Placeholder product images — replace with your photos |
| `requirements.txt` | Python dependencies |

---

## 1. Run it locally

```bash
pip install -r requirements.txt
python app.py
```

Open http://localhost:5000. The chatbot works **immediately** even without an API
key — it falls back to matching questions against your FAQ. Add a key (next step)
to unlock full conversational AI.

## 2. Add an AI model (recommended)

The bot supports three providers. **Google Gemini has a free tier**, so it's the
easiest start.

1. Get a key:
   - Gemini: https://aistudio.google.com/app/apikey (free)
   - OpenAI: https://platform.openai.com/api-keys (paid)
   - Anthropic: https://console.anthropic.com/ (paid)
2. Copy `.env.example` to `.env` and fill in your key + provider.
3. In `requirements.txt`, make sure the matching library line is uncommented
   (Gemini's is on by default).
4. Restart the app.

To load `.env` automatically when running locally, either export the variables in
your shell or `pip install python-dotenv` and add `from dotenv import load_dotenv; load_dotenv()` at the top of `app.py`.

## 3. Make it YOUR shop

Everything customer-facing comes from `knowledge_base.json`. Edit:

- **`shop`** — your name, tagline, Shopee URL, WhatsApp number (format: `60123456789`), location, hours.
- **`policies`** — shipping, returns, payment, warranty, stock. Write these in plain language; the AI reads them directly.
- **`faq`** — common questions and answers.
- **`products`** — name, price, description, Shopee link, and image filename for each item.

Then drop your real product photos into `static/` and update each product's
`image` field. Square images (1:1) look best.

---

## 4. Deploy to Render

1. Push this folder to a **GitHub** repository.
   *(Never commit `.env` — it's already in `.gitignore`.)*
2. On https://render.com → **New** → **Web Service** → connect your repo.
3. Settings:
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `gunicorn app:app`
4. Under **Environment**, add your variables:
   - `LLM_PROVIDER` = `gemini` (or your choice)
   - `GEMINI_API_KEY` = your key
5. Click **Create Web Service**. You'll get a live `…onrender.com` URL with HTTPS.

### Connect your own domain
In the service's **Settings → Custom Domains**, add your domain and create the DNS
records Render shows you at your registrar. **Remove any old AAAA (IPv6) records**
or the domain won't resolve. DNS can take from minutes up to a day.

### Two free-tier things to know
- **The app sleeps when idle**, so the first visit after a quiet spell is slow
  (a cold start). Before a demo, open the site a minute early to wake it — or use
  the $7/month Starter plan to keep it always on.
- **The filesystem resets on restart**, so captured leads (stored in memory) are
  cleared. For permanent storage, connect a Google Sheet or a database.

---

## How the AI stays accurate (talking point)

Rather than letting a language model answer from general knowledge — which would
invent wrong delivery times and prices — this app injects your `knowledge_base.json`
into the model's instructions on every request and tells it to answer only from
that. This is the same retrieval-grounding pattern production chatbots use to stay
reliable, scaled down to a single shop.
