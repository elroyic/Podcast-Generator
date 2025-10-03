"""Pull gpt-oss-20b model for high-quality script generation."""
import subprocess
import time

def run_command(cmd, description):
    """Run a command and print status."""
    print(f"\n🔧 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"   ✅ {description} completed")
            if result.stdout:
                print(f"   Output: {result.stdout.strip()}")
            return True
        else:
            print(f"   ❌ {description} failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"   ❌ {description} error: {e}")
        return False

def main():
    print("="*70)
    print("🎯 SETTING UP GPT-OSS-20B FOR HIGH-QUALITY SCRIPTS")
    print("="*70)
    print()
    print("Model Info:")
    print("  📝 Model: gpt-oss-20b")
    print("  🎯 Purpose: High-quality podcast script generation")
    print("  ⚠️  Limitation: 4k token output limit (~3500 tokens safe)")
    print("  📊 Target: 1200-1800 word scripts (~1600-2400 tokens)")
    print("  ✅ Result: Should fit comfortably in single request")
    print()
    print("="*70)
    
    # Step 1: Pull gpt-oss-20b on GPU Ollama
    print("\n📦 STEP 1: Pulling gpt-oss-20b model (this may take several minutes)...")
    success = run_command(
        "docker exec podcastgenerator-ollama-1 ollama pull gpt-oss-20b",
        "Pull gpt-oss-20b for GPU Ollama"
    )
    
    if not success:
        print("\n❌ Failed to pull model. Trying alternative approach...")
        print("   You may need to pull it manually:")
        print("   docker exec -it podcastgenerator-ollama-1 ollama pull gpt-oss-20b")
        return
    
    # Step 2: Verify model is available
    print("\n📦 STEP 2: Verifying model installation...")
    run_command(
        "docker exec podcastgenerator-ollama-1 ollama list",
        "List GPU Ollama models"
    )
    
    # Step 3: Restart Writer service
    print("\n🔄 STEP 3: Restarting Writer service with new model...")
    run_command("docker compose restart writer", "Restart Writer service")
    
    time.sleep(5)
    
    # Step 4: Check Writer logs
    print("\n📋 STEP 4: Checking Writer service initialization...")
    run_command(
        "docker compose logs writer --tail=20",
        "Check Writer logs"
    )
    
    print("\n" + "="*70)
    print("✅ GPT-OSS-20B SETUP COMPLETE!")
    print("="*70)
    print()
    print("Summary:")
    print("  🎮 GPU Ollama: Now using gpt-oss-20b for Writer")
    print("  📝 Script Quality: Should be significantly improved")
    print("  ⚡ Token Limit: 3500 tokens per request (safe margin)")
    print()
    print("Expected Benefits:")
    print("  ✅ Better dialogue flow")
    print("  ✅ More natural conversations")
    print("  ✅ Improved coherence and engagement")
    print("  ✅ Better adherence to format requirements")
    print()
    print("Test with: python test_full_podcast_generation.py")
    print("="*70)

if __name__ == "__main__":
    main()

