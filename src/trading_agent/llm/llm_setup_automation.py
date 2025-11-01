#!/usr/bin/env python3
"""
Automated LLM Integration Setup Script
Trading Agent v1.4 → v1.5 Upgrade Automation

This script automates the process of upgrading from MockLLMClient to real Anthropic API
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


class LLMIntegrationSetup:
    """Automated setup for LLM integration"""

    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.src_dir = self.project_root / "src" / "trading_agent"
        self.backup_dir = self.project_root / "backups" / "v1.4_backup"

        self.setup_log = []

    def log(self, message: str, level: str = "INFO"):
        """Log setup messages"""
        log_entry = f"[{level}] {message}"
        self.setup_log.append(log_entry)
        print(log_entry)

    def run_setup(self) -> bool:
        """Run complete LLM integration setup"""

        try:
            self.log("🚀 Starting LLM Integration Setup")

            # Step 1: Validate environment
            if not self._validate_environment():
                return False

            # Step 2: Create backups
            if not self._create_backups():
                return False

            # Step 3: Install dependencies
            if not self._install_dependencies():
                return False

            # Step 4: Copy new LLM client files
            if not self._copy_llm_files():
                return False

            # Step 5: Update imports and configurations
            if not self._update_imports():
                return False

            # Step 6: Create configuration files
            if not self._create_config_files():
                return False

            # Step 7: Run tests
            if not self._run_integration_tests():
                return False

            self.log("✅ LLM Integration Setup Complete!")
            self._print_next_steps()
            return True

        except Exception as e:
            self.log(f"❌ Setup failed: {str(e)}", "ERROR")
            return False

    def _validate_environment(self) -> bool:
        """Validate environment and requirements"""

        self.log("Validating environment...")

        # Check Python version

        # Check project structure
        if not self.src_dir.exists():
            self.log(f"❌ Source directory not found: {self.src_dir}", "ERROR")
            return False

        # Check for existing v1.4 files
        key_files = [
            "decision/engine.py",
            "inot_engine/orchestrator.py"
        ]

        for file_path in key_files:
            full_path = self.src_dir / file_path
            if not full_path.exists():
                self.log(f"⚠️ Key file not found: {full_path}")

        # Check for API key
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            self.log("⚠️ ANTHROPIC_API_KEY not set - you'll need to set it later")
        else:
            self.log("✅ API key found")

        self.log("✅ Environment validation passed")
        return True

    def _create_backups(self) -> bool:
        """Create backups of existing code"""

        self.log("Creating backups...")

        try:
            # Create backup directory
            self.backup_dir.mkdir(parents=True, exist_ok=True)

            # Backup key directories
            backup_dirs = ["decision", "inot_engine", "llm"]

            for dir_name in backup_dirs:
                src_path = self.src_dir / dir_name
                backup_path = self.backup_dir / dir_name

                if src_path.exists():
                    if backup_path.exists():
                        shutil.rmtree(backup_path)
                    shutil.copytree(src_path, backup_path)
                    self.log(f"✅ Backed up {dir_name}")
                else:
                    self.log(f"⚠️ Directory not found: {src_path}")

            return True

        except Exception as e:
            self.log(f"❌ Backup failed: {str(e)}", "ERROR")
            return False

    def _install_dependencies(self) -> bool:
        """Install required dependencies"""

        self.log("Installing dependencies...")

        try:
            # Install Anthropic package
            result = subprocess.run([
                sys.executable, "-m", "pip", "install", "anthropic"
            ], capture_output=True, text=True)

            if result.returncode == 0:
                self.log("✅ Anthropic package installed")
            else:
                self.log(f"❌ Failed to install anthropic: {result.stderr}", "ERROR")
                return False

            # Check other requirements
            try:
                import dataclasses
                import json
                import typing
                self.log("✅ Standard libraries available")
            except ImportError as e:
                self.log(f"❌ Missing standard library: {e}", "ERROR")
                return False

            return True

        except Exception as e:
            self.log(f"❌ Dependency installation failed: {str(e)}", "ERROR")
            return False

    def _copy_llm_files(self) -> bool:
        """Copy new LLM client files to project"""

        self.log("Copying LLM client files...")

        try:
            # Create LLM directory if it doesn't exist
            llm_dir = self.src_dir / "llm"
            llm_dir.mkdir(exist_ok=True)

            # Create __init__.py if it doesn't exist
            init_file = llm_dir / "__init__.py"
            if not init_file.exists():
                with open(init_file, "w") as f:
                    f.write('"""LLM integration module for Trading Agent"""\n')

            # Copy anthropic client (you'll need to copy the actual file)
            # This assumes the files are in the same directory as this script
            script_dir = Path(__file__).parent

            source_files = [
                ("anthropic_llm_client.py", "anthropic_client.py"),
                ("llm_integration_guide.py", "integration_guide.py")
            ]

            for source_name, target_name in source_files:
                source_path = script_dir / source_name
                target_path = llm_dir / target_name

                if source_path.exists():
                    shutil.copy2(source_path, target_path)
                    self.log(f"✅ Copied {source_name} → {target_name}")
                else:
                    self.log(f"⚠️ Source file not found: {source_path}")

            return True

        except Exception as e:
            self.log(f"❌ File copying failed: {str(e)}", "ERROR")
            return False

    def _update_imports(self) -> bool:
        """Update import statements in existing files"""

        self.log("Updating import statements...")

        try:
            # Files to update
            files_to_update = [
                self.src_dir / "decision" / "engine.py",
                self.src_dir / "inot_engine" / "orchestrator.py"
            ]

            for file_path in files_to_update:
                if file_path.exists():
                    self._update_file_imports(file_path)
                else:
                    self.log(f"⚠️ File not found for import update: {file_path}")

            return True

        except Exception as e:
            self.log(f"❌ Import update failed: {str(e)}", "ERROR")
            return False

    def _update_file_imports(self, file_path: Path):
        """Update imports in a specific file"""

        try:
            with open(file_path) as f:
                content = f.read()

            # Backup original
            backup_path = file_path.with_suffix(file_path.suffix + ".backup")
            with open(backup_path, "w") as f:
                f.write(content)

            # Add new import at the top (after existing imports)
            lines = content.split("\n")

            # Find where to insert the import
            insert_index = 0
            for i, line in enumerate(lines):
                if line.startswith("from ") or line.startswith("import "):
                    insert_index = i + 1

            # Insert new import
            new_import = "from trading_agent.llm.anthropic_client import AnthropicLLMClient"
            if new_import not in content:
                lines.insert(insert_index, new_import)

            # Write updated content
            with open(file_path, "w") as f:
                f.write("\n".join(lines))

            self.log(f"✅ Updated imports in {file_path.name}")

        except Exception as e:
            self.log(f"❌ Failed to update {file_path}: {str(e)}", "ERROR")

    def _create_config_files(self) -> bool:
        """Create configuration files"""

        self.log("Creating configuration files...")

        try:
            config_dir = self.project_root / "config"
            config_dir.mkdir(exist_ok=True)

            # Development config
            dev_config = {
                "llm": {
                    "provider": "anthropic",
                    "model": "claude-sonnet-4-20250514",
                    "max_tokens": 4000,
                    "temperature": 0.0,
                    "enable_real_llm": True,
                    "fallback_to_mock": True
                },
                "trading": {
                    "max_risk_per_trade": 0.02,
                    "confidence_threshold": 0.7,
                    "max_tools_per_decision": 5
                }
            }

            # Production config
            prod_config = dev_config.copy()
            prod_config["llm"]["fallback_to_mock"] = False
            prod_config["llm"]["temperature"] = 0.0

            # Save configs
            configs = [
                ("development.json", dev_config),
                ("production.json", prod_config)
            ]

            for filename, config in configs:
                config_path = config_dir / filename
                with open(config_path, "w") as f:
                    json.dump(config, f, indent=2)
                self.log(f"✅ Created {filename}")

            return True

        except Exception as e:
            self.log(f"❌ Config creation failed: {str(e)}", "ERROR")
            return False

    def _run_integration_tests(self) -> bool:
        """Run basic integration tests"""

        self.log("Running integration tests...")

        try:
            # Simple import test
            sys.path.insert(0, str(self.src_dir))

            try:
                from trading_agent.llm.anthropic_client import AnthropicLLMClient
                self.log("✅ AnthropicLLMClient import successful")
            except ImportError as e:
                self.log(f"⚠️ Import test failed: {e}")
                return False

            # API connectivity test (if API key available)
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if api_key:
                try:
                    client = AnthropicLLMClient(api_key=api_key)
                    response = client.complete("Hello Claude, please respond with just 'OK'")

                    if "ok" in response.content.lower():
                        self.log("✅ API connectivity test passed")
                    else:
                        self.log("⚠️ API test unclear response")

                except Exception as e:
                    self.log(f"⚠️ API test failed: {e}")
            else:
                self.log("⚠️ Skipping API test - no API key")

            return True

        except Exception as e:
            self.log(f"❌ Integration tests failed: {str(e)}", "ERROR")
            return False

    def _print_next_steps(self):
        """Print next steps for the user"""

        next_steps = f"""
🎯 LLM Integration Complete! Next Steps:

1. SET API KEY (if not already done):
   export ANTHROPIC_API_KEY="your_api_key_here"

2. UPDATE YOUR DECISION ENGINE:
   # Find this in your decision/engine.py:
   # OLD: client = MockLLMClient()
   # NEW: client = AnthropicLLMClient()

3. TEST THE INTEGRATION:
   cd {self.project_root}
   python -c "
   from src.trading_agent.llm.anthropic_client import AnthropicLLMClient
   client = AnthropicLLMClient()
   print('✅ Integration working!')
   "

4. RUN YOUR EXISTING TESTS:
   pytest src/trading_agent/tests/

5. MONITOR PERFORMANCE:
   - Check latency (should be ~1-3 seconds)
   - Monitor token usage
   - Validate decision quality

6. GRADUAL ROLLOUT:
   - Start with paper trading
   - Use small position sizes
   - Monitor for 24-48 hours
   - Scale up gradually

📁 FILES CREATED:
   - src/trading_agent/llm/anthropic_client.py
   - config/development.json
   - config/production.json
   - backups/v1.4_backup/ (your original code)

📋 LOGS SAVED TO: setup_log.txt
        """

        print(next_steps)

        # Save log to file
        log_file = self.project_root / "setup_log.txt"
        with open(log_file, "w") as f:
            f.write("\n".join(self.setup_log))

def main():
    """Main setup function"""

    print("🚀 Trading Agent LLM Integration Setup")
    print("=" * 50)

    # Get project root
    project_root = input("Enter project root directory (default: current): ").strip()
    if not project_root:
        project_root = "."

    # Confirm setup
    print(f"\nProject root: {os.path.abspath(project_root)}")
    confirm = input("Proceed with setup? (y/N): ").strip().lower()

    if confirm != 'y':
        print("Setup cancelled.")
        return

    # Run setup
    setup = LLMIntegrationSetup(project_root)
    success = setup.run_setup()

    if success:
        print("\n🎉 Setup completed successfully!")
        print("Your Trading Agent is now ready for real LLM integration.")
    else:
        print("\n❌ Setup failed. Check the logs for details.")
        print("You may need to complete some steps manually.")

if __name__ == "__main__":
    main()
