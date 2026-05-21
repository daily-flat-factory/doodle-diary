/* ============================================================
   Doodle-Diary — Frontend JS
   ============================================================ */

// ── 상태 ───────────────────────────────────────────────────
let selectedMood = "neutral";
let userStatus   = { today_count: 0, remaining: 3, daily_limit: 3 };


// ── 앱 초기화 ──────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", async () => {
  await initUser();
  await loadGallery();
  setupMoodButtons();
  setupCharCounter();
});


// ── 사용자 초기화 (UUID 발급 or 기존 세션 확인) ────────────
async function initUser() {
  try {
    const res  = await fetch("/api/user/init", { method: "POST", credentials: "include" });
    const data = await res.json();
    userStatus = data;
    updateLimitUI();
  } catch (e) {
    console.error("User init failed:", e);
  }
}


// ── 제한 UI 업데이트 ───────────────────────────────────────
function updateLimitUI() {
  const { today_count, remaining, daily_limit } = userStatus;

  // 헤더 뱃지
  const badge = document.getElementById("limit-badge");
  if (badge) {
    badge.textContent = `🖍️ 오늘 ${today_count} / ${daily_limit}`;
  }

  // 본문 제한 정보
  const info = document.getElementById("limit-info");
  if (!info) return;

  if (remaining <= 0) {
    info.className = "limit-info exceeded";
    info.textContent = "오늘의 그림일기를 다 썼어요 🎨 내일 자정에 다시 만나요!";
    const btn = document.getElementById("submit-btn");
    if (btn) btn.disabled = true;
  } else {
    info.className = "limit-info";
    info.textContent = remaining === daily_limit
      ? `오늘 ${daily_limit}번 그릴 수 있어요 ✏️`
      : `오늘 ${remaining}번 더 그릴 수 있어요!`;
  }
}


// ── 기분 버튼 ─────────────────────────────────────────────
function setupMoodButtons() {
  document.querySelectorAll(".mood-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".mood-btn").forEach(b => b.classList.remove("selected"));
      btn.classList.add("selected");
      selectedMood = btn.dataset.mood;
      document.getElementById("selected-mood").value = selectedMood;
    });
  });
}


// ── 글자 수 카운터 ─────────────────────────────────────────
function setupCharCounter() {
  const textarea = document.getElementById("diary-input");
  const counter  = document.getElementById("char-count");
  if (!textarea || !counter) return;

  textarea.addEventListener("input", () => {
    counter.textContent = textarea.value.length;
    counter.style.color = textarea.value.length > 1800 ? "#E85D5D" : "";
  });
}


// ── 일기 제출 ─────────────────────────────────────────────
async function submitDiary() {
  const content = document.getElementById("diary-input")?.value?.trim();
  if (!content) {
    alert("일기 내용을 입력해주세요 ✏️");
    return;
  }

  // 버튼 로딩 상태
  setSubmitLoading(true);

  try {
    const today = new Date().toISOString().split("T")[0];
    const res   = await fetch("/api/diary", {
      method:      "POST",
      credentials: "include",
      headers:     { "Content-Type": "application/json" },
      // ⚠️ 일기 원문을 서버로 전송 — 서버에서 프롬프트 변환 후 원문 폐기
      body: JSON.stringify({
        content: content,
        mood:    selectedMood,
        date:    today,
      }),
    });

    const data = await res.json();

    if (!res.ok) {
      if (res.status === 429) {
        // 일일 제한 초과
        userStatus.remaining = 0;
        updateLimitUI();
        alert(data.message || "오늘의 그림일기를 다 썼어요 🎨");
      } else {
        alert(data.error || "오류가 발생했어요. 다시 시도해주세요.");
      }
      return;
    }

    // 제한 카운트 업데이트
    userStatus.today_count = data.today_count;
    userStatus.remaining   = data.remaining;
    updateLimitUI();

    // 결과 표시
    showResult(data.image_path);

    // 갤러리 새로고침
    await loadGallery();

  } catch (e) {
    console.error("Submit failed:", e);
    alert("네트워크 오류가 발생했어요. 다시 시도해주세요.");
  } finally {
    setSubmitLoading(false);
  }
}


// ── 결과 표시 ─────────────────────────────────────────────
function showResult(imagePath) {
  const area = document.getElementById("result-area");
  const img  = document.getElementById("result-image");
  const dlBtn = document.getElementById("download-btn");

  if (!area || !img) return;

  img.src = imagePath;
  dlBtn.href = imagePath;
  area.style.display = "block";
  area.scrollIntoView({ behavior: "smooth", block: "start" });
}


// ── 폼 초기화 ─────────────────────────────────────────────
function resetForm() {
  const textarea = document.getElementById("diary-input");
  const result   = document.getElementById("result-area");
  const counter  = document.getElementById("char-count");

  if (textarea) textarea.value = "";
  if (counter)  counter.textContent = "0";
  if (result)   result.style.display = "none";

  // 기분 선택 초기화
  document.querySelectorAll(".mood-btn").forEach(b => b.classList.remove("selected"));
  selectedMood = "neutral";

  window.scrollTo({ top: 0, behavior: "smooth" });
}


// ── 갤러리 로드 ───────────────────────────────────────────
async function loadGallery() {
  try {
    const res  = await fetch("/api/diary/list", { credentials: "include" });
    if (!res.ok) return;

    const data    = await res.json();
    const grid    = document.getElementById("gallery-grid");
    const empty   = document.getElementById("gallery-empty");
    if (!grid) return;

    grid.innerHTML = "";

    if (!data.diaries || data.diaries.length === 0) {
      if (empty) empty.style.display = "block";
      return;
    }

    if (empty) empty.style.display = "none";

    data.diaries.forEach(diary => {
      const item = document.createElement("div");
      item.className = "gallery-item";
      item.innerHTML = `
        <img src="${diary.image_path}" alt="그림일기" loading="lazy" />
        <div class="gallery-item-date">${formatDate(diary.diary_date)}</div>
      `;
      item.addEventListener("click", () => {
        window.location.href = `/diary/${diary.id}`;
      });
      grid.appendChild(item);
    });

  } catch (e) {
    console.error("Gallery load failed:", e);
  }
}


// ── 유틸 ──────────────────────────────────────────────────
function setSubmitLoading(loading) {
  const btn     = document.getElementById("submit-btn");
  const btnText = btn?.querySelector(".btn-text");
  const btnLoad = btn?.querySelector(".btn-loading");
  if (!btn) return;

  btn.disabled = loading;
  if (btnText) btnText.style.display = loading ? "none"   : "inline";
  if (btnLoad) btnLoad.style.display = loading ? "inline" : "none";
}

function formatDate(dateStr) {
  if (!dateStr) return "";
  const [y, m, d] = dateStr.split("-");
  return `${m}월 ${d}일`;
}
