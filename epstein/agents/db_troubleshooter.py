"""
Database Troubleshooter Agent
Specialized agent for PostgreSQL database troubleshooting, performance analysis, and optimization.
"""

from typing import List, Dict, Any, Optional
import asyncio
import json
import logging
from datetime import datetime
from dataclasses import dataclass
import psycopg2
from psycopg2 import sql, pool
from psycopg2.extras import RealDictCursor
import psutil


@dataclass
class DatabaseHealth:
    """Database health metrics"""
    connection_status: str
    active_connections: int
    idle_connections: int
    blocked_queries: int
    slow_queries: int
    response_time: float
    uptime: str
    last_check: str


@dataclass
class IndexInfo:
    """Index information and statistics"""
    table_name: str
    index_name: str
    index_type: str
    size_mb: float
    scans: int
    tuples_read: int
    tuples_fetched: int
    efficiency: float


@dataclass
class QueryPerformance:
    """Query performance metrics"""
    query_text: str
    execution_time: float
    rows_affected: int
    index_used: str
    cost: float
    rows: int
    planning_time: float


class DatabaseTroubleshooter:
    """
    Specialized agent for PostgreSQL database troubleshooting, performance analysis, and optimization.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.db_pool = None
        self.logger = logging.getLogger(__name__)
        self.health_metrics = {}
        
        # Load configuration
        self.postgres_dsn = self.config.get('postgres_dsn', 
                                           'postgresql://analysis:analysis@localhost:5432/analysis')
        self.monitoring_interval = self.config.get('monitoring_interval', 60)
        self.slow_query_threshold = self.config.get('slow_query_threshold', 1000)
        self.connection_timeout = self.config.get('connection_timeout', 30)
        
        # Analysis configuration
        self.enable_execution_plans = self.config.get('enable_execution_plans', True)
        self.enable_index_analysis = self.config.get('enable_index_analysis', True)
        self.enable_table_statistics = self.config.get('enable_table_statistics', True)
        self.enable_vacuum_recommendations = self.config.get('enable_vacuum_recommendations', True)
    
    def _create_connection_pool(self) -> bool:
        """Create connection pool for database operations"""
        try:
            # Parse DSN to extract connection parameters
            import urllib.parse as urlparse
            parsed = urlparse.urlparse(self.postgres_dsn)
            
            # Create connection pool
            self.db_pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=1,
                maxconn=10,
                host=parsed.hostname,
                port=parsed.port or 5432,
                database=parsed.path[1:],
                user=parsed.username,
                password=parsed.password,
                connect_timeout=self.connection_timeout
            )
            
            # Test connection
            with self.db_pool.getconn() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    return True
                    
        except Exception as e:
            self.logger.error(f"Failed to create connection pool: {e}")
            return False
    
    async def check_database_health(self) -> Dict[str, Any]:
        """
        Perform comprehensive database health check.
        
        Returns:
            Dictionary with health check results
        """
        if not self.db_pool:
            if not self._create_connection_pool():
                return {"error": "Failed to connect to database"}
        
        try:
            health_metrics = DatabaseHealth(
                connection_status="unknown",
                active_connections=0,
                idle_connections=0,
                blocked_queries=0,
                slow_queries=0,
                response_time=0.0,
                uptime="unknown",
                last_check=datetime.now().isoformat()
            )
            
            with self.db_pool.getconn() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    
                    # Check connection status
                    start_time = datetime.now()
                    cur.execute("SELECT 1")
                    response_time = (datetime.now() - start_time).total_seconds()
                    health_metrics.response_time = response_time
                    
                    if response_time < 1.0:
                        health_metrics.connection_status = "healthy"
                    elif response_time < 5.0:
                        health_metrics.connection_status = "slow"
                    else:
                        health_metrics.connection_status = "critical"
                    
                    # Get connection statistics
                    cur.execute("""
                        SELECT 
                            count(*) as total_connections,
                            count(case when state = 'active' then 1 end) as active_connections,
                            count(case when state = 'idle' then 1 end) as idle_connections
                        FROM pg_stat_activity
                        WHERE pid != pg_backend_pid()
                    """)
                    conn_stats = cur.fetchone()
                    health_metrics.active_connections = conn_stats['active_connections']
                    health_metrics.idle_connections = conn_stats['idle_connections']
                    
                    # Check for blocked queries
                    cur.execute("""
                        SELECT count(*) as blocked_queries
                        FROM pg_locks blocked
                        JOIN pg_locks blocking ON blocked.locktype = blocking.locktype
                            AND blocked.database IS NOT DISTINCT FROM blocking.database
                            AND blocked.relation IS NOT DISTINCT FROM blocking.relation
                            AND blocked.page IS NOT DISTINCT FROM blocking.page
                            AND blocked.tuple IS NOT DISTINCT FROM blocking.tuple
                            AND blocked.virtualxid IS NOT DISTINCT FROM blocking.virtualxid
                            AND blocked.transactionid IS NOT DISTINCT FROM blocking.transactionid
                            AND blocked.classid IS NOT DISTINCT FROM blocking.classid
                            AND blocked.objid IS NOT DISTINCT FROM blocking.objid
                            AND blocked.objsubid IS NOT DISTINCT FROM blocking.objsubid
                            AND blocked.pid != blocking.pid
                    """)
                    blocked_stats = cur.fetchone()
                    health_metrics.blocked_queries = blocked_stats['blocked_queries']
                    
                    # Check for slow queries
                    cur.execute("""
                        SELECT count(*) as slow_queries
                        FROM pg_stat_statements
                        WHERE mean_time > %s
                    """, (self.slow_query_threshold,))
                    slow_stats = cur.fetchone()
                    health_metrics.slow_queries = slow_stats['slow_queries']
                    
                    # Get database uptime
                    cur.execute("""
                        SELECT pg_stat_activity.query_start
                        FROM pg_stat_activity
                        WHERE state = 'active'
                        ORDER BY query_start ASC
                        LIMIT 1
                    """)
                    uptime_result = cur.fetchone()
                    if uptime_result:
                        uptime_start = uptime_result['query_start']
                        uptime = datetime.now() - uptime_start
                        health_metrics.uptime = str(uptime)
            
            self.health_metrics = health_metrics
            
            return {
                "database_health": {
                    "connection_status": health_metrics.connection_status,
                    "response_time_ms": health_metrics.response_time * 1000,
                    "active_connections": health_metrics.active_connections,
                    "idle_connections": health_metrics.idle_connections,
                    "blocked_queries": health_metrics.blocked_queries,
                    "slow_queries": health_metrics.slow_queries,
                    "uptime": health_metrics.uptime
                },
                "health_score": self._calculate_health_score(health_metrics),
                "recommendations": self._generate_health_recommendations(health_metrics),
                "check_timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {"error": f"Health check failed: {e}"}
    
    async def check_indexes(self) -> Dict[str, Any]:
        """
        Analyze database indexes and provide optimization recommendations.
        
        Returns:
            Dictionary with index analysis results
        """
        if not self.db_pool:
            if not self._create_connection_pool():
                return {"error": "Failed to connect to database"}
        
        try:
            indexes = []
            recommendations = []
            
            with self.db_pool.getconn() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    
                    # Get index statistics
                    cur.execute("""
                        SELECT 
                            schemaname,
                            tablename,
                            indexname,
                            indexdef,
                            pg_size_pretty(pg_relation_size(indexname::regclass)) as size,
                            idx_scan,
                            idx_tup_read,
                            idx_tup_fetch,
                            CASE 
                                WHEN idx_scan = 0 THEN 0
                                WHEN idx_tup_read = 0 THEN 0
                                ELSE (idx_tup_fetch::float / idx_tup_read::float) * 100
                            END as efficiency
                        FROM pg_stat_user_indexes
                        JOIN pg_class ON pg_class.oid = indexrelid
                        ORDER BY idx_scan DESC
                    """)
                    
                    index_rows = cur.fetchall()
                    
                    for row in index_rows:
                        index_info = IndexInfo(
                            table_name=f"{row['schemaname']}.{row['tablename']}",
                            index_name=row['indexname'],
                            index_type="B-tree",  # Default, could be parsed from indexdef
                            size_mb=float(row['size'].split()[0]) if ' ' in row['size'] else 0.0,
                            scans=row['idx_scan'],
                            tuples_read=row['idx_tup_read'],
                            tuples_fetched=row['idx_tup_fetch'],
                            efficiency=row['efficiency'] if row['efficiency'] else 0.0
                        )
                        indexes.append(index_info)
                    
                    # Generate recommendations
                    for index in indexes:
                        if index.efficiency < 10.0 and index.scans > 100:
                            recommendations.append({
                                "type": "inefficient_index",
                                "index_name": index.index_name,
                                "table_name": index.table_name,
                                "issue": f"Low efficiency ({index.efficiency:.1f}%) with high usage ({index.scans} scans)",
                                "recommendation": "Consider dropping or rebuilding this index"
                            })
                        
                        if index.size_mb > 100:  # Large indexes
                            recommendations.append({
                                "type": "large_index",
                                "index_name": index.index_name,
                                "table_name": index.table_name,
                                "issue": f"Large index size ({index.size_mb:.1f}MB)",
                                "recommendation": "Consider partitioning or optimizing index structure"
                            })
                    
                    # Check for missing indexes
                    cur.execute("""
                        SELECT 
                            schemaname,
                            tablename,
                            attname,
                            n_distinct,
                            correlation
                        FROM pg_stats
                        WHERE n_distinct > 0
                        AND schemaname NOT IN ('pg_catalog', 'information_schema')
                        ORDER BY n_distinct DESC
                    """)
                    
                    table_stats = cur.fetchall()
                    
                    for stat in table_stats:
                        if stat['n_distinct'] > 1000 and stat['correlation'] < 0.3:
                            recommendations.append({
                                "type": "missing_index",
                                "table_name": f"{stat['schemaname']}.{stat['tablename']}",
                                "column": stat['attname'],
                                "issue": f"High cardinality ({stat['n_distinct']}) with low correlation ({stat['correlation']:.2f})",
                                "recommendation": f"Consider creating index on {stat['attname']}"
                            })
            
            return {
                "indexes": [
                    {
                        "table_name": idx.table_name,
                        "index_name": idx.index_name,
                        "type": idx.index_type,
                        "size_mb": idx.size_mb,
                        "scans": idx.scans,
                        "efficiency": idx.efficiency,
                        "status": "good" if idx.efficiency > 50 else "needs_attention"
                    }
                    for idx in indexes
                ],
                "recommendations": recommendations,
                "total_indexes": len(indexes),
                "recommendation_count": len(recommendations),
                "analysis_timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {"error": f"Index analysis failed: {e}"}
    
    async def check_table_statistics(self) -> Dict[str, Any]:
        """
        Analyze table statistics and performance metrics.
        
        Returns:
            Dictionary with table statistics results
        """
        if not self.db_pool:
            if not self._create_connection_pool():
                return {"error": "Failed to connect to database"}
        
        try:
            tables = []
            
            with self.db_pool.getconn() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    
                    # Get table statistics
                    cur.execute("""
                        SELECT 
                            schemaname,
                            tablename,
                            pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as total_size,
                            pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) as table_size,
                            pg_size_pretty(pg_indexes_size(schemaname||'.'||tablename)) as index_size,
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
                        ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
                    """)
                    
                    table_rows = cur.fetchall()
                    
                    for row in table_rows:
                        table_info = {
                            "table_name": f"{row['schemaname']}.{row['tablename']}",
                            "total_size": row['total_size'],
                            "table_size": row['table_size'],
                            "index_size": row['index_size'],
                            "seq_scan": row['seq_scan'],
                            "seq_tup_read": row['seq_tup_read'],
                            "idx_scan": row['idx_scan'],
                            "idx_tup_fetch": row['idx_tup_fetch'],
                            "n_tup_ins": row['n_tup_ins'],
                            "n_tup_upd": row['n_tup_upd'],
                            "n_tup_del": row['n_tup_del'],
                            "n_live_tup": row['n_live_tup'],
                            "n_dead_tup": row['n_dead_tup'],
                            "last_vacuum": row['last_vacuum'],
                            "last_autovacuum": row['last_autovacuum'],
                            "last_analyze": row['last_analyze'],
                            "last_autoanalyze": row['last_autoanalyze'],
                            "health_status": self._assess_table_health(row)
                        }
                        tables.append(table_info)
                    
                    # Check for tables needing maintenance
                    maintenance_needed = []
                    for table in tables:
                        if table['n_dead_tup'] > table['n_live_tup'] * 0.1:  # More than 10% dead tuples
                            maintenance_needed.append({
                                "table_name": table['table_name'],
                                "issue": f"High dead tuple ratio ({table['n_dead_tup']} dead tuples)",
                                "recommendation": "VACUUM this table"
                            })
                        
                        if table['seq_scan'] > table['idx_scan'] * 10:  # Heavy sequential scanning
                            maintenance_needed.append({
                                "table_name": table['table_name'],
                                "issue": f"High sequential scanning ({table['seq_scan']} seq scans vs {table['idx_scan']} idx scans)",
                                "recommendation": "Consider adding indexes"
                            })
            
            return {
                "tables": tables,
                "maintenance_needed": maintenance_needed,
                "total_tables": len(tables),
                "tables_needing_maintenance": len(maintenance_needed),
                "analysis_timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {"error": f"Table statistics analysis failed: {e}"}
    
    async def analyze_query_performance(self) -> Dict[str, Any]:
        """
        Analyze query performance and identify optimization opportunities.
        
        Returns:
            Dictionary with query performance analysis results
        """
        if not self.db_pool:
            if not self._create_connection_pool():
                return {"error": "Failed to connect to database"}
        
        try:
            slow_queries = []
            recommendations = []
            
            with self.db_pool.getconn() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    
                    # Get slow queries
                    cur.execute("""
                        SELECT 
                            query,
                            calls,
                            total_time,
                            mean_time,
                            rows,
                            shared_blks_hit,
                            shared_blks_read,
                            shared_blks_dirtied,
                            shared_blks_written,
                            local_blks_hit,
                            local_blks_read,
                            local_blks_dirtied,
                            local_blks_written,
                            temp_blks_read,
                            temp_blks_written,
                            blk_read_time,
                            blk_write_time
                        FROM pg_stat_statements
                        ORDER BY mean_time DESC
                        LIMIT 20
                    """)
                    
                    query_rows = cur.fetchall()
                    
                    for row in query_rows:
                        query_info = QueryPerformance(
                            query_text=row['query'][:200] + "..." if len(row['query']) > 200 else row['query'],
                            execution_time=row['mean_time'] / 1000.0,  # Convert to seconds
                            rows_affected=row['rows'],
                            index_used="unknown",
                            cost=row['total_time'] / row['calls'] if row['calls'] > 0 else 0,
                            rows=row['rows'],
                            planning_time=0.0
                        )
                        slow_queries.append(query_info)
                        
                        # Generate recommendations for slow queries
                        if query_info.execution_time > 1.0:  # Queries taking more than 1 second
                            recommendations.append({
                                "type": "slow_query",
                                "query_preview": query_info.query_text,
                                "execution_time": f"{query_info.execution_time:.2f}s",
                                "calls": row['calls'],
                                "recommendation": "Consider adding indexes or rewriting query"
                            })
                        
                        # Check for cache misses
                        if row['shared_blks_read'] > row['shared_blks_hit']:
                            recommendations.append({
                                "type": "cache_miss",
                                "query_preview": query_info.query_text,
                                "issue": "High cache miss ratio",
                                "recommendation": "Consider increasing shared_buffers or optimizing query"
                            })
                    
                    # Get query execution plans for slow queries
                    if self.enable_execution_plans and slow_queries:
                        cur.execute("SELECT query FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 5")
                        plan_queries = cur.fetchall()
                        
                        execution_plans = []
                        for query_row in plan_queries:
                            try:
                                cur.execute(f"EXPLAIN (ANALYZE, BUFFERS) {query_row['query']}")
                                plan_result = cur.fetchall()
                                execution_plans.append({
                                    "query": query_row['query'][:100] + "...",
                                    "plan": [str(row) for row in plan_result]
                                })
                            except Exception as e:
                                self.logger.warning(f"Failed to get execution plan: {e}")
                        
                        return {
                            "slow_queries": [
                                {
                                    "query": q.query_text,
                                    "execution_time": q.execution_time,
                                    "rows_affected": q.rows_affected,
                                    "status": "needs_optimization" if q.execution_time > 1.0 else "acceptable"
                                }
                                for q in slow_queries
                            ],
                            "recommendations": recommendations,
                            "execution_plans": execution_plans,
                            "total_slow_queries": len(slow_queries),
                            "recommendation_count": len(recommendations),
                            "analysis_timestamp": datetime.now().isoformat()
                        }
            
            return {
                "slow_queries": [
                    {
                        "query": q.query_text,
                        "execution_time": q.execution_time,
                        "rows_affected": q.rows_affected,
                        "status": "needs_optimization" if q.execution_time > 1.0 else "acceptable"
                    }
                    for q in slow_queries
                ],
                "recommendations": recommendations,
                "total_slow_queries": len(slow_queries),
                "recommendation_count": len(recommendations),
                "analysis_timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {"error": f"Query performance analysis failed: {e}"}
    
    async def optimize_database(self) -> Dict[str, Any]:
        """
        Provide comprehensive database optimization recommendations.
        
        Returns:
            Dictionary with optimization recommendations
        """
        try:
            # Run all optimization checks
            health_result = await self.check_database_health()
            index_result = await self.check_indexes()
            table_result = await self.check_table_statistics()
            query_result = await self.analyze_query_performance()
            
            # Combine all results
            optimization_results = {
                "database_health": health_result,
                "index_analysis": index_result,
                "table_statistics": table_result,
                "query_performance": query_result,
                "optimization_plan": self._generate_optimization_plan(
                    health_result, index_result, table_result, query_result
                ),
                "estimated_impact": self._estimate_optimization_impact(
                    health_result, index_result, table_result, query_result
                ),
                "optimization_timestamp": datetime.now().isoformat()
            }
            
            return optimization_results
            
        except Exception as e:
            return {"error": f"Database optimization failed: {e}"}
    
    def _calculate_health_score(self, health: DatabaseHealth) -> float:
        """Calculate overall database health score (0-100)"""
        score = 100.0
        
        # Deduct points for various issues
        if health.connection_status == "critical":
            score -= 40
        elif health.connection_status == "slow":
            score -= 20
        
        if health.blocked_queries > 0:
            score -= min(health.blocked_queries * 5, 30)
        
        if health.slow_queries > 10:
            score -= min(health.slow_queries, 20)
        
        if health.response_time > 5.0:
            score -= min(health.response_time * 5, 25)
        
        return max(0.0, score)
    
    def _generate_health_recommendations(self, health: DatabaseHealth) -> List[Dict[str, Any]]:
        """Generate health-based recommendations"""
        recommendations = []
        
        if health.connection_status == "slow":
            recommendations.append({
                "type": "performance",
                "priority": "high",
                "action": "Optimize database configuration",
                "description": "Database response time is slow"
            })
        
        if health.blocked_queries > 0:
            recommendations.append({
                "type": "blocking",
                "priority": "critical",
                "action": "Investigate blocked queries",
                "description": f"Found {health.blocked_queries} blocked queries"
            })
        
        if health.slow_queries > 10:
            recommendations.append({
                "type": "query_optimization",
                "priority": "medium",
                "action": "Optimize slow queries",
                "description": f"Found {health.slow_queries} slow queries"
            })
        
        return recommendations
    
    def _assess_table_health(self, table_stats: Dict[str, Any]) -> str:
        """Assess individual table health"""
        dead_ratio = table_stats['n_dead_tup'] / max(table_stats['n_live_tup'], 1)
        
        if dead_ratio > 0.2:  # More than 20% dead tuples
            return "critical"
        elif dead_ratio > 0.1:  # More than 10% dead tuples
            return "warning"
        elif table_stats['seq_scan'] > table_stats['idx_scan'] * 20:
            return "needs_indexes"
        else:
            return "healthy"
    
    def _generate_optimization_plan(self, health_result: Dict, index_result: Dict, 
                                  table_result: Dict, query_result: Dict) -> Dict[str, Any]:
        """Generate comprehensive optimization plan"""
        plan = {
            "immediate_actions": [],
            "short_term_actions": [],
            "long_term_actions": [],
            "estimated_impact": {}
        }
        
        # Analyze health issues
        if 'database_health' in health_result:
            db_health = health_result['database_health']
            if db_health.get('connection_status') == 'critical':
                plan['immediate_actions'].append("Investigate critical connection issues")
            
            if db_health.get('blocked_queries', 0) > 0:
                plan['immediate_actions'].append(f"Resolve {db_health['blocked_queries']} blocked queries")
        
        # Analyze index issues
        if 'recommendations' in index_result:
            for rec in index_result['recommendations']:
                if rec['type'] == 'inefficient_index':
                    plan['short_term_actions'].append(f"Rebuild or drop inefficient index: {rec['index_name']}")
                elif rec['type'] == 'missing_index':
                    plan['short_term_actions'].append(f"Create missing index on {rec['column']}")
        
        # Analyze table issues
        if 'maintenance_needed' in table_result:
            for maintenance in table_result['maintenance_needed']:
                if 'VACUUM' in maintenance['recommendation']:
                    plan['immediate_actions'].append(maintenance['recommendation'])
                else:
                    plan['short_term_actions'].append(maintenance['recommendation'])
        
        # Analyze query issues
        if 'recommendations' in query_result:
            for rec in query_result['recommendations']:
                if rec['type'] == 'slow_query':
                    plan['short_term_actions'].append(f"Optimize slow query: {rec['query_preview']}")
        
        return plan
    
    def _estimate_optimization_impact(self, health_result: Dict, index_result: Dict,
                                    table_result: Dict, query_result: Dict) -> Dict[str, Any]:
        """Estimate potential impact of optimizations"""
        impact = {
            "performance_improvement": "unknown",
            "query_speed_improvement": "unknown",
            "storage_savings": "unknown",
            "maintenance_reduction": "unknown"
        }
        
        # Estimate based on issues found
        total_issues = (
            health_result.get('database_health', {}).get('blocked_queries', 0) +
            len(index_result.get('recommendations', [])) +
            len(table_result.get('maintenance_needed', [])) +
            len(query_result.get('recommendations', []))
        )
        
        if total_issues > 20:
            impact['performance_improvement'] = "30-50%"
            impact['query_speed_improvement'] = "40-60%"
        elif total_issues > 10:
            impact['performance_improvement'] = "15-30%"
            impact['query_speed_improvement'] = "20-40%"
        else:
            impact['performance_improvement'] = "5-15%"
            impact['query_speed_improvement'] = "10-25%"
        
        return impact


# OpenAI-compatible function definitions
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "check_database_health",
            "description": "Perform comprehensive database health check",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_indexes",
            "description": "Analyze database indexes and provide optimization recommendations",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_table_statistics",
            "description": "Analyze table statistics and performance metrics",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_query_performance",
            "description": "Analyze query performance and identify optimization opportunities",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "optimize_database",
            "description": "Provide comprehensive database optimization recommendations",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    }
]


# Agent metadata
AGENT_INFO = {
    "name": "Database Troubleshooter",
    "description": "Specialized agent for PostgreSQL database troubleshooting, performance analysis, and optimization",
    "version": "1.0.0",
    "capabilities": [
        "Database health monitoring",
        "Query performance analysis",
        "Index optimization recommendations",
        "Connection pool management",
        "Dead tuple detection",
        "Slow query identification"
    ],
    "tools": TOOLS
}


if __name__ == "__main__":
    # Example usage
    troubleshooter = DatabaseTroubleshooter()
    
    async def main():
        # Check database health
        health_result = await troubleshooter.check_database_health()
        print("Database Health:", json.dumps(health_result, indent=2))
        
        # Check indexes
        index_result = await troubleshooter.check_indexes()
        print("Index Analysis:", json.dumps(index_result, indent=2))
        
        # Check table statistics
        table_result = await troubleshooter.check_table_statistics()
        print("Table Statistics:", json.dumps(table_result, indent=2))
        
        # Analyze query performance
        query_result = await troubleshooter.analyze_query_performance()
        print("Query Performance:", json.dumps(query_result, indent=2))
        
        # Optimize database
        optimization_result = await troubleshooter.optimize_database()
        print("Database Optimization:", json.dumps(optimization_result, indent=2))
    
    asyncio.run(main())
