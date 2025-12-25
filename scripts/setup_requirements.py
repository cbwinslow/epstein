#!/usr/bin/env python3
"""
Epstein Files Project - Automated Requirements and Setup Script

Automatically detects system requirements, installs dependencies,
and configures the environment for the Epstein Files project.

Usage:
    python scripts/setup_requirements.py [options]

Options:
    --check-only        Only check requirements, don't install
    --install-deps      Install Python dependencies
    --install-system    Install system dependencies
    --install-all       Install all dependencies (default)
    --verbose           Verbose output
    --force             Force installation even if requirements are met
"""

import argparse
import json
import os
import platform
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple, Optional


class SystemChecker:
    """Check system requirements and dependencies"""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.system_info = self._get_system_info()
        self.checks = []
    
    def _get_system_info(self) -> Dict:
        """Get system information"""
        return {
            "platform": platform.system(),
            "platform_version": platform.release(),
            "python_version": sys.version_info,
            "architecture": platform.architecture(),
            "processor": platform.processor()
        }
    
    def _log(self, message: str, level: str = "INFO"):
        """Log message if verbose mode is enabled"""
        if self.verbose:
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{timestamp}] {level}: {message}")
    
    def check_python_version(self) -> Tuple[bool, str]:
        """Check Python version"""
        required = (3, 9)
        current = self.system_info["python_version"]
        
        if current >= required:
            return True, f"Python {current.major}.{current.minor}.{current.micro} ✓"
        else:
            return False, f"Python {current.major}.{current.minor}.{current.micro} (requires {required[0]}.{required[1]}+) ✗"
    
    def check_docker(self) -> Tuple[bool, str]:
        """Check Docker installation"""
        try:
            result = subprocess.run(
                ["docker", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                version = result.stdout.strip()
                return True, f"Docker {version} ✓"
            else:
                return False, "Docker not found ✗"
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False, "Docker not found ✗"
    
    def check_postgresql(self) -> Tuple[bool, str]:
        """Check PostgreSQL installation"""
        try:
            result = subprocess.run(
                ["psql", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                version = result.stdout.strip()
                return True, f"PostgreSQL {version} ✓"
            else:
                return False, "PostgreSQL not found ✗"
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False, "PostgreSQL not found ✗"
    
    def check_tesseract(self) -> Tuple[bool, str]:
        """Check Tesseract OCR installation"""
        try:
            result = subprocess.run(
                ["tesseract", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                version = result.stdout.strip().split('\n')[0]
                return True, f"Tesseract {version} ✓"
            else:
                return False, "Tesseract OCR not found ✗"
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False, "Tesseract OCR not found ✗"
    
    def check_poppler(self) -> Tuple[bool, str]:
        """Check Poppler installation (for pdf2image)"""
        try:
            result = subprocess.run(
                ["pdftoppm", "-v"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                return True, "Poppler utilities ✓"
            else:
                return False, "Poppler utilities not found ✗"
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False, "Poppler utilities not found ✗"
    
    def check_memory(self) -> Tuple[bool, str]:
        """Check available memory"""
        try:
            if platform.system() == "Linux":
                with open('/proc/meminfo', 'r') as f:
                    meminfo = f.read()
                
                mem_total = int(meminfo.split('MemTotal:')[1].split()[0])
                mem_available = int(meminfo.split('MemAvailable:')[1].split()[0])
                
                # Convert to GB
                total_gb = mem_total / 1024 / 1024
                available_gb = mem_available / 1024 / 1024
                
                if available_gb >= 16:
                    return True, f"Memory: {available_gb:.1f}GB available ✓"
                else:
                    return False, f"Memory: {available_gb:.1f}GB available (requires 16GB+) ✗"
            
            elif platform.system() == "Darwin":  # macOS
                result = subprocess.run(
                    ["sysctl", "hw.memsize"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0:
                    mem_bytes = int(result.stdout.strip().split()[1])
                    mem_gb = mem_bytes / 1024 / 1024 / 1024
                    
                    if mem_gb >= 16:
                        return True, f"Memory: {mem_gb:.1f}GB ✓"
                    else:
                        return False, f"Memory: {mem_gb:.1f}GB (requires 16GB+) ✗"
            
            elif platform.system() == "Windows":
                result = subprocess.run(
                    ["wmic", "computersystem", "get", "TotalPhysicalMemory"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0:
                    mem_bytes = int(result.stdout.strip().split('\n')[1])
                    mem_gb = mem_bytes / 1024 / 1024 / 1024
                    
                    if mem_gb >= 16:
                        return True, f"Memory: {mem_gb:.1f}GB ✓"
                    else:
                        return False, f"Memory: {mem_gb:.1f}GB (requires 16GB+) ✗"
            
            return False, "Could not determine memory ✗"
        
        except Exception as e:
            return False, f"Memory check failed: {e} ✗"
    
    def check_disk_space(self) -> Tuple[bool, str]:
        """Check available disk space"""
        try:
            import shutil
            total, used, free = shutil.disk_usage("/")
            
            # Convert to GB
            free_gb = free // (1024**3)
            
            if free_gb >= 50:
                return True, f"Disk space: {free_gb}GB free ✓"
            else:
                return False, f"Disk space: {free_gb}GB free (requires 50GB+) ✗"
        
        except Exception as e:
            return False, f"Disk space check failed: {e} ✗"
    
    def run_all_checks(self) -> Dict[str, Tuple[bool, str]]:
        """Run all system checks"""
        checks = {
            "Python Version": self.check_python_version(),
            "Docker": self.check_docker(),
            "PostgreSQL": self.check_postgresql(),
            "Tesseract OCR": self.check_tesseract(),
            "Poppler": self.check_poppler(),
            "Memory": self.check_memory(),
            "Disk Space": self.check_disk_space()
        }
        
        self.checks = checks
        return checks
    
    def print_results(self):
        """Print check results"""
        print("\n" + "="*60)
        print("🔍 System Requirements Check")
        print("="*60)
        
        print(f"Platform: {self.system_info['platform']} {self.system_info['platform_version']}")
        print(f"Python: {self.system_info['python_version'].major}.{self.system_info['python_version'].minor}.{self.system_info['python_version'].micro}")
        print(f"Architecture: {self.system_info['architecture'][0]}")
        
        print("\n📋 Requirements Status:")
        print("-" * 40)
        
        passed = 0
        total = len(self.checks)
        
        for check_name, (status, message) in self.checks.items():
            status_icon = "✅" if status else "❌"
            print(f"{status_icon} {check_name}: {message}")
            if status:
                passed += 1
        
        print("-" * 40)
        print(f"Results: {passed}/{total} checks passed")
        
        if passed == total:
            print("🎉 All requirements met!")
        else:
            print(f"⚠️  {total - passed} requirements not met")
        
        return passed == total


class DependencyInstaller:
    """Install project dependencies"""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.system = platform.system()
    
    def _log(self, message: str):
        """Log message if verbose mode is enabled"""
        if self.verbose:
            print(f"[SETUP] {message}")
    
    def install_python_deps(self, force: bool = False) -> bool:
        """Install Python dependencies"""
        self._log("Installing Python dependencies...")
        
        try:
            # Install core dependencies
            core_deps = [
                "fastapi>=0.100.0",
                "uvicorn>=0.23.0",
                "asyncio>=3.4.3",
                "psycopg2-binary>=2.9.0",
                "sqlalchemy>=2.0.0",
                "spacy>=3.0.0",
                "torch>=1.9.0",
                "transformers>=4.0.0",
                "pytesseract>=0.3.10",
                "pdfplumber>=0.10.0",
                "pillow>=10.0.0",
                "beautifulsoup4>=4.12.0",
                "requests>=2.31.0",
                "aiohttp>=3.8.0",
                "pytest>=7.0.0",
                "pytest-asyncio>=0.20.0"
            ]
            
            # Install OpenTelemetry
            otel_deps = [
                "opentelemetry-api>=1.15.0",
                "opentelemetry-sdk>=1.15.0",
                "opentelemetry-instrumentation-fastapi>=0.36b0",
                "opentelemetry-instrumentation-requests>=0.36b0"
            ]
            
            # Install LangChain ecosystem
            langchain_deps = [
                "langchain>=0.0.300",
                "langchain-core>=0.1.0",
                "langsmith>=0.1.0",
                "langfuse>=0.0.70"
            ]
            
            # Install OpenRouter
            openrouter_deps = [
                "openrouter-sdk>=0.1.0"
            ]
            
            all_deps = core_deps + otel_deps + langchain_deps + openrouter_deps
            
            for dep in all_deps:
                self._log(f"Installing {dep}...")
                result = subprocess.run(
                    [sys.executable, "-m", "pip", "install", dep],
                    capture_output=True,
                    text=True
                )
                
                if result.returncode != 0:
                    print(f"❌ Failed to install {dep}")
                    print(f"Error: {result.stderr}")
                    return False
                else:
                    self._log(f"✅ Installed {dep}")
            
            # Download spaCy model
            self._log("Downloading spaCy model...")
            result = subprocess.run(
                [sys.executable, "-m", "spacy", "download", "en_core_web_lg"],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                print("⚠️  Warning: Failed to download spaCy model")
                print(f"Error: {result.stderr}")
            else:
                self._log("✅ Downloaded spaCy model")
            
            return True
        
        except Exception as e:
            print(f"❌ Python dependency installation failed: {e}")
            return False
    
    def install_system_deps(self) -> bool:
        """Install system dependencies"""
        self._log("Installing system dependencies...")
        
        try:
            if self.system == "Linux":
                return self._install_linux_deps()
            elif self.system == "Darwin":
                return self._install_macos_deps()
            elif self.system == "Windows":
                return self._install_windows_deps()
            else:
                print(f"❌ Unsupported platform: {self.system}")
                return False
        
        except Exception as e:
            print(f"❌ System dependency installation failed: {e}")
            return False
    
    def _install_linux_deps(self) -> bool:
        """Install Linux dependencies"""
        self._log("Installing Linux dependencies...")
        
        # Check for package manager
        package_managers = ["apt", "yum", "dnf", "pacman"]
        pkg_manager = None
        
        for pm in package_managers:
            if subprocess.run(["which", pm], capture_output=True).returncode == 0:
                pkg_manager = pm
                break
        
        if not pkg_manager:
            print("❌ No supported package manager found")
            return False
        
        self._log(f"Using package manager: {pkg_manager}")
        
        # Common dependencies
        deps = {
            "apt": [
                "tesseract-ocr",
                "tesseract-ocr-eng",
                "poppler-utils",
                "postgresql",
                "postgresql-contrib"
            ],
            "yum": [
                "tesseract",
                "tesseract-langpack-eng",
                "poppler-utils",
                "postgresql-server",
                "postgresql-contrib"
            ],
            "dnf": [
                "tesseract",
                "tesseract-langpack-eng",
                "poppler-utils",
                "postgresql-server",
                "postgresql-contrib"
            ],
            "pacman": [
                "tesseract",
                "tesseract-data-eng",
                "poppler",
                "postgresql"
            ]
        }
        
        if pkg_manager not in deps:
            print(f"❌ Package manager {pkg_manager} not supported")
            return False
        
        # Install dependencies
        for dep in deps[pkg_manager]:
            self._log(f"Installing {dep}...")
            result = subprocess.run(
                [pkg_manager, "install", "-y", dep],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                print(f"⚠️  Warning: Failed to install {dep}")
                print(f"Error: {result.stderr}")
            else:
                self._log(f"✅ Installed {dep}")
        
        return True
    
    def _install_macos_deps(self) -> bool:
        """Install macOS dependencies"""
        self._log("Installing macOS dependencies...")
        
        # Check for Homebrew
        if subprocess.run(["which", "brew"], capture_output=True).returncode != 0:
            print("❌ Homebrew not found. Please install Homebrew first.")
            return False
        
        # Install dependencies
        deps = ["tesseract", "poppler", "postgresql"]
        
        for dep in deps:
            self._log(f"Installing {dep}...")
            result = subprocess.run(
                ["brew", "install", dep],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                print(f"⚠️  Warning: Failed to install {dep}")
                print(f"Error: {result.stderr}")
            else:
                self._log(f"✅ Installed {dep}")
        
        return True
    
    def _install_windows_deps(self) -> bool:
        """Install Windows dependencies"""
        self._log("Installing Windows dependencies...")
        
        # Note: Windows installation is more complex and may require manual steps
        print("⚠️  Windows dependencies require manual installation:")
        print("1. Install Tesseract OCR from: https://github.com/tesseract-ocr/tesseract")
        print("2. Install Poppler from: https://github.com/oschwartz10612/poppler-windows")
        print("3. Install PostgreSQL from: https://www.postgresql.org/download/windows/")
        print("4. Add Tesseract to PATH: tessdata directory")
        
        return True
    
    def setup_virtual_environment(self) -> bool:
        """Setup Python virtual environment"""
        self._log("Setting up virtual environment...")
        
        try:
            venv_dir = Path(".venv")
            if venv_dir.exists():
                self._log("Virtual environment already exists")
                return True
            
            # Create virtual environment
            result = subprocess.run(
                [sys.executable, "-m", "venv", ".venv"],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                print(f"❌ Failed to create virtual environment")
                print(f"Error: {result.stderr}")
                return False
            
            self._log("✅ Created virtual environment")
            
            # Activate and install requirements
            if self.system == "Windows":
                activate_script = ".venv\\Scripts\\activate"
                pip_script = ".venv\\Scripts\\pip"
            else:
                activate_script = ".venv/bin/activate"
                pip_script = ".venv/bin/pip"
            
            # Install requirements in virtual environment
            result = subprocess.run(
                [pip_script, "install", "--upgrade", "pip"],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                print(f"❌ Failed to upgrade pip in virtual environment")
                return False
            
            self._log("✅ Virtual environment setup complete")
            return True
        
        except Exception as e:
            print(f"❌ Virtual environment setup failed: {e}")
            return False


class EnvironmentConfigurator:
    """Configure project environment"""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
    
    def _log(self, message: str):
        """Log message if verbose mode is enabled"""
        if self.verbose:
            print(f"[CONFIG] {message}")
    
    def create_env_file(self) -> bool:
        """Create .env file with default configuration"""
        self._log("Creating .env configuration file...")
        
        env_content = """# Epstein Files Project Configuration

# Database Configuration
DATABASE_URL=postgresql://epstein_user:epstein_password@localhost:5432/epstein_db
POSTGRES_DB=epstein_db
POSTGRES_USER=epstein_user
POSTGRES_PASSWORD=epstein_password

# Vector Database Configuration
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=your_qdrant_api_key

# OpenTelemetry Configuration
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
OTEL_SERVICE_NAME=epstein_files
OTEL_SERVICE_VERSION=1.0.0

# LangSmith Configuration
LANGCHAIN_TRACING_V2=true
LANGCHAIN_ENDPOINT=https://api.smith.langchain.com
LANGCHAIN_API_KEY=your_langsmith_api_key
LANGCHAIN_PROJECT=epstein_files

# LangFuse Configuration
LANGFUSE_SECRET_KEY=your_langfuse_secret_key
LANGFUSE_PUBLIC_KEY=your_langfuse_public_key
LANGFUSE_HOST=https://cloud.langfuse.com

# OpenRouter Configuration
OPENROUTER_API_KEY=your_openrouter_api_key
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1

# Processing Configuration
MAX_CONCURRENT_DOWNLOADS=5
MAX_WORKERS=4
BATCH_SIZE=10
OCR_ENABLED=true
NER_ENABLED=true

# Storage Configuration
DOWNLOAD_DIR=./downloads
PROCESSED_DIR=./processed
FAILED_DIR=./failed
TEMP_DIR=./temp

# Monitoring Configuration
ENABLE_METRICS=true
ENABLE_TRACING=true
METRICS_PORT=8000
HEALTH_CHECK_PORT=8001

# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_FILE=epstein_files.log
"""
        
        try:
            with open(".env", "w") as f:
                f.write(env_content)
            
            self._log("✅ Created .env configuration file")
            return True
        
        except Exception as e:
            print(f"❌ Failed to create .env file: {e}")
            return False
    
    def create_docker_compose(self) -> bool:
        """Create docker-compose.yml for development"""
        self._log("Creating docker-compose.yml...")
        
        docker_compose_content = """version: '3.8'

services:
  # PostgreSQL Database
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: epstein_db
      POSTGRES_USER: epstein_user
      POSTGRES_PASSWORD: epstein_password
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init-db.sql:/docker-entrypoint-initdb.d/init-db.sql
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U epstein_user -d epstein_db"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Qdrant Vector Database
  qdrant:
    image: qdrant/qdrant:latest
    environment:
      QDRANT__SERVICE__API_KEY: qdrant_api_key
    volumes:
      - qdrant_data:/qdrant/storage
    ports:
      - "6333:6333"
    healthcheck:
      test: ["CMD", "wget", "--no-verbose", "--tries=1", "--spider", "http://localhost:6333/"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Redis for Caching
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3

  # LangSmith (Optional)
  langsmith:
    image: langsmith/langsmith:latest
    environment:
      LANGSMITH_API_KEY: ${LANGCHAIN_API_KEY}
      LANGSMITH_PROJECT: ${LANGCHAIN_PROJECT}
    ports:
      - "8000:8000"
    depends_on:
      - postgres

  # Application
  epstein_files:
    build: .
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - QDRANT_URL=${QDRANT_URL}
      - OTEL_EXPORTER_OTLP_ENDPOINT=${OTEL_EXPORTER_OTLP_ENDPOINT}
      - LANGCHAIN_TRACING_V2=${LANGCHAIN_TRACING_V2}
      - OPENROUTER_API_KEY=${OPENROUTER_API_KEY}
    volumes:
      - ./downloads:/app/downloads
      - ./processed:/app/processed
      - ./failed:/app/failed
    ports:
      - "8000:8000"
      - "8765:8765"
    depends_on:
      postgres:
        condition: service_healthy
      qdrant:
        condition: service_healthy
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Monitoring Stack (Optional)
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
      - '--storage.tsdb.retention.time=200h'
      - '--web.enable-lifecycle'

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana_data:/var/lib/grafana
      - ./monitoring/grafana/dashboards:/etc/grafana/provisioning/dashboards
      - ./monitoring/grafana/datasources:/etc/grafana/provisioning/datasources

volumes:
  postgres_data:
  qdrant_data:
  redis_data:
  prometheus_data:
  grafana_data:
"""
        
        try:
            with open("docker-compose.yml", "w") as f:
                f.write(docker_compose_content)
            
            self._log("✅ Created docker-compose.yml")
            return True
        
        except Exception as e:
            print(f"❌ Failed to create docker-compose.yml: {e}")
            return False
    
    def create_monitoring_config(self) -> bool:
        """Create monitoring configuration files"""
        self._log("Creating monitoring configuration...")
        
        # Prometheus configuration
        prometheus_config = """global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'epstein_files'
    static_configs:
      - targets: ['epstein_files:8000']
    metrics_path: '/metrics'
    scrape_interval: 5s

  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres:5432']
    metrics_path: '/postgres'
    scrape_interval: 30s

  - job_name: 'qdrant'
    static_configs:
      - targets: ['qdrant:6333']
    metrics_path: '/metrics'
    scrape_interval: 30s

  - job_name: 'redis'
    static_configs:
      - targets: ['redis:6379']
    metrics_path: '/metrics'
    scrape_interval: 30s
"""
        
        # Grafana datasource
        grafana_datasource = """apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
"""
        
        # Grafana dashboard
        grafana_dashboard = """{
  "dashboard": {
    "id": null,
    "title": "Epstein Files Monitoring",
    "tags": ["epstein", "monitoring"],
    "timezone": "browser",
    "panels": [
      {
        "id": 1,
        "title": "System Overview",
        "type": "stat",
        "targets": [
          {
            "expr": "up",
            "legendFormat": "{{job}}"
          }
        ],
        "gridPos": {"h": 4, "w": 12, "x": 0, "y": 0}
      }
    ],
    "time": {
      "from": "now-1h",
      "to": "now"
    },
    "refresh": "5s"
  }
}"""
        
        try:
            # Create monitoring directory
            Path("monitoring").mkdir(exist_ok=True)
            Path("monitoring/grafana/dashboards").mkdir(parents=True, exist_ok=True)
            Path("monitoring/grafana/datasources").mkdir(parents=True, exist_ok=True)
            
            # Write configuration files
            with open("monitoring/prometheus.yml", "w") as f:
                f.write(prometheus_config)
            
            with open("monitoring/grafana/datasources/prometheus.yml", "w") as f:
                f.write(grafana_datasource)
            
            with open("monitoring/grafana/dashboards/epstein_files.json", "w") as f:
                f.write(grafana_dashboard)
            
            self._log("✅ Created monitoring configuration")
            return True
        
        except Exception as e:
            print(f"❌ Failed to create monitoring configuration: {e}")
            return False


def main():
    """Main setup function"""
    parser = argparse.ArgumentParser(
        description="Epstein Files Project - Automated Setup Script"
    )
    
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Only check requirements, don't install"
    )
    
    parser.add_argument(
        "--install-deps",
        action="store_true",
        help="Install Python dependencies"
    )
    
    parser.add_argument(
        "--install-system",
        action="store_true",
        help="Install system dependencies"
    )
    
    parser.add_argument(
        "--install-all",
        action="store_true",
        help="Install all dependencies (default)"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose output"
    )
    
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force installation even if requirements are met"
    )
    
    args = parser.parse_args()
    
    # Set default to install all if no specific option is given
    if not any([args.check_only, args.install_deps, args.install_system, args.install_all]):
        args.install_all = True
    
    print("🚀 Epstein Files Project - Automated Setup")
    print("="*60)
    
    # Step 1: Check system requirements
    print("\n🔍 Checking system requirements...")
    checker = SystemChecker(verbose=args.verbose)
    requirements_met = checker.run_all_checks()
    checker.print_results()
    
    if not requirements_met and not args.force:
        print("\n❌ System requirements not met. Please install missing dependencies.")
        print("Use --force to continue anyway.")
        return 1
    
    # Step 2: Install dependencies
    if args.check_only:
        print("\n✅ Check complete. Use --install-all to install dependencies.")
        return 0
    
    installer = DependencyInstaller(verbose=args.verbose)
    
    if args.install_system or args.install_all:
        print("\n📦 Installing system dependencies...")
        if not installer.install_system_deps():
            print("❌ System dependency installation failed")
            return 1
    
    if args.install_deps or args.install_all:
        print("\n🐍 Installing Python dependencies...")
        if not installer.install_python_deps(force=args.force):
            print("❌ Python dependency installation failed")
            return 1
        
        print("\n🐍 Setting up virtual environment...")
        if not installer.setup_virtual_environment():
            print("❌ Virtual environment setup failed")
            return 1
    
    # Step 3: Configure environment
    print("\n⚙️  Configuring environment...")
    configurator = EnvironmentConfigurator(verbose=args.verbose)
    
    if not configurator.create_env_file():
        print("❌ Environment configuration failed")
        return 1
    
    if not configurator.create_docker_compose():
        print("❌ Docker configuration failed")
        return 1
    
    if not configurator.create_monitoring_config():
        print("❌ Monitoring configuration failed")
        return 1
    
    # Step 4: Final instructions
    print("\n" + "="*60)
    print("🎉 Setup Complete!")
    print("="*60)
    
    print("\n📋 Next Steps:")
    print("1. Review and update .env file with your configuration")
    print("2. Start services: docker-compose up -d")
    print("3. Run tests: python tests/run_tests.py")
    print("4. Start development: python -m uvicorn epstein_files.main:app --reload")
    
    print("\n📚 Documentation:")
    print("- Project Overview: docs/README.md")
    print("- API Documentation: http://localhost:8000/docs")
    print("- Monitoring: http://localhost:3000 (Grafana)")
    
    print("\n🔧 Useful Commands:")
    print("- Check system status: python scripts/setup_requirements.py --check-only")
    print("- Run tests: python tests/run_tests.py --all --coverage")
    print("- Monitor system: docker-compose logs -f")
    
    return 0


if __name__ == "__main__":
    try:
        exit(main())
    except KeyboardInterrupt:
        print("\n🛑 Setup interrupted by user")
        exit(1)
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        exit(1)