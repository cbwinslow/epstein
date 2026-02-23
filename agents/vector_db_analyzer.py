"""
Vector Database Analyzer Agent
Specialized agent for analyzing and troubleshooting vector databases (Qdrant).
"""

import asyncio
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse


@dataclass
class VectorCollectionInfo:
    """Information about a vector collection"""
    name: str
    vectors_count: int
    vectors_config: dict[str, Any]
    status: str
    disk_usage: str | None = None
    memory_usage: str | None = None
    last_updated: str | None = None


@dataclass
class QueryPerformance:
    """Query performance metrics"""
    query_type: str
    execution_time: float
    results_count: int
    similarity_threshold: float
    index_used: str
    memory_usage: float | None = None


class VectorDBAnalyzer:
    """
    Specialized agent for analyzing vector databases, performance optimization,
    and troubleshooting Qdrant instances.
    """

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}
        self.qdrant_client = None
        self.collections = {}
        self.performance_metrics = []

    def _connect_to_qdrant(self) -> bool:
        """Connect to Qdrant instance"""
        try:
            qdrant_url = self.config.get('qdrant_url', 'http://localhost:6333')
            self.qdrant_client = QdrantClient(url=qdrant_url)
            # Test connection
            self.qdrant_client.get_collections()
            return True
        except Exception as e:
            print(f"Failed to connect to Qdrant: {e}")
            return False

    async def analyze_collection(self, collection_name: str) -> dict[str, Any]:
        """
        Analyze a specific vector collection in detail.

        Args:
            collection_name: Name of the collection to analyze

        Returns:
            Dictionary with detailed collection analysis
        """
        if not self.qdrant_client and not self._connect_to_qdrant():
            return {"error": "Failed to connect to Qdrant"}

        try:
            # Get collection info
            collection_info = self.qdrant_client.get_collection(collection_name)

            # Get collection stats
            stats = self.qdrant_client.get_collection(collection_name)

            # Get sample vectors for analysis
            sample_vectors = await self._get_sample_vectors(collection_name, limit=10)

            # Analyze vector dimensions and configuration
            config_analysis = self._analyze_vector_config(collection_info.config.params.vectors)

            # Check for potential issues
            issues = self._detect_collection_issues(collection_info, stats)

            return {
                "collection_name": collection_name,
                "status": collection_info.status,
                "vectors_count": getattr(stats, 'vectors_count', 0),
                "config_analysis": config_analysis,
                "sample_vectors": sample_vectors,
                "issues_detected": issues,
                "analysis_timestamp": datetime.now().isoformat(),
                "recommendations": self._generate_recommendations(config_analysis, issues)
            }

        except UnexpectedResponse as e:
            return {"error": f"Collection not found: {e}"}
        except Exception as e:
            return {"error": f"Analysis failed: {e}"}

    async def analyze_all_collections(self) -> dict[str, Any]:
        """
        Analyze all collections in the Qdrant instance.

        Returns:
            Dictionary with analysis of all collections
        """
        if not self.qdrant_client and not self._connect_to_qdrant():
            return {"error": "Failed to connect to Qdrant"}

        try:
            collections_info = self.qdrant_client.get_collections()
            collection_names = [col.name for col in collections_info.collections]

            analyses = {}
            total_vectors = 0

            for collection_name in collection_names:
                analysis = await self.analyze_collection(collection_name)
                if "error" not in analysis:
                    analyses[collection_name] = analysis
                    total_vectors += analysis.get("vectors_count", 0)

            return {
                "qdrant_status": "healthy",
                "total_collections": len(collection_names),
                "total_vectors": total_vectors,
                "collections": analyses,
                "overall_recommendations": self._generate_overall_recommendations(analyses),
                "analysis_timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            return {"error": f"Failed to analyze collections: {e}"}

    async def benchmark_query_performance(self, collection_name: str,
                                        query_text: str,
                                        limit: int = 10) -> dict[str, Any]:
        """
        Benchmark query performance for a collection.

        Args:
            collection_name: Name of the collection to query
            query_text: Text to search for
            limit: Number of results to return

        Returns:
            Dictionary with performance metrics
        """
        if not self.qdrant_client and not self._connect_to_qdrant():
            return {"error": "Failed to connect to Qdrant"}

        try:
            import time

            # Generate query embedding (placeholder - should use actual embedding model)
            query_embedding = [0.1] * 768  # 768-dimensional embedding

            # Perform search with timing
            start_time = time.time()
            search_result = self.qdrant_client.search(
                collection_name=collection_name,
                query_vector=query_embedding,
                limit=limit
            )
            end_time = time.time()

            execution_time = end_time - start_time

            # Analyze performance
            performance_analysis = {
                "execution_time_ms": execution_time * 1000,
                "results_count": len(search_result),
                "average_similarity": sum(score.score for score in search_result) / len(search_result) if search_result else 0,
                "similarity_distribution": {
                    "min": min(score.score for score in search_result) if search_result else 0,
                    "max": max(score.score for score in search_result) if search_result else 0,
                    "avg": sum(score.score for score in search_result) / len(search_result) if search_result else 0
                },
                "query_timestamp": datetime.now().isoformat()
            }

            return {
                "collection_name": collection_name,
                "query_text": query_text,
                "performance": performance_analysis,
                "recommendations": self._generate_performance_recommendations(performance_analysis)
            }

        except Exception as e:
            return {"error": f"Performance benchmark failed: {e}"}

    async def optimize_collection(self, collection_name: str) -> dict[str, Any]:
        """
        Provide optimization recommendations for a collection.

        Args:
            collection_name: Name of the collection to optimize

        Returns:
            Dictionary with optimization recommendations
        """
        analysis = await self.analyze_collection(collection_name)

        if "error" in analysis:
            return analysis

        recommendations = []

        # Check for common optimization opportunities
        config = analysis.get("config_analysis", {})

        if config.get("vector_size", 0) > 1024:
            recommendations.append({
                "type": "vector_size",
                "issue": "Large vector dimensions may impact performance",
                "recommendation": "Consider using dimensionality reduction techniques",
                "priority": "medium"
            })

        if analysis.get("vectors_count", 0) > 100000:
            recommendations.append({
                "type": "indexing",
                "issue": "Large collection size may benefit from specialized indexing",
                "recommendation": "Consider using HNSW with optimized parameters",
                "priority": "high"
            })

        if analysis.get("issues_detected", []):
            recommendations.extend(analysis.get("issues_detected", []))

        return {
            "collection_name": collection_name,
            "optimization_recommendations": recommendations,
            "estimated_improvement": self._estimate_improvement(recommendations),
            "implementation_priority": self._prioritize_recommendations(recommendations),
            "optimization_timestamp": datetime.now().isoformat()
        }

    async def _get_sample_vectors(self, collection_name: str, limit: int = 10) -> list[dict[str, Any]]:
        """Get sample vectors from collection for analysis"""
        try:
            # Get a few sample vectors
            sample_result = self.qdrant_client.scroll(
                collection_name=collection_name,
                limit=limit,
                with_payload=True
            )

            return [
                {
                    "id": str(point.id),
                    "vector_size": len(point.vector) if hasattr(point, 'vector') else 0,
                    "payload": point.payload if hasattr(point, 'payload') else {}
                }
                for point in sample_result[0]
            ]
        except Exception as e:
            return [{"error": f"Failed to get sample vectors: {e}"}]

    def _analyze_vector_config(self, vectors_config: Any) -> dict[str, Any]:
        """Analyze vector configuration"""
        if hasattr(vectors_config, 'config'):
            config = vectors_config.config
            return {
                "vector_size": getattr(config, 'size', 0),
                "distance_metric": getattr(config, 'distance', 'unknown'),
                "index_type": getattr(config, 'index', {}).get('type', 'unknown'),
                "index_params": getattr(config, 'index', {}).get('params', {})
            }
        return {"error": "Could not parse vector configuration"}

    def _detect_collection_issues(self, collection_info: Any, stats: Any) -> list[dict[str, Any]]:
        """Detect potential issues with collection configuration"""
        issues = []

        # Check for common issues
        if hasattr(collection_info, 'config') and hasattr(collection_info.config, 'params'):
            config = collection_info.config.params

            # Check if using default HNSW parameters
            if hasattr(config.vectors, 'index') and hasattr(config.vectors.index, 'params'):
                index_params = config.vectors.index.params
                if hasattr(index_params, 'ef') and index_params.ef < 200:
                    issues.append({
                        "type": "index_parameter",
                        "issue": "Low ef value may impact search quality",
                        "recommendation": "Consider increasing ef parameter for better recall",
                        "severity": "medium"
                    })

                if hasattr(index_params, 'm') and index_params.m > 64:
                    issues.append({
                        "type": "index_parameter",
                        "issue": "High m value may impact memory usage",
                        "recommendation": "Consider reducing m parameter for better memory efficiency",
                        "severity": "low"
                    })

        return issues

    def _generate_recommendations(self, config_analysis: dict[str, Any],
                                 issues: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Generate optimization recommendations"""
        recommendations = []

        # Add configuration-based recommendations
        if config_analysis.get("vector_size", 0) > 768:
            recommendations.append({
                "type": "optimization",
                "recommendation": "Consider using dimensionality reduction to reduce vector size",
                "impact": "high",
                "effort": "medium"
            })

        # Add issue-based recommendations
        recommendations.extend(issues)

        return recommendations

    def _generate_overall_recommendations(self, collections: dict[str, Any]) -> list[dict[str, Any]]:
        """Generate overall recommendations for all collections"""
        recommendations = []

        len(collections)
        large_collections = [name for name, info in collections.items()
                            if info.get("vectors_count", 0) > 50000]

        if large_collections:
            recommendations.append({
                "type": "scaling",
                "recommendation": f"Consider sharding for {len(large_collections)} large collections",
                "collections": large_collections,
                "priority": "high"
            })

        return recommendations

    def _generate_performance_recommendations(self, performance: dict[str, Any]) -> list[dict[str, Any]]:
        """Generate performance optimization recommendations"""
        recommendations = []
        exec_time = performance.get("execution_time_ms", 0)

        if exec_time > 1000:  # More than 1 second
            recommendations.append({
                "type": "performance",
                "issue": "Query execution time is high",
                "recommendation": "Consider optimizing index parameters or reducing vector dimensions",
                "current_time_ms": exec_time,
                "target_time_ms": 500
            })

        return recommendations

    def _estimate_improvement(self, recommendations: list[dict[str, Any]]) -> dict[str, Any]:
        """Estimate potential improvement from recommendations"""
        high_priority = [r for r in recommendations if r.get("priority") == "high"]
        medium_priority = [r for r in recommendations if r.get("priority") == "medium"]

        return {
            "high_priority_count": len(high_priority),
            "medium_priority_count": len(medium_priority),
            "estimated_performance_improvement": "30-50%" if high_priority else "10-20%",
            "estimated_memory_improvement": "20-40%" if len(recommendations) > 2 else "5-15%"
        }

    def _prioritize_recommendations(self, recommendations: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Prioritize recommendations by impact and effort"""
        priority_order = {"high": 3, "medium": 2, "low": 1}

        return sorted(recommendations,
                    key=lambda x: priority_order.get(x.get("priority", "low"), 0),
                    reverse=True)


# OpenAI-compatible function definitions
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "analyze_vector_collection",
            "description": "Analyze a specific vector collection in detail",
            "parameters": {
                "type": "object",
                "properties": {
                    "collection_name": {
                        "type": "string",
                        "description": "Name of the collection to analyze"
                    }
                },
                "required": ["collection_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_all_collections",
            "description": "Analyze all collections in the Qdrant instance",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "benchmark_query_performance",
            "description": "Benchmark query performance for a collection",
            "parameters": {
                "type": "object",
                "properties": {
                    "collection_name": {
                        "type": "string",
                        "description": "Name of the collection to benchmark"
                    },
                    "query_text": {
                        "type": "string",
                        "description": "Text to search for performance testing"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of results to return",
                        "default": 10
                    }
                },
                "required": ["collection_name", "query_text"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "optimize_collection",
            "description": "Provide optimization recommendations for a collection",
            "parameters": {
                "type": "object",
                "properties": {
                    "collection_name": {
                        "type": "string",
                        "description": "Name of the collection to optimize"
                    }
                },
                "required": ["collection_name"]
            }
        }
    }
]


# Agent metadata
AGENT_INFO = {
    "name": "Vector Database Analyzer",
    "description": "Specialized agent for analyzing vector databases, performance optimization, and troubleshooting Qdrant instances",
    "version": "1.0.0",
    "capabilities": [
        "Vector collection analysis",
        "Query performance benchmarking",
        "Database optimization recommendations",
        "Issue detection and troubleshooting",
        "Performance monitoring"
    ],
    "tools": TOOLS
}


if __name__ == "__main__":
    # Example usage
    analyzer = VectorDBAnalyzer()

    async def main():
        # Analyze all collections
        result = await analyzer.analyze_all_collections()
        print("All collections analysis:", json.dumps(result, indent=2))

        # Benchmark performance
        if "collections" in result:
            for collection_name in result["collections"]:
                perf_result = await analyzer.benchmark_query_performance(
                    collection_name, "test query", 5
                )
                print(f"Performance benchmark for {collection_name}:",
                      json.dumps(perf_result, indent=2))
                break  # Just test one collection

    asyncio.run(main())
