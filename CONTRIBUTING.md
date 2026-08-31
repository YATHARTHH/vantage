# Contributing to Vantage ⚡

Thank you for your interest in contributing to **Vantage**! We welcome contributions from open-source developers, AI researchers, and platform engineers.

---

## 🚀 How to Get Started

### 1. Fork & Clone
```bash
git clone git@github-personal:YATHARTHH/vantage.git
cd vantage
```

### 2. Set Up Development Environment
```bash
# Python Virtual Environment
python -m venv .venv
.\.venv\Scripts\activate   # Windows (or source .venv/bin/activate on Linux/macOS)
pip install -e .
pip install pytz pytest pytest-asyncio uvicorn httpx

# Frontend Setup
cd frontend
npm install
```

### 3. Run Tests
Ensure all 29 tests pass locally before creating a pull request:
```bash
pytest tests/ -v
```

---

## 🛠️ Code Conventions

- **Python**: Follow PEP 8 guidelines. Type hints are mandatory.
- **FastAPI / Pydantic**: Use Pydantic v2 `BaseModel` for API requests and response schemas.
- **React Frontend**: Use TypeScript for all components and utilities.
- **Git Commit Messages**: Use Conventional Commits format (e.g., `feat: ...`, `fix: ...`, `docs: ...`).

---

## 📮 Submitting a Pull Request

1. Create a descriptive branch: `git checkout -b feat/your-feature-name`
2. Commit your changes: `git commit -m 'feat: added new anomaly detector rule'`
3. Push to your fork: `git push origin feat/your-feature-name`
4. Open a Pull Request on GitHub with detailed description of changes and test evidence.

Thank you for building the future of AI Observability with us! 🚀
