#!/usr/bin/env python3
"""
Local setup script for Podcast AI services without Docker.
This script sets up and runs services locally for testing.
"""

import os
import sys
import subprocess
import time
import signal
import threading
from pathlib import Path
from typing import Dict, List, Optional

class LocalServiceManager:
    """Manages local service processes."""
    
    def __init__(self):
        self.processes: Dict[str, subprocess.Popen] = {}
        self.service_configs = {
            "api-gateway": {
                "port": 8000,
                "path": "services/api-gateway",
                "env": {
                    "DATABASE_URL": "sqlite:///./podcast_ai.db",
                    "REDIS_URL": "redis://localhost:6379",
                    "PYTHONPATH": "/workspace"
                }
            },
            "news-feed": {
                "port": 8001,
                "path": "services/news-feed",
                "env": {
                    "DATABASE_URL": "sqlite:///./podcast_ai.db",
                    "PYTHONPATH": "/workspace"
                }
            },
            "text-generation": {
                "port": 8002,
                "path": "services/text-generation",
                "env": {
                    "DATABASE_URL": "sqlite:///./podcast_ai.db",
                    "OLLAMA_BASE_URL": "http://localhost:11434",
                    "PYTHONPATH": "/workspace"
                }
            },
            "writer": {
                "port": 8003,
                "path": "services/writer",
                "env": {
                    "DATABASE_URL": "sqlite:///./podcast_ai.db",
                    "OLLAMA_BASE_URL": "http://localhost:11434",
                    "PYTHONPATH": "/workspace"
                }
            },
            "presenter": {
                "port": 8004,
                "path": "services/presenter",
                "env": {
                    "DATABASE_URL": "sqlite:///./podcast_ai.db",
                    "PYTHONPATH": "/workspace"
                }
            },
            "publishing": {
                "port": 8005,
                "path": "services/publishing",
                "env": {
                    "DATABASE_URL": "sqlite:///./podcast_ai.db",
                    "LOCAL_STORAGE_PATH": "/tmp/podcast_storage",
                    "LOCAL_SERVER_URL": "http://localhost:8080",
                    "PYTHONPATH": "/workspace"
                }
            },
            "podcast-host": {
                "port": 8006,
                "path": "services/podcast-host",
                "env": {
                    "DATABASE_URL": "sqlite:///./podcast_ai.db",
                    "LOCAL_STORAGE_PATH": "/tmp/podcast_storage",
                    "LOCAL_SERVER_URL": "http://localhost:8080"
                }
            }
        }
    
    def install_dependencies(self):
        """Install required Python dependencies."""
        print("📦 Installing dependencies...")
        
        # Install common dependencies
        common_deps = [
            "fastapi==0.104.1",
            "uvicorn==0.24.0", 
            "sqlalchemy==2.0.23",
            "pydantic==2.5.0",
            "httpx==0.25.2",
            "requests==2.31.0",
            "python-dotenv==1.0.0",
            "python-multipart==0.0.6",
            "jinja2==3.1.2",
            "feedparser==6.0.10",
            "aiofiles==23.2.1"
        ]
        
        for dep in common_deps:
            try:
                subprocess.run([
                    sys.executable, "-m", "pip", "install", dep, "--break-system-packages"
                ], check=True, capture_output=True)
                print(f"✅ Installed {dep}")
            except subprocess.CalledProcessError as e:
                print(f"❌ Failed to install {dep}: {e}")
    
    def create_storage_directories(self):
        """Create necessary storage directories."""
        print("📁 Creating storage directories...")
        
        storage_paths = [
            "/tmp/podcast_storage",
            "/tmp/podcast_storage/episodes",
            "/tmp/podcast_storage/rss",
            "/tmp/podcast_storage/podcast"
        ]
        
        for path in storage_paths:
            Path(path).mkdir(parents=True, exist_ok=True)
            print(f"✅ Created {path}")
    
    def start_service(self, service_name: str) -> bool:
        """Start a single service."""
        if service_name not in self.service_configs:
            print(f"❌ Unknown service: {service_name}")
            return False
        
        config = self.service_configs[service_name]
        service_path = Path(config["path"])
        
        if not service_path.exists():
            print(f"❌ Service path not found: {service_path}")
            return False
        
        print(f"🚀 Starting {service_name} on port {config['port']}...")
        
        # Prepare environment
        env = os.environ.copy()
        env.update(config["env"])
        
        try:
            # Start the service
            process = subprocess.Popen([
                sys.executable, "main.py"
            ], cwd=service_path, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            self.processes[service_name] = process
            
            # Give it a moment to start
            time.sleep(2)
            
            # Check if it's still running
            if process.poll() is None:
                print(f"✅ {service_name} started successfully (PID: {process.pid})")
                return True
            else:
                stdout, stderr = process.communicate()
                print(f"❌ {service_name} failed to start")
                print(f"STDOUT: {stdout.decode()}")
                print(f"STDERR: {stderr.decode()}")
                return False
                
        except Exception as e:
            print(f"❌ Error starting {service_name}: {e}")
            return False
    
    def start_all_services(self) -> bool:
        """Start all services."""
        print("🚀 Starting all services...")
        
        # Install dependencies first
        self.install_dependencies()
        
        # Create storage directories
        self.create_storage_directories()
        
        # Start services in dependency order
        service_order = [
            "news-feed",
            "text-generation", 
            "writer",
            "presenter",
            "publishing",
            "podcast-host",
            "api-gateway"
        ]
        
        success_count = 0
        for service_name in service_order:
            if self.start_service(service_name):
                success_count += 1
                time.sleep(1)  # Brief pause between services
            else:
                print(f"⚠️ Failed to start {service_name}, continuing with other services...")
        
        print(f"\n📊 Started {success_count}/{len(service_order)} services")
        return success_count > 0
    
    def stop_all_services(self):
        """Stop all running services."""
        print("🛑 Stopping all services...")
        
        for service_name, process in self.processes.items():
            try:
                process.terminate()
                process.wait(timeout=5)
                print(f"✅ Stopped {service_name}")
            except subprocess.TimeoutExpired:
                process.kill()
                print(f"🔪 Force killed {service_name}")
            except Exception as e:
                print(f"❌ Error stopping {service_name}: {e}")
        
        self.processes.clear()
    
    def check_service_health(self, service_name: str) -> bool:
        """Check if a service is healthy."""
        if service_name not in self.service_configs:
            return False
        
        config = self.service_configs[service_name]
        port = config["port"]
        
        try:
            import httpx
            response = httpx.get(f"http://localhost:{port}/health", timeout=5.0)
            return response.status_code == 200
        except Exception:
            return False
    
    def monitor_services(self):
        """Monitor services and restart if needed."""
        print("👀 Monitoring services...")
        
        while True:
            for service_name, process in list(self.processes.items()):
                if process.poll() is not None:
                    print(f"⚠️ {service_name} stopped unexpectedly, restarting...")
                    self.processes.pop(service_name)
                    self.start_service(service_name)
            
            time.sleep(10)  # Check every 10 seconds
    
    def run_interactive(self):
        """Run in interactive mode."""
        print("🎙️ Podcast AI Local Development Environment")
        print("=" * 50)
        
        def signal_handler(sig, frame):
            print("\n🛑 Shutting down...")
            self.stop_all_services()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        try:
            if self.start_all_services():
                print("\n✅ All services started! Press Ctrl+C to stop.")
                
                # Start monitoring in background
                monitor_thread = threading.Thread(target=self.monitor_services, daemon=True)
                monitor_thread.start()
                
                # Keep main thread alive
                while True:
                    time.sleep(1)
            else:
                print("❌ Failed to start services")
                return False
                
        except KeyboardInterrupt:
            print("\n🛑 Shutting down...")
            self.stop_all_services()
            return True


def main():
    """Main function."""
    manager = LocalServiceManager()
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == "start":
            return manager.start_all_services()
        elif command == "stop":
            manager.stop_all_services()
            return True
        elif command == "restart":
            manager.stop_all_services()
            time.sleep(2)
            return manager.start_all_services()
        else:
            print(f"Unknown command: {command}")
            print("Usage: python local_setup.py [start|stop|restart]")
            return False
    else:
        return manager.run_interactive()


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)