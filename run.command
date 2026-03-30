#!/bin/bash
# ──────────────────────────────────────────
#  사주 분석 — 로컬 서버 원클릭 실행
#  더블클릭하면 FastAPI 서버가 실행되고 브라우저가 열립니다.
# ──────────────────────────────────────────

set -e

# 스크립트가 있는 디렉토리로 이동 (더블클릭 시 경로 문제 방지)
ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

echo ""
echo "🔮 사주 분석 서버를 시작합니다..."
echo ""

# ── 종료 처리 ──
cleanup() {
    echo ""
    echo "🛑 서버를 종료합니다..."
    kill $BACKEND_PID 2>/dev/null
    wait $BACKEND_PID 2>/dev/null
    echo "✅ 종료 완료."
}
trap cleanup EXIT INT TERM

# ── Python 확인 ──
if ! command -v python3 &>/dev/null; then
    echo "❌ python3이 설치되어 있지 않습니다."
    echo "   https://www.python.org/downloads/ 에서 설치해주세요."
    echo ""
    read -p "아무 키나 누르면 종료합니다..."
    exit 1
fi

# ── 기존 프로세스 정리 (포트 8000) ──
if lsof -ti:8000 &>/dev/null; then
    echo "⚠️  포트 8000이 사용 중입니다. 기존 프로세스를 종료합니다..."
    lsof -ti:8000 | xargs kill -9 2>/dev/null || true
    sleep 1
fi

# ── 백엔드 설정 ──
echo "⚙️  서버 설정 중..."
cd "$ROOT_DIR/backend"

if [ ! -d "venv" ]; then
    echo "   📦 가상환경 생성 중..."
    python3 -m venv venv
fi

source venv/bin/activate
pip install -q -r requirements.txt 2>/dev/null

echo "   ✅ 준비 완료"
echo ""

# ── 서버 시작 ──
echo "🚀 서버 시작 중 (http://localhost:8000) ..."
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# 서버가 뜰 때까지 대기
sleep 2

# macOS: 자동으로 브라우저 열기
if command -v open &>/dev/null; then
    open "http://localhost:8000"
fi

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║        🔮 사주 분석 서버 실행 중         ║"
echo "╠══════════════════════════════════════════╣"
echo "║                                          ║"
echo "║  웹 페이지:   http://localhost:8000       ║"
echo "║  API 문서:    http://localhost:8000/docs  ║"
echo "║                                          ║"
echo "║  종료: Ctrl+C 또는 터미널 창 닫기        ║"
echo "╚══════════════════════════════════════════╝"
echo ""

wait
