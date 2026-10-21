/**
 * ============================================================================
 * Loop Compiler — Frontend Application Logic
 * Interactive Code Editor, REST API Client, Token Visualizer, AST & Error Viewer
 * ============================================================================
 */

document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const codeEditor = document.getElementById('codeEditor');
    const lineNumbers = document.getElementById('lineNumbers');
    const lineColIndicator = document.getElementById('lineColIndicator');
    const charCount = document.getElementById('charCount');
    const compileBtn = document.getElementById('compileBtn');
    const clearCodeBtn = document.getElementById('clearCodeBtn');
    const copyCodeBtn = document.getElementById('copyCodeBtn');
    const exampleSelect = document.getElementById('exampleSelect');
    
    // Status & Badges
    const compilerModeBadge = document.getElementById('compilerModeBadge');
    const compilerModeText = document.getElementById('compilerModeText');
    const compilerStatusIndicator = document.getElementById('compilerStatusIndicator');
    const compilerStatusLabel = document.getElementById('compilerStatusLabel');
    const execTimeBadge = document.getElementById('execTimeBadge');
    const demoModeBanner = document.getElementById('demoModeBanner');

    // Tabs
    const tabButtons = document.querySelectorAll('.tab-btn');
    const tabPanels = document.querySelectorAll('.tab-panel');
    const tokensCountBadge = document.getElementById('tokensCountBadge');
    const errorsCountBadge = document.getElementById('errorsCountBadge');

    // Outputs
    const tokensTableBody = document.getElementById('tokensTableBody');
    const tokenFilterInput = document.getElementById('tokenFilterInput');
    const copyTokensBtn = document.getElementById('copyTokensBtn');
    const astOutput = document.getElementById('astOutput');
    const copyAstBtn = document.getElementById('copyAstBtn');
    const diagnosticsContainer = document.getElementById('diagnosticsContainer');
    const rawStdout = document.getElementById('rawStdout');
    const rawStderr = document.getElementById('rawStderr');
    const logMetaBar = document.getElementById('logMetaBar');
    const copyLogsBtn = document.getElementById('copyLogsBtn');

    // Theme & Modal
    const themeToggleBtn = document.getElementById('themeToggleBtn');
    const moonIcon = document.getElementById('moonIcon');
    const sunIcon = document.getElementById('sunIcon');
    const infoModalBtn = document.getElementById('infoModalBtn');
    const infoModal = document.getElementById('infoModal');
    const closeModalBtn = document.getElementById('closeModalBtn');
    const modalOkBtn = document.getElementById('modalOkBtn');
    const toastContainer = document.getElementById('toastContainer');

    // State
    let currentTokens = [];
    let currentCompilationResult = null;
    let examplesCache = {};

    /* ============================================================================
     * 1. Theme Management (Dark / Light)
     * ============================================================================ */
    const savedTheme = localStorage.getItem('loop_compiler_theme') || 'dark';
    setTheme(savedTheme);

    function setTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem('loop_compiler_theme', theme);
        if (theme === 'light') {
            moonIcon.classList.add('hidden');
            sunIcon.classList.remove('hidden');
        } else {
            moonIcon.classList.remove('hidden');
            sunIcon.classList.add('hidden');
        }
    }

    themeToggleBtn.addEventListener('click', () => {
        const current = document.documentElement.getAttribute('data-theme') || 'dark';
        setTheme(current === 'dark' ? 'light' : 'dark');
    });

    /* ============================================================================
     * 2. Modal Management
     * ============================================================================ */
    function openModal() {
        infoModal.classList.remove('hidden');
    }
    function closeModal() {
        infoModal.classList.add('hidden');
    }

    infoModalBtn.addEventListener('click', openModal);
    closeModalBtn.addEventListener('click', closeModal);
    modalOkBtn.addEventListener('click', closeModal);
    infoModal.addEventListener('click', (e) => {
        if (e.target === infoModal) closeModal();
    });
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && !infoModal.classList.contains('hidden')) {
            closeModal();
        }
    });

    /* ============================================================================
     * 3. Toast Notifications
     * ============================================================================ */
    function showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        
        let iconSvg = '';
        if (type === 'success') {
            iconSvg = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"></polyline></svg>`;
        } else if (type === 'error') {
            iconSvg = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line></svg>`;
        } else {
            iconSvg = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>`;
        }

        toast.innerHTML = `${iconSvg}<span>${escapeHtml(message)}</span>`;
        toastContainer.appendChild(toast);

        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateY(10px)';
            toast.style.transition = 'all 0.25s ease';
            setTimeout(() => toast.remove(), 250);
        }, 3200);
    }

    /* ============================================================================
     * 4. Editor Line Numbers, Sync & Cursor Position
     * ============================================================================ */
    function updateLineNumbers() {
        const text = codeEditor.value;
        const lineCount = (text.split('\n')).length;
        const numbers = Array.from({ length: lineCount }, (_, idx) => idx + 1).join('\n');
        lineNumbers.textContent = numbers;

        charCount.textContent = `${lineCount} line${lineCount === 1 ? '' : 's'}, ${text.length} chars`;
    }

    function updateCursorPosition() {
        const text = codeEditor.value;
        const selStart = codeEditor.selectionStart;
        const linesUpToCursor = text.substring(0, selStart).split('\n');
        const line = linesUpToCursor.length;
        const col = linesUpToCursor[linesUpToCursor.length - 1].length + 1;
        lineColIndicator.textContent = `Ln ${line}, Col ${col}`;
    }

    codeEditor.addEventListener('input', () => {
        updateLineNumbers();
        updateCursorPosition();
    });

    codeEditor.addEventListener('scroll', () => {
        lineNumbers.scrollTop = codeEditor.scrollTop;
    });

    codeEditor.addEventListener('keyup', updateCursorPosition);
    codeEditor.addEventListener('click', updateCursorPosition);

    // Tab key support & auto closing pairs
    codeEditor.addEventListener('keydown', (e) => {
        // Tab key: Insert 4 spaces
        if (e.key === 'Tab') {
            e.preventDefault();
            const start = codeEditor.selectionStart;
            const end = codeEditor.selectionEnd;
            codeEditor.value = codeEditor.value.substring(0, start) + '    ' + codeEditor.value.substring(end);
            codeEditor.selectionStart = codeEditor.selectionEnd = start + 4;
            updateLineNumbers();
            updateCursorPosition();
        }

        // Ctrl + Enter to compile
        if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
            e.preventDefault();
            triggerCompile();
        }

        // Ctrl + L to clear
        if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'l') {
            e.preventDefault();
            clearEditor();
        }
    });

    function clearEditor() {
        codeEditor.value = '';
        updateLineNumbers();
        updateCursorPosition();
        if (exampleSelect) exampleSelect.value = '';

        // Reset displayed results appropriately
        currentTokens = [];
        currentCompilationResult = null;
        tokensCountBadge.textContent = '0';
        errorsCountBadge.textContent = '0';
        setCompilationStatus('ready', 'Ready');
        execTimeBadge.classList.add('hidden');

        tokensTableBody.innerHTML = `
            <tr class="empty-row">
                <td colspan="5">
                    <div class="empty-state">
                        <p>Click <strong>Compile</strong> to inspect lexical tokens.</p>
                    </div>
                </td>
            </tr>
        `;
        astOutput.innerHTML = `<code>Click "Compile" to generate the Abstract Syntax Tree.</code>`;
        diagnosticsContainer.innerHTML = `
            <div class="empty-state">
                <p>Click <strong>Compile</strong> to perform syntax and semantic validation.</p>
            </div>
        `;
        rawStdout.innerHTML = `<code>(No compilation output yet)</code>`;
        rawStderr.innerHTML = `<code>(No error stream output)</code>`;
        logMetaBar.innerHTML = `
            <span>Exit Code: —</span>
            <span>Time: —</span>
        `;

        codeEditor.focus();
        showToast('Editor and outputs cleared', 'info');
    }

    clearCodeBtn.addEventListener('click', clearEditor);

    copyCodeBtn.addEventListener('click', () => {
        if (!codeEditor.value.trim()) {
            showToast('No code to copy', 'info');
            return;
        }
        navigator.clipboard.writeText(codeEditor.value)
            .then(() => showToast('C source code copied to clipboard!', 'success'))
            .catch(() => showToast('Failed to copy to clipboard', 'error'));
    });

    /* ============================================================================
     * 5. Example Loader
     * ============================================================================ */
    async function loadExamplesList() {
        try {
            const resp = await fetch('/api/examples');
            if (!resp.ok) return;
            const data = await resp.json();
            if (data.examples && Array.isArray(data.examples)) {
                data.examples.forEach(ex => {
                    examplesCache[ex.id] = ex.code;
                });
            }
        } catch (err) {
            console.warn('Could not preload examples:', err);
        }
    }

    exampleSelect.addEventListener('change', async (e) => {
        const exampleId = e.target.value;
        if (!exampleId) return;

        if (examplesCache[exampleId]) {
            codeEditor.value = examplesCache[exampleId];
            updateLineNumbers();
            updateCursorPosition();
            showToast(`Loaded example: ${e.target.options[e.target.selectedIndex].text}`, 'success');
        } else {
            try {
                const resp = await fetch(`/api/examples/${exampleId}`);
                if (!resp.ok) throw new Error('Failed to load example');
                const data = await resp.json();
                examplesCache[exampleId] = data.code;
                codeEditor.value = data.code;
                updateLineNumbers();
                updateCursorPosition();
                showToast(`Loaded example: ${data.title}`, 'success');
            } catch (err) {
                showToast(`Error loading example: ${err.message}`, 'error');
            }
        }
    });

    /* ============================================================================
     * 6. Compiler Status Check
     * ============================================================================ */
    async function checkCompilerStatus() {
        try {
            const resp = await fetch('/api/status');
            if (!resp.ok) throw new Error('Status endpoint unavailable');
            const status = await resp.json();

            compilerModeBadge.className = 'mode-badge';
            if (status.mode === 'real') {
                compilerModeBadge.classList.add('mode-real');
                compilerModeText.textContent = 'Real C Compiler';
                compilerModeBadge.title = `Connected to native binary: ${status.compiler_binary || 'compiler.exe'}`;
                demoModeBanner.classList.add('hidden');
            } else {
                compilerModeBadge.classList.add('mode-demo');
                compilerModeText.textContent = 'Demo Mode (Simulated)';
                compilerModeBadge.title = 'Real compiler binary not found. Showing simulated analysis.';
                demoModeBanner.classList.remove('hidden');
            }
        } catch (err) {
            compilerModeBadge.className = 'mode-badge mode-demo';
            compilerModeText.textContent = 'Demo Mode';
            demoModeBanner.classList.remove('hidden');
        }
    }

    /* ============================================================================
     * 7. Tab Switching
     * ============================================================================ */
    tabButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const targetId = btn.getAttribute('data-tab');
            switchTab(targetId);
        });
    });

    function switchTab(tabId) {
        tabButtons.forEach(btn => {
            const isMatch = btn.getAttribute('data-tab') === tabId;
            btn.classList.toggle('active', isMatch);
            btn.setAttribute('aria-selected', isMatch ? 'true' : 'false');
        });

        tabPanels.forEach(panel => {
            panel.classList.toggle('active', panel.id === tabId);
        });
    }

    /* ============================================================================
     * 8. Compilation Action
     * ============================================================================ */
    compileBtn.addEventListener('click', triggerCompile);

    async function triggerCompile() {
        const sourceCode = codeEditor.value;

        // Set Compiling UI state
        setCompilingState(true);

        try {
            const startTime = performance.now();
            const response = await fetch('/compile', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ source_code: sourceCode }),
            });

            const data = await response.json();
            const clientElapsed = Math.round(performance.now() - startTime);

            currentCompilationResult = data;
            renderCompilationResults(data, clientElapsed);

        } catch (err) {
            console.error('Compilation error:', err);
            setCompilationStatus('failed', 'Network Error');
            showToast(`Backend connection failed: ${err.message}`, 'error');
        } finally {
            setCompilingState(false);
        }
    }

    function setCompilingState(isCompiling) {
        if (isCompiling) {
            compileBtn.disabled = true;
            compileBtn.classList.add('btn-loading');
            setCompilationStatus('compiling', 'Compiling...');
        } else {
            compileBtn.disabled = false;
            compileBtn.classList.remove('btn-loading');
        }
    }

    function setCompilationStatus(status, label, timeMs = null) {
        compilerStatusIndicator.className = `status-indicator status-${status}`;
        compilerStatusLabel.textContent = label;
        
        if (timeMs !== null) {
            execTimeBadge.textContent = `${timeMs} ms`;
            execTimeBadge.classList.remove('hidden');
        } else {
            execTimeBadge.classList.add('hidden');
        }
    }

    /* ============================================================================
     * 9. Render Compilation Output
     * ============================================================================ */
    function renderCompilationResults(data, clientElapsed) {
        const timeToDisplay = data.execution_time_ms || clientElapsed;

        // 1. Update Compiler Mode Badge & Banner
        if (data.mode === 'real') {
            compilerModeBadge.className = 'mode-badge mode-real';
            compilerModeText.textContent = 'Real C Compiler';
            demoModeBanner.classList.add('hidden');
        } else if (data.mode === 'demo') {
            compilerModeBadge.className = 'mode-badge mode-demo';
            compilerModeText.textContent = 'Demo Mode (Simulated)';
            demoModeBanner.classList.remove('hidden');
        }

        // 2. Status Label
        if (data.success) {
            setCompilationStatus('success', 'Success', timeToDisplay);
            showToast('Compilation succeeded! Valid loop syntax.', 'success');
        } else {
            const errCount = (data.errors || []).length;
            setCompilationStatus('failed', `Failed (${errCount} error${errCount === 1 ? '' : 's'})`, timeToDisplay);
            showToast(`Compilation failed with ${errCount} error(s).`, 'error');
        }

        // 3. Render Tokens
        currentTokens = data.tokens || [];
        tokensCountBadge.textContent = currentTokens.length;
        renderTokensTable(currentTokens);

        // 4. Render AST
        renderAst(data.ast, data.success);

        // 5. Render Diagnostics / Errors
        const errors = data.errors || [];
        const warnings = data.warnings || [];
        errorsCountBadge.textContent = errors.length;
        renderDiagnostics(errors, warnings, data.success);

        // If errors occurred, auto-switch to Diagnostics tab so user sees them immediately!
        if (errors.length > 0) {
            switchTab('diagnosticsTab');
        }

        // 6. Render Raw Logs
        renderLogs(data);
    }

    /* ============================================================================
     * 10. Tokens Table Rendering & Filter
     * ============================================================================ */
    function renderTokensTable(tokens) {
        tokensTableBody.innerHTML = '';

        if (!tokens || tokens.length === 0) {
            tokensTableBody.innerHTML = `
                <tr class="empty-row">
                    <td colspan="5">
                        <div class="empty-state">
                            <p>No tokens were produced.</p>
                        </div>
                    </td>
                </tr>
            `;
            return;
        }

        const fragment = document.createDocumentFragment();

        tokens.forEach((t, idx) => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td class="token-index">${idx + 1}</td>
                <td><span class="token-badge ${escapeHtml(t.type)}">${escapeHtml(t.type)}</span></td>
                <td class="token-lexeme"><code>${escapeHtml(t.lexeme)}</code></td>
                <td>${t.line || 1}</td>
                <td>${t.column || 1}</td>
            `;
            fragment.appendChild(tr);
        });

        tokensTableBody.appendChild(fragment);
    }

    tokenFilterInput.addEventListener('input', (e) => {
        const query = e.target.value.toLowerCase().trim();
        if (!query) {
            renderTokensTable(currentTokens);
            return;
        }

        const filtered = currentTokens.filter(t => 
            (t.type && t.type.toLowerCase().includes(query)) ||
            (t.lexeme && t.lexeme.toLowerCase().includes(query))
        );
        renderTokensTable(filtered);
    });

    copyTokensBtn.addEventListener('click', () => {
        if (!currentTokens.length) {
            showToast('No tokens to copy', 'info');
            return;
        }
        navigator.clipboard.writeText(JSON.stringify(currentTokens, null, 2))
            .then(() => showToast('Tokens JSON copied to clipboard!', 'success'))
            .catch(() => showToast('Failed to copy tokens', 'error'));
    });

    /* ============================================================================
     * 11. AST Rendering
     * ============================================================================ */
    function renderAst(astString, isSuccess) {
        if (!astString || !astString.trim()) {
            if (isSuccess) {
                astOutput.innerHTML = `<code>(Empty AST or no statements parsed)</code>`;
            } else {
                astOutput.innerHTML = `<code style="color: var(--color-error-light)">AST generation failed due to syntax errors in source code.</code>`;
            }
            return;
        }

        astOutput.innerHTML = `<code>${escapeHtml(astString)}</code>`;
    }

    copyAstBtn.addEventListener('click', () => {
        const text = astOutput.innerText;
        if (!text || text.includes('Click "Compile"')) {
            showToast('No AST to copy', 'info');
            return;
        }
        navigator.clipboard.writeText(text)
            .then(() => showToast('AST output copied to clipboard!', 'success'))
            .catch(() => showToast('Failed to copy AST', 'error'));
    });

    /* ============================================================================
     * 12. Diagnostics / Errors Rendering & Editor Jumping
     * ============================================================================ */
    function renderDiagnostics(errors, warnings, isSuccess) {
        diagnosticsContainer.innerHTML = '';

        if (isSuccess && errors.length === 0 && warnings.length === 0) {
            diagnosticsContainer.innerHTML = `
                <div class="diagnostic-card success-banner">
                    <div class="diag-icon">
                        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                            <polyline points="22 4 12 14.01 9 11.01"></polyline>
                        </svg>
                    </div>
                    <div class="diag-body">
                        <div class="diag-header">
                            <span class="diag-type" style="color: var(--color-success-light);">Compilation Successful</span>
                        </div>
                        <div class="diag-message">
                            Zero syntax or lexical errors detected! All loop structures and statements are syntactically valid.
                        </div>
                    </div>
                </div>
            `;
            return;
        }

        // Render Errors
        errors.forEach(err => {
            const card = document.createElement('div');
            card.className = 'diagnostic-card error';
            card.innerHTML = `
                <div class="diag-icon">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <circle cx="12" cy="12" r="10"></circle>
                        <line x1="15" y1="9" x2="9" y2="15"></line>
                        <line x1="9" y1="9" x2="15" y2="15"></line>
                    </svg>
                </div>
                <div class="diag-body">
                    <div class="diag-header">
                        <span class="diag-type">${escapeHtml(err.type || 'SyntaxError')}</span>
                        <span class="diag-location" title="Click to jump to line in editor" data-line="${err.line || 1}">Line ${err.line || 1}, Col ${err.column || 1} &rarr; Jump</span>
                    </div>
                    <div class="diag-message">${escapeHtml(err.message || 'Unknown syntax error')}</div>
                </div>
            `;
            diagnosticsContainer.appendChild(card);
        });

        // Render Warnings
        warnings.forEach(warn => {
            const card = document.createElement('div');
            card.className = 'diagnostic-card warning';
            card.innerHTML = `
                <div class="diag-icon">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path>
                        <line x1="12" y1="9" x2="12" y2="13"></line>
                        <line x1="12" y1="17" x2="12.01" y2="17"></line>
                    </svg>
                </div>
                <div class="diag-body">
                    <div class="diag-header">
                        <span class="diag-type">${escapeHtml(warn.type || 'SemanticWarning')}</span>
                        <span class="diag-location" title="Click to jump to line in editor" data-line="${warn.line || 1}">Line ${warn.line || 1}, Col ${warn.column || 1} &rarr; Jump</span>
                    </div>
                    <div class="diag-message">${escapeHtml(warn.message)}</div>
                </div>
            `;
            diagnosticsContainer.appendChild(card);
        });

        // Add Click-to-Jump functionality
        diagnosticsContainer.querySelectorAll('.diag-location').forEach(loc => {
            loc.addEventListener('click', () => {
                const lineNum = parseInt(loc.getAttribute('data-line'), 10);
                if (lineNum && !isNaN(lineNum)) {
                    jumpToLine(lineNum);
                }
            });
        });
    }

    function jumpToLine(lineNumber) {
        const lines = codeEditor.value.split('\n');
        let charIndex = 0;
        for (let i = 0; i < lineNumber - 1 && i < lines.length; i++) {
            charIndex += lines[i].length + 1; // +1 for '\n'
        }

        codeEditor.focus();
        codeEditor.setSelectionRange(charIndex, charIndex + (lines[lineNumber - 1] ? lines[lineNumber - 1].length : 0));
        
        // Approximate scroll
        const lineHeight = 22; // px approx
        codeEditor.scrollTop = Math.max(0, (lineNumber - 3) * lineHeight);
        updateCursorPosition();
        showToast(`Jumped to line ${lineNumber}`, 'info');
    }

    /* ============================================================================
     * 13. Raw Logs Rendering
     * ============================================================================ */
    function renderLogs(data) {
        rawStdout.innerHTML = `<code>${escapeHtml(data.raw_stdout || '(No stdout produced)')}</code>`;
        rawStderr.innerHTML = `<code>${escapeHtml(data.raw_stderr || '(No stderr output)')}</code>`;

        logMetaBar.innerHTML = `
            <span><strong>Mode:</strong> ${escapeHtml(data.mode ? data.mode.toUpperCase() : 'UNKNOWN')}</span>
            <span><strong>Exit Code:</strong> ${data.exit_code !== undefined ? data.exit_code : '—'}</span>
            <span><strong>Time:</strong> ${data.execution_time_ms !== undefined ? data.execution_time_ms + ' ms' : '—'}</span>
            ${data.compiler_binary ? `<span><strong>Binary:</strong> <code>${escapeHtml(data.compiler_binary)}</code></span>` : ''}
        `;
    }

    copyLogsBtn.addEventListener('click', () => {
        if (!currentCompilationResult) {
            showToast('No compiler logs available', 'info');
            return;
        }
        const text = `=== STDOUT ===\n${currentCompilationResult.raw_stdout || ''}\n\n=== STDERR ===\n${currentCompilationResult.raw_stderr || ''}\n\nExit Code: ${currentCompilationResult.exit_code}\nExecution Time: ${currentCompilationResult.execution_time_ms} ms`;
        navigator.clipboard.writeText(text)
            .then(() => showToast('Compiler logs copied to clipboard!', 'success'))
            .catch(() => showToast('Failed to copy logs', 'error'));
    });

    /* ============================================================================
     * 14. Helper Functions
     * ============================================================================ */
    function escapeHtml(str) {
        if (!str) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    /* ============================================================================
     * 15. Initial Load & Setup
     * ============================================================================ */
    async function init() {
        await checkCompilerStatus();
        await loadExamplesList();

        // Load default while_loop example if editor is empty
        if (!codeEditor.value.trim()) {
            if (examplesCache['while_loop']) {
                codeEditor.value = examplesCache['while_loop'];
                exampleSelect.value = 'while_loop';
            } else {
                codeEditor.value = `#include <stdio.h>\n\nint main() {\n    int i = 0;\n\n    while (i < 5) {\n        printf("%d\\n", i);\n        i++;\n    }\n\n    return 0;\n}`;
            }
        }

        updateLineNumbers();
        updateCursorPosition();
    }

    init();
});
