document.addEventListener("DOMContentLoaded", () => {
  const state = {
    token: localStorage.getItem("iams_token"),
    cache: { plans: [], questions: [], records: [], users: [] },
    editing: { planId: null, questionId: null, recordId: null, userId: null },
    currentUser: null,
    selectedRecordPlanId: "",
  };

  const selectors = {
    loginView: "loginView",
    appView: "appView",
    userLabel: "userLabel",
    loginForm: "loginForm",
    account: "account",
    password: "password",
    loginError: "loginError",
    planForm: "planForm",
    questionForm: "questionForm",
    recordForm: "recordForm",
    actionForm: "actionForm",
    userForm: "userForm",
    planTable: "planTable",
    questionTable: "questionTable",
    recordTable: "recordTable",
    actionTable: "actionTable",
    userTable: "userTable",
    recordQuestionSelect: "recordQuestionSelect",
    actionRecordSelect: "actionRecordSelect",
    planImportFile: "planImportFile",
    questionImportFile: "questionImportFile",
    recordImportFile: "recordImportFile",
    exportPlansBtn: "exportPlansBtn",
    importPlansBtn: "importPlansBtn",
    exportQuestionsBtn: "exportQuestionsBtn",
    importQuestionsBtn: "importQuestionsBtn",
    exportRecordsBtn: "exportRecordsBtn",
    importRecordsBtn: "importRecordsBtn",
    logoutBtn: "logoutBtn",
    addPlanBtn: "addPlanBtn",
    addQuestionBtn: "addQuestionBtn",
    addRecordBtn: "addRecordBtn",
    addUserBtn: "addUserBtn",
    recordPlanFilter: "recordPlanFilter",
    clearRecordPlanFilter: "clearRecordPlanFilter",
    recordPlanFilterList: "recordPlanFilterList",
    recordPlanFilterSuggestions: "recordPlanFilterSuggestions",
    recordPlanSelect: "recordPlanSelect",
  };

  const E = Object.fromEntries(Object.entries(selectors).map(([key, id]) => [key, document.getElementById(id)]));

  const $ = id => document.getElementById(id);

  const getHeaders = (headers = {}) => ({
    ...headers,
    ...(state.token ? { Authorization: `Bearer ${state.token}` } : {}),
  });

  const downloadBlob = (blob, filename) => {
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  };

  const handleUnauthorized = async response => {
    if (response.status === 401) {
      localStorage.removeItem("iams_token");
      state.token = null;
      throw new Error("未授權或登入逾時，請重新登入。\n請重新整理後再登入。");
    }
    return response;
  };

  const readableError = errorBody => {
    if (!errorBody) return "API request failed";
    const detail = errorBody.detail || errorBody.message || errorBody;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail.map(item => {
        if (typeof item === "string") return item;
        const loc = Array.isArray(item.loc) ? item.loc.join(".") : "";
        return [loc, item.msg || JSON.stringify(item)].filter(Boolean).join(": ");
      }).join(", ");
    }
    return JSON.stringify(detail);
  };

  const api = async (path, options = {}) => {
    const headers = getHeaders(options.headers);
    if (
      options.body &&
      !(options.body instanceof FormData) &&
      !(options.body instanceof URLSearchParams) &&
      !headers["Content-Type"]
    ) {
      headers["Content-Type"] = "application/json";
    }
    const res = await fetch(path, { ...options, headers });
    await handleUnauthorized(res);
    if (!res.ok) {
      let errorBody = null;
      try { errorBody = await res.json(); } catch {}
      throw new Error(readableError(errorBody));
    }
    return res.json();
  };

  const fetchBlob = async path => {
    const res = await fetch(path, { headers: getHeaders() });
    await handleUnauthorized(res);
    if (!res.ok) {
      let errorBody = null;
      try { errorBody = await res.json(); } catch {}
      throw new Error(readableError(errorBody));
    }
    return res.blob();
  };

  const formData = form => Object.fromEntries(
    [...new FormData(form).entries()].filter(([, value]) => value !== "")
  );

  const fillForm = (form, values) => {
    Object.entries(values).forEach(([key, value]) => {
      const field = form.elements[key];
      if (!field) return;
      field.value = value ?? "";
    });
  };

  const normalizePayload = payload => {
    const normalized = { ...payload };
    if ("year" in normalized) normalized.year = Number(normalized.year);
    if ("enabled" in normalized) normalized.enabled = normalized.enabled === true || normalized.enabled === "true";
    return normalized;
  };

  const showModal = id => bootstrap.Modal.getOrCreateInstance($(id)).show();

  const exportXlsx = async (path, prefix) => {
    const blob = await fetchBlob(path);
    downloadBlob(blob, `${prefix}_${new Date().toISOString().slice(0, 10)}.xlsx`);
  };

  const importXlsx = async (input, path, callback) => {
    const file = input.files[0];
    if (!file) return;
    const body = new FormData();
    body.append("file", file);
    const res = await api(path, { method: "POST", body });
    input.value = "";
    if (callback) await callback(res);
    return res;
  };

  const renderTable = (table, headers, rows, rowRenderer) => {
    table.innerHTML = `
      <thead><tr>${headers.map(header => `<th>${header}</th>`).join("")}</tr></thead>
      <tbody>${rows.map(rowRenderer).join("")}</tbody>
    `;
  };

  const renderOptions = (select, items, labelFn) => {
    select.innerHTML = items.map(item => {
      const option = labelFn ? labelFn(item) : item;
      return `<option value="${option.value}">${option.label}</option>`;
    }).join("");
  };

  const normalizeSearchText = value => String(value || "").trim().toLowerCase();

  const filterPlans = (query, plans) => {
    if (!query) return plans;
    const text = normalizeSearchText(query);
    return plans.filter(plan => {
      return [plan.task_no, plan.cycle_name, plan.department, plan.year].some(field =>
        String(field).toLowerCase().includes(text)
      );
    });
  };

  const findPlanByExactValue = value => {
    const norm = normalizeSearchText(value);
    return state.cache.plans.find(plan => normalizeSearchText(`${plan.task_no} / ${plan.year} / ${plan.cycle_name} / ${plan.department}`) === norm || normalizeSearchText(plan.task_no) === norm);
  };

  const updateRecordPlanFilterHint = (matches, query) => {
    if (!query) {
      E.recordPlanFilterHint.textContent = "輸入任務編號、年度或部門，即可從下拉清單快速選擇對應稽核任務。";
      return;
    }
    if (!matches.length) {
      E.recordPlanFilterHint.textContent = "找不到符合條件的稽核任務，請調整搜尋關鍵字。";
      return;
    }
    E.recordPlanFilterHint.textContent = `已找到 ${matches.length} 筆相符任務，請從下拉選擇。`;
  };

  const renderPlanFilterList = plans => {
    E.recordPlanFilterList.innerHTML = plans.map(plan => (
      `<option value="${plan.task_no} / ${plan.year} / ${plan.cycle_name} / ${plan.department}" data-id="${plan.id}"></option>`
    )).join("");
  };

  const setSelectedAuditPlan = planId => {
    state.selectedRecordPlanId = String(planId || "");
    if (state.selectedRecordPlanId) {
      E.recordPlanSelect.value = state.selectedRecordPlanId;
    }
  };

  const renderPlanFilterSuggestions = plans => {
    if (!plans.length) {
      E.recordPlanFilterSuggestions.classList.add("d-none");
      E.recordPlanFilterSuggestions.innerHTML = "";
      return;
    }
    E.recordPlanFilterSuggestions.innerHTML = plans.slice(0, 8).map(plan => {
      const label = `${plan.task_no} / ${plan.year} / ${plan.cycle_name} / ${plan.department}`;
      return `<button type="button" class="autocomplete-item" data-id="${plan.id}" data-value="${label}">${label}</button>`;
    }).join("");
    E.recordPlanFilterSuggestions.classList.remove("d-none");
  };

  const selectPlanSuggestion = async option => {
    const value = option.dataset.value;
    const planId = option.dataset.id;
    E.recordPlanFilter.value = value;
    setSelectedAuditPlan(planId);
    E.recordPlanFilterSuggestions.classList.add("d-none");
    updateRecordPlanFilterHint([state.cache.plans.find(p => String(p.id) === String(planId))], value);
    await loadRecords();
  };

  const showApp = async user => {
    state.currentUser = user;
    E.loginView.classList.add("d-none");
    E.appView.classList.remove("d-none");
    E.userLabel.textContent = `${user.name} / ${user.role}`;
    await loadAll();
  };

  const renderMetrics = stats => {
    const metricMap = [
      ["年度計畫", stats.audit_plan_count],
      ["進行中計畫", stats.open_plan_count],
      ["啟用題目", stats.question_count],
      ["查核記錄", stats.audit_record_count],
      ["CAR/OFI", `${stats.car_count}/${stats.ofi_count}`],
      ["待追蹤改善", stats.open_corrective_action_count],
    ];
    $("metrics").innerHTML = metricMap.map(([label, value]) => `
      <div class="col-md-4 col-xl-2"><div class="metric"><div class="metric-label">${label}</div><div class="metric-value">${value}</div></div></div>
    `).join("");
  };

  const renderAnnouncements = items => {
    $("announcementList").innerHTML = items.map(item => `
      <div class="announcement-card p-3 mb-3 shadow-sm">
        <div class="d-flex flex-column flex-md-row justify-content-between gap-3">
          <div>
            <div class="fw-semibold mb-1">${item.title}</div>
            <div class="text-muted">${item.content}</div>
          </div>
          <span class="badge bg-primary bg-opacity-10 text-primary align-self-start">公告</span>
        </div>
      </div>
    `).join("");
  };

  const loadDashboard = async () => {
    const [stats, announcements] = await Promise.all([
      api("/api/reports/dashboard"),
      api("/api/announcements"),
    ]);
    renderMetrics(stats.data);
    renderAnnouncements(announcements.data);
  };

  const loadPlans = async () => {
    const res = await api("/api/audit-plans");
    state.cache.plans = res.data;

    renderTable(E.planTable,
      ["任務編號", "年度", "循環", "部門", "稽核員", "狀態", ""],
      res.data,
      plan => `
        <tr>
          <td data-label="任務編號">${plan.task_no}</td>
          <td data-label="年度">${plan.year}</td>
          <td data-label="循環">${plan.cycle_name}</td>
          <td data-label="部門">${plan.department}</td>
          <td data-label="稽核員">${plan.auditor_name || ""}</td>
          <td data-label="狀態">${plan.status}</td>
          <td class="text-end" data-label="操作"><button class="btn btn-outline-primary btn-sm" data-edit-plan="${plan.id}">編輯</button></td>
        </tr>
      `
    );

    renderOptions(E.recordPlanSelect, res.data, plan => ({ value: plan.id, label: `${plan.task_no} ${plan.cycle_name}` }));
    renderPlanFilterList(res.data);
    updateRecordPlanFilterHint(res.data, "");

    if (!state.selectedRecordPlanId && res.data.length) {
      setSelectedAuditPlan(res.data[0].id);
    }

    const selectedPlan = res.data.find(row => String(row.id) === state.selectedRecordPlanId);
    E.recordPlanFilter.value = selectedPlan ? `${selectedPlan.task_no} / ${selectedPlan.year} / ${selectedPlan.cycle_name} / ${selectedPlan.department}` : "";
    setSelectedAuditPlan(state.selectedRecordPlanId);
  };

  const loadQuestions = async () => {
    const res = await api("/api/questions");
    state.cache.questions = res.data;
    renderTable(E.questionTable,
      ["循環", "部門", "題目", "啟用", ""],
      res.data,
      question => `
        <tr>
          <td data-label="循環">${question.cycle_name}</td>
          <td data-label="部門">${question.department}</td>
          <td data-label="題目">${question.question}</td>
          <td data-label="啟用">${question.enabled ? "是" : "否"}</td>
          <td class="text-end" data-label="操作"><button class="btn btn-outline-primary btn-sm" data-edit-question="${question.id}">編輯</button></td>
        </tr>
      `
    );
    renderOptions(E.recordQuestionSelect, res.data, question => ({ value: question.id, label: `${question.cycle_name} ${question.question}` }));
  };

  const loadRecords = async () => {
    if (!state.selectedRecordPlanId) {
      state.cache.records = [];
      E.recordTable.innerHTML = `<tbody><tr><td class="text-secondary">請先建立並選定稽核任務。</td></tr></tbody>`;
      return;
    }
    const res = await api(`/api/audit-records?audit_plan_id=${encodeURIComponent(state.selectedRecordPlanId)}`);
    state.cache.records = res.data;
    renderTable(E.recordTable,
      ["結果", "查核說明", "改善建議", "建立時間", ""],
      res.data,
      record => `
        <tr>
          <td data-label="結果">${record.result_type}</td>
          <td data-label="查核說明">${record.finding || ""}</td>
          <td data-label="改善建議">${record.suggestion || ""}</td>
          <td data-label="建立時間">${new Date(record.created_at).toLocaleString()}</td>
          <td class="text-end" data-label="操作"><button class="btn btn-outline-primary btn-sm" data-edit-record="${record.id}">編輯</button></td>
        </tr>
      `
    );
    renderOptions(E.actionRecordSelect, res.data, record => ({ value: record.id, label: `${record.result_type} ${record.finding || record.id}` }));
  };

  const loadActions = async () => {
    const res = await api("/api/corrective-actions");
    renderTable(E.actionTable,
      ["責任單位", "期限", "狀態", "改善說明"],
      res.data,
      action => `
        <tr>
          <td data-label="責任單位">${action.responsible_department}</td>
          <td data-label="期限">${action.due_date}</td>
          <td data-label="狀態">${action.status}</td>
          <td data-label="改善說明">${action.action_description}</td>
        </tr>
      `
    );
  };

  const loadUsers = async () => {
    if (!state.currentUser || state.currentUser.role !== "Admin") {
      E.userTable.innerHTML = `<tbody><tr><td class="text-secondary">只有 Admin 可以維護用戶。</td></tr></tbody>`;
      return;
    }
    const res = await api("/api/auth/users");
    state.cache.users = res.data;
    renderTable(E.userTable,
      ["帳號", "姓名", "角色", "建立時間", ""],
      res.data,
      user => `
        <tr>
          <td data-label="帳號">${user.account}</td>
          <td data-label="姓名">${user.name}</td>
          <td data-label="角色">${user.role}</td>
          <td data-label="建立時間">${new Date(user.created_at).toLocaleString()}</td>
          <td class="text-end" data-label="操作"><button class="btn btn-outline-primary btn-sm" data-edit-user="${user.id}">編輯</button></td>
        </tr>
      `
    );
  };

  const withFormValidation = (form, callback) => async event => {
    event.preventDefault();
    if (!form.checkValidity()) {
      form.reportValidity();
      return;
    }
    await callback(event);
  };

  const createOrUpdate = async (form, entity, id, endpoint, refreshFn) => {
    const payload = normalizePayload(formData(form));
    const path = id ? `${endpoint}/${id}` : endpoint;
    const method = id ? "PUT" : "POST";
    await api(path, { method, body: JSON.stringify(payload) });
    bootstrap.Modal.getInstance(form.closest(".modal")).hide();
    if (refreshFn) await refreshFn();
  };

  const initEvents = () => {
    E.loginForm.addEventListener("submit", withFormValidation(E.loginForm, async () => {
      const body = new URLSearchParams({ username: E.account.value, password: E.password.value });
      try {
        const res = await api("/api/auth/login", { method: "POST", headers: { "Content-Type": "application/x-www-form-urlencoded" }, body });
        state.token = res.access_token;
        localStorage.setItem("iams_token", state.token);
        await showApp(res.user);
      } catch (err) {
        E.loginError.textContent = err.message;
      }
    }));

    E.planForm.addEventListener("submit", withFormValidation(E.planForm, async () => {
      await createOrUpdate(E.planForm, "plan", state.editing.planId, "/api/audit-plans", async () => {
        state.editing.planId = null;
        E.planForm.reset();
        await loadAll();
      });
    }));

    E.questionForm.addEventListener("submit", withFormValidation(E.questionForm, async () => {
      await createOrUpdate(E.questionForm, "question", state.editing.questionId, "/api/questions", async () => {
        state.editing.questionId = null;
        E.questionForm.reset();
        await loadAll();
      });
    }));

    E.recordForm.addEventListener("submit", withFormValidation(E.recordForm, async () => {
      const payload = normalizePayload(formData(E.recordForm));
      const path = state.editing.recordId ? `/api/audit-records/${state.editing.recordId}` : "/api/audit-records";
      const method = state.editing.recordId ? "PUT" : "POST";
      await api(path, { method, body: JSON.stringify(payload) });
      bootstrap.Modal.getInstance(E.recordForm.closest(".modal")).hide();
      state.editing.recordId = null;
      E.recordForm.reset();
      await loadAll();
    }));

    E.actionForm.addEventListener("submit", withFormValidation(E.actionForm, async () => {
      await api("/api/corrective-actions", { method: "POST", body: JSON.stringify(formData(E.actionForm)) });
      bootstrap.Modal.getInstance(E.actionForm.closest(".modal")).hide();
      E.actionForm.reset();
      await loadAll();
    }));

    E.userForm.addEventListener("submit", withFormValidation(E.userForm, async () => {
      const payload = formData(E.userForm);
      const endpoint = state.editing.userId ? `/api/auth/users/${state.editing.userId}` : "/api/auth/users";
      const method = state.editing.userId ? "PUT" : "POST";
      if (state.editing.userId) {
        delete payload.account;
        if (!payload.password) delete payload.password;
      }
      await api(endpoint, { method, body: JSON.stringify(payload) });
      bootstrap.Modal.getInstance(E.userForm.closest(".modal")).hide();
      state.editing.userId = null;
      E.userForm.reset();
      await loadUsers();
    }));

    E.addPlanBtn.addEventListener("click", () => {
      state.editing.planId = null;
      $("planModalTitle").textContent = "新增年度計畫";
      E.planForm.reset();
      E.planForm.elements.year.value = "2026";
    });

    E.addQuestionBtn.addEventListener("click", () => {
      state.editing.questionId = null;
      $("questionModalTitle").textContent = "新增題目";
      E.questionForm.reset();
      E.questionForm.elements.enabled.value = "true";
    });

    E.addRecordBtn.addEventListener("click", event => {
      if (!state.selectedRecordPlanId) {
        event.preventDefault();
        event.stopPropagation();
        alert("請先選定稽核任務。");
        return;
      }
      state.editing.recordId = null;
      $("recordModalTitle").textContent = "新增查核記錄";
      E.recordForm.reset();
      E.recordForm.elements.audit_plan_id.value = state.selectedRecordPlanId;
    });

    E.addUserBtn.addEventListener("click", () => {
      state.editing.userId = null;
      $("userModalTitle").textContent = "新增用戶";
      E.userForm.reset();
      E.userForm.elements.account.disabled = false;
      E.userForm.elements.password.required = true;
      E.userForm.elements.role.value = "Viewer";
    });

    E.planTable.addEventListener("click", event => {
      const button = event.target.closest("[data-edit-plan]");
      if (!button) return;
      const row = state.cache.plans.find(item => String(item.id) === button.dataset.editPlan);
      if (!row) return;
      state.editing.planId = row.id;
      $("planModalTitle").textContent = "編輯年度計畫";
      fillForm(E.planForm, row);
      showModal("planModal");
    });

    E.questionTable.addEventListener("click", event => {
      const button = event.target.closest("[data-edit-question]");
      if (!button) return;
      const row = state.cache.questions.find(item => String(item.id) === button.dataset.editQuestion);
      if (!row) return;
      state.editing.questionId = row.id;
      $("questionModalTitle").textContent = "編輯題目";
      fillForm(E.questionForm, { ...row, enabled: row.enabled ? "true" : "false" });
      showModal("questionModal");
    });

    E.recordTable.addEventListener("click", event => {
      const button = event.target.closest("[data-edit-record]");
      if (!button) return;
      const row = state.cache.records.find(item => String(item.id) === button.dataset.editRecord);
      if (!row) return;
      state.editing.recordId = row.id;
      $("recordModalTitle").textContent = "編輯查核記錄";
      fillForm(E.recordForm, row);
      E.recordForm.elements.audit_plan_id.value = state.selectedRecordPlanId;
      showModal("recordModal");
    });

    E.userTable.addEventListener("click", event => {
      const button = event.target.closest("[data-edit-user]");
      if (!button) return;
      const row = state.cache.users.find(item => String(item.id) === button.dataset.editUser);
      if (!row) return;
      state.editing.userId = row.id;
      $("userModalTitle").textContent = "編輯用戶";
      fillForm(E.userForm, { ...row, password: "" });
      E.userForm.elements.account.disabled = true;
      E.userForm.elements.password.required = false;
      showModal("userModal");
    });

    const hideRecordPlanSuggestions = () => {
      E.recordPlanFilterSuggestions.classList.add("d-none");
    };

    const showRecordPlanSuggestions = plans => {
      renderPlanFilterSuggestions(plans);
    };

    const getSuggestionItems = () => Array.from(E.recordPlanFilterSuggestions.querySelectorAll(".autocomplete-item"));

    const activateSuggestion = index => {
      const items = getSuggestionItems();
      if (!items.length) return;
      const normalized = ((index % items.length) + items.length) % items.length;
      items.forEach(item => item.classList.remove("active"));
      items[normalized].classList.add("active");
      items[normalized].scrollIntoView({ block: "nearest" });
    };

    const selectMatchingPlanByInput = async value => {
      const exactOption = Array.from(E.recordPlanFilterList.options).find(item => item.value === value);
      const exactPlan = exactOption ? state.cache.plans.find(plan => String(plan.id) === exactOption.dataset.id) : findPlanByExactValue(value);
      if (exactPlan) {
        setSelectedAuditPlan(exactPlan.id);
        E.recordPlanFilter.value = `${exactPlan.task_no} / ${exactPlan.year} / ${exactPlan.cycle_name} / ${exactPlan.department}`;
        await loadRecords();
        return true;
      }
      return false;
    };

    E.recordPlanFilter.addEventListener("input", async event => {
      const value = event.target.value.trim();
      const matches = filterPlans(value, state.cache.plans);
      renderPlanFilterList(matches);
      showRecordPlanSuggestions(matches);
      updateRecordPlanFilterHint(matches, value);
      const exactOption = Array.from(E.recordPlanFilterList.options).find(item => item.value === event.target.value);
      if (exactOption) {
        setSelectedAuditPlan(exactOption.dataset.id);
        await loadRecords();
      }
    });

    E.recordPlanFilter.addEventListener("change", async event => {
      const value = event.target.value.trim();
      if (value) {
        await selectMatchingPlanByInput(value);
      }
    });

    E.recordPlanFilter.addEventListener("focus", event => {
      const value = event.target.value.trim();
      const matches = filterPlans(value, state.cache.plans);
      showRecordPlanSuggestions(matches);
      updateRecordPlanFilterHint(matches, value);
    });

    E.recordPlanFilter.addEventListener("blur", async event => {
      const value = event.target.value.trim();
      if (!value) {
        setSelectedAuditPlan("");
        hideRecordPlanSuggestions();
        updateRecordPlanFilterHint([], "");
        return;
      }
      const exactOption = Array.from(E.recordPlanFilterList.options).find(item => item.value === value);
      if (exactOption) {
        setSelectedAuditPlan(exactOption.dataset.id);
        await loadRecords();
        hideRecordPlanSuggestions();
        return;
      }
      const exactPlan = findPlanByExactValue(value);
      if (exactPlan) {
        event.target.value = `${exactPlan.task_no} / ${exactPlan.year} / ${exactPlan.cycle_name} / ${exactPlan.department}`;
        setSelectedAuditPlan(exactPlan.id);
        await loadRecords();
        hideRecordPlanSuggestions();
        return;
      }
      hideRecordPlanSuggestions();
    });

    E.recordPlanFilter.addEventListener("keydown", async event => {
      const items = getSuggestionItems();
      if (!items.length || E.recordPlanFilterSuggestions.classList.contains("d-none")) return;
      const currentIndex = items.findIndex(item => item.classList.contains("active"));
      if (event.key === "ArrowDown") {
        event.preventDefault();
        activateSuggestion(currentIndex + 1);
      } else if (event.key === "ArrowUp") {
        event.preventDefault();
        activateSuggestion(currentIndex - 1);
      } else if (event.key === "Enter") {
        const active = items.find(item => item.classList.contains("active")) || items[0];
        if (active) {
          event.preventDefault();
          await selectPlanSuggestion(active);
        }
      }
    });

    E.recordPlanFilterSuggestions.addEventListener("click", async event => {
      const option = event.target.closest(".autocomplete-item");
      if (!option) return;
      await selectPlanSuggestion(option);
    });

    document.addEventListener("click", event => {
      if (E.recordPlanFilter.contains(event.target) || E.recordPlanFilterSuggestions.contains(event.target)) return;
      hideRecordPlanSuggestions();
    });

    E.clearRecordPlanFilter.addEventListener("click", async () => {
      E.recordPlanFilter.value = "";
      setSelectedAuditPlan("");
      renderPlanFilterList(state.cache.plans);
      hideRecordPlanSuggestions();
      updateRecordPlanFilterHint([], "");
      await loadRecords();
    });

    const bindImportExport = (button, input, url, prefix, afterLoad) => {
      button.addEventListener("click", async () => {
        if (url.includes("audit-records") && !state.selectedRecordPlanId) {
          alert("請先選定稽核任務。");
          return;
        }
        await exportXlsx(url, prefix);
      });

      input.addEventListener("change", async event => {
        try {
          await importXlsx(event.target, url, async res => {
            alert(`匯入完成：新增 ${res.data.created} 筆，更新 ${res.data.updated} 筆`);
            if (afterLoad) await afterLoad();
          });
        } catch (err) {
          alert(`匯入失敗：${err.message}`);
        }
      });
    };

    bindImportExport(E.exportPlansBtn, E.planImportFile, "/api/audit-plans/export", "audit_plans", async () => { await loadPlans(); await loadDashboard(); });
    E.importPlansBtn.addEventListener("click", () => E.planImportFile.click());
    bindImportExport(E.exportQuestionsBtn, E.questionImportFile, "/api/questions/export", "audit_questions", async () => { await loadQuestions(); await loadDashboard(); });
    E.importQuestionsBtn.addEventListener("click", () => E.questionImportFile.click());
    E.exportRecordsBtn.addEventListener("click", async () => {
      if (!state.selectedRecordPlanId) {
        alert("請先選定稽核任務。");
        return;
      }
      await exportXlsx(`/api/audit-records/export?audit_plan_id=${encodeURIComponent(state.selectedRecordPlanId)}`, "audit_records");
    });
    E.importRecordsBtn.addEventListener("click", () => {
      if (!state.selectedRecordPlanId) {
        alert("請先選定稽核任務。");
        return;
      }
      E.recordImportFile.click();
    });
    E.recordImportFile.addEventListener("change", async event => {
      try {
        await importXlsx(event.target, `/api/audit-records/import?audit_plan_id=${encodeURIComponent(state.selectedRecordPlanId)}`, async res => {
          alert(`匯入完成：新增 ${res.data.created} 筆，更新 ${res.data.updated} 筆`);
          await loadRecords();
          await loadDashboard();
        });
      } catch (err) {
        alert(`匯入失敗：${err.message}`);
      }
    });

    document.querySelectorAll("[data-view]").forEach(link => link.addEventListener("click", event => {
      event.preventDefault();
      document.querySelectorAll("[data-view]").forEach(item => item.classList.remove("active"));
      link.classList.add("active");
      document.querySelectorAll(".view").forEach(view => view.classList.add("d-none"));
      $(link.dataset.view).classList.remove("d-none");
    }));

    E.logoutBtn.addEventListener("click", () => {
      localStorage.removeItem("iams_token");
      window.location.reload();
    });
  };

  const loadAll = async () => {
    await Promise.all([loadDashboard(), loadPlans(), loadQuestions(), loadActions(), loadUsers()]);
    await loadRecords();
  };

  const initialize = async () => {
    initEvents();
    if (state.token) {
      try {
        const user = await api("/api/auth/me");
        await showApp(user);
      } catch (err) {
        state.token = null;
        localStorage.removeItem("iams_token");
        E.loginView.classList.remove("d-none");
      }
    }
  };

  initialize().catch(err => {
    console.error("AUD app initialization failed:", err);
  });
});
