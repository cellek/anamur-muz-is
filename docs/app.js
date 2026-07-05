/* AnamurMuzİş — ön yüz mantığı */
(() => {
  "use strict";

  const WORK_TYPES = [
    "Hasat",
    "Paketleme",
    "Dikim",
    "Bakım / İlaçlama",
    "Sera İşleri",
    "Taşıma / Yükleme",
    "Sürücü",
    "Diğer",
  ];

  const state = { jobs: [], workers: [] };

  // API yoksa (ör. GitHub Pages gibi statik barındırma) localStorage kullanılır.
  let staticMode = false;
  const STORAGE_KEY = "anamurmuzis-data";

  const STATIC_SEED = {
    jobs: [
      {
        id: "seed-job-1",
        title: "Muz hasadı için 5 işçi aranıyor",
        employer: "Yılmaz Tarım",
        location: "Ören Mahallesi",
        workType: "Hasat",
        wage: "Günlük 900 TL + yemek",
        workersNeeded: 5,
        startDate: "2026-07-10",
        duration: "2 hafta",
        phone: "0532 000 00 01",
        description: "Sera muz hasadı. Deneyimli işçiler tercih edilir. Servis mevcuttur.",
        createdAt: "2026-07-03T08:00:00+00:00",
      },
      {
        id: "seed-job-2",
        title: "Paketleme tesisine eleman alınacak",
        employer: "Anamur Muz Paketleme",
        location: "Bahçelievler",
        workType: "Paketleme",
        wage: "Aylık 26.000 TL, sigortalı",
        workersNeeded: 3,
        startDate: "2026-07-15",
        duration: "Sürekli",
        phone: "0532 000 00 02",
        description: "Muz paketleme ve etiketleme. Kadın-erkek eleman alınacaktır.",
        createdAt: "2026-07-04T10:30:00+00:00",
      },
    ],
    workers: [
      {
        id: "seed-worker-1",
        name: "Mehmet K.",
        workTypes: ["Hasat", "Bakım / İlaçlama"],
        experience: "8 yıl sera muz deneyimi",
        availableFrom: "2026-07-07",
        expectedWage: "Günlük 850 TL",
        location: "Anamur Merkez",
        phone: "0532 000 00 03",
        note: "Kendi ulaşımım var, Ören ve Kaledran tarafına gidebilirim.",
        createdAt: "2026-07-02T09:00:00+00:00",
      },
    ],
  };

  function loadLocal() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) return JSON.parse(raw);
    } catch (err) { /* bozuk veri — baştan başla */ }
    return JSON.parse(JSON.stringify(STATIC_SEED));
  }

  function saveLocal() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({ jobs: state.jobs, workers: state.workers }));
    } catch (err) { /* depolama dolu/kapalı — sessizce geç */ }
  }

  const $ = (sel) => document.querySelector(sel);

  // ---------- yardımcılar ----------
  function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function meta(label, value) {
    if (!value) return null;
    const span = el("span");
    span.append(el("span", "label", label + ":"), document.createTextNode(value));
    return span;
  }

  function formatDate(iso) {
    if (!iso) return "";
    const d = new Date(iso);
    if (isNaN(d)) return iso;
    return d.toLocaleDateString("tr-TR", { day: "numeric", month: "long", year: "numeric" });
  }

  function callLink(phone) {
    const a = el("a", "call-btn", "📞 " + phone);
    a.href = "tel:" + phone.replace(/[^+\d]/g, "");
    return a;
  }

  async function fetchJSON(url, options) {
    const res = await fetch(url, options);
    const body = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(body.error || "Sunucu hatası");
    return body;
  }

  // ---------- kartlar ----------
  function jobCard(job) {
    const card = el("article", "card");

    const head = el("div", "card-head");
    const titleWrap = el("div");
    titleWrap.append(el("h3", null, job.title), el("p", "subtitle", job.employer + " · " + job.location));
    const badges = el("div");
    badges.append(el("span", "badge type", job.workType));
    head.append(titleWrap, badges);

    const metas = el("div", "card-meta");
    [
      meta("Ücret", job.wage),
      meta("İşçi sayısı", job.workersNeeded ? job.workersNeeded + " kişi" : ""),
      meta("Başlangıç", formatDate(job.startDate)),
      meta("Süre", job.duration),
    ].forEach((m) => m && metas.append(m));

    card.append(head, metas);
    if (job.description) card.append(el("p", "desc", job.description));

    const foot = el("div", "card-foot");
    const time = el("time", null, "İlan tarihi: " + formatDate(job.createdAt));
    foot.append(time, callLink(job.phone));
    card.append(foot);
    return card;
  }

  function workerCard(w) {
    const card = el("article", "card");

    const head = el("div", "card-head");
    const titleWrap = el("div");
    titleWrap.append(el("h3", null, w.name), el("p", "subtitle", w.location));
    const badges = el("div");
    (w.workTypes || []).forEach((t) => {
      badges.append(el("span", "badge type", t), document.createTextNode(" "));
    });
    head.append(titleWrap, badges);

    const metas = el("div", "card-meta");
    [
      meta("Deneyim", w.experience),
      meta("Müsait", formatDate(w.availableFrom)),
      meta("Beklenen ücret", w.expectedWage),
    ].forEach((m) => m && metas.append(m));

    card.append(head, metas);
    if (w.note) card.append(el("p", "desc", w.note));

    const foot = el("div", "card-foot");
    foot.append(el("time", null, "Kayıt tarihi: " + formatDate(w.createdAt)), callLink(w.phone));
    card.append(foot);
    return card;
  }

  // ---------- listeleme + filtre ----------
  function renderJobs() {
    const q = $("#job-search").value.trim().toLowerCase();
    const type = $("#job-filter-type").value;
    const list = $("#job-list");
    list.innerHTML = "";

    const filtered = state.jobs.filter((j) => {
      if (type && j.workType !== type) return false;
      if (!q) return true;
      return [j.title, j.employer, j.location, j.description, j.wage]
        .join(" ").toLowerCase().includes(q);
    });

    filtered.forEach((j) => list.append(jobCard(j)));
    $("#job-empty").classList.toggle("hidden", filtered.length > 0);
    $("#count-jobs").textContent = state.jobs.length;
  }

  function renderWorkers() {
    const q = $("#worker-search").value.trim().toLowerCase();
    const type = $("#worker-filter-type").value;
    const list = $("#worker-list");
    list.innerHTML = "";

    const filtered = state.workers.filter((w) => {
      if (type && !(w.workTypes || []).includes(type)) return false;
      if (!q) return true;
      return [w.name, w.location, w.experience, w.note, (w.workTypes || []).join(" ")]
        .join(" ").toLowerCase().includes(q);
    });

    filtered.forEach((w) => list.append(workerCard(w)));
    $("#worker-empty").classList.toggle("hidden", filtered.length > 0);
    $("#count-workers").textContent = state.workers.length;
  }

  // ---------- sekmeler ----------
  document.querySelectorAll(".tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      document.querySelectorAll(".tab").forEach((t) => {
        const active = t === tab;
        t.classList.toggle("active", active);
        t.setAttribute("aria-selected", String(active));
      });
      $("#panel-jobs").classList.toggle("hidden", tab.dataset.tab !== "jobs");
      $("#panel-workers").classList.toggle("hidden", tab.dataset.tab !== "workers");
    });
  });

  // ---------- iş türü seçenekleri ----------
  function fillTypeOptions() {
    [$("#job-filter-type"), $("#worker-filter-type"), $("#job-form-type")].forEach((select) => {
      WORK_TYPES.forEach((t) => {
        const opt = el("option", null, t);
        opt.value = t;
        select.append(opt);
      });
    });
    const grid = $("#worker-form-types");
    WORK_TYPES.forEach((t) => {
      const label = el("label");
      const cb = document.createElement("input");
      cb.type = "checkbox";
      cb.name = "workTypes";
      cb.value = t;
      label.append(cb, document.createTextNode(t));
      grid.append(label);
    });
  }

  // ---------- formlar ----------
  function setupDialog(dialogSel, openBtnSel, formSel, errorSel, endpoint, buildPayload, onSaved) {
    const dialog = $(dialogSel);
    const form = $(formSel);
    const errorBox = $(errorSel);

    $(openBtnSel).addEventListener("click", () => {
      form.reset();
      errorBox.classList.add("hidden");
      dialog.showModal();
    });

    dialog.querySelector("[data-close]").addEventListener("click", () => dialog.close());

    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      errorBox.classList.add("hidden");

      const payload = buildPayload(new FormData(form));
      try {
        let saved;
        if (staticMode) {
          if (!form.checkValidity()) throw new Error("Zorunlu alanlar eksik");
          if (payload.workTypes && payload.workTypes.length === 0) throw new Error("Zorunlu alanlar eksik");
          saved = Object.assign({}, payload, {
            id: "local-" + Date.now().toString(36),
            createdAt: new Date().toISOString(),
          });
        } else {
          saved = await fetchJSON(endpoint, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
          });
        }
        onSaved(saved);
        if (staticMode) saveLocal();
        dialog.close();
      } catch (err) {
        errorBox.textContent = err.message === "Zorunlu alanlar eksik"
          ? "Lütfen yıldızlı (*) zorunlu alanları doldurun."
          : "Kayıt başarısız: " + err.message;
        errorBox.classList.remove("hidden");
      }
    });
  }

  setupDialog(
    "#job-dialog", "#btn-new-job", "#job-form", "#job-form-error", "/api/jobs",
    (fd) => Object.fromEntries(fd.entries()),
    (saved) => { state.jobs.unshift(saved); renderJobs(); }
  );

  setupDialog(
    "#worker-dialog", "#btn-new-worker", "#worker-form", "#worker-form-error", "/api/workers",
    (fd) => {
      const payload = Object.fromEntries(fd.entries());
      payload.workTypes = fd.getAll("workTypes");
      return payload;
    },
    (saved) => { state.workers.unshift(saved); renderWorkers(); }
  );

  // ---------- filtre olayları ----------
  $("#job-search").addEventListener("input", renderJobs);
  $("#job-filter-type").addEventListener("change", renderJobs);
  $("#worker-search").addEventListener("input", renderWorkers);
  $("#worker-filter-type").addEventListener("change", renderWorkers);

  // ---------- başlangıç ----------
  async function init() {
    fillTypeOptions();
    try {
      const [jobs, workers] = await Promise.all([
        fetchJSON("api/jobs"),
        fetchJSON("api/workers"),
      ]);
      state.jobs = jobs;
      state.workers = workers;
    } catch (err) {
      // API yok: statik barındırma (GitHub Pages) — localStorage'a geç.
      staticMode = true;
      const data = loadLocal();
      const byDate = (a, b) => (b.createdAt || "").localeCompare(a.createdAt || "");
      state.jobs = (data.jobs || []).sort(byDate);
      state.workers = (data.workers || []).sort(byDate);
    }
    renderJobs();
    renderWorkers();
  }

  init();
})();
