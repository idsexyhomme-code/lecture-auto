/**
 * 코어 캠퍼스 — 인라인 어드민 모드
 *
 * 사용법: 어떤 페이지든 URL에 ?admin=1을 추가하면 활성화.
 * 처음 진입 시 GitHub Personal Access Token을 한 번 입력 (localStorage 보관, 본인 브라우저에서만).
 *
 * 동작:
 *   1. data-edit-field="<file>:<key>" 속성을 가진 요소 옆에 ✏️ 버튼 표시
 *   2. ✏️ 클릭 → input/textarea로 변환 → 편집 → 저장 시 GitHub Contents API로 PUT
 *   3. 저장 후 GitHub Actions의 agent-loop 워크플로우를 dispatch로 트리거
 *   4. 1~2분 뒤 자동 새로고침
 *
 * 보안:
 *   - PAT는 localStorage에만 저장 (회원님 브라우저에서만)
 *   - 페이지 source에는 PAT가 절대 들어가지 않음
 *   - 저장 실패 시 에러 토스트로 안내
 */
(() => {
  "use strict";

  // ── build.py가 inject하는 사이트 정보 ────────────────────────
  const REPO_OWNER = window.__ADMIN_REPO_OWNER__ || "";
  const REPO_NAME  = window.__ADMIN_REPO_NAME__  || "";
  const BRANCH     = window.__ADMIN_BRANCH__     || "main";
  const WORKFLOW_FILE = "agent-loop.yml";

  // ── 활성화 조건 — ?admin=1 ───────────────────────────────────
  const params = new URLSearchParams(location.search);
  if (params.get("admin") !== "1") return;

  if (!REPO_OWNER || !REPO_NAME) {
    console.error("[admin] repo 정보 누락 — build.py에서 inject되어야 합니다");
    return;
  }

  // ── PAT 확보 ────────────────────────────────────────────────
  let pat = localStorage.getItem("cc_admin_pat");
  if (!pat) {
    pat = window.prompt(
      "GitHub Personal Access Token을 입력하세요\n" +
      "(repo + workflow scope 필요. localStorage에 본인 브라우저에서만 저장됩니다.)"
    );
    if (!pat) return;
    localStorage.setItem("cc_admin_pat", pat.trim());
    pat = pat.trim();
  }

  // ── 어드민 표시 ─────────────────────────────────────────────
  document.body.classList.add("admin-mode");
  injectAdminBar();

  // ── 편집 가능 필드 스캔 ─────────────────────────────────────
  document.querySelectorAll("[data-edit-field]").forEach(decorateField);

  // ────────────────────────────────────────────────────────────
  // GitHub API helpers
  // ────────────────────────────────────────────────────────────
  async function ghGet(path) {
    const r = await fetch(
      `https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/contents/${path}?ref=${BRANCH}`,
      { headers: { "Authorization": `Bearer ${pat}` } }
    );
    if (!r.ok) throw new Error(`GET ${path} → ${r.status}`);
    return r.json();
  }
  async function ghPut(path, sha, content, message) {
    const encoded = btoa(unescape(encodeURIComponent(content)));
    const r = await fetch(
      `https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/contents/${path}`,
      {
        method: "PUT",
        headers: {
          "Authorization": `Bearer ${pat}`,
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ message, content: encoded, sha, branch: BRANCH })
      }
    );
    if (!r.ok) throw new Error(`PUT ${path} → ${r.status}`);
    return r.json();
  }
  async function dispatchWorkflow() {
    const r = await fetch(
      `https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/actions/workflows/${WORKFLOW_FILE}/dispatches`,
      {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${pat}`,
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ ref: BRANCH })
      }
    );
    return r.ok;
  }

  // ────────────────────────────────────────────────────────────
  // 편집 가능 필드 데코레이션
  // ────────────────────────────────────────────────────────────
  function decorateField(el) {
    if (el.dataset.editDecorated) return;
    el.dataset.editDecorated = "1";
    el.classList.add("ce-editable");

    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "ce-edit-btn";
    btn.title = "이 텍스트 수정";
    btn.textContent = "✏️";
    btn.addEventListener("click", (e) => {
      e.preventDefault();
      e.stopPropagation();
      enterEdit(el);
    });
    el.appendChild(btn);
  }

  function enterEdit(el) {
    const original = el.dataset.originalText || el.textContent.replace(/✏️\s*$/, "").trim();
    el.dataset.originalText = original;

    const isLong = original.length > 60;
    const input = document.createElement(isLong ? "textarea" : "input");
    if (!isLong) input.type = "text";
    input.value = original;
    input.className = "ce-edit-input";
    if (isLong) input.rows = Math.min(8, Math.max(2, Math.ceil(original.length / 40)));

    const saveBtn = document.createElement("button");
    saveBtn.type = "button";
    saveBtn.className = "ce-save-btn";
    saveBtn.textContent = "저장";

    const cancelBtn = document.createElement("button");
    cancelBtn.type = "button";
    cancelBtn.className = "ce-cancel-btn";
    cancelBtn.textContent = "취소";

    const wrap = document.createElement("span");
    wrap.className = "ce-edit-wrap";
    wrap.appendChild(input);
    wrap.appendChild(saveBtn);
    wrap.appendChild(cancelBtn);

    // 원본 자식 비우고 wrap만
    const stash = Array.from(el.childNodes);
    el.innerHTML = "";
    el.appendChild(wrap);
    input.focus();
    input.select();

    cancelBtn.addEventListener("click", () => {
      el.innerHTML = "";
      stash.forEach(n => el.appendChild(n));
    });

    saveBtn.addEventListener("click", async () => {
      const newValue = input.value.trim();
      if (newValue === original) {
        cancelBtn.click();
        return;
      }
      saveBtn.disabled = true;
      saveBtn.textContent = "저장 중…";
      try {
        await persistField(el.dataset.editField, newValue);
        showToast("✅ 저장 완료. 워크플로우 트리거 중…", "success");
        const ok = await dispatchWorkflow();
        if (ok) {
          showToast("⏳ 빌드 시작 — 약 1분 뒤 자동 새로고침합니다", "success");
          setTimeout(() => location.reload(), 75 * 1000); // 75초 후 reload
        } else {
          showToast("⚠️ 저장은 됐지만 워크플로우 dispatch 실패 — 수동 트리거 필요", "warn");
        }
        // 우선 화면에는 새 값 반영
        el.dataset.originalText = newValue;
        el.innerHTML = "";
        el.appendChild(document.createTextNode(newValue));
        decorateField(el);
      } catch (err) {
        console.error("[admin] save failed", err);
        showToast(`❌ 저장 실패: ${err.message}`, "error");
        saveBtn.disabled = false;
        saveBtn.textContent = "저장";
      }
    });
  }

  // ────────────────────────────────────────────────────────────
  // 필드 저장 — JSON 파일 부분 갱신
  // ────────────────────────────────────────────────────────────
  async function persistField(spec, newValue) {
    // spec 예시:
    //   "site_config:site_name"
    //   "site_config:site_headline"
    //   "site_config:course_overrides.claude-bizflow.title_override"
    //   "site_config:course_overrides.claude-sop.tagline_override"
    const [bucket, fieldPath] = spec.split(":", 2);
    if (bucket !== "site_config") {
      throw new Error(`아직 site_config 버킷만 지원 (받은 값: ${bucket})`);
    }
    const path = "site_config.json";

    const meta = await ghGet(path);
    const sha = meta.sha;
    const decoded = decodeURIComponent(escape(atob(meta.content.replace(/\s/g, ""))));
    const data = JSON.parse(decoded);

    setNested(data, fieldPath, newValue);

    const updated = JSON.stringify(data, null, 2) + "\n";
    await ghPut(path, sha, updated, `admin: ${fieldPath} 인라인 수정`);
  }

  function setNested(obj, dottedPath, value) {
    const keys = dottedPath.split(".");
    let cur = obj;
    for (let i = 0; i < keys.length - 1; i++) {
      const k = keys[i];
      if (cur[k] === undefined || cur[k] === null || typeof cur[k] !== "object") {
        cur[k] = {};
      }
      cur = cur[k];
    }
    cur[keys[keys.length - 1]] = value;
  }

  // ────────────────────────────────────────────────────────────
  // 어드민 바 + 토스트
  // ────────────────────────────────────────────────────────────
  function injectAdminBar() {
    const bar = document.createElement("div");
    bar.className = "ce-admin-bar";
    bar.innerHTML = `
      <span class="ce-admin-label">✏️ 편집 모드</span>
      <span class="ce-admin-hint">텍스트 옆 ✏️ 클릭 → 수정 → 저장</span>
      <span class="ce-admin-spacer"></span>
      <button type="button" class="ce-admin-btn" id="ce-admin-exit">나가기</button>
      <button type="button" class="ce-admin-btn ce-admin-btn-danger" id="ce-admin-forget">PAT 잊기</button>
    `;
    document.body.appendChild(bar);
    bar.querySelector("#ce-admin-exit").addEventListener("click", () => {
      location.search = ""; // ?admin=1 제거
    });
    bar.querySelector("#ce-admin-forget").addEventListener("click", () => {
      if (confirm("저장된 PAT를 이 브라우저에서 삭제할까요?")) {
        localStorage.removeItem("cc_admin_pat");
        location.search = "";
      }
    });
  }

  function showToast(text, kind = "info") {
    const t = document.createElement("div");
    t.className = `ce-toast ce-toast-${kind}`;
    t.textContent = text;
    document.body.appendChild(t);
    setTimeout(() => t.classList.add("show"), 20);
    setTimeout(() => {
      t.classList.remove("show");
      setTimeout(() => t.remove(), 300);
    }, 4500);
  }
})();
