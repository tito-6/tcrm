## Getting Ngrok Auth Token for External Webhook Access

Your webhook needs to be publicly accessible for Facebook to send leads. Here's how to set up ngrok:

### Step 1: Get Free Ngrok Auth Token
1. Go to: https://ngrok.com/
2. Sign up for a free account (no credit card required)
3. Go to: https://dashboard.ngrok.com/get-started/your-authtoken
4. Copy your authtoken

### Step 2: Update .env File
Add your ngrok authtoken to the `.env` file:
```
NGROK_AUTHTOKEN=your_token_here
```

### Step 3: Restart Ngrok
```bash
docker compose up -d ngrok
```

### Step 4: Get Public URL
1. Visit: http://localhost:4040
2. Copy the HTTPS URL (something like: https://abc123.ngrok-free.app)
3. Your webhook URL will be: https://abc123.ngrok-free.app/webhooks/meta

### Alternative: Local Development Only
If you just want to test locally without external access, you can also:
1. Use Facebook's Test Events feature in App Dashboard
2. Or skip ngrok and configure webhook later when ready for production

### Why We Need Public Access
Facebook's webhook system needs to:
1. Verify your webhook URL (GET request with challenge)
2. Send real-time lead data (POST requests)

Both require your webhook to be accessible from the internet.