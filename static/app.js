/* ════════════════════════════════════════════
   FutureReady AI – Frontend Logic (app.js)
   ════════════════════════════════════════════ */

const API = "https://futureready-ai-2.onrender.com/api";

/* ─── State ─── */
let state = {
  studentId:   localStorage.getItem("fra_student_id") || null,
  profile:     JSON.parse(localStorage.getItem("fra_profile") || "null"),
  skillGap:    null,
  roadmap:     [],
  portfolio:   JSON.parse(localStorage.getItem("fra_portfolio") || "[]"),
  careers:     [],
  currentQ:    null,
  sessionLogs: [],
};

/* ─── Navigation ─── */
function navigate(pageId) {
  document.querySelectorAll(".page").forEach(p => p.classList.remove("active"));
  document.querySelectorAll(".nav-link").forEach(l => l.classList.remove("active"));
  const page = document.getElementById("page-" + pageId);
  const link = document.querySelector(`[data-page="${pageId}"]`);
  if (page) page.classList.add("active");
  if (link) link.classList.add("active");
  window.scrollTo({ top: 0, behavior: "smooth" });
  onPageEnter(pageId);
}

function onPageEnter(pageId) {
  if (pageId === "analysis")  renderAnalysis();
  if (pageId === "roadmap")   renderRoadmap();
  if (pageId === "dashboard") loadDashboard();
  if (pageId === "portfolio") renderPortfolio();
}

/* ─── Toast ─── */
function showToast(msg, type = "") {
  const t = document.getElementById("toast");
  t.textContent = msg;
  t.className = `toast ${type}`;
  clearTimeout(t._timer);
  t._timer = setTimeout(() => { t.className = "toast hidden"; }, 3500);
}

/* ─── API Helpers ─── */
async function apiPost(endpoint, body) {
  const res = await fetch(API + endpoint, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return res.json();
}

async function apiGet(endpoint) {
  const res = await fetch(API + endpoint);
  return res.json();
}

/* ─── Load Careers into dropdowns ─── */
async function loadCareers() {
  try {
    const data = await apiGet("/careers");
    state.careers = data.careers || [];
    const sel = document.getElementById("p_career");
    state.careers.forEach(c => {
      const opt = document.createElement("option");
      opt.value = c.career_role;
      opt.textContent = `${c.career_role} (${c.demand_level} demand)`;
      sel.appendChild(opt);
    });
  } catch (e) {
    console.error("Could not load careers:", e);
  }
}

/* ─── Profile Form ─── */
document.getElementById("profileForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const status = document.getElementById("profileStatus");
  status.textContent = "Saving…";
  status.className = "status-msg";

  const profile = {
    student_id:           state.studentId,
    name:                 v("p_name"),
    email:                v("p_email"),
    degree:               v("p_degree"),
    specialization:       v("p_spec"),
    year_of_study:        v("p_year"),
    target_career:        v("p_career"),
    programming_skills:   v("p_prog"),
    database_skills:      v("p_db"),
    web_dev_skills:       v("p_web"),
    projects:             v("p_projects"),
    certifications:       v("p_certs"),
    internship_experience:v("p_intern"),
    communication_level:  v("p_comm"),
    problem_solving_level:v("p_ps"),
  };

  try {
    const res = await apiPost("/analyze", profile);
    if (res.error) { status.textContent = "Error: " + res.error; status.className = "status-msg error"; return; }

    state.studentId = res.student_id;
    state.profile   = profile;
    state.skillGap  = res.skill_gap;
    state.roadmap   = res.roadmap;

    localStorage.setItem("fra_student_id", state.studentId);
    localStorage.setItem("fra_profile", JSON.stringify(state.profile));

    status.textContent = "✓ Profile saved!";
    showToast("Profile saved! Navigating to Skill Analysis…", "success");
    setTimeout(() => navigate("analysis"), 800);
  } catch (err) {
    status.textContent = "Server error – could not reach backend.";
    status.className = "status-msg error";
    showToast("Cannot reach backend. The server may be starting up, please try again.", "error");
  }
});

function v(id) { return document.getElementById(id)?.value?.trim() || ""; }

/* ─── Restore profile form if re-visiting ─── */
function restoreProfile() {
  const p = state.profile;
  if (!p) return;
  const fields = {
    p_name: p.name, p_email: p.email, p_degree: p.degree,
    p_spec: p.specialization, p_year: p.year_of_study, p_career: p.target_career,
    p_prog: p.programming_skills, p_db: p.database_skills, p_web: p.web_dev_skills,
    p_projects: p.projects, p_certs: p.certifications,
    p_intern: p.internship_experience, p_comm: p.communication_level,
    p_ps: p.problem_solving_level,
  };
  for (const [id, val] of Object.entries(fields)) {
    const el = document.getElementById(id);
    if (el && val) el.value = val;
  }
}

/* ─── Skill-Gap Analysis Page ─── */
function renderAnalysis() {
  const gap = state.skillGap;
  if (!gap) {
    show("analysisPrompt"); hide("analysisResults"); return;
  }
  hide("analysisPrompt"); show("analysisResults");

  setText("gapMatchPct",    gap.match_percentage + "%");
  setText("gapMissingCount",gap.missing_skills.length);
  setText("gapMatchedCount",gap.matched_skills.length);
  setText("gapSalary",      "₹" + (gap.avg_salary / 100000).toFixed(1) + "L");
  setText("gapRole",        gap.career_role);

  const bar = document.getElementById("gapBar");
  const lbl = document.getElementById("gapBarLabel");
  bar.style.width = gap.match_percentage + "%";
  lbl.textContent = gap.match_percentage + "%";

  renderTags("matchedSkillsList", gap.matched_skills, "tag-green");
  renderTags("missingSkillsList", gap.missing_skills, "tag-red");
  renderTags("extraSkillsList",   gap.extra_skills,   "tag-amber");

  // AI Recommendation text
  const missing = gap.missing_skills.slice(0, 3).join(", ") || "no critical gaps";
  const rec = `You have ${gap.matched_skills.length} of ${gap.required_skills.length} required skills for ${gap.career_role}. ` +
    `Focus first on: ${missing}. ` +
    `Recommended projects: ${gap.recommended_projects.slice(0, 2).join(", ")}. ` +
    `With consistent effort, you can bridge this gap in 3–6 months.`;
  setText("aiRecommendation", rec);
}

/* ─── Roadmap Page ─── */
async function renderRoadmap() {
  if (!state.roadmap || state.roadmap.length === 0) {
    if (state.studentId) await fetchRoadmapFromServer();
    if (!state.roadmap || state.roadmap.length === 0) {
      show("roadmapPrompt"); hide("roadmapContent"); return;
    }
  }
  hide("roadmapPrompt"); show("roadmapContent");

  const career = state.profile?.target_career || "your target role";
  setText("roadmapCareer", career);

  const container = document.getElementById("roadmapSteps");
  container.innerHTML = "";

  state.roadmap.forEach((step, idx) => {
    const div = document.createElement("div");
    div.className = `roadmap-step ${step.status === "completed" ? "completed" : step.status === "in_progress" ? "in_progress" : ""}`;
    div.dataset.idx = idx;

    const badgeClass = { study: "badge-study", project: "badge-project", practice: "badge-practice", milestone: "badge-milestone" }[step.type] || "badge-study";
    const icon = step.status === "completed" ? "✅" : step.status === "in_progress" ? "🔄" : "⬜";

    div.innerHTML = `
      <div class="step-number">${icon}</div>
      <div class="step-info">
        <div class="step-title">${step.title} <span class="step-type-badge ${badgeClass}">${step.type}</span></div>
        <div class="step-detail">${step.detail}</div>
      </div>
      <div class="step-actions">
        <button class="step-btn ${step.status === 'in_progress' ? 'active-btn' : ''}" onclick="updateStep(${idx}, 'in_progress')">🔄 Start</button>
        <button class="step-btn ${step.status === 'completed' ? 'active-btn' : ''}" onclick="updateStep(${idx}, 'completed')">✅ Done</button>
        <button class="step-btn" onclick="updateStep(${idx}, 'not_started')">↩ Reset</button>
      </div>`;
    container.appendChild(div);
  });

  updateRoadmapSummary();
}

async function updateStep(idx, status) {
  state.roadmap[idx].status = status;
  if (state.studentId) {
    await apiPost("/roadmap/update", { student_id: state.studentId, step_index: idx, status });
  }
  renderRoadmap();
}

async function fetchRoadmapFromServer() {
  if (!state.studentId) return;
  try {
    const p = await apiGet(`/profile/${state.studentId}`);
    if (p.profile?.roadmap) state.roadmap = p.profile.roadmap;
  } catch {}
}

function updateRoadmapSummary() {
  const done  = state.roadmap.filter(s => s.status === "completed").length;
  const total = state.roadmap.length;
  setText("roadmapProgress", `${done}/${total} steps completed`);
}

/* ─── Interview Coach ─── */
document.getElementById("getQBtn").addEventListener("click", async () => {
  const qtype  = document.getElementById("qType").value;
  const career = state.profile?.target_career || "Software Developer";
  try {
    const res = await apiPost("/interview/question", { career_role: career, question_type: qtype });
    state.currentQ = res.question;

    setText("currentQuestion", res.question);
    setText("qTypeBadge", qtype.charAt(0).toUpperCase() + qtype.slice(1));
    document.getElementById("answerInput").value = "";
    hide("feedbackPanel");
    show("interviewSession");
    document.getElementById("answerInput").focus();
  } catch { showToast("Backend not reachable.", "error"); }
});

document.getElementById("submitAnswerBtn").addEventListener("click", async () => {
  const answer = document.getElementById("answerInput").value.trim();
  if (!answer) { showToast("Please type your answer first.", "error"); return; }
  const career = state.profile?.target_career || "Software Developer";
  try {
    const res = await apiPost("/interview/evaluate", {
      question: state.currentQ, answer, career_role: career
    });
    const fb = res.feedback;
    setText("fb_comm",   fb.communication);
    setText("fb_tech",   fb.technical);
    setText("fb_struct", fb.structure);
    setText("fb_score",  fb.overall_score + "/10");
    setText("fb_followup", fb.followup);

    const posEl = document.getElementById("fb_positives");
    posEl.innerHTML = fb.positives.map(p => `<li>${p}</li>`).join("");
    const impEl = document.getElementById("fb_improvements");
    impEl.innerHTML = fb.improvements.map(i => `<li>${i}</li>`).join("");

    state.sessionLogs.push({ q: state.currentQ, a: answer, fb });
    show("feedbackPanel");
  } catch { showToast("Backend not reachable.", "error"); }
});

document.getElementById("nextQBtn").addEventListener("click", () => {
  document.getElementById("getQBtn").click();
});

/* ─── Portfolio ─── */
document.getElementById("genDescBtn").addEventListener("click", async () => {
  const name    = document.getElementById("port_name").value.trim();
  const tech    = document.getElementById("port_tech").value.trim();
  const role    = document.getElementById("port_role").value.trim();
  const outcome = document.getElementById("port_outcome").value.trim();
  if (!name || !tech) { showToast("Enter project name and tech first.", "error"); return; }
  try {
    const res = await apiPost("/portfolio/generate-description", {
      project_name: name, tech_used: tech, role, outcome
    });
    document.getElementById("port_desc").value = res.description;
  } catch { showToast("Backend not reachable.", "error"); }
});

document.getElementById("addProjectBtn").addEventListener("click", () => {
  const name = document.getElementById("port_name").value.trim();
  const tech = document.getElementById("port_tech").value.trim();
  const desc = document.getElementById("port_desc").value.trim();
  if (!name) { showToast("Enter a project name.", "error"); return; }

  state.portfolio.push({ name, tech, desc, id: Date.now() });
  localStorage.setItem("fra_portfolio", JSON.stringify(state.portfolio));
  ["port_name","port_tech","port_role","port_outcome","port_desc"].forEach(id => {
    document.getElementById(id).value = "";
  });
  renderPortfolio();
  showToast("Project added to portfolio!", "success");
});

function renderPortfolio() {
  const list = document.getElementById("projectList");
  if (state.portfolio.length === 0) {
    list.innerHTML = `<p class="muted-text">No projects added yet.</p>`;
  } else {
    list.innerHTML = state.portfolio.map(p => `
      <div class="project-item">
        <h4>${p.name}</h4>
        <div class="proj-tech">🛠 ${p.tech || "—"}</div>
        <div class="proj-desc">${p.desc || ""}</div>
        <span class="proj-remove" onclick="removeProject(${p.id})">✕ Remove</span>
      </div>`).join("");
  }

  // Skills
  const prof = state.profile;
  const skillsEl = document.getElementById("portfolioSkillTags");
  if (prof) {
    const allSkills = [
      ...(prof.programming_skills || "").split(","),
      ...(prof.database_skills || "").split(","),
      ...(prof.web_dev_skills || "").split(","),
    ].map(s => s.trim()).filter(Boolean);
    skillsEl.innerHTML = allSkills.map(s => `<span class="tag tag-blue">${s}</span>`).join("");
  } else { skillsEl.innerHTML = `<p class="muted-text">Complete profile to see skills.</p>`; }

  // Certs
  const certsEl = document.getElementById("portfolioCerts");
  const certs = (prof?.certifications || "").split(",").map(s => s.trim()).filter(Boolean);
  certsEl.innerHTML = certs.length
    ? certs.map(c => `<span class="tag tag-amber">${c}</span>`).join("")
    : `<p class="muted-text">No certifications added.</p>`;
}

function removeProject(id) {
  state.portfolio = state.portfolio.filter(p => p.id !== id);
  localStorage.setItem("fra_portfolio", JSON.stringify(state.portfolio));
  renderPortfolio();
}

/* ─── Dashboard ─── */
async function loadDashboard() {
  if (!state.studentId) {
    show("dashboardPrompt"); hide("dashboardContent"); return;
  }
  try {
    const res = await apiGet(`/dashboard/${state.studentId}`);
    if (res.error) { show("dashboardPrompt"); hide("dashboardContent"); return; }
    hide("dashboardPrompt"); show("dashboardContent");

    const s = res.scores;
    setRing("ring_tech",      "score_tech",      s.technical_skills);
    setRing("ring_comm",      "score_comm",      s.communication);
    setRing("ring_ps",        "score_ps",        s.problem_solving);
    setRing("ring_interview", "score_interview", s.interview_preparation);

    const cp = s.profile_completeness;
    document.getElementById("completeness_bar").style.width = cp + "%";
    setText("completeness_pct", cp + "%");

    const rp = res.roadmap_progress;
    const total = rp.total || 1;
    setBar("rp_completed", "rp_completed_n", rp.completed, total);
    setBar("rp_inprog",    "rp_inprog_n",    rp.in_progress, total);
    setBar("rp_ns",        "rp_ns_n",        rp.not_started, total);
  } catch { showToast("Backend not reachable.", "error"); }
}

function refreshDashboard() { loadDashboard(); }

function setRing(ringId, numId, value) {
  const circumference = 201; // 2π × 32
  const fill = circumference - (value / 10) * circumference;
  const ring = document.getElementById(ringId);
  if (ring) ring.style.strokeDashoffset = fill;
  setText(numId, value + "/10");
}

function setBar(barId, countId, count, total) {
  const pct = total > 0 ? Math.round(count / total * 100) : 0;
  const bar = document.getElementById(barId);
  if (bar) bar.style.width = pct + "%";
  setText(countId, count);
}

/* ─── Helpers ─── */
function setText(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = val;
}
function show(id) {
  const el = document.getElementById(id);
  if (el) el.classList.remove("hidden");
}
function hide(id) {
  const el = document.getElementById(id);
  if (el) el.classList.add("hidden");
}
function renderTags(containerId, items, cls) {
  const el = document.getElementById(containerId);
  if (!el) return;
  el.innerHTML = items.length
    ? items.map(s => `<span class="tag ${cls}">${s}</span>`).join("")
    : `<span class="muted-text">None</span>`;
}

/* ─── Nav click delegation ─── */
document.querySelectorAll(".nav-link").forEach(link => {
  link.addEventListener("click", e => {
    e.preventDefault();
    navigate(link.dataset.page);
  });
});

/* ─── Hamburger ─── */
document.getElementById("hamburger").addEventListener("click", () => {
  document.getElementById("navLinks").classList.toggle("open");
});

/* ─── Init ─── */
(async function init() {
  await loadCareers();
  restoreProfile();
  // Restore skill gap if profile exists
  if (state.studentId) {
    try {
      const p = await apiGet(`/profile/${state.studentId}`);
      if (p.profile) {
        state.profile = p.profile;
        if (p.profile.roadmap) state.roadmap = p.profile.roadmap;
        // Re-run analysis silently to populate state.skillGap
        const career = p.profile.target_career;
        if (career) {
          const allSkills = [
            p.profile.programming_skills || "",
            p.profile.database_skills    || "",
            p.profile.web_dev_skills     || "",
          ].filter(Boolean).join(", ");
          const gap = await apiPost("/skill-gap", { career_role: career, all_skills: allSkills });
          if (!gap.error) state.skillGap = gap;
        }
        restoreProfile();
      }
    } catch {}
  }
  navigate("home");
})();
