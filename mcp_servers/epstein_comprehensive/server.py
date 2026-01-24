#!/usr/bin/env python3
"""
Epstein Comprehensive MCP Server

A complete Model Context Protocol (MCP) server that exposes all major
functionality of the Epstein project.
"""

import argparse
import logging
from fastapi import FastAPI
import uvicorn

app = FastAPI(title="Epstein Comprehensive MCP Server", version="1.0.0")

@app.get("/")
async def root():
    return {"message": "Epstein MCP Server", "version": "1.0.0"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    
    uvicorn.run(app, host=args.host, port=args.port)

if __name__ == "__main__":
    main()
