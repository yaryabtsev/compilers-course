const reportStateKey = "compiler-analysis-report-state";
const detailSections = () => Array.from(document.querySelectorAll("main > details"));
const roadmapNodes = () => Array.from(document.querySelectorAll(".roadmap-node"));
let restoring = false;

function sectionTitle(details) {
    return details.querySelector("summary h2 .section-title")?.textContent.trim()
        || details.querySelector("summary h2")?.textContent.trim()
        || "";
}

function loadReportState() {
    try {
        return JSON.parse(localStorage.getItem(reportStateKey) || "{}");
    } catch {
        return {};
    }
}

function saveReportState(state) {
    localStorage.setItem(reportStateKey, JSON.stringify(state));
}

function updateOpenState() {
    if (restoring) return;
    const state = loadReportState();
    state.open = state.open || {};
    detailSections().forEach((details) => {
        const title = sectionTitle(details);
        if (title) state.open[title] = details.open;
    });
    saveReportState(state);
}

function saveActiveSection() {
    if (restoring) return;
    const candidates = detailSections()
        .map((details) => ({details, top: Math.abs(details.getBoundingClientRect().top)}))
        .sort((left, right) => left.top - right.top);
    const active = candidates[0]?.details;
    const title = active ? sectionTitle(active) : "";
    if (!title) return;
    const state = loadReportState();
    state.active = title;
    saveReportState(state);
}

function restoreReportState() {
    const state = loadReportState();
    restoring = true;
    detailSections().forEach((details) => {
        const title = sectionTitle(details);
        if (title && state.open && Object.prototype.hasOwnProperty.call(state.open, title)) {
            details.open = state.open[title];
        }
    });
    restoring = false;
    const active = state.active ? detailSections().find((details) => sectionTitle(details) === state.active) : null;
    if (active) {
        window.requestAnimationFrame(() => active.scrollIntoView({block: "start"}));
    }
}

function setAllDetails(open) {
    detailSections().forEach((details) => {
        details.open = open;
    });
    updateOpenState();
}

function statusLabel(status) {
    return {
        "available": "available",
        "empty": "empty",
        "warning": "warning",
        "not-applicable": "n/a"
    }[status] || status;
}

function sectionHasSubstantialContent(details) {
    return Boolean(
        details.querySelector("tbody tr")
        || details.querySelector("img")
        || details.querySelector(".mir-lines li")
        || details.querySelector(".value-card")
        || details.querySelector(".placeholder-note")
    );
}

function classifySection(details) {
    if (!details) return "not-applicable";
    const title = sectionTitle(details).toLowerCase();
    const bodyText = Array.from(details.children)
        .filter((child) => child.tagName.toLowerCase() !== "summary")
        .map((child) => child.textContent || "")
        .join(" ")
        .replace(/\s+/g, " ")
        .trim()
        .toLowerCase();

    if (title.includes("scope stubs") || /\b(out of scope|not applicable|unsupported papers)\b/.test(bodyText)) {
        return "not-applicable";
    }
    if (
        details.querySelector("td.false, .placeholder-note")
        || /\b(warning|missing|truncated|unsupported arity|failed|cyclic|cycle cut)\b/.test(bodyText)
    ) {
        return "warning";
    }
    if (!sectionHasSubstantialContent(details) || /\b(no rows|no .* detected|no .* candidates)\b/.test(bodyText)) {
        return "empty";
    }
    return "available";
}

function updateRoadmapStatuses() {
    roadmapNodes().forEach((node) => {
        const href = node.getAttribute("href") || "";
        const target = href.startsWith("#") ? document.getElementById(href.slice(1)) : null;
        const status = classifySection(target);
        node.dataset.status = status;
        node.classList.toggle("is-disabled", status === "not-applicable" && !target);
        const badge = node.querySelector(".roadmap-status");
        if (badge) badge.textContent = statusLabel(status);
    });
}

function rememberSection(details) {
    const title = details ? sectionTitle(details) : "";
    if (!title) return;
    const state = loadReportState();
    state.active = title;
    saveReportState(state);
}

function openLinkedSection(link) {
    const href = link.getAttribute("href") || "";
    if (!href.startsWith("#title-")) return;
    const target = document.getElementById(href.slice(1));
    if (!target) return;
    target.open = true;
    rememberSection(target);
}

window.addEventListener("message", (event) => {
    if (event.data && event.data.type === "compiler-theme") {
        window.CompilerTheme.apply(event.data.mode, false);
    }
});

window.CompilerTheme.init();
restoreReportState();
updateRoadmapStatuses();
detailSections().forEach((details) => details.addEventListener("toggle", updateOpenState));
document.querySelector("[data-expand]")?.addEventListener("click", () => setAllDetails(true));
document.querySelector("[data-collapse]")?.addEventListener("click", () => setAllDetails(false));
document.querySelectorAll('a[href^="#title-"]').forEach((link) => {
    link.addEventListener("click", () => {
        openLinkedSection(link);
    });
});
window.addEventListener("scroll", () => window.requestAnimationFrame(saveActiveSection), {passive: true});
window.CompilerReportState = {
    save() {
        updateOpenState();
        saveActiveSection();
    }
};
window.addEventListener("beforeunload", () => {
    updateOpenState();
    saveActiveSection();
});
