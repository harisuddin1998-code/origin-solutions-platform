"""
Agency CRM — Launcher
Opens each service in its own terminal window on Windows.
"""

import subprocess
import sys
import os

BACKEND_DIR = os.path.join(os.path.dirname(__file__), 'backend')
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), 'frontend')
STREAMLIT_APP = os.path.join(os.path.dirname(__file__), 'app.py')
PROJECT_DIR = os.path.dirname(__file__)


def get_venv_python():
    """Find the Python executable in the current virtual environment."""
    # Check common venv locations
    for venv_name in ['.venv', 'venv', 'env']:
        venv_dir = os.path.join(PROJECT_DIR, venv_name)
        if os.path.isdir(venv_dir):
            if sys.platform == 'win32':
                py_path = os.path.join(venv_dir, 'Scripts', 'python.exe')
            else:
                py_path = os.path.join(venv_dir, 'bin', 'python')
            if os.path.isfile(py_path):
                return py_path
    # Fallback to system python
    return sys.executable


def main():
    print()
    print("  ╔══════════════════════════════════════╗")
    print("  ║        Agency CRM  Launcher          ║")
    print("  ╚══════════════════════════════════════╝")
    print()

    venv_python = get_venv_python()

    if sys.platform == 'win32':
        # Backend
        print("  [1/3] Opening FastAPI backend...")
        subprocess.Popen(
            f'start "FastAPI Backend" cmd /k "{venv_python} -m uvicorn app.main:app --reload --port 8001"',
            cwd=BACKEND_DIR,
            shell=True,
        )

        # Frontend
        print("  [2/3] Opening React frontend...")
        subprocess.Popen(
            'start "React Frontend" cmd /k "npm run dev"',
            cwd=FRONTEND_DIR,
            shell=True,
        )

        # Streamlit
        print("  [3/3] Opening Streamlit app...")
        subprocess.Popen(
            f'start "Streamlit App" cmd /k "{venv_python} -m streamlit run app.py --server.port 8501"',
            shell=True,
        )
    else:
        subprocess.Popen([venv_python, '-m', 'uvicorn', 'app.main:app', '--reload', '--port', '8001'], cwd=BACKEND_DIR)
        subprocess.Popen(['npm', 'run', 'dev'], cwd=FRONTEND_DIR)
        subprocess.Popen([venv_python, '-m', 'streamlit', 'run', STREAMLIT_APP, '--server.port', '8501'])

    print()
    print("  ✅ All services launched!")
    print("  🌐 Frontend : http://localhost:3000")
    print("  🔧 Backend  : http://127.0.0.1:8001")
    print("  📊 Streamlit: http://localhost:8501")
    print()
    print("  Close each terminal window to stop that service.")
    print()


if __name__ == '__main__':
    main()