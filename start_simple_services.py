#!/usr/bin/env python3
"""
Simple startup script for Podcast AI services.
This script starts all simplified services for local testing.
"""

import os
import sys
import subprocess
import time
import signal
import threading
from pathlib import Path

class SimpleServiceManager:
    """Manages simplified service processes."""
    
    def __init__(self):
        self.processes = {}
        self.service_configs = {
            "news-feed": {
                "port": 8001,
                "script": "services/news-feed/main_simple.py"
            },
            "text-generation": {
                "port": 8002,
                "script": "services/text-generation/main_simple.py"
            },
            "writer": {
                "port": 8003,
                "script": "services/writer/main_simple.py"
            },
            "presenter": {
                "port": 8004,
                "script": "services/presenter/main_simple.py"
            },
            "publishing": {
                "port": 8005,
                "script": "services/publishing/main_simple.py"
            },
            "podcast-host": {
                "port": 8006,
                "script": "services/podcast-host/main_simple.py"
            },
            "api-gateway": {
                "port": 8000,
                "script": "services/api-gateway/main_simple.py"
            }
        }
    
    def install_dependencies(self):
        """Install required Python dependencies."""
        print("📦 Installing dependencies...")
        
        dependencies = [
            "fastapi==0.104.1",
            "uvicorn==0.24.0", 
            "sqlalchemy==2.0.23",
            "pydantic==2.5.0",
            "httpx==0.25.2",
            "python-dotenv==1.0.0",
            "python-multipart==0.0.6",
            "jinja2==3.1.2"
        ]
        
        for dep in dependencies:
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
        script_path = Path(config["script"])
        
        if not script_path.exists():
            print(f"❌ Service script not found: {script_path}")
            return False
        
        print(f"🚀 Starting {service_name} on port {config['port']}...")
        
        try:
            # Start the service
            process = subprocess.Popen([
                sys.executable, str(script_path)
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            self.processes[service_name] = process
            
            # Give it a moment to start
            time.sleep(3)
            
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
        print("🚀 Starting all simplified services...")
        
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
                time.sleep(2)  # Brief pause between services
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
        print("🎙️ Podcast AI Simplified Services")
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
                print("\n🌐 Service URLs:")
                for service_name, config in self.service_configs.items():
                    print(f"  {service_name}: http://localhost:{config['port']}")
                
                print("\n📋 Test the system:")
                print("  python3 test_system.py")
                
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
    manager = SimpleServiceManager()
    
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
            print("Usage: python start_simple_services.py [start|stop|restart]")
            return False
    else:
        return manager.run_interactive()


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
