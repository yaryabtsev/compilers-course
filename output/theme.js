window.CompilerTheme = (() => {
    const key = "compiler-analysis-theme";
    const media = window.matchMedia("(prefers-color-scheme: dark)");

    function resolve(mode) {
        return mode === "dark" || (mode === "system" && media.matches) ? "dark" : "light";
    }

    function updateButtons(mode) {
        document.querySelectorAll("[data-theme-choice]").forEach((button) => {
            button.setAttribute("aria-pressed", String(button.dataset.themeChoice === mode));
        });
    }

    function apply(mode, store = true) {
        const selected = mode || "system";
        document.documentElement.dataset.theme = resolve(selected);
        document.documentElement.dataset.themeMode = selected;
        updateButtons(selected);
        if (store) localStorage.setItem(key, selected);
        return selected;
    }

    function current() {
        return localStorage.getItem(key) || "system";
    }

    function init(onChange) {
        document.querySelectorAll("[data-theme-choice]").forEach((button) => {
            button.addEventListener("click", () => {
                const selected = apply(button.dataset.themeChoice);
                if (onChange) onChange(selected);
            });
        });
        media.addEventListener("change", () => {
            if (current() === "system") {
                const selected = apply("system", false);
                if (onChange) onChange(selected);
            }
        });
        return apply(current(), false);
    }

    return {apply, current, init};
})();
