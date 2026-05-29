const datasetKey = "compiler-analysis-dataset";
const datasetSelect = document.querySelector("#datasetSelect");
const datasetFrame = document.querySelector("#datasetFrame");

function postThemeToFrame(mode) {
    if (datasetFrame.contentWindow) {
        datasetFrame.contentWindow.postMessage({type: "compiler-theme", mode}, "*");
    }
}

function formatTime(value) {
    if (!value) return "not tracked";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return date.toLocaleString(undefined, {dateStyle: "medium", timeStyle: "medium"});
}

function setText(id, value) {
    document.querySelector(id).textContent = value ?? "-";
}

function saveCurrentFrameState() {
    try {
        datasetFrame.contentWindow?.CompilerReportState?.save();
    } catch {
        return;
    }
}

function selectDataset(index) {
    const dataset = DATASETS[index];
    if (!dataset) return;
    saveCurrentFrameState();
    datasetSelect.value = String(index);
    datasetFrame.src = dataset.href;
    setText("#metaName", dataset.name || dataset.label);
    setText("#metaDumped", formatTime(dataset.dumped_at));
    setText("#metaProcessed", formatTime(dataset.processed_at));
    setText("#metaSource", dataset.source || "not tracked");
    setText("#metaBlocks", dataset.blocks);
    setText("#metaRegions", dataset.region_steps);
    localStorage.setItem(datasetKey, dataset.id);
}

DATASETS.forEach((dataset, index) => {
    const option = document.createElement("option");
    option.value = String(index);
    option.textContent = dataset.label;
    datasetSelect.append(option);
});

datasetSelect.addEventListener("change", () => selectDataset(Number(datasetSelect.value)));
datasetFrame.addEventListener("load", () => postThemeToFrame(window.CompilerTheme.current()));
window.CompilerTheme.init(postThemeToFrame);
const savedDataset = localStorage.getItem(datasetKey);
const startIndex = Math.max(0, DATASETS.findIndex((dataset) => dataset.id === savedDataset));
if (DATASETS.length) selectDataset(startIndex);
