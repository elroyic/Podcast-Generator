"""Setup dual Ollama instances with appropriate models."""
import subprocess
import time

def run_command(cmd, description):
    """Run a command and print status."""
    print(f"\n🔧 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"   ✅ {description} completed")
            return True
        else:
            print(f"   ❌ {description} failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"   ❌ {description} error: {e}")
        return False

def main():
    print("="*70)
    print("🎯 DUAL OLLAMA SETUP - GPU + CPU OPTIMIZATION")
    print("="*70)
    print()
    print("Resource Allocation:")
    print("  📊 GPU Ollama (RTX 3070Ti):")
    print("     - Writer: Qwen3 (intensive script generation)")
    print("     - Port: 11434")
    print()
    print("  💻 CPU Ollama (16 cores):")
    print("     - Reviewer: Qwen2-0.5b & Qwen2-1.5b (categorization)")
    print("     - Editor: Qwen2-1.5b (script review)")
    print("     - Port: 11435")
    print()
    print("="*70)
    
    # Step 1: Start ollama-cpu
    print("\n📦 STEP 1: Starting CPU Ollama instance...")
    run_command("docker compose up -d ollama-cpu", "Start ollama-cpu")
    time.sleep(10)
    
    # Step 2: Pull CPU models
    print("\n📦 STEP 2: Pulling lightweight models for CPU...")
    run_command(
        "docker exec podcastgenerator-ollama-cpu-1 ollama pull qwen2:0.5b",
        "Pull Qwen2-0.5b for CPU"
    )
    run_command(
        "docker exec podcastgenerator-ollama-cpu-1 ollama pull qwen2:1.5b",
        "Pull Qwen2-1.5b for CPU"
    )
    
    # Step 3: Verify GPU models
    print("\n📦 STEP 3: Verifying GPU Ollama models...")
    run_command("docker compose restart ollama", "Restart GPU Ollama")
    time.sleep(10)
    run_command(
        "docker exec podcastgenerator-ollama-1 ollama list",
        "List GPU models"
    )
    
    # Step 4: Restart affected services
    print("\n🔄 STEP 4: Restarting services with new configuration...")
    services = [
        "light-reviewer",
        "heavy-reviewer", 
        "reviewer",
        "editor",
        "writer"
    ]
    for service in services:
        run_command(f"docker compose restart {service}", f"Restart {service}")
    
    print("\n" + "="*70)
    print("✅ DUAL OLLAMA SETUP COMPLETE!")
    print("="*70)
    print()
    print("Summary:")
    print("  🎮 GPU Ollama: Handling intensive Writer tasks (Qwen3)")
    print("  💻 CPU Ollama: Handling lighter Review/Edit tasks (Qwen2)")
    print()
    print("This should:")
    print("  ✅ Prevent GPU memory crashes")
    print("  ✅ Allow parallel CPU + GPU processing")
    print("  ✅ Speed up overall workflow")
    print()
    print("Test with: python test_full_podcast_generation.py")
    print("="*70)

if __name__ == "__main__":
    main()

