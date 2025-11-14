## How to Get a Fresh Facebook User Access Token

Your Meta User Access Token has expired. Follow these steps to get a new one:

### Step 1: Go to Facebook Graph API Explorer
1. Open: https://developers.facebook.com/tools/explorer
2. Make sure you're logged into the Facebook account that manages your pages

### Step 2: Select Your App
1. In the "Facebook App" dropdown, select your app: `1576155436683126`
2. If you don't see it, click "Get Token" → "Get User Access Token"

### Step 3: Request Permissions
Click "Generate Access Token" and make sure these permissions are selected:
- `pages_manage_metadata` (to manage page webhook subscriptions)
- `pages_read_engagement` (to read page data)
- `leads_retrieval` (to retrieve lead form data)
- `pages_show_list` (to list your pages)

### Step 4: Generate Long-Lived Token
The token from Graph Explorer expires in 1 hour. To get a long-lived token (60 days):

1. Copy the short-lived token from Graph Explorer
2. Use this URL (replace YOUR_SHORT_TOKEN):
```
https://graph.facebook.com/oauth/access_token?grant_type=fb_exchange_token&client_id=1576155436683126&client_secret=3f5d85f87c288bd97fa1439b96875b38&fb_exchange_token=YOUR_SHORT_TOKEN
```

### Step 5: Update .env File
1. Copy the new access token
2. Replace the `META_USER_ACCESS_TOKEN` value in your `.env` file
3. Save the file

### Quick Alternative Method
You can also run this script after getting the short-lived token: