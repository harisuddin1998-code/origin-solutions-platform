# startup.sh
#!/bin/bash

echo "Starting Lead Generation Platform..."

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install backend dependencies
pip install -r backend/requirements.txt

# Install Playwright browsers
playwright install chromium

# Setup database
python -c "from backend.app.models.lead import db; db.engine.execute('CREATE TABLE IF NOT EXISTS leads (...)')"

# Start backend server
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &

# Start frontend
cd ../frontend
npm install
npm start

echo "Platform started! Access at http://localhost:3000"