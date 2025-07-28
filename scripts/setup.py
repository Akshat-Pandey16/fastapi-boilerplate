#!/usr/bin/env python3
"""
Setup script for FastAPI Boilerplate
This script helps you quickly set up the project with initial migrations.
"""

import subprocess
import sys
from pathlib import Path


def run_command(command: str, description: str) -> bool:
    print(f"🔄 {description}...")
    try:
        _ = subprocess.run(
            command, shell=True, check=True, capture_output=True, text=True
        )
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e}")
        print(f"Error output: {e.stderr}")
        return False


def check_prerequisites() -> bool:
    print("🔍 Checking prerequisites...")

    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ is required")
        return False

    if not Path(".env").exists():
        print(
            "⚠️  .env file not found. Please copy .env.example to .env and configure it."
        )
        return False

    print("✅ Prerequisites check passed")
    return True


def setup_database() -> bool:
    print("\n🗄️  Setting up database...")

    if not run_command(
        "alembic revision --autogenerate -m 'Initial migration'",
        "Creating initial migration",
    ):
        return False

    if not run_command("alembic upgrade head", "Applying migrations"):
        return False

    return True


def main() -> None:
    print("🚀 FastAPI Boilerplate Setup")
    print("=" * 40)

    if not check_prerequisites():
        print("\n❌ Setup failed. Please fix the issues above and try again.")
        sys.exit(1)

    if not setup_database():
        print("\n❌ Database setup failed. Please check the errors above.")
        sys.exit(1)

    print("\n✅ Setup completed successfully!")
    print("\n🎉 You can now start the application with:")
    print("   python main.py")
    print("\n📚 API documentation will be available at:")
    print("   http://localhost:8000/docs")


if __name__ == "__main__":
    main()
