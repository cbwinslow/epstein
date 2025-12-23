"""
Database Troubleshooting Agent
Specialized agent for PostgreSQL database troubleshooting, performance analysis, and optimization.
"""

from typing import List, Dict, Any, Optional
import asyncio
import json
import time
from datetime import datetime
from dataclasses import dataclass
import psycopg2
from psycopg2 import sql, OperationalError, Error
from psycopg2.extras import RealDictCursor


@dataclass
class DatabaseHealth:
    """Database health metrics"""
    connection_status: str
    response_time: float
    active_connections: int
    idle_connections: int
    blocked_queries: int
    slow_queries: int
    last_checked: str


@dataclass
class QueryAnalysis:
    """Query performance analysis"""
    query_text: str
    execution_time: float
    rows_affected: int
    index_usage: List[str]
    recommendations: List[str]
    execution_plan: Optional[str] = None


class DatabaseTroubleshooter:
    """
    Specialized agent for PostgreSQL database troubleshooting, performance analysis,
    and optimization recommendations.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.connection = None
        self.health_metrics = {}
        
    def _connect_to_postgres(self) -> bool:
        """Connect to PostgreSQL database"""
        try:
            dsn = self.config.get('postgres_dsn', 'postgresql://analysis:analysis@localhost:5432/analysis')
            self.connection = psycopg2.connect(dsn)
            self.connection.autocommit = True
            return True
        except OperationalError as e:
            print(f"Failed to connect to PostgreSQL: {e}")
            return False
        except Exception as e:
            print(f"Unexpected error connecting to PostgreSQL: {e}")
            return False
    
    async def check_database_health(self) -> Dict[str, Any]:
        """
        Perform comprehensive database health check.
        
        Returns:
            Dictionary with database health metrics
        """
        if not self.connection:
            if not self._connect_to_postgres():
                return {"error": "Failed to connect to PostgreSQL"}
        
        try:
            health_metrics = DatabaseHealth(
                connection_status="unknown",
                response_time=0.0,
                active_connections=0,
                idle_connections=0,
                blocked_queries=0,
                slow_queries=0,
                last_checked=datetime.now().isoformat()
            )
            
            cursor = self.connection.cursor(cursor_factory=RealDictCursor)
            
            # Test basic connectivity
            start_time = time.time()
            cursor.execute("SELECT 1")
            response_time = time.time() - start_time
            health_metrics.response_time = response_time
            health_metrics.connection_status = "healthy" if response_time < 1.0 else "slow"
            
            # Get connection statistics
            cursor.execute("""
                SELECT count(*) as active_connections 
                FROM pg_stat_activity 
                WHERE state = 'active'
            """)
            health_metrics.active_connections = cursor.fetchone()['active_connections']
            
            cursor.execute("""
                SELECT count(*) as idle_connections 
                FROM pg_stat_activity 
                WHERE state = 'idle'
            """)
            health_metrics.idle_connections = cursor.fetchone()['idle_connections']
            
            # Check for blocked queries
            cursor.execute("""
                SELECT count(*) as blocked_queries 
                FROM pg_stat_activity 
                WHERE wait_event_type = 'Lock'
            """)
            health_metrics.blocked_queries = cursor.fetchone()['blocked_queries']
            
            # Check for slow queries (assuming > 1 second is slow)
            cursor.execute("""
                SELECT count(*) as slow_queries 
                FROM pg_stat_statements 
                WHERE mean_time > 1000
                ORDER BY mean_time DESC
                LIMIT 10
            """)
            health_metrics.slow_queries = cursor.fetchone()['slow_queries']
            
            cursor.close()
            
            self.health_metrics = health_metrics
            
            return {
                "database_health": {
                    "connection_status": health_metrics.connection_status,
                    "response_time_ms": health_metrics.response_time * 1000,
                    "active_connections": health_metrics.active_connections,
                    "idle_connections": health_metrics.idle_connections,
                    "blocked_queries": health_metrics.blocked_queries,
                    "slow_queries": health_metrics.slow_queries,
                    "last_checked": health_metrics.last_checked
                },
                "recommendations": self._generate_health_recommendations(health_metrics),
                "overall_status": "healthy" if health_metrics.blocked_queries == 0 else "needs_attention"
            }
            
        except Exception as e:
            return {"error": f"Health check failed: {e}"}
    
    async def analyze_query_performance(self, query_text: str) -> Dict[str, Any]:
        """
        Analyze query performance and provide optimization recommendations.
        
        Args:
            query_text: SQL query to analyze
            
        Returns:
            Dictionary with query analysis results
        """
        if not self.connection:
            if not self._connect_to_postgres():
                return {"error": "Failed to connect to PostgreSQL"}
        
        try:
            cursor = self.connection.cursor(cursor_factory=RealDictCursor)
            
            # Get execution plan
            execution_plan = None
            try:
                cursor.execute(f"EXPLAIN ANALYZE {query_text}")
                execution_plan_rows = cursor.fetchall()
                execution_plan = "\n".join([row['QUERY PLAN'] for row in execution_plan_rows])
            except Exception as e:
                execution_plan = f"Failed to get execution plan: {e}"
            
            # Execute query and measure performance
            start_time = time.time()
            cursor.execute(query_text)
            execution_time = time.time() - start_time
            
            rows_affected = cursor.rowcount
            
            # Get index usage information
            index_usage = []
            try:
                cursor.execute("""
                    SELECT indexrelid::regclass as index_name
                    FROM pg_stat_user_indexes
                    WHERE relid = (
                        SELECT relid FROM pg_stat_user_tables 
                        WHERE schemaname = 'public' 
                        AND tablename IN (
                            SELECT tablename FROM pg_tables 
                            WHERE schemaname = 'public'
                            LIMIT 1
                        )
                    )
                """)
                index_usage = [row['index_name'] for row in cursor.fetchall()]
            except:
                pass
            
            cursor.close()
            
            # Generate recommendations
            recommendations = self._generate_query_recommendations(
                query_text, execution_time, execution_plan
            )
            
            query_analysis = QueryAnalysis(
                query_text=query_text,
                execution_time=execution_time,
                rows_affected=rows_affected,
                index_usage=index_usage,
                recommendations=recommendations,
                execution_plan=execution_plan
            )
            
            return {
                "query_analysis": {
                    "query_text": query_text,
                    "execution_time_ms": execution_time * 1000,
                    "rows_affected": rows_affected,
                    "index_usage": index_usage,
                    "execution_plan": execution_plan,
                    "recommendations": recommendations
                },
                "performance_score": self._calculate_performance_score(execution_time, rows_affected),
                "optimization_priority": self._determine_optimization_priority(execution_time, recommendations)
            }
            
        except Exception as e:
            return {"error": f"Query analysis failed: {e}"}
    
    async def check_indexes(self) -> Dict[str, Any]:
        """
        Analyze database indexes and provide optimization recommendations.
        
        Returns:
            Dictionary with index analysis results
        """
        if not self.connection:
            if not self._connect_to_postgres():
                return {"error": "Failed to connect to PostgreSQL"}
        
        try:
            cursor = self.connection.cursor(cursor_factory=RealDictCursor)
            
            # Get all indexes
            cursor.execute("""
                SELECT 
                    schemaname,
                    tablename,
                    indexname,
                    indexdef,
                    idx_scan,
                    idx_tup_read,
                    idx_tup_fetch,
                    CASE 
                        WHEN idx_scan = 0 THEN 'unused'
                        WHEN idx_scan < 100 THEN 'rarely_used'
                        ELSE 'frequently_used'
                    END as usage_status
                FROM pg_stat_user_indexes
                ORDER BY schemaname, tablename, indexname
            """)
            
            indexes = cursor.fetchall()
            
            # Get missing indexes
            cursor.execute("""
                SELECT 
                    schemaname,
                    tablename,
                    indexdef
                FROM pg_stat_user_indexes
                WHERE idx_scan = 0
                AND indexname NOT LIKE '%_pkey%'
            """)
            
            unused_indexes = cursor.fetchall()
            
            # Get potential missing indexes
            cursor.execute("""
                SELECT 
                    schemaname,
                    tablename,
                    attname as column_name,
                    correlation
                FROM pg_stats
                WHERE correlation > 0.3
                AND schemaname = 'public'
                ORDER BY correlation DESC
                LIMIT 10
            """)
            
            potential_indexes = cursor.fetchall()
            
            cursor.close()
            
            return {
                "index_analysis": {
                    "total_indexes": len(indexes),
                    "frequently_used": len([idx for idx in indexes if idx['usage_status'] == 'frequently_used']),
                    "rarely_used": len([idx for idx in indexes if idx['usage_status'] == 'rarely_used']),
                    "unused": len([idx for idx in indexes if idx['usage_status'] == 'unused']),
                    "unused_indexes": unused_indexes,
                    "potential_indexes": potential_indexes
                },
                "recommendations": self._generate_index_recommendations(indexes, unused_indexes, potential_indexes)
            }
            
        except Exception as e:
            return {"error": f"Index analysis failed: {e}"}
    
    async def check_table_statistics(self) -> Dict[str, Any]:
        """
        Analyze table statistics and performance metrics.
        
        Returns:
            Dictionary with table statistics
        """
        if not self.connection:
            if not self._connect_to_postgres():
                return {"error": "Failed to connect to PostgreSQL"}
        
        try:
            cursor = self.connection.cursor(cursor_factory=RealDictCursor)
            
            # Get table statistics
            cursor.execute("""
                SELECT 
                    schemaname,
                    tablename,
                    seq_scan,
                    seq_tup_read,
                    idx_scan,
                    idx_tup_fetch,
                    n_tup_ins,
                    n_tup_upd,
                    n_tup_del,
                    n_live_tup,
                    n_dead_tup,
                    last_vacuum,
                    last_autovacuum,
                    last_analyze,
                    last_autoanalyze
                FROM pg_stat_user_tables
                ORDER BY seq_scan DESC
                LIMIT 20
            """)
            
            tables = cursor.fetchall()
            
            # Get table sizes
            cursor.execute("""
                SELECT 
                    schemaname,
                    tablename,
                    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
                    pg_total_relation_size(schemaname||'.'||tablename) as size_bytes
                FROM pg_tables
                WHERE schemaname = 'public'
                ORDER BY size_bytes DESC
                LIMIT 20
            """)
            
            table_sizes = cursor.fetchall()
            
            cursor.close()
            
            return {
                "table_statistics": {
                    "total_tables": len(tables),
                    "tables_with_high_seq_scan": len([t for t in tables if t['seq_scan'] > 1000]),
                    "largest_tables": table_sizes[:10],
                    "tables_needing_vacuum": [t for t in tables if t['n_dead_tup'] > 1000],
                    "tables_needing_analyze": [t for t in tables if t['last_analyze'] is None]
                },
                "recommendations": self._generate_table_recommendations(tables, table_sizes)
            }
            
        except Exception as e:
            return {"error": f"Table statistics analysis failed: {e}"}
    
    async def optimize_database(self) -> Dict[str, Any]:
        """
        Provide comprehensive database optimization recommendations.
        
        Returns:
            Dictionary with optimization recommendations
        """
        try:
            # Run all analyses
            health_check = await self.check_database_health()
            index_analysis = await self.check_indexes()
            table_stats = await self.check_table_statistics()
            
            recommendations = []
            
            # Combine recommendations from all analyses
            if "recommendations" in health_check:
                recommendations.extend(health_check["recommendations"])
            
            if "recommendations" in index_analysis:
                recommendations.extend(index_analysis["recommendations"])
            
            if "recommendations" in table_stats:
                recommendations.extend(table_stats["recommendations"])
            
            # Prioritize recommendations
            prioritized_recommendations = self._prioritize_optimization_recommendations(recommendations)
            
            return {
                "database_optimization": {
                    "overall_health": health_check.get("database_health", {}),
                    "index_status": index_analysis.get("index_analysis", {}),
                    "table_status": table_stats.get("table_statistics", {}),
                    "prioritized_recommendations": prioritized_recommendations,
                    "estimated_improvement": self._estimate_optimization_impact(prioritized_recommendations),
                    "optimization_timestamp": datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            return {"error": f"Database optimization failed: {e}"}
    
    def _generate_health_recommendations(self, health: DatabaseHealth) -> List[Dict[str, Any]]:
        """Generate recommendations based on health metrics"""
        recommendations = []
        
        if health.response_time > 1.0:
            recommendations.append({
                "type": "performance",
                "issue": "High database response time",
                "recommendation": "Consider increasing shared_buffers or optimizing queries",
                "priority": "high"
            })
        
        if health.blocked_queries > 0:
            recommendations.append({
                "type": "blocking",
                "issue": f"{health.blocked_queries} blocked queries detected",
                "recommendation": "Investigate long-running transactions and consider query optimization",
                "priority": "critical"
            })
        
        if health.idle_connections > health.active_connections * 2:
            recommendations.append({
                "type": "connections",
                "issue": "High number of idle connections",
                "recommendation": "Consider reducing connection pool size or implementing connection timeouts",
                "priority": "medium"
            })
        
        return recommendations
    
    def _generate_query_recommendations(self, query: str, execution_time: float, 
                                      execution_plan: Optional[str]) -> List[str]:
        """Generate query optimization recommendations"""
        recommendations = []
        
        if execution_time > 1.0:
            recommendations.append("Query execution time is high - consider adding appropriate indexes")
        
        if "Seq Scan" in execution_plan:
            recommendations.append("Sequential scan detected - consider adding indexes for better performance")
        
        if "Hash Join" in execution_plan and execution_time > 0.5:
            recommendations.append("Hash join detected - ensure proper join conditions and indexes")
        
        if "Nested Loop" in execution_plan and execution_time > 0.5:
            recommendations.append("Nested loop detected - consider optimizing join conditions")
        
        if len(recommendations) == 0:
            recommendations.append("Query appears to be well-optimized")
        
        return recommendations
    
    def _generate_index_recommendations(self, indexes: List[Dict], unused: List[Dict], 
                                      potential: List[Dict]) -> List[Dict[str, Any]]:
        """Generate index optimization recommendations"""
        recommendations = []
        
        # Remove unused indexes
        if unused:
            recommendations.append({
                "type": "cleanup",
                "action": "Remove unused indexes",
                "indexes": [idx['indexname'] for idx in unused],
                "impact": "Reduce storage and maintenance overhead",
                "priority": "low"
            })
        
        # Add potential indexes
        if potential:
            recommendations.append({
                "type": "optimization",
                "action": "Consider adding indexes on high-correlation columns",
                "columns": [f"{row['tablename']}.{row['column_name']}" for row in potential],
                "impact": "Improve query performance for filtered operations",
                "priority": "medium"
            })
        
        return recommendations
    
    def _generate_table_recommendations(self, tables: List[Dict], sizes: List[Dict]) -> List[Dict[str, Any]]:
        """Generate table maintenance recommendations"""
        recommendations = []
        
        # Tables needing vacuum
        vacuum_needed = [t for t in tables if t['n_dead_tup'] > 1000]
        if vacuum_needed:
            recommendations.append({
                "type": "maintenance",
                "action": "Schedule VACUUM for tables with high dead tuples",
                "tables": [t['tablename'] for t in vacuum_needed],
                "impact": "Reduce table size and improve query performance",
                "priority": "medium"
            })
        
        # Large tables
        large_tables = [t for t in sizes if t['size_bytes'] > 100 * 1024 * 1024]  # > 100MB
        if large_tables:
            recommendations.append({
                "type": "partitioning",
                "action": "Consider table partitioning for large tables",
                "tables": [t['tablename'] for t in large_tables],
                "impact": "Improve maintenance and query performance",
                "priority": "low"
            })
        
        return recommendations
    
    def _calculate_performance_score(self, execution_time: float, rows_affected: int) -> float:
        """Calculate query performance score (0-100)"""
        if execution_time == 0:
            return 100.0
        
        # Score based on execution time and rows processed
        time_score = max(0, 100 - (execution_time * 1000))  # Penalize slow queries
        efficiency_score = min(100, (rows_affected / execution_time) * 10)  # Reward efficiency
        
        return (time_score + efficiency_score) / 2
    
    def _determine_optimization_priority(self, execution_time: float, 
                                       recommendations: List[str]) -> str:
        """Determine optimization priority"""
        if execution_time > 5.0:
            return "high"
        elif execution_time > 1.0:
            return "medium"
        else:
            return "low"
    
    def _prioritize_optimization_recommendations(self, recommendations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Prioritize optimization recommendations"""
        priority_order = {"critical": 4, "high": 3, "medium": 2, "low": 1}
        
        return sorted(recommendations, 
                    key=lambda x: priority_order.get(x.get("priority", "low"), 0),
                    reverse=True)
    
