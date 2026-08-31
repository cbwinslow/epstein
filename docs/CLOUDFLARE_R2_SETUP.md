# Cloudflare R2 Setup for Public Document Distribution

## Overview

This guide walks through setting up Cloudflare R2 to host OCR-processed Epstein documents for public access. R2 is a cost-effective alternative to AWS S3 with **zero egress fees**, making it ideal for public document distribution.

## Why Cloudflare R2?

✅ **Zero Egress Fees**: Unlimited downloads at no cost
✅ **Low Storage Costs**: $0.015/GB/month (10x cheaper than S3)
✅ **Public Access**: Direct HTTPS URLs for downloads
✅ **Global CDN**: Fast downloads worldwide
✅ **S3 Compatible**: Works with existing tools
✅ **Custom Domains**: Use your own domain

## Cost Comparison

| Provider | Storage (100GB) | Egress (1TB) | Total/Month |
|----------|----------------|--------------|-------------|
| Cloudflare R2 | $1.50 | **$0** | **$1.50** |
| AWS S3 | $2.30 | $92.16 | $94.46 |
| Google Cloud | $2.00 | $120 | $122.00 |

**Savings**: ~$93/month (~$1,116/year) for 1TB egress with R2! 🎉

## Prerequisites

1. Cloudflare account (free tier available)
2. R2 subscription enabled (pay-as-you-go, no minimum)
3. Payment method on file (R2 is not included in free tier)

## Step-by-Step Setup

### Part 1: Create Cloudflare Account

1. **Sign up at Cloudflare**
   - Visit https://dash.cloudflare.com/sign-up
   - Enter email and create password
   - Verify email address

2. **Enable R2**
   - Log in to Cloudflare dashboard
   - Navigate to **R2 Object Storage** in left sidebar
   - Click **Enable R2**
   - Add payment method (required, but you only pay for what you use)
   - Accept terms and conditions

### Part 2: Create R2 Bucket

1. **Navigate to R2**
   - Go to https://dash.cloudflare.com
   - Click **R2** in left sidebar

2. **Create Bucket**
   - Click **Create bucket** button
   - **Name**: `epstein-documents` (or your preferred name)
   - **Location**: Leave as "Automatic" for optimal performance
   - Click **Create bucket**

3. **Configure Bucket Settings**
   - Click on your newly created bucket
   - Go to **Settings** tab
   - Note your bucket name for later

### Part 3: Enable Public Access

1. **Allow Public Access**
   - In bucket settings, find **Public Access** section
   - Click **Allow Access** or **Connect Domain**
   - Two options:
     - **Option A**: Use Cloudflare's public URL (`pub-xxx.r2.dev`)
     - **Option B**: Connect custom domain (advanced)

2. **For Quick Setup (Option A)**
   - Cloudflare provides: `https://pub-{account-id}.r2.dev`
   - Format: `https://pub-{account-id}.r2.dev/{bucket-name}/{file-path}`
   - Example: `https://pub-abc123.r2.dev/epstein-documents/ocr-results/file.pdf`

3. **For Custom Domain (Option B)**
   - Requires domain managed by Cloudflare
   - Go to bucket **Settings** → **Public Access**
   - Click **Connect Domain**
   - Enter subdomain: `documents.yourdomain.com`
   - Cloudflare automatically configures DNS
   - SSL certificate is auto-provisioned

### Part 4: Create API Token

1. **Generate R2 API Token**
   - Go to **R2** → **Manage R2 API Tokens**
   - Click **Create API Token**

2. **Configure Token Permissions**
   - **Token Name**: `github-actions-ocr-workflow`
   - **Permissions**:
     - ✅ Object Read & Write
   - **Bucket Restriction**: Select `epstein-documents`
   - **Expiration**: Set to 1 year (or longer)
   - Click **Create API Token**

3. **Save Credentials**
   - **Account ID**: Copy and save (looks like: `abc123def456`)
   - **API Token**: Copy and save (looks like: `v1.0_abc123...`)
   - ⚠️ **Important**: You won't see the token again!

### Part 5: Configure GitHub Secrets

1. **Go to Repository Settings**
   - Navigate to your GitHub repository
   - Click **Settings** → **Secrets and variables** → **Actions**

2. **Add Repository Secrets**
   Click **New repository secret** for each:

   **Secret 1: CLOUDFLARE_ACCOUNT_ID**
   - Name: `CLOUDFLARE_ACCOUNT_ID`
   - Value: Your account ID (e.g., `abc123def456`)
   - Click **Add secret**

   **Secret 2: CLOUDFLARE_R2_TOKEN**
   - Name: `CLOUDFLARE_R2_TOKEN`
   - Value: Your R2 API token (e.g., `v1.0_abc123...`)
   - Click **Add secret**

   **Secret 3: CLOUDFLARE_R2_BUCKET**
   - Name: `CLOUDFLARE_R2_BUCKET`
   - Value: `epstein-documents` (your bucket name)
   - Click **Add secret**

3. **Verify Secrets**
   - You should see 3 secrets listed
   - Values are hidden for security
   - These will be available to workflow as environment variables

### Part 6: Test the Setup

1. **Run Test Upload**
   ```bash
   # Install Wrangler CLI locally
   npm install -g wrangler

   # Authenticate
   wrangler login

   # Test upload
   echo "Test file" > test.txt
   wrangler r2 object put epstein-documents/test/test.txt --file test.txt

   # Verify
   wrangler r2 object get epstein-documents/test/test.txt
   ```

2. **Test Public Access**
   ```bash
   # Get your public URL
   curl https://pub-{your-account-id}.r2.dev/epstein-documents/test/test.txt
   ```

3. **Test in Workflow**
   - Go to Actions → OCR Processing Workflow
   - Run workflow with:
     - Sources: `doj`
     - Max documents: `5`
     - Upload to R2: `✓ true`
   - Check workflow logs for success
   - Verify file appears in R2 bucket

## Usage in Workflow

Once configured, the workflow automatically:

1. Processes documents with OCR
2. Creates compressed archive
3. Uploads to R2 bucket
4. Generates public URL
5. Commits URL to repository

**Example public URL**:
```
https://pub-abc123.r2.dev/epstein-documents/ocr-results/20250107/ocr-results-123456.tar.gz
```

## Advanced Configuration

### Custom Domain Setup

1. **Add Domain to Cloudflare**
   - Add your domain to Cloudflare (if not already)
   - Update nameservers to Cloudflare

2. **Connect Domain to Bucket**
   - In R2 bucket settings → **Public Access**
   - Click **Connect Domain**
   - Enter: `documents.yourdomain.com`
   - Cloudflare creates CNAME record automatically
   - SSL certificate is auto-provisioned (takes ~15 minutes)

3. **Update Workflow**
   ```yaml
   # In workflow file
   env:
     R2_PUBLIC_URL: "https://documents.yourdomain.com"
   ```

### CORS Configuration

For web applications accessing R2 directly:

1. **Configure CORS**
   - Go to bucket **Settings** → **CORS**
   - Add CORS rule:
   ```json
   {
     "AllowedOrigins": ["*"],
     "AllowedMethods": ["GET", "HEAD"],
     "AllowedHeaders": ["*"],
     "ExposeHeaders": [],
     "MaxAgeSeconds": 3600
   }
   ```

### Lifecycle Policies

To automatically delete old files:

1. **Create Lifecycle Rule**
   - Go to bucket **Settings** → **Lifecycle**
   - Add rule:
     - Name: `auto-delete-old-results`
     - Prefix: `ocr-results/`
     - Action: Delete after 365 days

### Access Logging

To track downloads:

1. **Enable Access Logs**
   - Go to bucket **Settings** → **Access Logs**
   - Create logging bucket: `epstein-documents-logs`
   - Enable logging
   - Logs format: JSON

## Security Best Practices

### 1. Token Security

- ✅ Never commit tokens to repository
- ✅ Use GitHub Secrets for tokens
- ✅ Set token expiration (rotate annually)
- ✅ Restrict token to specific bucket
- ✅ Use read-only tokens where possible

### 2. Bucket Security

- ✅ Enable access logging
- ✅ Monitor bandwidth usage
- ✅ Set up CloudFlare alerts
- ✅ Regular security audits
- ✅ Use private buckets for sensitive data

### 3. Content Policy

- ✅ Only upload public documents
- ✅ No personal information (PII)
- ✅ No classified materials
- ✅ Include disclaimer on download page
- ✅ Link to original sources

## Monitoring and Maintenance

### Check Usage

1. **View Storage Stats**
   - Go to **R2** dashboard
   - View **Metrics** tab
   - Check storage usage and API calls

2. **Estimate Costs**
   - Storage: `{GB} × $0.015`
   - API calls: Usually < $0.10/month
   - Egress: Always $0

### Monthly Tasks

1. **Review usage statistics**
2. **Check for unusual activity**
3. **Verify billing charges**
4. **Update documentation**
5. **Test public access**

### Troubleshooting

#### Issue: Token Authentication Failed

**Solution**:
1. Verify token in GitHub Secrets
2. Check token hasn't expired
3. Ensure token has write permissions
4. Regenerate token if needed

#### Issue: Public Access Not Working

**Solution**:
1. Verify public access is enabled
2. Check bucket name is correct
3. Test with Wrangler CLI first
4. Wait 5 minutes for DNS propagation

#### Issue: Upload Fails with 403

**Solution**:
1. Check token permissions
2. Verify bucket exists
3. Ensure account ID is correct
4. Try smaller file first

## Cost Management

### Optimize Costs

1. **Compression**
   - Always compress archives before upload
   - Use `.tar.gz` or `.zip`
   - Can reduce storage by 70-90%

2. **Cleanup**
   - Set lifecycle policies
   - Delete test files regularly
   - Archive old results

3. **Monitoring**
   - Set up CloudFlare billing alerts
   - Monitor storage growth
   - Review API call patterns

### Expected Costs

**Small Project (10GB)**:
- Storage: $0.15/month
- API calls: $0.01/month
- Total: **~$0.16/month**

**Medium Project (100GB)**:
- Storage: $1.50/month
- API calls: $0.05/month
- Total: **~$1.55/month**

**Large Project (1TB)**:
- Storage: $15.00/month
- API calls: $0.10/month
- Total: **~$15.10/month**

## Making Documents Discoverable

### Create Index Page

Create `index.html` in bucket:

```html
<!DOCTYPE html>
<html>
<head>
    <title>Epstein Documents - OCR Processed</title>
    <meta name="description" content="Public archive of OCR-processed Epstein documents">
</head>
<body>
    <h1>Epstein Documents Archive</h1>
    <p>OCR-processed documents from official government sources.</p>
    <ul id="documents"></ul>
    <script>
        // Fetch and display document list
        fetch('/ocr-results/manifest.json')
            .then(r => r.json())
            .then(data => {
                const list = document.getElementById('documents');
                data.documents.forEach(doc => {
                    const li = document.createElement('li');
                    li.innerHTML = `<a href="/ocr-results/${doc.path}">${doc.filename}</a> (${doc.size} bytes)`;
                    list.appendChild(li);
                });
            });
    </script>
</body>
</html>
```

### Submit to Search Engines

1. **Google Search Console**
   - Add property: `documents.yourdomain.com`
   - Submit sitemap
   - Request indexing

2. **Bing Webmaster Tools**
   - Add site
   - Submit URL

3. **Social Sharing**
   - Share on Twitter/X
   - Post on Reddit
   - Share in relevant communities

## Alternative: AWS S3 Setup

If you prefer AWS S3:

```yaml
# In workflow, replace R2 upload with:
- name: Upload to S3
  env:
    AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
    AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
  run: |
    aws s3 cp ocr-results.tar.gz \
      s3://epstein-documents/ocr-results/ \
      --acl public-read
```

**Note**: AWS S3 has egress fees (~$0.09/GB), making it much more expensive for public downloads.

## Getting Help

### Resources

- [Cloudflare R2 Docs](https://developers.cloudflare.com/r2/)
- [Wrangler CLI Docs](https://developers.cloudflare.com/workers/wrangler/)
- [Workflow Guide](./OCR_WORKFLOW_GUIDE.md)

### Support Channels

1. **Cloudflare Community**: https://community.cloudflare.com/
2. **GitHub Issues**: Create issue in this repository
3. **Documentation**: Check this guide and official docs

## Summary Checklist

- [ ] Create Cloudflare account
- [ ] Enable R2 subscription
- [ ] Create bucket `epstein-documents`
- [ ] Enable public access
- [ ] Generate API token
- [ ] Add GitHub Secrets (3 secrets)
- [ ] Test upload with Wrangler
- [ ] Run workflow with R2 enabled
- [ ] Verify public access works
- [ ] Set up monitoring/alerts

---

**Last Updated**: 2025-01-07
**Version**: 1.0.0
**Author**: Epstein Project Team

**Questions?** Open an issue or check [OCR_WORKFLOW_GUIDE.md](./OCR_WORKFLOW_GUIDE.md)
