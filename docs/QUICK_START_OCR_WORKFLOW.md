# Quick Start: OCR Processing Workflow

## 🚀 Run the Workflow in 3 Steps

### Step 1: Navigate to Actions
1. Go to your GitHub repository
2. Click the **Actions** tab
3. Select **OCR Processing Workflow**

### Step 2: Configure Settings
Click **Run workflow** and choose:

**Basic Run (Recommended for First Time)**
```
Sources: doj
Enable OCR: ✓ true
Upload to R2: ✗ false
Max documents: 50
Create release: ✗ false
```

**Full Run (All Sources)**
```
Sources: all
Enable OCR: ✓ true
Upload to R2: ✗ false
Max documents: 0
Create release: ✗ false
```

### Step 3: Download Results
After workflow completes:
1. Scroll to **Artifacts** section
2. Download `ocr-processed-results`
3. Extract and use!

## 📦 What You Get

```
ocr-processed-results/
├── ocr/           # Searchable PDFs
├── text/          # Extracted text files
├── SUMMARY.md     # Processing summary
└── ocr_manifest.json  # File manifest with checksums
```

## 🔧 Common Configurations

### Test Run (Fast)
```
Sources: doj
Max documents: 10
Enable OCR: true
```
**Time**: ~15 minutes

### Production Run (Complete)
```
Sources: all
Max documents: 0
Enable OCR: true
```
**Time**: ~4-6 hours

### Public Release
```
Sources: all
Max documents: 0
Enable OCR: true
Upload to R2: true (requires setup)
Create release: true
```
**Time**: ~5-7 hours

## 📊 Expected Results

| Documents | OCR Time | Storage | Cost |
|-----------|----------|---------|------|
| 10 PDFs   | ~5 min   | 100MB   | Free |
| 100 PDFs  | ~30 min  | 1GB     | Free |
| 1000 PDFs | ~5 hours | 10GB    | Free |

## ⚙️ Optional: Cloudflare R2 Setup

For long-term public storage:

1. **Create R2 Bucket**
   - Sign up at https://dash.cloudflare.com
   - Go to R2 → Create Bucket
   - Name: `epstein-documents`

2. **Get API Token**
   - R2 → Manage API Tokens
   - Create token with Read/Write
   - Copy Account ID and Token

3. **Add to GitHub Secrets**
   - Settings → Secrets → Actions
   - Add `CLOUDFLARE_ACCOUNT_ID`
   - Add `CLOUDFLARE_R2_TOKEN`
   - Add `CLOUDFLARE_R2_BUCKET`

4. **Enable in Workflow**
   ```
   Upload to R2: ✓ true
   ```

**Cost**: ~$1.50/month for 100GB

## 🆘 Troubleshooting

### Workflow Failed?
1. Check logs in the failed job
2. Look for error message
3. Try with fewer documents first

### Downloads Slow?
1. Reduce `max_documents`
2. Run during off-peak hours
3. Try one source at a time

### OCR Errors?
- Check PDF is valid
- Try with different PDFs
- OCR may fail on some scanned documents (expected)

## 📚 Full Documentation

- [Complete Workflow Guide](./OCR_WORKFLOW_GUIDE.md)
- [Storage Options](./OCR_WORKFLOW_STORAGE_OPTIONS.md)
- [MCP Server Docs](../mcp_servers/epstein_files_downloader/README.md)

## 💡 Tips

1. **Start small**: Test with 10-50 documents first
2. **Check artifacts**: Download expires in 90 days
3. **Use R2 for permanent**: Set up R2 for long-term storage
4. **Schedule runs**: Use cron schedule for automatic updates
5. **Monitor costs**: Check GitHub Actions minutes if private repo

## 🎯 Quick Commands

### Trigger via API
```bash
curl -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/OWNER/REPO/dispatches \
  -d '{"event_type":"ocr-processing"}'
```

### Download Latest Artifact
```bash
gh run download --name ocr-processed-results
```

### View Workflow Status
```bash
gh run list --workflow=ocr-processing.yml
```

---

**Need Help?** Check [OCR_WORKFLOW_GUIDE.md](./OCR_WORKFLOW_GUIDE.md) or open an issue!
