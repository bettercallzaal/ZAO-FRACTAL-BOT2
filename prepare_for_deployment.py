#!/usr/bin/env python3
"""
Prepare Fractal Bot for deployment to Bot-Hosting.net
This script creates a deployment-ready zip file with all necessary files.
"""

import os
import zipfile
import shutil
import sys

def create_deployment_package():
    """Create a deployment package for Bot-Hosting.net"""
    print("Preparing Fractal Bot for deployment to Bot-Hosting.net...")
    
    # Files to include in the deployment package
    essential_files = [
        "main.py",
        "zao_commands.py",
        "zao_addresses.py",
        "requirements.txt",
    ]
    
    # Directories to include (if they exist)
    essential_dirs = [
        "utils",
        "cogs",
    ]
    
    # Create a temporary directory for deployment files
    if os.path.exists("deploy_temp"):
        shutil.rmtree("deploy_temp")
    os.makedirs("deploy_temp")
    
    # Copy essential files
    for file in essential_files:
        if os.path.exists(file):
            shutil.copy(file, os.path.join("deploy_temp", file))
            print(f"Added {file}")
        else:
            print(f"Warning: {file} not found, skipping")
    
    # Copy essential directories
    for directory in essential_dirs:
        if os.path.exists(directory):
            shutil.copytree(directory, os.path.join("deploy_temp", directory))
            print(f"Added directory {directory}")
        else:
            print(f"Note: {directory} not found, skipping")
    
    # Create a deployment zip file
    with zipfile.ZipFile("fractalbot_deployment.zip", "w") as zipf:
        for root, _, files in os.walk("deploy_temp"):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, "deploy_temp")
                zipf.write(file_path, arcname)
    
    # Clean up
    shutil.rmtree("deploy_temp")
    
    print("\nDeployment package created: fractalbot_deployment.zip")
    print("Upload this file to Bot-Hosting.net")
    print("\nRemember to set these environment variables:")
    print("- DISCORD_TOKEN: Your Discord bot token")
    print("- ALCHEMY_API_KEY: Your Alchemy API key")

if __name__ == "__main__":
    create_deployment_package()
