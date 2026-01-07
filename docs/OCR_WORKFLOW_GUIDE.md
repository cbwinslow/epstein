# OCR Processing Workflow Guide

## Overview

The OCR Processing Workflow is a GitHub Actions workflow that automates the download and OCR processing of Epstein-related documents from official government sources. This workflow uses AI agent principles to orchestrate document retrieval, processing, and storage.

**Workflow File**: `.github/workflows/ocr-processing.yml`

## Features

- ✅ **Automated Document Discovery**: Uses MCP server to discover available documents
- ✅ **Multi-Source Downloads**: Downloads from DOJ, FBI Vault, and House Oversight
- ✅ **OCR Processing**: Converts scanned PDFs to searchable documents
- ✅ **Text Extraction**: Extracts plain text for analysis
- ✅ **Multiple Storage Options**: GitHub Artifacts, Cloudflare R2, GitHub Releases
- ✅ **Manifest Generation**: Creates detailed manifests with checksums
- ✅ **Progress Tracking**: Real-time progress updates
- ✅ **Error Handling**: Robust retry logic and error reporting

## Quick Start

### Running the Workflow Manually

1. Go to the **Actions** tab in your GitHub repository
2. Click on **OCR Processing Workflow**
3. Click **Run workflow**
4. Configure the inputs:
   - **Sources**: Choose `doj`, `fbi`, `house`, or `all`
   - **Enable OCR**: `true` (recommended)
   - **Upload to R2**: `false` (requires setup)
   - **Max documents**: `0` (unlimited) or a specific number
   - **Create release**: `false` (or `true` for public release)
5. Click **Run workflow** button

### Example Configurations

#### Download and Process All Documents
```
sources: all
enable_ocr: true
upload_to_r2: false
max_documents: 0
create_release: false
```

#### Process DOJ Documents Only (Limited)
```
sources: doj
enable_ocr: true
upload_to_r2: false
max_documents: 100
create_release: false
```

#### Full Processing with Public Release
```
sources: all
enable_ocr: true
upload_to_r2: true
max_documents: 0
create_release: true
```

## Workflow Architecture

### Job Flow

```
┌─────────────────────┐
│ 1. Download         │
│    Documents        │
│                     │
│  - Start MCP Server │
│  - Discover sources │
│  - Download PDFs    │
│  - Create manifests │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ 2. OCR Processing   │
│                     │
│  - Install OCR deps │
│  - Process PDFs     │
│  - Extract text     │
│  - Generate manifest│
└──────────┬──────────┘
           │
           ├─────────────────────┬──────────────────┐
           ▼                     ▼                  ▼
┌────────────────┐    ┌──────────────────┐  ┌─────────────┐
│ 3a. Upload R2  │    │ 3b. Create       │  │ 3c. Summary │
│     (Optional) │    │     Release      │  │             │
│                │    │     (Optional)   │  │  - Report   │
└────────────────┘    └──────────────────┘  └─────────────┘
```

### Job Descriptions

#### Job 1: Download Documents
- **Purpose**: Download documents from government sources
- **Duration**: ~30-120 minutes
- **Resources**: CPU: 2 cores, RAM: 4GB
- **Outputs**: 
  - Downloaded PDF files
  - Download manifest
  - Download count

#### Job 2: OCR Processing
- **Purpose**: Process PDFs with OCR and extract text
- **Duration**: ~60-240 minutes (depends on document count)
- **Resources**: CPU: 2 cores, RAM: 8GB
- **Outputs**:
  - OCR-processed PDFs
  - Extracted text files
  - Processing manifest
  - Summary statistics

#### Job 3: Upload to Cloudflare R2
- **Purpose**: Upload results to cloud storage for public access
- **Duration**: ~10-60 minutes
- **Conditions**: Only runs if `upload_to_r2` is `true`
- **Requirements**: Cloudflare R2 secrets configured

#### Job 4: Create GitHub Release
- **Purpose**: Create a versioned release with results
- **Duration**: ~5 minutes
- **Conditions**: Only runs if `create_release` is `true`

#### Job 5: Summary
- **Purpose**: Generate workflow summary report
- **Duration**: ~1 minute
- **Always runs**: Even if other jobs fail

## Configuration

### Workflow Inputs

| Input | Type | Default | Description |
|-------|------|---------|-------------|
| `sources` | string | `all` | Comma-separated sources: `doj`, `fbi`, `house`, `all` |
| `enable_ocr` | boolean | `true` | Enable OCR processing |
| `upload_to_r2` | boolean | `false` | Upload to Cloudflare R2 |
| `max_documents` | number | `0` | Max docs to process (0 = unlimited) |
| `create_release` | boolean | `false` | Create GitHub release with results |

### Environment Variables

The workflow uses these environment variables (automatically set):

```yaml
env:
  PYTHON_VERSION: '3.10'
  ARTIFACTS_DIR: ./epstein_artifacts
  RESULTS_DIR: ./ocr_results
  MANIFEST_DIR: ./manifests
```

### GitHub Secrets (Required for Cloudflare R2)

To use Cloudflare R2 storage, configure these secrets in your repository:

1. Go to **Settings** → **Secrets and variables** → **Actions**
2. Add the following secrets:

| Secret Name | Description | Example |
|-------------|-------------|---------|
| `CLOUDFLARE_ACCOUNT_ID` | Your Cloudflare account ID | `abc123def456` |
| `CLOUDFLARE_R2_TOKEN` | R2 API token with read/write permissions | `v1.xxx...` |
| `CLOUDFLARE_R2_BUCKET` | R2 bucket name | `epstein-documents` |

See [OCR_WORKFLOW_STORAGE_OPTIONS.md](./OCR_WORKFLOW_STORAGE_OPTIONS.md) for detailed R2 setup instructions.

## Workflow Triggers

### Manual Trigger (workflow_dispatch)
- Run from GitHub Actions UI
- Allows input configuration
- Useful for on-demand processing

### Scheduled Trigger (cron)
```yaml
schedule:
  - cron: '0 2 * * 0'  # Weekly on Sunday at 2 AM UTC
```

### Repository Dispatch
```bash
# Trigger from API or other workflows
curl -X POST \
  -H "Accept: application/vnd.github.v3+json" \
  -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/OWNER/REPO/dispatches \
  -d '{"event_type":"ocr-processing"}'
```

## Output Artifacts

### Artifact Structure

After a successful workflow run, the following artifacts are available:

```
Artifacts (retention: 7-90 days)
├── downloaded-documents/
│   ├── downloads/
│   │   ├── document_001.pdf
│   │   ├── document_002.pdf
│   │   └── ...
│   └── download_summary.json
│
├── ocr-processed-results/
│   ├── ocr/
│   │   ├── document_001.pdf (searchable)
│   │   └── ...
│   ├── text/
│   │   ├── document_001.txt
│   │   └── ...
│   ├── SUMMARY.md
│   └── ocr_manifest.json
│
└── ocr-results-archive/
    └── ocr-results-{run_id}.tar.gz (compressed)
```

### Manifest Files

#### Download Manifest (`download_summary.json`)
```json
{
  "total_downloaded": 150,
  "total_failed": 2,
  "sources": ["doj", "fbi"],
  "timestamp": 1704672000.0
}
```

#### OCR Manifest (`ocr_manifest.json`)
```json
{
  "processing_date": "2025-01-07 12:00:00 UTC",
  "workflow_run": "1234567890",
  "total_documents": 148,
  "documents": [
    {
      "filename": "document_001.pdf",
      "path": "ocr/document_001.pdf",
      "size": 2048576,
      "sha256": "abc123...",
      "text_file": "text/document_001.txt",
      "text_size": 45678
    }
  ]
}
```

## Accessing Results

### Option 1: GitHub Actions Artifacts (Recommended)

1. Go to the workflow run page
2. Scroll down to **Artifacts** section
3. Click on artifact name to download
4. Artifacts are available for 90 days

**Pros**: Free, easy access, integrated
**Cons**: Requires GitHub account, temporary (90 days)

### Option 2: Cloudflare R2 (For Public Distribution)

If R2 upload is enabled, results are available at:
```
https://pub-{account_id}.r2.dev/ocr-results/{date}/ocr-results-{run_id}.tar.gz
```

**Pros**: Public access, no authentication, permanent, free downloads
**Cons**: Requires R2 setup, storage costs (~$1.50/month for 100GB)

### Option 3: GitHub Releases

If release creation is enabled, results are attached to a GitHub release:
```
https://github.com/{owner}/{repo}/releases/tag/ocr-{run_number}
```

**Pros**: Versioned, permanent, public, easy discovery
**Cons**: Manual trigger, 2GB per file limit

## Monitoring and Debugging

### Viewing Logs

1. Go to the workflow run page
2. Click on job name (e.g., "OCR Processing")
3. Expand step to view logs
4. Click "View raw logs" to download

### Common Issues and Solutions

#### Issue: Downloads Fail

**Symptoms**:
- "Failed to download from source"
- HTTP timeout errors

**Solutions**:
1. Check source URL accessibility
2. Verify network connectivity
3. Increase timeout in workflow
4. Check rate limiting

#### Issue: OCR Processing Fails

**Symptoms**:
- "ocrmypdf failed"
- "Tesseract error"

**Solutions**:
1. Check PDF is not corrupted
2. Verify OCR dependencies installed
3. Try with `--skip-text` option
4. Check available disk space

#### Issue: R2 Upload Fails

**Symptoms**:
- "Authentication failed"
- "Bucket not found"

**Solutions**:
1. Verify R2 secrets are configured
2. Check bucket exists and is accessible
3. Verify API token permissions
4. Check account ID is correct

#### Issue: Out of Disk Space

**Symptoms**:
- "No space left on device"
- Workflow terminates early

**Solutions**:
1. Reduce `max_documents`
2. Process in smaller batches
3. Enable compression earlier
4. Clean up intermediate files

### Workflow Timeouts

Each job has a timeout to prevent runaway processes:

- Download: 120 minutes
- OCR Processing: 240 minutes
- R2 Upload: 60 minutes
- Total workflow: ~420 minutes (7 hours)

If processing takes longer:
1. Reduce document count
2. Process in multiple runs
3. Optimize OCR settings

## Performance Optimization

### Processing Speed

Typical processing times:
- Download: ~100-200 documents/hour
- OCR: ~20-50 documents/hour (depends on quality)
- Upload: ~500MB/minute

### Optimization Tips

1. **Parallel Processing**
   - Adjust `max_workers` in config
   - Use `--jobs` flag for ocrmypdf

2. **Compression**
   - Enable early compression
   - Use `--optimize` for OCR output

3. **Batching**
   - Process in smaller batches
   - Use `max_documents` input

4. **Resource Allocation**
   - Use larger GitHub runners if available
   - Monitor CPU/memory usage

## Cost Analysis

### GitHub Actions

**Free Tier**:
- Public repositories: Unlimited
- Private repositories: 2,000 minutes/month

**Typical Workflow Costs** (private repos):
- Download + OCR: ~300 minutes
- ~$0.008 per minute = $2.40 per run
- Monthly (4 runs): ~$10

### Cloudflare R2

**Storage Costs**:
- $0.015 per GB/month
- Example: 100GB = $1.50/month

**Egress Costs**:
- **FREE** (no egress fees)
- Unlimited downloads at no cost

**API Costs**:
- Class A (write): $4.50 per million requests
- Class B (read): $0.36 per million requests

**Typical Monthly Cost**:
- Storage (100GB): $1.50
- API calls: < $0.10
- **Total: ~$1.60/month**

### Total Cost Estimate

**For Public Repository**:
- GitHub Actions: Free
- R2 Storage: ~$1.60/month
- **Total: ~$1.60/month**

**For Private Repository**:
- GitHub Actions: ~$10/month
- R2 Storage: ~$1.60/month
- **Total: ~$11.60/month**

## Security Considerations

### Data Privacy

1. **Public Documents Only**
   - All processed documents are public records
   - No PII or classified information
   - Downloaded from official sources

2. **Access Control**
   - GitHub artifacts: Require repository access
   - R2 public access: Anyone can download
   - Releases: Public by default

3. **Audit Trail**
   - All operations logged
   - Manifests include checksums
   - Source URLs tracked

### Secrets Management

1. **Never commit secrets**
2. **Use GitHub Secrets** for API tokens
3. **Rotate tokens** regularly
4. **Minimum permissions** for tokens

### Supply Chain Security

1. **Pin action versions**
   ```yaml
   uses: actions/checkout@v4  # Use specific version
   ```

2. **Verify checksums**
   - All files checksummed (SHA-256)
   - Manifests include verification data

3. **Container security**
   - Use official Python images
   - Install from official repos
   - Verify package signatures

## Advanced Usage

### Custom OCR Settings

Edit the pipeline configuration in the workflow:

```yaml
- name: Create pipeline configuration
  run: |
    cat > config.json << 'EOF'
    {
      "ocrmypdf_lang": "eng+fra",  # Multiple languages
      "ocrmypdf_extra_args": [
        "--skip-text",
        "--rotate-pages",
        "--deskew",              # Fix skewed scans
        "--optimize 2",          # More aggressive optimization
        "--jobs 4"               # Parallel processing
      ]
    }
    EOF
```

### Processing Specific Documents

Use the MCP server API to filter documents:

```python
# In the download step
def filter_documents(documents):
    return [
        doc for doc in documents
        if "2024" in doc.get("publish_date", "")
    ]
```

### Custom Post-Processing

Add additional processing steps:

```yaml
- name: Custom post-processing
  run: |
    # Example: Extract specific entities
    python scripts/extract_entities.py ${RESULTS_DIR}/text/
    
    # Example: Generate index
    python scripts/generate_index.py ${RESULTS_DIR}/
```

## Integration with Other Workflows

### Trigger from Another Workflow

```yaml
# In another workflow file
- name: Trigger OCR workflow
  uses: peter-evans/repository-dispatch@v2
  with:
    token: ${{ secrets.GITHUB_TOKEN }}
    event-type: ocr-processing
```

### Use Results in Another Workflow

```yaml
# Download artifacts from another workflow
- name: Download OCR results
  uses: dawidd6/action-download-artifact@v2
  with:
    workflow: ocr-processing.yml
    workflow_conclusion: success
    name: ocr-processed-results
```

## Troubleshooting Guide

### Diagnostic Steps

1. **Check workflow logs**
   - Navigate to Actions → Workflow run
   - Review each job's logs

2. **Verify inputs**
   - Check workflow dispatch inputs
   - Verify secrets are set

3. **Test locally**
   - Clone repository
   - Run scripts manually
   - Check for errors

4. **Review manifests**
   - Download manifest files
   - Check for patterns in failures

### Getting Help

1. **Check documentation**
   - This guide
   - [Storage Options](./OCR_WORKFLOW_STORAGE_OPTIONS.md)
   - [MCP Server README](../mcp_servers/epstein_files_downloader/README.md)

2. **Review issues**
   - Check GitHub Issues
   - Search for similar problems

3. **Create issue**
   - Provide workflow run ID
   - Include error messages
   - Attach relevant logs

## Maintenance

### Regular Tasks

1. **Weekly**
   - Review workflow runs
   - Check artifact usage
   - Monitor R2 storage

2. **Monthly**
   - Review costs
   - Update dependencies
   - Check for new documents

3. **Quarterly**
   - Update OCR engine
   - Review security settings
   - Optimize performance

### Updating the Workflow

1. **Test changes locally**
2. **Create feature branch**
3. **Update workflow file**
4. **Test on small dataset**
5. **Create pull request**
6. **Review and merge**

## Future Enhancements

Potential improvements:

- [ ] Named Entity Recognition (NER)
- [ ] Automatic document categorization
- [ ] Deduplication detection
- [ ] Multi-language support
- [ ] Incremental processing
- [ ] Real-time notifications
- [ ] Web dashboard
- [ ] API for accessing results

## Related Documentation

- [Storage Options Guide](./OCR_WORKFLOW_STORAGE_OPTIONS.md)
- [MCP Server Documentation](../mcp_servers/epstein_files_downloader/README.md)
- [Pipeline Documentation](../epstein/README.md)
- [DOJ Releases 2024](../knowledge_base/doj_releases_2024.md)

---

**Last Updated**: 2025-01-07
**Version**: 1.0.0
**Maintained By**: Epstein Project Team
