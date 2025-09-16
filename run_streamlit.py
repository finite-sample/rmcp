#!/usr/bin/env python3
"""
Launch script for RMCP Streamlit app
"""

import subprocess
import sys
import os

def main():
    """Launch the Streamlit app"""
    app_path = os.path.join(os.path.dirname(__file__), "streamlit_app.py")
    
    try:
        # Launch Streamlit
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", app_path,
            "--server.headless", "false",
            "--server.port", "8501"
        ], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error launching Streamlit: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nShutting down Streamlit app...")
        sys.exit(0)

if __name__ == "__main__":
    main()