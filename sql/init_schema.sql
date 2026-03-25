-- 사주 앱 Postgres 스키마 — 실서비스용
-- 8개 테이블: users, prompt_versions, saju_requests, saju_results,
--             llm_logs, payments, subscriptions, admin_audit_logs

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =========================================================
-- USERS
-- =========================================================
CREATE TABLE IF NOT EXISTS users (
    id          BIGSERIAL PRIMARY KEY,
    email       VARCHAR(255) UNIQUE,
    nickname    VARCHAR(100),
    hashed_pw   VARCHAR(255),
    provider    VARCHAR(30) DEFAULT 'email',  -- email, kakao, naver
    is_active   BOOLEAN NOT NULL DEFAULT TRUE,
    is_admin    BOOLEAN NOT NULL DEFAULT FALSE,
    created_at  TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMP NOT NULL DEFAULT NOW()
);

-- =========================================================
-- PROMPT VERSIONS — LLM 프롬프트 버전 관리
-- =========================================================
CREATE TABLE IF NOT EXISTS prompt_versions (
    id              BIGSERIAL PRIMARY KEY,
    version_code    VARCHAR(50) NOT NULL UNIQUE,
    category        VARCHAR(50) NOT NULL,         -- comprehensive, personality, career, study
    system_prompt   TEXT NOT NULL,
    user_prompt     TEXT NOT NULL,
    description     TEXT,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMP NOT NULL DEFAULT NOW()
);

-- =========================================================
-- SAJU REQUESTS — 입력 원본 저장
-- =========================================================
CREATE TABLE IF NOT EXISTS saju_requests (
    id              BIGSERIAL PRIMARY KEY,
    user_id         BIGINT REFERENCES users(id) ON DELETE SET NULL,
    input_name      VARCHAR(100),
    birth_date      DATE NOT NULL,
    birth_time      TIME,
    gender          VARCHAR(10) NOT NULL,
    calendar_type   VARCHAR(10) NOT NULL DEFAULT 'solar',
    is_leap_month   BOOLEAN DEFAULT FALSE,
    birthplace      VARCHAR(255),
    request_ip      VARCHAR(45),
    user_agent      TEXT,
    created_at      TIMESTAMP NOT NULL DEFAULT NOW()
);

-- =========================================================
-- SAJU RESULTS — 계산/해석 결과 분리 저장
-- =========================================================
CREATE TABLE IF NOT EXISTS saju_results (
    id                      BIGSERIAL PRIMARY KEY,
    request_id              BIGINT NOT NULL REFERENCES saju_requests(id) ON DELETE CASCADE,
    prompt_version_id       BIGINT REFERENCES prompt_versions(id) ON DELETE SET NULL,
    raw_calculation_json    JSONB NOT NULL,          -- 내부 엔진 계산 결과 원본
    interpretation_json     JSONB,                   -- 템플릿 해석 결과
    final_text              TEXT,                    -- Claude 자연어 해석
    result_status           VARCHAR(20) NOT NULL DEFAULT 'calculated',  -- calculated, interpreted, failed
    created_at              TIMESTAMP NOT NULL DEFAULT NOW()
);

-- =========================================================
-- LLM LOGS — Claude API 호출 추적
-- =========================================================
CREATE TABLE IF NOT EXISTS llm_logs (
    id                  BIGSERIAL PRIMARY KEY,
    result_id           BIGINT REFERENCES saju_results(id) ON DELETE SET NULL,
    provider            VARCHAR(30) NOT NULL DEFAULT 'anthropic',
    model_name          VARCHAR(100) NOT NULL,
    category            VARCHAR(50),
    input_tokens        INT,
    output_tokens       INT,
    request_payload     JSONB,
    response_payload    JSONB,
    latency_ms          INT,
    status_code         INT,
    error_message       TEXT,
    created_at          TIMESTAMP NOT NULL DEFAULT NOW()
);

-- =========================================================
-- PAYMENTS
-- =========================================================
CREATE TABLE IF NOT EXISTS payments (
    id              BIGSERIAL PRIMARY KEY,
    user_id         BIGINT REFERENCES users(id) ON DELETE SET NULL,
    amount          INT NOT NULL,
    currency        VARCHAR(10) DEFAULT 'KRW',
    payment_method  VARCHAR(50),
    payment_key     VARCHAR(255),
    status          VARCHAR(20) NOT NULL DEFAULT 'pending',
    created_at      TIMESTAMP NOT NULL DEFAULT NOW()
);

-- =========================================================
-- SUBSCRIPTIONS
-- =========================================================
CREATE TABLE IF NOT EXISTS subscriptions (
    id              BIGSERIAL PRIMARY KEY,
    user_id         BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    plan_code       VARCHAR(50) NOT NULL,
    starts_at       TIMESTAMP NOT NULL,
    expires_at      TIMESTAMP,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMP NOT NULL DEFAULT NOW()
);

-- =========================================================
-- ADMIN AUDIT LOGS
-- =========================================================
CREATE TABLE IF NOT EXISTS admin_audit_logs (
    id              BIGSERIAL PRIMARY KEY,
    admin_user_id   BIGINT REFERENCES users(id) ON DELETE SET NULL,
    action          VARCHAR(100) NOT NULL,
    target_table    VARCHAR(100),
    target_id       BIGINT,
    detail          JSONB,
    created_at      TIMESTAMP NOT NULL DEFAULT NOW()
);

-- =========================================================
-- INDEXES
-- =========================================================
CREATE INDEX IF NOT EXISTS idx_saju_requests_user    ON saju_requests(user_id);
CREATE INDEX IF NOT EXISTS idx_saju_requests_date    ON saju_requests(created_at);
CREATE INDEX IF NOT EXISTS idx_saju_results_request  ON saju_results(request_id);
CREATE INDEX IF NOT EXISTS idx_llm_logs_result       ON llm_logs(result_id);
CREATE INDEX IF NOT EXISTS idx_llm_logs_created      ON llm_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_payments_user         ON payments(user_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_user    ON subscriptions(user_id);
