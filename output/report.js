const reportStateKey = "compiler-analysis-report-state";
const detailSections = () => Array.from(document.querySelectorAll("main > details"));
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

window.addEventListener("message", (event) => {
    if (event.data && event.data.type === "compiler-theme") {
        window.CompilerTheme.apply(event.data.mode, false);
    }
});

window.CompilerTheme.init();
restoreReportState();
detailSections().forEach((details) => details.addEventListener("toggle", updateOpenState));
document.querySelector("[data-expand]")?.addEventListener("click", () => setAllDetails(true));
document.querySelector("[data-collapse]")?.addEventListener("click", () => setAllDetails(false));
document.querySelectorAll(".sidebar a").forEach((link) => {
    link.addEventListener("click", () => {
        const title = link.textContent.replace(/^\d+\s*/, "").trim();
        const state = loadReportState();
        state.active = title;
        saveReportState(state);
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
