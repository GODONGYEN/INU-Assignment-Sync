import { useEffect, useMemo, useState } from "react";

const DEFAULT_SETTINGS = {
  BASE_URL: "https://cyber.inu.ac.kr",
  CALENDAR_NAME: "INU 과제",
  CALENDAR_MONTHS_BACK: "2",
  CALENDAR_MONTHS_FORWARD: "6",
  INCLUDE_PAST_ASSIGNMENTS: "false",
  REMINDER_MINUTES: "1440,180",
  DRY_RUN: "true",
};

const DEFAULT_SUMMARY = {
  collected: "-",
  created: "-",
  updated: "-",
  skipped: "-",
};

function parseSummaryFromLine(line, previous) {
  const next = { ...previous };
  const mapping = [
    ["collected", /\[INFO\] 수집된 과제 수: (\d+)/],
    ["created", /\[INFO\] 신규 등록 대상: (\d+)/],
    ["updated", /\[INFO\] 업데이트 대상: (\d+)/],
    ["skipped", /\[INFO\] 스킵: (\d+)/],
  ];

  for (const [key, pattern] of mapping) {
    const match = line.match(pattern);
    if (match) {
      next[key] = match[1];
    }
  }

  return next;
}

function buildInitialStatuses(settings) {
  return {
    lms: {
      label: "수동 로그인 필요",
      detail: settings.BASE_URL,
      tone: "warn",
    },
    calendar: {
      label: "대기 중",
      detail: settings.CALENDAR_NAME,
      tone: "idle",
    },
    dryRun: {
      label: settings.DRY_RUN === "true" ? "활성화" : "비활성화",
      detail: settings.DRY_RUN === "true" ? "테스트 모드" : "실제 Calendar 반영",
      tone: settings.DRY_RUN === "true" ? "warn" : "ok",
    },
  };
}

function normalizeSettings(settings) {
  return {
    BASE_URL: settings.BASE_URL ?? DEFAULT_SETTINGS.BASE_URL,
    CALENDAR_NAME: settings.CALENDAR_NAME ?? DEFAULT_SETTINGS.CALENDAR_NAME,
    CALENDAR_MONTHS_BACK: settings.CALENDAR_MONTHS_BACK ?? DEFAULT_SETTINGS.CALENDAR_MONTHS_BACK,
    CALENDAR_MONTHS_FORWARD: settings.CALENDAR_MONTHS_FORWARD ?? DEFAULT_SETTINGS.CALENDAR_MONTHS_FORWARD,
    INCLUDE_PAST_ASSIGNMENTS:
      settings.INCLUDE_PAST_ASSIGNMENTS ?? DEFAULT_SETTINGS.INCLUDE_PAST_ASSIGNMENTS,
    REMINDER_MINUTES: settings.REMINDER_MINUTES ?? DEFAULT_SETTINGS.REMINDER_MINUTES,
    DRY_RUN: settings.DRY_RUN ?? DEFAULT_SETTINGS.DRY_RUN,
  };
}

function toneClass(tone) {
  if (tone === "ok") {
    return "status-card status-card-ok";
  }
  if (tone === "warn") {
    return "status-card status-card-warn";
  }
  if (tone === "error") {
    return "status-card status-card-error";
  }
  return "status-card";
}

function toBoolString(value) {
  return value ? "true" : "false";
}

export default function App() {
  const api = window.electronAPI ?? window.inuSync ?? null;
  const [settings, setSettings] = useState(DEFAULT_SETTINGS);
  const [summary, setSummary] = useState(DEFAULT_SUMMARY);
  const [logs, setLogs] = useState("[renderer] Electron React UI Loaded\n");
  const [statusMessage, setStatusMessage] = useState("초기화 중...");
  const [statuses, setStatuses] = useState(buildInitialStatuses(DEFAULT_SETTINGS));
  const [appState, setAppState] = useState(null);
  const [isRunning, setIsRunning] = useState(false);
  const [apiMissing, setApiMissing] = useState(false);

  useEffect(() => {
    console.log("[renderer] App mounted");

    if (!api) {
      console.error("[renderer] preload API not found: window.electronAPI/window.inuSync is missing");
      setApiMissing(true);
      setStatusMessage("Electron preload API를 찾지 못했습니다. DevTools Console을 확인해 주세요.");
      setLogs((previous) => previous + "[ERROR] preload API missing\n");
      return undefined;
    }

    let disposeOutput = null;
    let disposeExit = null;

    async function bootstrap() {
      console.log("[renderer] bootstrap start");
      const payload = await api.getConfig();
      const nextSettings = normalizeSettings(payload.settings ?? {});

      setSettings(nextSettings);
      setStatuses(buildInitialStatuses(nextSettings));
      setAppState(payload.state ?? null);
      setStatusMessage("준비 완료");

      const existingLogs = await api.readLogFile();
      if (existingLogs) {
        setLogs((previous) => previous + existingLogs);
      }
    }

    bootstrap().catch((error) => {
      console.error("[renderer] bootstrap failed", error);
      setStatusMessage(`초기화 실패: ${error.message}`);
      setLogs((previous) => previous + `[ERROR] bootstrap failed: ${error.message}\n`);
    });

    try {
      disposeOutput = api.onSyncOutput((chunk) => {
        setLogs((previous) => previous + chunk);

        for (const line of chunk.split(/\r?\n/)) {
          if (!line.trim()) {
            continue;
          }

          setSummary((previous) => parseSummaryFromLine(line, previous));

          if (line.includes("로그인")) {
            setStatuses((previous) => ({
              ...previous,
              lms: {
                label: "로그인 진행 중",
                detail: "브라우저에서 직접 로그인해 주세요",
                tone: "warn",
              },
            }));
          }

          if (line.includes("[INFO] 수집된 과제 수:")) {
            setStatuses((previous) => ({
              ...previous,
              lms: {
                label: "과제 수집 완료",
                detail: "캘린더 이벤트를 읽었습니다",
                tone: "ok",
              },
            }));
          }

          if (line.includes("[OK] 등록 완료") || line.includes("[UPDATE] 수정 완료")) {
            setStatuses((previous) => ({
              ...previous,
              calendar: {
                label: "동기화 반영됨",
                detail: settings.CALENDAR_NAME,
                tone: "ok",
              },
            }));
          }

          if (line.includes("[SKIP]")) {
            setStatuses((previous) => ({
              ...previous,
              calendar: {
                label: "일부 항목 스킵",
                detail: settings.CALENDAR_NAME,
                tone: "warn",
              },
            }));
          }

          if (line.includes("[ERROR]")) {
            setStatuses((previous) => ({
              ...previous,
              calendar: {
                label: "오류 발생",
                detail: "로그를 확인해 주세요",
                tone: "error",
              },
            }));
          }
        }
      });

      disposeExit = api.onSyncExit(({ code, signal }) => {
        setIsRunning(false);
        setStatusMessage(code === 0 ? "동기화가 완료되었습니다." : `동기화 종료 코드: ${code ?? signal}`);
        api.getConfig().then((payload) => setAppState(payload.state ?? null)).catch(() => undefined);
      });
    } catch (error) {
      console.error("[renderer] event subscription failed", error);
      setLogs((previous) => previous + `[ERROR] event subscription failed: ${error.message}\n`);
    }

    return () => {
      if (typeof disposeOutput === "function") {
        disposeOutput();
      }
      if (typeof disposeExit === "function") {
        disposeExit();
      }
    };
  }, [api, settings.CALENDAR_NAME]);

  const cards = useMemo(
    () => [
      { title: "LMS 연결 상태", ...statuses.lms },
      { title: "Calendar 동기화 상태", ...statuses.calendar },
      { title: "DRY RUN 여부", ...statuses.dryRun },
    ],
    [statuses],
  );

  const logLines = useMemo(() => {
    return logs
      .split(/\r?\n/)
      .filter((line) => line.length > 0)
      .map((line, index) => ({
        id: `${index}-${line.slice(0, 24)}`,
        text: line,
        tone: line.includes("[ERROR]")
          ? "error"
          : line.includes("[UPDATE]")
            ? "update"
            : line.includes("[SKIP]")
              ? "skip"
              : line.includes("[OK]")
                ? "ok"
                : "default",
      }));
  }, [logs]);

  async function refreshAppState() {
    if (!api) {
      return;
    }
    const payload = await api.getConfig();
    setAppState(payload.state ?? null);
  }

  async function saveSettings() {
    if (!api) {
      setStatusMessage("Electron API가 없어 설정을 저장할 수 없습니다.");
      return false;
    }

    const updates = {
      BASE_URL: settings.BASE_URL.trim(),
      CALENDAR_NAME: settings.CALENDAR_NAME.trim(),
      CALENDAR_MONTHS_BACK: settings.CALENDAR_MONTHS_BACK.trim(),
      CALENDAR_MONTHS_FORWARD: settings.CALENDAR_MONTHS_FORWARD.trim(),
      INCLUDE_PAST_ASSIGNMENTS: settings.INCLUDE_PAST_ASSIGNMENTS,
      REMINDER_MINUTES: settings.REMINDER_MINUTES.trim(),
      DRY_RUN: settings.DRY_RUN,
    };

    if (!updates.CALENDAR_NAME) {
      setStatusMessage("Calendar 이름을 입력해 주세요.");
      return false;
    }

    if (!/^\d+$/.test(updates.CALENDAR_MONTHS_BACK) || !/^\d+$/.test(updates.CALENDAR_MONTHS_FORWARD)) {
      setStatusMessage("수집 개월 수는 숫자로 입력해 주세요.");
      return false;
    }

    const response = await api.saveConfig(updates);
    const nextSettings = normalizeSettings(response.settings ?? {});
    setSettings(nextSettings);
    setStatuses(buildInitialStatuses(nextSettings));
    setStatusMessage("설정을 저장했습니다.");
    await refreshAppState();
    return true;
  }

  async function runSync(forceDryRun) {
    if (!api) {
      setStatusMessage("Electron API가 없어 동기화를 실행할 수 없습니다.");
      return;
    }

    const saved = await saveSettings();
    if (!saved) {
      return;
    }

    setLogs((previous) => `${previous}\n[INFO] ${forceDryRun ? "DRY RUN" : "동기화"} 실행 요청\n`);
    setSummary(DEFAULT_SUMMARY);
    setIsRunning(true);
    setStatusMessage("Python 동기화 실행 중...");

    const response = await api.runSync({
      settings,
      forceDryRun,
    });

    if (!response.ok) {
      setIsRunning(false);
      setStatusMessage(response.error);
      setLogs((previous) => `${previous}[ERROR] ${response.error}\n`);
    }
  }

  async function resetSyncHistory() {
    if (!api) {
      return;
    }
    await api.resetSyncHistory();
    setStatusMessage("동기화 기록을 초기화했습니다.");
    setLogs((previous) => `${previous}[INFO] 동기화 기록 초기화 완료\n`);
    await refreshAppState();
  }

  async function clearLogs() {
    if (api) {
      await api.clearLogFile();
    }
    setLogs("[renderer] logs cleared\n");
    setStatusMessage("로그를 지웠습니다.");
  }

  async function openLogFile() {
    if (api) {
      await api.openLogFile();
    }
  }

  async function openReadme() {
    if (api) {
      await api.openReadme();
    }
  }

  return (
    <div className="app-shell">
      <div className="app-container">
        <header className="hero-card">
          <div>
            <p className="hero-kicker">INU LMS macOS Desktop</p>
            <h1>INU Assignment Sync</h1>
            <p className="hero-subtitle">Electron React UI Loaded</p>
            <p className="hero-description">
              Electron 창이 정상 렌더링되면 이 화면이 먼저 보여야 합니다. 이후 설정 저장, 로그 표시, Python 동기화
              실행 기능이 단계적으로 연결됩니다.
            </p>
          </div>
          <div className="hero-meta">
            <div>프로젝트 루트: {appState?.projectRoot ?? "-"}</div>
            <div>Python 실행기: {appState?.pythonExecutable ?? "-"}</div>
            <div>API 상태: {apiMissing ? "누락됨" : "정상 또는 확인 중"}</div>
          </div>
        </header>

        <section className="status-grid">
          {cards.map((card) => (
            <article className={toneClass(card.tone)} key={card.title}>
              <p className="status-title">{card.title}</p>
              <h2>{card.label}</h2>
              <p className="status-detail">{card.detail}</p>
            </article>
          ))}
        </section>

        {apiMissing ? (
          <section className="notice-banner notice-banner-error">
            <strong>Electron API 연결 실패</strong>
            <span>preload 스크립트 또는 contextBridge 노출 상태를 DevTools Console에서 확인해 주세요.</span>
          </section>
        ) : (
          <section className="notice-banner">
            <strong>앱 준비 상태</strong>
            <span>좌측에서 설정을 저장하고, 우측 로그 패널을 보면서 Python 동기화를 실행할 수 있습니다.</span>
          </section>
        )}

        <section className="dashboard-grid">
          <div className="sidebar-stack">
            <div className="panel">
              <div className="panel-header">
                <div>
                  <h2>설정</h2>
                  <p>기존 Python CLI를 그대로 사용하면서 Electron 대시보드에서 값을 관리합니다.</p>
                </div>
                <button className="soft-button" onClick={openReadme} type="button">
                  README 열기
                </button>
              </div>

              <div className="form-grid">
                <label className="field">
                  <span>BASE_URL</span>
                  <input disabled readOnly value={settings.BASE_URL} />
                </label>
                <label className="field">
                  <span>Calendar 이름</span>
                  <input
                    value={settings.CALENDAR_NAME}
                    onChange={(event) => setSettings((previous) => ({ ...previous, CALENDAR_NAME: event.target.value }))}
                  />
                </label>
                <label className="field">
                  <span>이전 수집 개월 수</span>
                  <input
                    value={settings.CALENDAR_MONTHS_BACK}
                    onChange={(event) =>
                      setSettings((previous) => ({ ...previous, CALENDAR_MONTHS_BACK: event.target.value }))
                    }
                  />
                </label>
                <label className="field">
                  <span>이후 수집 개월 수</span>
                  <input
                    value={settings.CALENDAR_MONTHS_FORWARD}
                    onChange={(event) =>
                      setSettings((previous) => ({ ...previous, CALENDAR_MONTHS_FORWARD: event.target.value }))
                    }
                  />
                </label>
                <label className="field field-full">
                  <span>알림 시간(분)</span>
                  <input
                    placeholder="1440,180"
                    value={settings.REMINDER_MINUTES}
                    onChange={(event) =>
                      setSettings((previous) => ({ ...previous, REMINDER_MINUTES: event.target.value }))
                    }
                  />
                </label>
              </div>

              <div className="toggle-row">
                <button
                  className={`toggle-chip ${settings.INCLUDE_PAST_ASSIGNMENTS === "true" ? "toggle-chip-on" : ""}`}
                  onClick={() =>
                    setSettings((previous) => ({
                      ...previous,
                      INCLUDE_PAST_ASSIGNMENTS: toBoolString(previous.INCLUDE_PAST_ASSIGNMENTS !== "true"),
                    }))
                  }
                  type="button"
                >
                  지난 과제 포함
                </button>

                <button
                  className={`toggle-chip ${settings.DRY_RUN === "true" ? "toggle-chip-on" : ""}`}
                  onClick={() =>
                    setSettings((previous) => ({
                      ...previous,
                      DRY_RUN: toBoolString(previous.DRY_RUN !== "true"),
                    }))
                  }
                  type="button"
                >
                  DRY_RUN
                </button>
              </div>

              <div className="button-row">
                <button className="primary-button" disabled={isRunning || !api} onClick={saveSettings} type="button">
                  설정 저장
                </button>
                <button className="primary-button" disabled={isRunning || !api} onClick={() => runSync(false)} type="button">
                  동기화 실행
                </button>
                <button className="soft-button" disabled={isRunning || !api} onClick={() => runSync(true)} type="button">
                  DRY RUN 실행
                </button>
                <button className="soft-button" disabled={!api} onClick={resetSyncHistory} type="button">
                  동기화 기록 초기화
                </button>
                <button className="soft-button" onClick={clearLogs} type="button">
                  로그 지우기
                </button>
                <button className="soft-button" disabled={!api} onClick={openLogFile} type="button">
                  logs/app.log 열기
                </button>
              </div>
            </div>

            <div className="panel">
              <div className="panel-header">
                <div>
                  <h2>결과 요약</h2>
                  <p>Python 로그를 읽어 현재 상태를 요약합니다.</p>
                </div>
              </div>

              <div className="summary-grid">
                <div className="summary-card">
                  <span>수집된 과제 수</span>
                  <strong>{summary.collected}</strong>
                </div>
                <div className="summary-card">
                  <span>신규 등록 수</span>
                  <strong>{summary.created}</strong>
                </div>
                <div className="summary-card">
                  <span>수정 수</span>
                  <strong>{summary.updated}</strong>
                </div>
                <div className="summary-card">
                  <span>스킵 수</span>
                  <strong>{summary.skipped}</strong>
                </div>
              </div>

              <div className="runtime-card">
                <div className="runtime-title">상태</div>
                <div>{statusMessage}</div>
                <div className="runtime-meta">
                  <div>.env 파일: {appState?.envExists ? "존재" : "없음"}</div>
                  <div>SQLite 기록: {appState?.databaseExists ? "존재" : "없음"}</div>
                  <div>로그 파일: {appState?.logExists ? "존재" : "없음"}</div>
                </div>
              </div>
            </div>
          </div>

          <section className="panel panel-log">
            <div className="panel-header">
              <div>
                <h2>실행 로그</h2>
                <p>Python stdout/stderr와 renderer 진단 로그를 함께 표시합니다.</p>
              </div>
              <span className="pill">{isRunning ? "실행 중" : "대기 중"}</span>
            </div>
            <div className="log-box">
              {logLines.length ? (
                logLines.map((line) => (
                  <div className={`log-line log-line-${line.tone}`} key={line.id}>
                    {line.text}
                  </div>
                ))
              ) : (
                <div className="log-line">아직 로그가 없습니다.</div>
              )}
            </div>
          </section>
        </section>
      </div>
    </div>
  );
}
