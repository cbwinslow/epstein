#!/usr/bin/env python3
"""
Multi-Agent System Usage Example
Demonstrates how to use the Epstein Multi-Agent Analysis System for comprehensive
vector database analysis, troubleshooting, and document processing.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any

# Import the multi-agent orchestrator
from agents.multi_agent_orchestrator import MultiAgentOrchestrator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def example_comprehensive_analysis():
    """
    Example: Comprehensive vector database analysis across all agents
    """
    logger.info("=== Comprehensive Analysis Example ===")
    
    # Initialize the orchestrator
    orchestrator = MultiAgentOrchestrator()
    
    try:
        # Coordinate comprehensive analysis
        result = await orchestrator.coordinate_comprehensive_analysis(
            collection_name="epstein_documents",
            query_text="Jeffrey Epstein financial transactions"
        )
        
        logger.info(f"Analysis completed with status: {result['status']}")
        
        if result['status'] == 'completed':
            analysis_result = result['result']
            
            # Print summary
            print("\n" + "="*50)
            print("COMPREHENSIVE ANALYSIS RESULTS")
            print("="*50)
            
            print(f"Collection: {analysis_result['collection_name']}")
            print(f"Analysis Time: {analysis_result['analysis_timestamp']}")
            print(f"Overall Status: {analysis_result['summary']['overall_status']}")
            
            # Print key findings
            print("\nKey Findings:")
            for finding in analysis_result['summary']['key_findings']:
                print(f"  • {finding}")
            
            # Print component results
            print("\nComponent Results:")
            for component_name, component_result in analysis_result['components'].items():
                print(f"\n  {component_name.upper()}:")
                if 'error' in component_result:
                    print(f"    Error: {component_result['error']}")
                else:
                    print(f"    Status: Success")
                    if component_name == 'vector_analysis' and 'collections' in component_result:
                        print(f"    Collections analyzed: {len(component_result['collections'])}")
                    elif component_name == 'performance_benchmark':
                        print(f"    Query time: {component_result['performance']['execution_time_ms']:.2f}ms")
                        print(f"    Results: {component_result['performance']['results_count']}")
        
        else:
            logger.error(f"Analysis failed: {result['error']}")
            
    except Exception as e:
        logger.error(f"Comprehensive analysis example failed: {e}")


async def example_database_troubleshooting():
    """
    Example: Database troubleshooting across relevant agents
    """
    logger.info("=== Database Troubleshooting Example ===")
    
    orchestrator = MultiAgentOrchestrator()
    
    try:
        # Coordinate database troubleshooting
        result = await orchestrator.coordinate_database_troubleshooting()
        
        logger.info(f"Database troubleshooting completed with status: {result['status']}")
        
        if result['status'] == 'completed':
            troubleshooting_result = result['result']
            
            print("\n" + "="*50)
            print("DATABASE TROUBLESHOOTING RESULTS")
            print("="*50)
            
            print(f"Troubleshooting Time: {troubleshooting_result['troubleshooting_timestamp']}")
            
            # Print recommendations
            if 'recommendations' in troubleshooting_result:
                print("\nRecommendations:")
                for i, rec in enumerate(troubleshooting_result['recommendations'], 1):
                    print(f"  {i}. {rec['type'].upper()}: {rec['action']}")
                    print(f"     Priority: {rec['priority'].upper()}")
                    print(f"     Description: {rec['description']}")
            
            # Print component results
            print("\nComponent Analysis:")
            for component_name, component_result in troubleshooting_result['components'].items():
                print(f"\n  {component_name.upper()}:")
                if 'error' in component_result:
                    print(f"    Error: {component_result['error']}")
                else:
                    print(f"    Status: Success")
                    if component_name == 'health_check' and 'database_health' in component_result:
                        db_health = component_result['database_health']
                        print(f"    Connection Status: {db_health.get('connection_status', 'unknown')}")
                        print(f"    Active Connections: {db_health.get('active_connections', 0)}")
        
        else:
            logger.error(f"Database troubleshooting failed: {result['error']}")
            
    except Exception as e:
        logger.error(f"Database troubleshooting example failed: {e}")


async def example_pipeline_optimization():
    """
    Example: Pipeline optimization across monitoring and analysis agents
    """
    logger.info("=== Pipeline Optimization Example ===")
    
    orchestrator = MultiAgentOrchestrator()
    
    try:
        # Coordinate pipeline optimization
        result = await orchestrator.coordinate_pipeline_optimization()
        
        logger.info(f"Pipeline optimization completed with status: {result['status']}")
        
        if result['status'] == 'completed':
            optimization_result = result['result']
            
            print("\n" + "="*50)
            print("PIPELINE OPTIMIZATION RESULTS")
            print("="*50)
            
            print(f"Optimization Time: {optimization_result['optimization_timestamp']}")
            
            # Print optimization plan
            if 'optimization_plan' in optimization_result:
                plan = optimization_result['optimization_plan']
                
                print("\nOptimization Plan:")
                if plan['immediate_actions']:
                    print("  Immediate Actions:")
                    for action in plan['immediate_actions']:
                        print(f"    • {action}")
                
                if plan['short_term_actions']:
                    print("  Short-term Actions:")
                    for action in plan['short_term_actions']:
                        print(f"    • {action}")
                
                if plan['long_term_actions']:
                    print("  Long-term Actions:")
                    for action in plan['long_term_actions']:
                        print(f"    • {action}")
                
                if plan['estimated_impact']:
                    print("\nEstimated Impact:")
                    for impact_type, impact_value in plan['estimated_impact'].items():
                        print(f"    {impact_type}: {impact_value}")
            
            # Print component results
            print("\nComponent Analysis:")
            for component_name, component_result in optimization_result['components'].items():
                print(f"\n  {component_name.upper()}:")
                if 'error' in component_result:
                    print(f"    Error: {component_result['error']}")
                else:
                    print(f"    Status: Success")
                    if component_name == 'health_monitoring':
                        print(f"    Health Score: {component_result.get('health_score', 'N/A')}")
                    elif component_name == 'performance_trends':
                        print(f"    Throughput Trend: {component_result.get('throughput_trend', 'N/A')}")
        
        else:
            logger.error(f"Pipeline optimization failed: {result['error']}")
            
    except Exception as e:
        logger.error(f"Pipeline optimization example failed: {e}")


async def example_document_analysis():
    """
    Example: Document analysis across relevant agents
    """
    logger.info("=== Document Analysis Example ===")
    
    orchestrator = MultiAgentOrchestrator()
    
    # Note: This would require an actual document file
    document_path = "/path/to/sample_document.pdf"
    
    try:
        # Coordinate document analysis
        result = await orchestrator.coordinate_document_analysis(document_path)
        
        logger.info(f"Document analysis completed with status: {result['status']}")
        
        if result['status'] == 'completed':
            document_result = result['result']
            
            print("\n" + "="*50)
            print("DOCUMENT ANALYSIS RESULTS")
            print("="*50)
            
            print(f"Document: {document_result['document_path']}")
            print(f"Analysis Time: {document_result['analysis_timestamp']}")
            
            # Print document summary
            if 'summary' in document_result:
                summary = document_result['summary']
                print(f"\nDocument Summary:")
                print(f"  Type: {summary['document_type']}")
                print(f"  Complexity: {summary['complexity']}")
                print(f"  Key Entities: {', '.join(summary['key_entities']) if summary['key_entities'] else 'None'}")
                print(f"  Sentiment: {summary['sentiment']}")
                print(f"  Quality Score: {summary['quality_score']:.2f}")
            
            # Print component results
            print("\nComponent Analysis:")
            for component_name, component_result in document_result['components'].items():
                print(f"\n  {component_name.upper()}:")
                if 'error' in component_result:
                    print(f"    Error: {component_result['error']}")
                else:
                    print(f"    Status: Success")
                    if component_name == 'document_processing' and 'results' in component_result:
                        processing = component_result['results']
                        print(f"    Entities Found: {len(processing.get('entities', []))}")
                        print(f"    Text Length: {len(processing.get('extracted_text', ''))}")
        
        else:
            logger.error(f"Document analysis failed: {result['error']}")
            
    except Exception as e:
        logger.error(f"Document analysis example failed: {e}")


async def example_system_status():
    """
    Example: Get overall system status across all agents
    """
    logger.info("=== System Status Example ===")
    
    orchestrator = MultiAgentOrchestrator()
    
    try:
        # Get system status
        status = await orchestrator.get_system_status()
        
        print("\n" + "="*50)
        print("SYSTEM STATUS")
        print("="*50)
        
        print(f"Timestamp: {status['timestamp']}")
        print(f"Queue Size: {status['queue_size']}")
        
        # Print task statistics
        tasks = status['tasks']
        print(f"\nTask Statistics:")
        print(f"  Total Tasks: {tasks['total']}")
        print(f"  Pending: {tasks['pending']}")
        print(f"  Running: {tasks['running']}")
        print(f"  Completed: {tasks['completed']}")
        print(f"  Failed: {tasks['failed']}")
        
        # Print agent status
        print(f"\nAgent Status:")
        for agent_name, agent_status in status['agents'].items():
            status_icon = "✅" if agent_status.get('status') == 'active' else "❌"
            print(f"  {status_icon} {agent_name}: {agent_status.get('status', 'unknown')}")
            if 'last_check' in agent_status:
                print(f"     Last Check: {agent_status['last_check']}")
            if 'error' in agent_status:
                print(f"     Error: {agent_status['error']}")
        
    except Exception as e:
        logger.error(f"System status example failed: {e}")


async def example_custom_workflow():
    """
    Example: Custom multi-agent workflow for specific use case
    """
    logger.info("=== Custom Workflow Example ===")
    
    orchestrator = MultiAgentOrchestrator()
    
    try:
        # Custom workflow: Analyze vector database health and optimize
        print("\n" + "="*50)
        print("CUSTOM WORKFLOW: Vector Database Health Check & Optimization")
        print("="*50)
        
        # Step 1: Get vector database analysis
        logger.info("Step 1: Analyzing vector database...")
        vector_result = await orchestrator.agents['vector_db_analyzer'].analyze_all_collections()
        
        if 'error' not in vector_result:
            print(f"✅ Vector database analysis completed")
            print(f"   Collections: {vector_result.get('total_collections', 0)}")
            print(f"   Total Vectors: {vector_result.get('total_vectors', 0)}")
        else:
            print(f"❌ Vector database analysis failed: {vector_result['error']}")
            return
        
        # Step 2: Get database health status
        logger.info("Step 2: Checking database health...")
        db_result = await orchestrator.agents['db_troubleshooter'].check_database_health()
        
        if 'error' not in db_result:
            print(f"✅ Database health check completed")
            db_health = db_result.get('database_health', {})
            print(f"   Connection Status: {db_health.get('connection_status', 'unknown')}")
            print(f"   Active Connections: {db_health.get('active_connections', 0)}")
        else:
            print(f"❌ Database health check failed: {db_result['error']}")
        
        # Step 3: Get pipeline monitoring
        logger.info("Step 3: Monitoring pipeline health...")
        pipeline_result = await orchestrator.agents['pipeline_monitor'].monitor_pipeline_health()
        
        if 'error' not in pipeline_result:
            print(f"✅ Pipeline monitoring completed")
            print(f"   Health Score: {pipeline_result.get('health_score', 'N/A')}")
            print(f"   Active Tasks: {pipeline_result.get('active_tasks', 0)}")
        else:
            print(f"❌ Pipeline monitoring failed: {pipeline_result['error']}")
        
        # Step 4: Generate comprehensive report
        logger.info("Step 4: Generating comprehensive report...")
        
        report = {
            "workflow_type": "vector_database_health_check",
            "timestamp": datetime.now().isoformat(),
            "components": {
                "vector_analysis": vector_result,
                "database_health": db_result,
                "pipeline_monitoring": pipeline_result
            },
            "summary": {
                "overall_health": "healthy",
                "recommendations": [],
                "action_items": []
            }
        }
        
        # Analyze results and generate recommendations
        if 'error' not in vector_result and vector_result.get('total_collections', 0) == 0:
            report['summary']['overall_health'] = "warning"
            report['summary']['recommendations'].append("No collections found in vector database")
        
        if 'error' not in db_result:
            db_health = db_result.get('database_health', {})
            if db_health.get('connection_status') == 'slow':
                report['summary']['overall_health'] = "needs_attention"
                report['summary']['action_items'].append("Optimize database configuration")
        
        print(f"\n📋 Comprehensive Report:")
        print(f"   Overall Health: {report['summary']['overall_health'].upper()}")
        print(f"   Recommendations: {len(report['summary']['recommendations'])}")
        print(f"   Action Items: {len(report['summary']['action_items'])}")
        
        # Save report to file
        report_filename = f"health_check_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_filename, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n📄 Report saved to: {report_filename}")
        
    except Exception as e:
        logger.error(f"Custom workflow example failed: {e}")


async def main():
    """
    Main function to run all examples
    """
    print("🚀 Epstein Multi-Agent Analysis System - Usage Examples")
    print("=" * 60)
    
    # Run all examples
    await example_system_status()
    await example_comprehensive_analysis()
    await example_database_troubleshooting()
    await example_pipeline_optimization()
    await example_custom_workflow()
    
    # Note: Document analysis requires actual document files
    # await example_document_analysis()
    
    print("\n" + "=" * 60)
    print("✅ All examples completed!")
    print("Check the logs for detailed information about each example.")


if __name__ == "__main__":
    # Run the examples
    asyncio.run(main())
