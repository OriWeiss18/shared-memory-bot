# Shared Memory Bot — Gaia Local + WhatsApp Development Setup

This guide explains how Gaia can run the **Shared Memory Bot** locally and work with the **same Meta app, the same WhatsApp bot/test number, and the same Supabase database** that Ori is already using.

This is the recommended setup for the current MVP.

---

## 0. What is shared and what is local?

For now, both developers use the same project infrastructure:

### Shared between Ori and Gaia

- GitHub repository
- Supabase project and database
- Google Cloud project
- Meta app: `Shared Memory Bot`
- WhatsApp Business Account used by the project
- Meta WhatsApp bot/test number
- WhatsApp Phone Number ID
- Existing webhook subscription configuration
- Existing WABA subscription to the Meta app

### Local / personal for each developer

Each developer should have her own:

- local repository checkout
- Python virtual environment (`.venv`)
- `.env` file
- Gemini API key
- Meta WhatsApp access token
- webhook verification token
- ngrok installation and tunnel

> Never commit `.env`, access tokens, API keys, or secret keys to Git.

---

# 1. What Gaia does NOT need to recreate

Gaia does **not** need to repeat the entire Meta setup that Ori already completed.

She does **not** need to create:

- a new Meta app
- a new WhatsApp Business Account
- a new WhatsApp bot/test number
- a new Supabase project
- a new database schema
- a new privacy-policy page
- a new WABA-to-app subscription, as long as the existing Meta app remains subscribed
- a new GitHub repository

The goal is for Gaia to get access to the existing project and run the same code locally.

---

# 2. Prerequisites to install on Gaia's computer

Gaia should have the following installed.

## 2.1 Git

Check:

```bash
git --version
```

If Git is missing, install Git from:

```text
https://git-scm.com/
```

---

## 2.2 Python 3.12

The project is currently developed with Python 3.12.

Check:

```bash
python --version
```

or on Windows:

```powershell
py --version
```

Recommended result:

```text
Python 3.12.x
```

If Python 3.12 is not installed, install it before creating the virtual environment.

---

## 2.3 ngrok

ngrok is required only when Gaia wants Meta to send **real WhatsApp webhook events** to her local computer.

Check:

```bash
ngrok version
```

If it is not installed, install ngrok from:

```text
https://ngrok.com/download
```

After creating/logging into an ngrok account, connect the local installation to the account using the command shown in the ngrok dashboard.

It normally looks like:

```bash
ngrok config add-authtoken <YOUR_NGROK_AUTH_TOKEN>
```

The auth token is Gaia's own ngrok credential and must not be committed to Git.

---

# 3. Get the latest project code

If Gaia already cloned the repository:

```bash
git checkout main
git pull origin main
```

If she is starting a new feature:

```bash
git checkout -b feature/<feature-name>
```

If she does not have the repository yet:

```bash
git clone <repository-url>
cd shared-memory-bot
```

---

# 4. Create the local Python virtual environment

The `.venv` folder should be created separately on every computer.

Do not copy Ori's `.venv`.

## Windows

From the repository directory:

```powershell
py -3.12 -m venv .venv
```

Activate it:

```powershell
.venv\Scripts\activate
```

Install all Python dependencies:

```powershell
pip install -r requirements.txt
```

## macOS / Linux

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

The project dependencies are installed from `requirements.txt`, so Gaia should **not** manually reinstall every Python package one by one.

The requirements currently cover the project's backend packages such as:

- FastAPI
- Uvicorn
- httpx
- python-dotenv
- Supabase client
- Google GenAI SDK

---

# 5. Create Gaia's local `.env`

Gaia must create her own `.env` file.

Do not send her Ori's `.env` file.

On macOS/Linux:

```bash
cp .env.example .env
```

On Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

The current `.env.example` contains:

```env
SUPABASE_URL=
SUPABASE_SECRET_KEY=
GEMINI_API_KEY=
WHATSAPP_VERIFY_TOKEN=
WHATSAPP_PHONE_NUMBER_ID=
WHATSAPP_ACCESS_TOKEN=
```

Gaia now fills in the values in **her local `.env` only**.

---

# 6. Environment variables — exactly what Gaia needs

This section is important.

| Variable | Shared or Gaia-specific? | What Gaia should do |
|---|---|---|
| `SUPABASE_URL` | Shared | Use the URL of the existing shared Supabase project |
| `SUPABASE_SECRET_KEY` | Shared project backend access | Obtain the backend secret for the same Supabase project through the project dashboard / secure team sharing |
| `GEMINI_API_KEY` | Gaia-specific | Gaia should create her own API key for the shared Google project |
| `WHATSAPP_VERIFY_TOKEN` | Gaia-specific/local | Gaia should generate her own random verification token |
| `WHATSAPP_PHONE_NUMBER_ID` | Shared | Use the same Phone Number ID as the existing bot/test number |
| `WHATSAPP_ACCESS_TOKEN` | Gaia-specific | Gaia should generate her own Meta access token after receiving access to the existing Meta app / WhatsApp asset |

---

## 6.1 `SUPABASE_URL`

This points the local backend to the shared Supabase project.

Gaia should use the same project URL as Ori:

```env
SUPABASE_URL=https://<project-ref>.supabase.co
```

This is expected to be the same on both machines.

---

## 6.2 `SUPABASE_SECRET_KEY`

The FastAPI backend needs privileged server-side access to the shared Supabase project.

Gaia should retrieve the appropriate backend secret from the existing Supabase project after she has been added as a collaborator.

Example:

```env
SUPABASE_SECRET_KEY=<project-backend-secret>
```

Never put the real key into:

- Git
- `.env.example`
- README files
- screenshots
- public chats/issues

If Supabase allows separate secret keys for developers, prefer a separate key for Gaia. Otherwise, use the existing project backend credential through a secure sharing method.

---

## 6.3 `GEMINI_API_KEY`

Gaia should create **her own Gemini API key**.

She already has access to the shared Google Cloud project, so she should create a key for herself and place it in:

```env
GEMINI_API_KEY=<Gaia's Gemini API key>
```

Do not copy Ori's Gemini API key into Gaia's environment.

Important:

Separate API keys are better for security and developer independence, but Gemini quotas may still be enforced at the Google project/model level.

---

## 6.4 `WHATSAPP_VERIFY_TOKEN`

This is **not supplied by Meta**.

It is a random secret chosen by the developer and is used only when Meta verifies the webhook URL.

Gaia can generate one with Python:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Then:

```env
WHATSAPP_VERIFY_TOKEN=<Gaia's generated value>
```

When Gaia later changes the Meta Callback URL to her ngrok URL, she must enter the exact same token in Meta's **Verify Token** field.

Ori and Gaia do not need to use the same verify token.

---

## 6.5 `WHATSAPP_PHONE_NUMBER_ID`

Because both developers are using the same WhatsApp bot/test number, this value is shared.

```env
WHATSAPP_PHONE_NUMBER_ID=<existing shared phone number ID>
```

Gaia should not create another WhatsApp bot number just for local development.

---

## 6.6 `WHATSAPP_ACCESS_TOKEN`

Gaia should create **her own access token** from Meta after she has been granted access to the existing Meta app and WhatsApp Business asset.

```env
WHATSAPP_ACCESS_TOKEN=<Gaia's Meta access token>
```

Do not commit it.

Development/test access tokens may expire. If outgoing WhatsApp messages suddenly fail with an authentication error, generate a fresh token.

---

# 7. Example `.env`

Gaia's local `.env` should conceptually look like this:

```env
# Shared Supabase project
SUPABASE_URL=<shared-supabase-url>
SUPABASE_SECRET_KEY=<shared-project-backend-secret>

# Gaia's own Gemini credential
GEMINI_API_KEY=<gaia-gemini-api-key>

# Gaia's own local webhook verification secret
WHATSAPP_VERIFY_TOKEN=<gaia-random-verify-token>

# Same WhatsApp bot/test number used by Ori
WHATSAPP_PHONE_NUMBER_ID=<shared-phone-number-id>

# Gaia's own Meta access token
WHATSAPP_ACCESS_TOKEN=<gaia-meta-access-token>
```

These are placeholders only.

Never place real values in this documentation file.

---

# 8. Verify that `.env` is protected from Git

From the repository directory:

```bash
git check-ignore .env
git ls-files .env
```

Expected:

```text
git check-ignore .env
```

should return:

```text
.env
```

And:

```text
git ls-files .env
```

should return nothing.

If `.env` appears as a tracked file, stop before committing anything.

---

# 9. Meta Developer access

Gaia's Facebook account must first be registered as a Meta/Facebook Developer account.

Gaia should:

1. Sign in to Meta for Developers with her own Facebook account.
2. Complete the developer registration.
3. Accept the required terms.
4. Tell Ori when the account is registered.

She does **not** need to create a new app.

Then Ori should add Gaia to the existing `Shared Memory Bot` app with the **Developer** role.

Administrator access is not required for normal development.

---

# 10. Meta Business / WhatsApp asset access

Being a Developer on the Meta app may not automatically give Gaia access to every Business asset.

If needed, Ori should also add Gaia to the existing Business Portfolio / Business Manager and assign access to the WhatsApp asset used by this project.

The goal is that Gaia can:

- see the existing WhatsApp API setup
- use the existing WhatsApp bot/test number
- generate her own access token
- inspect or update the webhook configuration when she is the developer doing live testing

Do not create a second WABA just for Gaia.

---

# 11. Add Gaia's personal WhatsApp number as a test recipient

If the project is still using Meta's test phone number, Gaia should add **her own personal WhatsApp number** as an allowed recipient.

Inside the existing Meta app / WhatsApp API setup:

1. Add Gaia's personal phone number as a test recipient.
2. Complete the verification process Meta sends to her phone.
3. Keep using the same Meta bot/test sender number.

This allows Gaia to test conversations from her own WhatsApp account.

---

# 12. Start the backend locally

Activate the virtual environment first.

Then run:

```bash
uvicorn app.main:app --reload
```

The backend should start on:

```text
http://127.0.0.1:8000
```

Check:

```bash
curl http://127.0.0.1:8000/health
```

Expected:

```json
{"status":"ok"}
```

On Windows, `curl` is normally available in modern PowerShell. If not, the same endpoint can simply be opened in a browser.

---

# 13. Check the database connection

Because both developers use the same Supabase project, Gaia should verify that her `.env` connects correctly.

Use the project's existing database test endpoint.

For example:

```text
http://127.0.0.1:8000/db-test
```

Expected result should indicate that the database is connected.

If this fails, first check:

```env
SUPABASE_URL=
SUPABASE_SECRET_KEY=
```

---

# 14. Local testing without Meta or ngrok

Gaia does **not** need to use the real WhatsApp transport for every change.

She can test the local webhook with `curl` or another HTTP client.

For example:

```text
POST http://127.0.0.1:8000/webhook
```

using a fake WhatsApp webhook payload.

This is useful because it:

- does not require ngrok
- does not change the Meta webhook
- does not interrupt Ori's live testing
- can test message parsing
- can test SAVE
- can test SEARCH
- can test duplicate protection
- can test error handling

Use local testing whenever the feature does not specifically require real WhatsApp delivery.

---

# 15. Start ngrok for real WhatsApp testing

When Gaia wants real inbound messages from Meta:

Terminal 1:

```bash
uvicorn app.main:app --reload
```

Terminal 2:

```bash
ngrok http 8000
```

ngrok will show a public HTTPS URL, for example:

```text
https://example-name.ngrok-free.app
```

Gaia's callback URL is then:

```text
https://example-name.ngrok-free.app/webhook
```

Keep both terminals running.

---

# 16. Important: only one local live webhook at a time

Meta sends WhatsApp webhook events to the Callback URL configured for the app.

When Ori is testing:

```text
WhatsApp
   |
   v
Ori's ngrok URL
   |
   v
Ori's localhost:8000
```

When Gaia is testing:

```text
WhatsApp
   |
   v
Gaia's ngrok URL
   |
   v
Gaia's localhost:8000
```

Therefore, only one local computer should be treated as the active live webhook target at a time.

---

# 17. Point Meta's webhook to Gaia

Only do this when Gaia wants real WhatsApp events on her computer.

In the existing Meta app:

1. Open the WhatsApp webhook configuration.
2. Change the Callback URL to:

```text
https://<Gaia-ngrok-domain>/webhook
```

3. Enter Gaia's local:

```env
WHATSAPP_VERIFY_TOKEN
```

into Meta's **Verify Token** field.
4. Verify the webhook.
5. Confirm that the `messages` webhook field is still subscribed.

Gaia does not need to recreate the webhook product configuration from scratch.

---

# 18. Existing WABA subscription should not need to be repeated

The Meta app has already been subscribed to the existing WhatsApp Business Account.

This was previously fixed by subscribing the existing app to the WABA's `subscribed_apps`.

Gaia should **not normally need to repeat this** just because the webhook is now pointing to her ngrok URL.

Only investigate WABA subscription again if:

- webhook verification succeeds
- the `messages` field is subscribed
- Gaia sends a real message
- and no inbound webhook reaches the server at all

---

# 19. Switching live testing back to Ori

When Gaia finishes and Ori wants live traffic again:

1. Ori starts her FastAPI backend.
2. Ori starts her ngrok tunnel.
3. Update Meta's Callback URL back to Ori's ngrok URL.
4. Use Ori's local `WHATSAPP_VERIFY_TOKEN` during verification.
5. Confirm `messages` is still subscribed.

Nothing else needs to be recreated.

---

# 20. Same database does NOT automatically mean same shared space

Both developers are using the same Supabase database.

However:

```text
Same database != same shared space
```

The backend currently identifies users by their WhatsApp sender number.

If Gaia sends from her own WhatsApp number, the backend can create a separate `app_user`.

Depending on the current flow, Gaia may also receive a different `space`.

Therefore, Gaia may be able to SAVE and SEARCH correctly while still not seeing the exact items previously stored by Ori.

If both developers should search the same saved data, both users must be members of the same space in:

```text
space_members
```

For the MVP, this can be configured manually in Supabase.

Later, the correct product solution is a real feature such as:

```text
Invite member to shared space
```

---

# 21. Real end-to-end test

Once Gaia's webhook is active, test in this order.

## Test 1 — SAVE

Send a normal content message from Gaia's WhatsApp, for example:

```text
Travel recommendation: Nahal Ayun near Metula has waterfalls and a beautiful trail.
```

Expected:

```text
Saved ✅
<generated title>
```

---

## Test 2 — SEARCH

Send:

```text
Find the travel recommendation near Metula
```

Expected:

- intent becomes SEARCH
- semantic search runs
- the best stored item is found
- the original item is returned

---

## Test 3 — Not found

Search for something that does not exist.

Expected user-facing result:

```text
No sufficiently matching item was found.
```

The webhook should still return HTTP `200`.

---

## Test 4 — Gemini quota / temporary outage

If Gemini returns errors such as:

```text
429 RESOURCE_EXHAUSTED
```

or:

```text
503 UNAVAILABLE
```

the backend should catch the failure and return a friendly temporary message to the WhatsApp user.

The webhook should return HTTP `200`, not `500`, so Meta does not repeatedly retry the same message.

---

## Test 5 — Duplicate delivery

If Meta retries the same incoming WhatsApp message, the backend should recognize the existing:

```text
source_platform + source_message_id
```

and skip duplicate processing.

This prevents:

- duplicate rows
- duplicate Gemini calls
- repeated embeddings
- unnecessary quota usage

---

# 22. Common issues

## `500 Internal Server Error` after a Gemini call

Look for:

```text
429 RESOURCE_EXHAUSTED
```

or:

```text
503 UNAVAILABLE
```

This means Gemini quota/rate limiting or temporary service load.

Do not keep resending messages rapidly.

---

## Duplicate key error in Supabase

Example:

```text
duplicate key value violates unique constraint
```

for:

```text
(source_platform, source_message_id)
```

This usually means Meta retried the same webhook event.

The backend now has duplicate-message protection and should return `200 OK`.

---

## Real WhatsApp message never reaches Gaia's backend

Check:

1. `uvicorn` is running
2. ngrok is running
3. Meta Callback URL points to Gaia's current ngrok domain
4. the URL ends in `/webhook`
5. webhook verification succeeded
6. the `messages` field is subscribed
7. Gaia's personal phone number is an allowed test recipient
8. the Meta app still has access to the existing WABA

---

## Sending WhatsApp replies fails

Check:

```env
WHATSAPP_ACCESS_TOKEN=
WHATSAPP_PHONE_NUMBER_ID=
```

The access token may have expired.

Generate a new access token from Gaia's Meta account.

---

## Webhook verification fails

Check that Meta's Verify Token exactly matches Gaia's local:

```env
WHATSAPP_VERIFY_TOKEN=
```

If the server was started before `.env` was changed, restart Uvicorn.

---

## Search works for Ori but not Gaia

Check the database:

```text
app_users
spaces
space_members
```

Make sure both users belong to the same logical shared space if that is the intended test.

---

# 23. Security checklist

Never commit:

```text
.env
Gemini API keys
Meta access tokens
Supabase backend secrets
Meta App Secret
ngrok auth tokens
```

Before every important commit:

```bash
git check-ignore .env
git ls-files .env
git status
```

`.env.example` should contain only empty variable names:

```env
SUPABASE_URL=
SUPABASE_SECRET_KEY=
GEMINI_API_KEY=
WHATSAPP_VERIFY_TOKEN=
WHATSAPP_PHONE_NUMBER_ID=
WHATSAPP_ACCESS_TOKEN=
```

If a real secret is accidentally exposed, rotate/regenerate it immediately.

---

# 24. Quick Gaia setup checklist

Gaia should be able to follow only this checklist once the access setup is complete:

- [ ] Register her Facebook account as a Meta Developer
- [ ] Accept the Developer invitation to `Shared Memory Bot`
- [ ] Receive access to the existing Meta Business / WhatsApp asset
- [ ] Add and verify her personal WhatsApp number as a test recipient if needed
- [ ] Install Git if missing
- [ ] Install Python 3.12 if missing
- [ ] Install ngrok and authenticate it
- [ ] Pull the latest `main`
- [ ] Create `.venv`
- [ ] Activate `.venv`
- [ ] Run `pip install -r requirements.txt`
- [ ] Copy `.env.example` to `.env`
- [ ] Fill in shared `SUPABASE_URL`
- [ ] Fill in the shared-project `SUPABASE_SECRET_KEY`
- [ ] Create her own `GEMINI_API_KEY`
- [ ] Create her own `WHATSAPP_VERIFY_TOKEN`
- [ ] Fill in the shared `WHATSAPP_PHONE_NUMBER_ID`
- [ ] Generate her own `WHATSAPP_ACCESS_TOKEN`
- [ ] Run `uvicorn app.main:app --reload`
- [ ] Check `/health`
- [ ] Check `/db-test`
- [ ] Run `ngrok http 8000` when real WhatsApp testing is needed
- [ ] Change Meta Callback URL to Gaia's ngrok URL
- [ ] Verify using Gaia's `WHATSAPP_VERIFY_TOKEN`
- [ ] Confirm the `messages` webhook field is subscribed
- [ ] Test SAVE
- [ ] Test SEARCH
- [ ] If shared data is required, make sure Gaia and Ori are members of the same `space`

---

# 25. Recommended future improvement

The local ngrok setup is fine for the MVP, but it creates one limitation:

```text
Only one developer's localhost can receive the live Meta webhook at a time.
```

Later, deploy the FastAPI backend to a permanent public server:

```text
WhatsApp
    |
    v
Permanent deployed FastAPI backend
    |
    v
Shared Supabase database
```

Then Meta always uses one stable webhook URL, and both developers can work locally without changing the production webhook.
