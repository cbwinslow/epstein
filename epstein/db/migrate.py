#!/usr/bin/env python3
"""
Database migration management script for Epstein Document Analysis Pipeline.

Usage:
    python db/migrate.py up                    # Run pending migrations
    python db/migrate.py down                  # Rollback last migration
    python db/migrate.py status                # Show migration status
    python db/migrate.py create <description>   # Create new migration
"""

import argparse
import os
import re
import sys
from datetime import datetime
from pathlib import Path
import psycopg2
from psycopg2.extras import DictCursor


class MigrationManager:
    def __init__(self, db_url=None):
        self.db_url = db_url or os.getenv('DATABASE_URL')
        self.migrations_dir = Path(__file__).parent / 'migrations'
        
    def get_connection(self):
        """Get database connection"""
        if not self.db_url:
            raise ValueError("DATABASE_URL environment variable must be set")
        return psycopg2.connect(self.db_url, cursor_factory=DictCursor)
    
    def ensure_migration_table(self):
        """Ensure schema_migrations table exists"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS schema_migrations (
                        version VARCHAR(50) PRIMARY KEY,
                        description TEXT,
                        executed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                    )
                """)
                conn.commit()
    
    def get_applied_migrations(self):
        """Get list of applied migrations"""
        self.ensure_migration_table()
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT version FROM schema_migrations ORDER BY version")
                return {row['version'] for row in cur.fetchall()}
    
    def get_pending_migrations(self):
        """Get list of pending migrations"""
        applied = self.get_applied_migrations()
        all_migrations = sorted(self.migrations_dir.glob('*.sql'))
        return [m for m in all_migrations if m.stem not in applied]
    
    def run_migration(self, migration_file):
        """Run a single migration file"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                try:
                    # Read and execute migration file
                    sql = migration_file.read_text()
                    
                    # Remove the INSERT statement for schema_migrations if present
                    # (we'll handle it separately)
                    sql = re.sub(
                        r"INSERT INTO schema_migrations.*ON CONFLICT.*?;",
                        "",
                        sql,
                        flags=re.DOTALL
                    )
                    
                    cur.execute(sql)
                    
                    # Record migration
                    version = migration_file.stem
                    description = f"Applied migration {version}"
                    cur.execute("""
                        INSERT INTO schema_migrations (version, description, executed_at)
                        VALUES (%s, %s, NOW())
                        ON CONFLICT (version) DO NOTHING
                    """, (version, description))
                    
                    conn.commit()
                    print(f"✅ Applied migration: {migration_file.name}")
                    
                except Exception as e:
                    conn.rollback()
                    print(f"❌ Failed to apply migration {migration_file.name}: {e}")
                    raise
    
    def migrate_up(self):
        """Run all pending migrations"""
        pending = self.get_pending_migrations()
        if not pending:
            print("✅ No pending migrations")
            return
        
        print(f"📦 Found {len(pending)} pending migrations")
        for migration in pending:
            self.run_migration(migration)
        print("✅ All migrations applied successfully")
    
    def migrate_down(self):
        """Rollback last migration (not fully implemented)"""
        print("⚠️  Rollback not implemented yet")
        print("   Manual database restore required for rollback operations")
    
    def show_status(self):
        """Show migration status"""
        applied = self.get_applied_migrations()
        pending = self.get_pending_migrations()
        
        print("\n📊 Migration Status:")
        print(f"   Applied migrations: {len(applied)}")
        for version in sorted(applied):
            print(f"     ✅ {version}")
        
        print(f"   Pending migrations: {len(pending)}")
        for migration in pending:
            print(f"     ⏳ {migration.name}")
    
    def create_migration(self, description):
        """Create new migration file"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{description.lower().replace(' ', '_')}.sql"
        filepath = self.migrations_dir / filename
        
        template = f"""-- ============================================================================
-- File: db/migrations/{filename}
-- Date: {datetime.now().strftime('%Y-%m-%d')}
-- Purpose: {description.title()}
-- Description: {description}
-- ============================================================================

-- Add your migration SQL here

-- Record migration completion
INSERT INTO schema_migrations (version, description, executed_at) 
VALUES ('{timestamp}', '{description}', NOW())
ON CONFLICT (version) DO NOTHING;
"""
        
        filepath.write_text(template)
        print(f"✅ Created migration: {filename}")


def main():
    parser = argparse.ArgumentParser(description='Database migration manager')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Up command
    subparsers.add_parser('up', help='Run pending migrations')
    
    # Down command
    subparsers.add_parser('down', help='Rollback last migration')
    
    # Status command
    subparsers.add_parser('status', help='Show migration status')
    
    # Create command
    create_parser = subparsers.add_parser('create', help='Create new migration')
    create_parser.add_argument('description', help='Migration description')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    manager = MigrationManager()
    
    if args.command == 'up':
        manager.migrate_up()
    elif args.command == 'down':
        manager.migrate_down()
    elif args.command == 'status':
        manager.show_status()
    elif args.command == 'create':
        manager.create_migration(args.description)


if __name__ == '__main__':
    main()
