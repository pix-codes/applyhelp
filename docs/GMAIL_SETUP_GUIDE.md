# Google OAuth 2.0 & Gmail API Configuration Guide

This guide walks you through setting up Google OAuth credentials so ApplyHelp can save generated email outreach directly as drafts in your personal Gmail account without any mailbox read permissions or automated email sending.

---

## 🔒 Security Principles
- **Minimal Scope**: Only `https://www.googleapis.com/auth/gmail.compose` is requested.
- **No Reading / No Auto-Send**: ApplyHelp cannot read your inbox or send emails automatically.
- **Encrypted at Rest**: OAuth refresh tokens and client secrets are encrypted in PostgreSQL using Fernet symmetric encryption.
- **UI Editable**: All credentials can be set directly in the **Settings** page or through `.env`.

---

## Step 1: Create a Project in Google Cloud Console
1. Navigate to the [Google Cloud Console](https://console.cloud.google.com/).
2. Click the project dropdown at the top left and click **New Project**.
3. Name it `ApplyHelp-Outreach` and click **Create**.

---

## Step 2: Enable the Gmail API
1. In the navigation menu (left sidebar), go to **APIs & Services** > **Library**.
2. Search for **Gmail API**.
3. Select **Gmail API** and click **Enable**.

---

## Step 3: Configure the OAuth Consent Screen
1. In the navigation menu, go to **APIs & Services** > **OAuth consent screen**.
2. Select User Type: **External** (since it's a personal Gmail account) and click **Create**.
3. Fill in the required fields:
   - **App name**: `ApplyHelp`
   - **User support email**: Your Gmail address
   - **Developer contact information**: Your Gmail address
4. Click **Save and Continue**.
5. On the **Scopes** page:
   - Click **Add or Remove Scopes**.
   - Filter or search for `https://www.googleapis.com/auth/gmail.compose` (or `gmail.compose`).
   - Check the box for `.../auth/gmail.compose` (*Compose and send emails, modify drafts*).
   - Click **Update** and then **Save and Continue**.
6. On the **Test users** page:
   - Click **+ Add Users**.
   - Enter your own Gmail address (this allows you to authorize the app without waiting for Google app verification).
   - Click **Save and Continue**.

---

## Step 4: Create OAuth 2.0 Client Credentials
1. In the navigation menu, go to **APIs & Services** > **Credentials**.
2. Click **+ Create Credentials** at the top > **OAuth client ID**.
3. Set **Application type** to: `Web application`.
4. Set **Name** to: `ApplyHelp Web Client`.
5. Under **Authorized redirect URIs**:
   - Click **+ Add URI**.
   - Enter: `http://localhost:8501` (or your custom host/port if different).
6. Click **Create**.
7. A dialog will appear with your **Client ID** and **Client Secret**. Keep these handy.

---

## Step 5: Configure & Connect in ApplyHelp
1. In ApplyHelp, navigate to the **Settings** page in the left sidebar.
2. Click on the **📬 Gmail Integration** tab.
3. Paste your **Google Client ID** and **Google Client Secret**.
4. Confirm the **Redirect URI** is `http://localhost:8501`.
5. Click **💾 Save Google OAuth Credentials**.
6. Click the generated **Authorize Gmail with Google** link.
7. Sign in with your Google account. If you see Google's *"Google hasn’t verified this app"* warning screen, click **Advanced** > **Go to ApplyHelp (unsafe)**.
8. Approve the draft composition permissions.
9. Google will redirect your browser back to `http://localhost:8501/?code=4/0A...`.
10. Copy the full code string (everything after `code=` up to any subsequent `&` or end of URL).
11. Paste it into the **Authorization Code** field in ApplyHelp and click **Complete Connection**.

Once connected, you can draft emails in the **Outreach Studio** and save them directly as Gmail drafts with a single click.
