#!/usr/bin/env python3
"""
PydanticAI Document Downloader Agent

Example implementation of a PydanticAI agent for downloading Epstein documents
using the MCP server.

Usage:
    python pydantic_downloader_agent.py "Download all DOJ disclosure documents"
"""

import asyncio
import os
import sys

import requests
from pydantic import BaseModel, Field

# Check if pydantic-ai is installed
try:
    from pydantic_ai import Agent
except ImportError:
    print("ERROR: pydantic-ai is not installed.")
    print("Install it with: pip install pydantic-ai")
    sys.exit(1)


# Configuration
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8765")
DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR", "/tmp/downloads")


# Data Models
class CollectionInfo(BaseModel):
    """Information about a document collection"""

    collection_id: str
    name: str
    description: str
    document_count: int
    url: str
    source: str


class DownloadRequest(BaseModel):
    """Request to download documents"""

    collection_id: str
    destination: str = Field(default=DOWNLOAD_DIR)
    filter_criteria: dict = Field(default_factory=dict)


class DownloadStatus(BaseModel):
    """Status of a download task"""

    task_id: str
    url: str
    status: str
    progress: float
    destination: str


# Agent Implementation
class DocumentDownloaderAgent:
    """
    PydanticAI agent for downloading Epstein documents

    This agent can:
    - Discover available document collections
    - List documents in collections
    - Download single or multiple documents
    - Monitor download progress
    - Report completion status
    """

    def __init__(self, model: str = "openai:gpt-4", mcp_server_url: str = MCP_SERVER_URL):
        self.mcp_url = mcp_server_url
        self.agent = Agent(model=model, system_prompt=self._get_system_prompt())
        self._register_tools()

    def _get_system_prompt(self) -> str:
        """Get the system prompt for the agent"""
        return """You are a specialized document retrieval agent for the Epstein Files project.

Your primary responsibilities:
1. Help users discover available document collections
2. Provide information about documents in collections
3. Download documents efficiently and track progress
4. Report status and handle errors gracefully

You have access to tools for:
- Listing available collections
- Getting collection details
- Listing documents in a collection
- Downloading single documents
- Bulk downloading collections
- Checking download status

Always:
- Verify collections exist before downloading
- Provide progress updates for long-running downloads
- Report errors clearly and suggest solutions
- Confirm completion with file locations

Never:
- Download without user confirmation
- Overwrite existing files without warning
- Ignore errors or failures
- Make up information about unavailable documents
"""

    def _register_tools(self):
        """Register all tools with the agent"""

        @self.agent.tool
        def list_collections() -> list[CollectionInfo]:
            """List all available document collections from government sources"""
            try:
                response = requests.get(f"{self.mcp_url}/collections")
                response.raise_for_status()
                collections = response.json()
                return [CollectionInfo(**c) for c in collections]
            except Exception as e:
                return [{"error": f"Failed to list collections: {e}"}]

        @self.agent.tool
        def get_collection_info(collection_id: str) -> CollectionInfo:
            """Get detailed information about a specific collection"""
            try:
                response = requests.get(f"{self.mcp_url}/collections/{collection_id}")
                response.raise_for_status()
                return CollectionInfo(**response.json())
            except Exception as e:
                return {"error": f"Failed to get collection info: {e}"}

        @self.agent.tool
        def list_documents(collection_id: str, limit: int = 10) -> list[dict]:
            """List documents in a collection"""
            try:
                response = requests.get(
                    f"{self.mcp_url}/collections/{collection_id}/documents",
                    params={"limit": limit, "offset": 0},
                )
                response.raise_for_status()
                return response.json()
            except Exception as e:
                return [{"error": f"Failed to list documents: {e}"}]

        @self.agent.tool
        def download_collection(request: DownloadRequest) -> list[DownloadStatus]:
            """
            Download all documents from a collection.
            Returns list of download tasks.
            """
            try:
                response = requests.post(f"{self.mcp_url}/download/bulk", json=request.model_dump())
                response.raise_for_status()
                tasks = response.json()
                return [DownloadStatus(**t) for t in tasks]
            except Exception as e:
                return [{"error": f"Failed to start download: {e}"}]

        @self.agent.tool
        def download_document(url: str, destination: str = DOWNLOAD_DIR) -> DownloadStatus:
            """Download a single document"""
            try:
                response = requests.post(
                    f"{self.mcp_url}/download", json={"url": url, "destination": destination}
                )
                response.raise_for_status()
                return DownloadStatus(**response.json())
            except Exception as e:
                return {"error": f"Failed to download document: {e}"}

        @self.agent.tool
        def check_download_status(task_id: str) -> DownloadStatus:
            """Check the status of a download task"""
            try:
                response = requests.get(f"{self.mcp_url}/download/status/{task_id}")
                response.raise_for_status()
                return DownloadStatus(**response.json())
            except Exception as e:
                return {"error": f"Failed to check status: {e}"}

        @self.agent.tool
        def get_all_download_status() -> list[DownloadStatus]:
            """Get status of all active downloads"""
            try:
                response = requests.get(f"{self.mcp_url}/download/status")
                response.raise_for_status()
                statuses = response.json()
                return [DownloadStatus(**s) for s in statuses]
            except Exception as e:
                return [{"error": f"Failed to get statuses: {e}"}]

        @self.agent.tool
        def get_server_health() -> dict:
            """Check if the MCP server is healthy and responding"""
            try:
                response = requests.get(f"{self.mcp_url}/health")
                response.raise_for_status()
                return response.json()
            except Exception as e:
                return {"error": f"Server health check failed: {e}"}

    async def run(self, user_request: str) -> str:
        """
        Run the agent with a user request

        Args:
            user_request: Natural language request from user

        Returns:
            Agent's response as string
        """
        result = await self.agent.run(user_request)
        return result.data

    async def chat(self):
        """
        Interactive chat mode
        """
        print("=== Epstein Document Downloader Agent ===")
        print("Type 'quit' or 'exit' to end the session")
        print()

        while True:
            try:
                user_input = input("You: ").strip()

                if user_input.lower() in ["quit", "exit"]:
                    print("Goodbye!")
                    break

                if not user_input:
                    continue

                print("\nAgent: ", end="", flush=True)
                response = await self.run(user_input)
                print(response)
                print()

            except KeyboardInterrupt:
                print("\nGoodbye!")
                break
            except Exception as e:
                print(f"\nError: {e}")
                print()


# CLI Interface
async def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="PydanticAI Document Downloader Agent")
    parser.add_argument(
        "request", nargs="*", help="Natural language request (omit for interactive mode)"
    )
    parser.add_argument(
        "--model", default="openai:gpt-4", help="LLM model to use (default: openai:gpt-4)"
    )
    parser.add_argument(
        "--server", default=MCP_SERVER_URL, help=f"MCP server URL (default: {MCP_SERVER_URL})"
    )

    args = parser.parse_args()

    # Create agent
    agent = DocumentDownloaderAgent(model=args.model, mcp_server_url=args.server)

    # Check server health
    health_response = requests.get(f"{args.server}/health")
    if health_response.status_code != 200:
        print(f"ERROR: MCP server at {args.server} is not responding")
        print("Please start the server with:")
        print("  cd mcp_servers/epstein_files_downloader")
        print("  python server.py")
        sys.exit(1)

    print(f"✓ Connected to MCP server at {args.server}")

    # Run agent
    if args.request:
        # Single request mode
        request = " ".join(args.request)
        print(f"\nRequest: {request}")
        print("\nAgent: ", end="", flush=True)
        response = await agent.run(request)
        print(response)
    else:
        # Interactive chat mode
        await agent.chat()


if __name__ == "__main__":
    asyncio.run(main())
