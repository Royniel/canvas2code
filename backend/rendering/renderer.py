import asyncio
import os
import re
import tempfile
from pathlib import Path
from typing import Optional

from playwright.async_api import Browser

DEFAULT_VIEWPORT = {"width": 1280, "height": 800}


HTML_HARNESS = """<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<script src="https://cdn.tailwindcss.com"></script>
</head>
<body>
__BODY__
</body>
</html>
"""

REACT_HARNESS = """<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<script src="https://unpkg.com/react@18/umd/react.production.min.js"></script>
<script src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js"></script>
<script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>
<script src="https://cdn.tailwindcss.com"></script>
</head>
<body>
<div id="root"></div>
<script type="text/babel" data-presets="react,typescript">
__CODE__

(function() {
  const rootEl = document.getElementById('root');
  const root = ReactDOM.createRoot(rootEl);
  try {
    root.render(React.createElement(__COMPONENT_NAME__));
  } catch (e) {
    rootEl.innerText = 'Render error: ' + (e && e.message || e);
  }
})();
</script>
</body>
</html>
"""

VUE_HARNESS = """<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<script src="https://unpkg.com/vue@3.5.13/dist/vue.global.prod.js"></script>
<script src="https://cdn.jsdelivr.net/npm/vue3-sfc-loader@0.9.5/dist/vue3-sfc-loader.js"></script>
<script src="https://cdn.tailwindcss.com"></script>
</head>
<body>
<div id="app"></div>
<script id="sfc-source" type="text/plain">__SFC_SOURCE__</script>
<script>
(function() {
  const sfcSource = document.getElementById('sfc-source').textContent;
  const { loadModule } = window['vue3-sfc-loader'];
  const options = {
    moduleCache: { vue: Vue },
    getFile: () => Promise.resolve(sfcSource),
    addStyle: (styleText) => {
      const style = document.createElement('style');
      style.textContent = styleText;
      document.head.appendChild(style);
    },
  };
  const app = Vue.createApp({
    components: {
      AppComp: Vue.defineAsyncComponent(() => loadModule('App.vue', options)),
    },
    template: '<AppComp />',
  });
  try {
    app.mount('#app');
  } catch (e) {
    document.getElementById('app').innerText = 'Render error: ' + (e && e.message || e);
  }
})();
</script>
</body>
</html>
"""


def _escape_script_content(code: str) -> str:
    return code.replace("</script>", r"<\/script>")


def _strip_react_module_syntax(code: str) -> str:
    code = re.sub(r"^\s*import\s+.*?;\s*$", "", code, flags=re.MULTILINE)
    code = re.sub(
        r"^\s*export\s+default\s+\w+\s*;?\s*$", "", code, flags=re.MULTILINE
    )
    code = re.sub(r"\bexport\s+default\s+", "", code)
    return code


def _find_react_component_name(code: str) -> str:
    for pattern in (
        r"const\s+([A-Z]\w*)\s*[=:]",
        r"function\s+([A-Z]\w*)\s*\(",
        r"class\s+([A-Z]\w*)",
    ):
        m = re.search(pattern, code)
        if m:
            return m.group(1)
    return "App"


def _build_html_harness(code: str) -> str:
    snippet = code[:200].lower()
    if "<!doctype" in snippet or "<html" in snippet:
        return code
    return HTML_HARNESS.replace("__BODY__", code)


def _build_react_harness(code: str) -> str:
    cleaned = _strip_react_module_syntax(code)
    name = _find_react_component_name(cleaned)
    safe = _escape_script_content(cleaned)
    return REACT_HARNESS.replace("__CODE__", safe).replace(
        "__COMPONENT_NAME__", name
    )


def _build_vue_harness(code: str) -> str:
    safe = _escape_script_content(code)
    return VUE_HARNESS.replace("__SFC_SOURCE__", safe)


def _build_harness(code: str, framework: str) -> str:
    if framework == "HTML/CSS":
        return _build_html_harness(code)
    if framework == "React":
        return _build_react_harness(code)
    if framework == "Vue 3":
        return _build_vue_harness(code)
    raise ValueError(f"Unsupported framework: {framework}")


async def render_code_to_screenshot(
    code: str,
    framework: str,
    browser: Browser,
    viewport: Optional[dict] = None,
    stability_delay: float = 0.8,
    navigation_timeout_ms: int = 15000,
) -> bytes:
    viewport = viewport or DEFAULT_VIEWPORT
    html = _build_harness(code, framework)

    fd, temp_path = tempfile.mkstemp(suffix=".html")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(html)
        file_url = Path(temp_path).as_uri()

        context = await browser.new_context(viewport=viewport)
        try:
            page = await context.new_page()
            await page.goto(
                file_url, wait_until="networkidle", timeout=navigation_timeout_ms
            )
            await asyncio.sleep(stability_delay)
            return await page.screenshot(type="png", full_page=False)
        finally:
            await context.close()
    finally:
        try:
            os.unlink(temp_path)
        except OSError:
            pass
