# Data Sources

This document catalogs all Epstein-related document sources identified in the project codebase, including access requirements, estimated document counts, data formats, and other relevant metadata.

## govinfo.gov
- **Description**: Official government information repository containing court documents, legislative materials, and public records related to the Epstein case.
- **Access Requirements**: Public access via website and bulk data API. API key recommended for high-volume downloads to avoid rate limits.
- **Estimated Document Count**: Thousands of documents; bulk datasets can be GB-scale.
- **Data Formats**: PDF, XML, HTML, ZIP archives.
- **URL**: https://www.govinfo.gov
- **API Endpoint**: https://www.govinfo.gov/bulkdata/bulkdata
- **Notes**: Supports search for "Jeffrey Epstein" to discover relevant collections.

## congress.gov
- **Description**: Congressional website with bill metadata, legislative actions, and vote records potentially related to Epstein investigations.
- **Access Requirements**: Public API access available.
- **Estimated Document Count**: Variable; depends on search queries.
- **Data Formats**: JSON, XML.
- **URL**: https://www.congress.gov
- **Notes**: Primarily metadata rather than full document content.

## openstates.org
- **Description**: State-level legislative data that may include bills or resolutions related to Epstein matters.
- **Access Requirements**: Public API access.
- **Estimated Document Count**: Variable per state.
- **Data Formats**: JSON with state-specific schemas.
- **URL**: https://openstates.org
- **Notes**: Requires normalization due to different schemas per state.

## justice.gov (DOJ Epstein Library)
- **Description**: Department of Justice disclosures and releases related to the Epstein case, including declassified documents and press releases.
- **Access Requirements**: Public website access; no authentication required.
- **Estimated Document Count**: Multiple datasets (Data Set 1-N), each containing numerous files.
- **Data Formats**: ZIP archives containing PDFs, documents, and other files.
- **URL**: https://www.justice.gov/epstein/doj-disclosures
- **Notes**: Auto-discovers dataset pages and ZIP links from index page.

## vault.fbi.gov (FBI Vault FOIA)
- **Description**: FBI Freedom of Information Act (FOIA) releases for Jeffrey Epstein case, organized into numbered parts.
- **Access Requirements**: Public access; direct PDF downloads.
- **Estimated Document Count**: Multiple parts (01-N), each a large PDF file.
- **Data Formats**: PDF.
- **URL**: https://vault.fbi.gov/jeffrey-epstein
- **Notes**: Uses stable "/at_download/file" endpoints for reliable downloads.

## oversight.house.gov (House Oversight Committee)
- **Description**: U.S. House Oversight Committee press releases containing Epstein-related records and estate documents.
- **Access Requirements**: Public website; links to external storage (Google Drive, Dropbox).
- **Estimated Document Count**: Thousands of documents across multiple releases.
- **Data Formats**: Various (PDFs, documents, images) stored in cloud folders.
- **URLs**:
  - https://oversight.house.gov/release/oversight-committee-releases-epstein-records-provided-by-the-department-of-justice/
  - https://oversight.house.gov/release/oversight-committee-releases-additional-epstein-estate-documents/
- **Notes**: Requires external tools (gdown for Google Drive, rclone for Dropbox) for bulk folder downloads.

## nysd.uscourts.gov (Southern District of New York Court)
- **Description**: Federal court documents from the Southern District of New York related to Epstein case filings, motions, and rulings.
- **Access Requirements**: Public court records access.
- **Estimated Document Count**: Hundreds to thousands of case materials.
- **Data Formats**: PDF, court documents.
- **URL**: https://www.nysd.uscourts.gov/cases-opinions
- **Notes**: Part of the Public Access to Court Electronic Records (PACER) system, though direct links may be available.
