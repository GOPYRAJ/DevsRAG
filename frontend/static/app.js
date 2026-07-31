/**
 * DevsRAG - Frontend Application Logic
 */

document.addEventListener('DOMContentLoaded', () => {
    // State Management
    const state = {
        documents: [],
        selectedDocId: null, // null means "All Documents" (Collection Mode)
        filter: 'all',
        uploading: false,
        chatHistory: [], // Rolling array of last 5 turns: { role: 'user'|'assistant', content: string }
        activeCitations: [], // Current active message citations for drawer navigation
        currentCitationIdx: 0
    };

    // DOM Elements
    const dropzone = document.getElementById('dropzone');
    const fileInput = document.getElementById('file-input');
    const docListContainer = document.getElementById('document-list');
    const docCountBadge = document.getElementById('doc-count');
    const filterButtons = document.querySelectorAll('.filter-tab');
    const scopePill = document.getElementById('active-scope-pill');
    const clearChatBtn = document.getElementById('clear-chat-btn');
    const exportChatBtn = document.getElementById('export-chat-btn');
    const toastContainer = document.getElementById('toast-container');

    // Architecture Modal Elements
    const openArchBtn = document.getElementById('open-arch-btn');
    const closeArchBtn = document.getElementById('close-arch-btn');
    const dismissArchBtn = document.getElementById('dismiss-arch-btn');
    const archModal = document.getElementById('arch-modal');
    
    const chatContainer = document.getElementById('chat-container');
    const queryForm = document.getElementById('query-form');
    const queryInput = document.getElementById('query-input');
    const submitBtn = document.getElementById('submit-btn');

    // Side Preview Drawer Elements
    const previewDrawer = document.getElementById('preview-drawer');
    const drawerBackdrop = document.getElementById('drawer-backdrop');
    const closeDrawerBtn = document.getElementById('close-drawer-btn');
    const drawerDocName = document.getElementById('drawer-doc-name');
    const drawerPageNum = document.getElementById('drawer-page-num');
    const drawerChunkContent = document.getElementById('drawer-chunk-content');
    const prevChunkBtn = document.getElementById('prev-chunk-btn');
    const nextChunkBtn = document.getElementById('next-chunk-btn');
    const chunkCounter = document.getElementById('chunk-counter');

    // Default Welcome Banner Template HTML
    const welcomeBannerHTML = `
        <div class="chat-welcome max-w-md mx-auto my-auto text-center p-6 bg-[#121212] border border-amber-500/20 backdrop-blur-md rounded-2xl shadow-xl">
            <div class="text-4xl mb-3">🔍</div>
            <h2 class="text-lg font-bold text-amber-300 mb-2">DevsRAG Research Assistant</h2>
            <p class="text-xs text-gray-400 mb-4">Ask natural-language questions, compare files side-by-side, or query metadata about your uploaded documents.</p>
            
            <div class="suggested-queries space-y-2 text-left">
                <button class="w-full text-xs p-2.5 bg-[#18181b] border border-amber-500/20 rounded-xl text-gray-300 hover:border-amber-400 hover:bg-amber-500/10 transition-all hover:shadow-[0_0_12px_rgba(245,158,11,0.2)]" onclick="document.getElementById('query-input').value='Provide a summary of the uploaded document'; document.getElementById('query-form').dispatchEvent(new Event('submit'));">
                    💡 Summarize active document
                </button>
                <button class="w-full text-xs p-2.5 bg-[#18181b] border border-amber-500/20 rounded-xl text-gray-300 hover:border-amber-400 hover:bg-amber-500/10 transition-all hover:shadow-[0_0_12px_rgba(245,158,11,0.2)]" onclick="document.getElementById('query-input').value='At what time was the pdf uploaded and how many pages does it have?'; document.getElementById('query-form').dispatchEvent(new Event('submit'));">
                    ⏱ Check upload timestamp & pages
                </button>
                <button class="w-full text-xs p-2.5 bg-[#18181b] border border-amber-500/20 rounded-xl text-gray-300 hover:border-amber-400 hover:bg-amber-500/10 transition-all hover:shadow-[0_0_12px_rgba(245,158,11,0.2)]" onclick="document.getElementById('query-input').value='Compare the uploaded files and list key differences'; document.getElementById('query-form').dispatchEvent(new Event('submit'));">
                    ⚖️ Compare documents side-by-side
                </button>
            </div>
        </div>
    `;

    // In-App Toast Notification Helper (Replaces browser alerts)
    function showToast(message, type = 'info') {
        const toast = document.createElement('div');
        let typeClasses = 'bg-[#18181b] border-amber-500/40 text-amber-200';
        let icon = 'ℹ️';

        if (type === 'success') {
            typeClasses = 'bg-[#121b14] border-emerald-500/40 text-emerald-300';
            icon = '✅';
        } else if (type === 'error') {
            typeClasses = 'bg-[#201212] border-red-500/40 text-red-300';
            icon = '⚠️';
        } else if (type === 'update') {
            typeClasses = 'bg-[#18181b] border-amber-400/60 text-amber-300 shadow-[0_0_15px_rgba(245,158,11,0.25)]';
            icon = '🔄';
        }

        toast.className = `flex items-center gap-2.5 px-4 py-3 border rounded-xl shadow-xl text-xs font-medium backdrop-blur-md pointer-events-auto transform transition-all duration-300 translate-y-[-10px] opacity-0 ${typeClasses}`;
        toast.innerHTML = `<span>${icon}</span><span>${message}</span>`;

        toastContainer.appendChild(toast);

        // Animate in
        requestAnimationFrame(() => {
            toast.classList.remove('translate-y-[-10px]', 'opacity-0');
        });

        // Auto dismiss after 3.5 seconds
        setTimeout(() => {
            toast.classList.add('opacity-0', 'translate-y-[-10px]');
            setTimeout(() => toast.remove(), 300);
        }, 3500);
    }

    // Architecture Modal Event Handlers
    openArchBtn.addEventListener('click', () => {
        archModal.classList.remove('hidden');
    });

    [closeArchBtn, dismissArchBtn].forEach(btn => {
        btn.addEventListener('click', () => {
            archModal.classList.add('hidden');
        });
    });

    archModal.addEventListener('click', (e) => {
        if (e.target === archModal) archModal.classList.add('hidden');
    });

    // Clear Chat Action Handler
    clearChatBtn.addEventListener('click', () => {
        state.chatHistory = [];
        state.activeCitations = [];
        state.currentCitationIdx = 0;
        closeDrawer();
        chatContainer.innerHTML = welcomeBannerHTML;
        showToast("Chat history cleared.", "update");
    });

    // Export Chat Log Action Handler
    exportChatBtn.addEventListener('click', () => {
        if (!state.chatHistory || state.chatHistory.length === 0) {
            showToast("No active conversation log to export.", "info");
            return;
        }

        const dateStr = new Date().toLocaleString();
        let markdownContent = `# DevsRAG Conversation Session Export\n`;
        markdownContent += `**Exported At:** ${dateStr}\n`;
        markdownContent += `**Scope:** ${state.selectedDocId ? 'Single Document Scope' : 'Entire Workspace Collection'}\n\n`;
        markdownContent += `---\n\n`;

        for (let i = 0; i < state.chatHistory.length; i += 2) {
            const userMsg = state.chatHistory[i];
            const assistantMsg = state.chatHistory[i + 1];

            if (userMsg) {
                markdownContent += `### 👤 User Query\n${userMsg.content}\n\n`;
            }
            if (assistantMsg) {
                markdownContent += `### ⚡ DevsRAG Response\n${assistantMsg.content}\n\n`;
                markdownContent += `---\n\n`;
            }
        }

        const blob = new Blob([markdownContent], { type: 'text/markdown;charset=utf-8;' });
        const link = document.createElement('a');
        const url = URL.createObjectURL(blob);
        link.setAttribute('href', url);
        link.setAttribute('download', 'devsrag_session_export.md');
        link.style.visibility = 'hidden';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);

        showToast("Chat log exported as devsrag_session_export.md", "success");
    });

    // Format Date: DD MMM, hh:mm am/pm (e.g. "31 Jul, 07:28 pm")
    function formatTimestamp(isoString) {
        if (!isoString) return 'Just now';
        const dObj = new Date(isoString);
        if (isNaN(dObj.getTime())) return 'Recently';
        const day = String(dObj.getDate()).padStart(2, '0');
        const month = dObj.toLocaleDateString('en-US', { month: 'short' });
        const timeStr = dObj.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: true }).toLowerCase();
        return `${day} ${month}, ${timeStr}`;
    }

    // Format File Size
    function formatBytes(bytes) {
        if (!bytes || bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    // Initialize API Data Fetch on Component Mount
    fetchDocuments();

    // Setup Polling Loop for Pending Documents
    setInterval(() => {
        const hasPending = state.documents.some(d => d.status === 'pending' || d.status === 'processing');
        if (hasPending) {
            fetchDocuments(true);
        }
    }, 2500);

    // API Calls
    async function fetchDocuments(silent = false) {
        try {
            const res = await fetch('/api/v1/documents');
            if (!res.ok) throw new Error('Failed to fetch documents');
            const data = await res.json();
            state.documents = data.documents || [];
            renderDocumentList();
            updateScopeUI();
        } catch (err) {
            if (!silent) console.error('Fetch docs error:', err);
        }
    }

    async function uploadFiles(files) {
        if (!files || files.length === 0) return;
        state.uploading = true;
        
        for (const file of files) {
            const formData = new FormData();
            formData.append('file', file);

            try {
                const res = await fetch('/api/v1/documents?overwrite=true', {
                    method: 'POST',
                    body: formData
                });
                
                if (!res.ok) {
                    const errData = await res.json();
                    showToast(`Upload failed for ${file.name}: ${errData.detail || 'Unknown error'}`, 'error');
                    continue;
                }

                const docData = await res.json();
                showToast(`'${file.name}' indexed & updated successfully`, 'success');
            } catch (err) {
                showToast(`Network error uploading ${file.name}`, 'error');
            }
        }
        
        state.uploading = false;
        fetchDocuments();
    }

    async function deleteDocument(docId, event) {
        event.stopPropagation();
        const docToDelete = state.documents.find(d => d.id === docId);
        const docName = docToDelete ? docToDelete.filename : 'document';

        try {
            const res = await fetch(`/api/v1/documents/${docId}`, { method: 'DELETE' });
            if (res.ok) {
                if (state.selectedDocId === docId) {
                    state.selectedDocId = null;
                }
                showToast(`Removed '${docName}' and cleared associated vector indices`, 'info');
                fetchDocuments();
            } else {
                showToast(`Failed to delete '${docName}'`, 'error');
            }
        } catch (err) {
            showToast(`Error deleting '${docName}'`, 'error');
        }
    }

    // Drag and Drop Upload Event Handlers
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropzone.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    ['dragenter', 'dragover'].forEach(eventName => {
        dropzone.addEventListener(eventName, () => dropzone.classList.add('border-amber-400', 'shadow-[0_0_20px_rgba(245,158,11,0.3)]'), false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropzone.addEventListener(eventName, () => dropzone.classList.remove('border-amber-400', 'shadow-[0_0_20px_rgba(245,158,11,0.3)]'), false);
    });

    dropzone.addEventListener('drop', (e) => {
        const dt = e.dataTransfer;
        const files = dt.files;
        uploadFiles(files);
    });

    dropzone.addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('change', (e) => uploadFiles(e.target.files));

    // Filter Buttons logic
    filterButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            filterButtons.forEach(b => {
                b.classList.remove('bg-amber-500', 'text-black', 'font-semibold');
                b.classList.add('text-gray-400');
            });
            btn.classList.add('bg-amber-500', 'text-black', 'font-semibold');
            btn.classList.remove('text-gray-400');
            state.filter = btn.dataset.filter;
            renderDocumentList();
        });
    });

    // Render Document List with Bento Cards
    function renderDocumentList() {
        const filtered = state.documents.filter(doc => {
            if (state.filter === 'all') return true;
            return doc.status === state.filter;
        });

        docCountBadge.textContent = `${state.documents.length} doc${state.documents.length === 1 ? '' : 's'}`;

        if (filtered.length === 0) {
            docListContainer.innerHTML = `
                <div class="text-center py-6 text-xs text-gray-500">
                    No ${state.filter !== 'all' ? state.filter : ''} documents found.
                </div>
            `;
            return;
        }

        docListContainer.innerHTML = filtered.map(doc => {
            const isSelected = state.selectedDocId === doc.id;
            const timeFormatted = formatTimestamp(doc.created_at);

            let statusBadge = '';
            if (doc.status === 'ready') {
                statusBadge = '<span class="px-1.5 py-0.5 text-[10px] font-semibold uppercase rounded-md bg-emerald-500/20 text-emerald-400 border border-emerald-500/40">ready</span>';
            } else if (doc.status === 'pending' || doc.status === 'processing') {
                statusBadge = '<span class="px-1.5 py-0.5 text-[10px] font-semibold uppercase rounded-md bg-amber-500/20 text-amber-300 border border-amber-500/40">processing</span>';
            } else {
                const errReason = doc.status_message || "No selectable text found in PDF / Scanned Document";
                statusBadge = `<span class="px-1.5 py-0.5 text-[10px] font-semibold uppercase rounded-md bg-red-500/20 text-red-400 border border-red-500/40 cursor-help" title="${errReason}">failed</span>`;
            }

            return `
                <div class="doc-card p-3.5 bg-[#121215] border ${isSelected ? 'border-amber-400 bg-amber-500/10 shadow-[0_0_15px_rgba(245,158,11,0.25)]' : 'border-amber-500/20'} hover:border-amber-400/60 hover:shadow-[0_0_12px_rgba(245,158,11,0.18)] rounded-2xl cursor-pointer transition-all" data-id="${doc.id}">
                    <div class="flex justify-between items-center mb-1.5">
                        <span class="font-semibold text-xs text-white truncate max-w-[190px]" title="${doc.filename}">${doc.filename}</span>
                        ${statusBadge}
                    </div>
                    <div class="flex justify-between text-[11px] text-gray-400">
                        <span>${formatBytes(doc.file_size_bytes)} • ${doc.chunk_count} chunk${doc.chunk_count === 1 ? '' : 's'}</span>
                        <span>${timeFormatted}</span>
                    </div>
                    <div class="flex justify-end mt-1.5">
                        <button class="delete-btn text-[10px] text-red-400 hover:text-red-300 transition-colors" data-id="${doc.id}">
                            ✕ Remove
                        </button>
                    </div>
                </div>
            `;
        }).join('');

        // Attach event listeners
        document.querySelectorAll('.doc-card').forEach(card => {
            card.addEventListener('click', () => {
                const id = card.dataset.id;
                state.selectedDocId = state.selectedDocId === id ? null : id; // toggle single-doc vs collection mode
                renderDocumentList();
                updateScopeUI();
            });
        });

        document.querySelectorAll('.delete-btn').forEach(btn => {
            btn.addEventListener('click', (e) => deleteDocument(btn.dataset.id, e));
        });
    }

    function updateScopeUI() {
        if (!state.selectedDocId) {
            scopePill.textContent = 'Scope: Entire Document Collection';
            scopePill.className = 'text-xs text-amber-300 font-medium px-3 py-1 bg-amber-500/10 border border-amber-500/30 rounded-full';
        } else {
            const selectedDoc = state.documents.find(d => d.id === state.selectedDocId);
            const docName = selectedDoc ? selectedDoc.filename : 'Selected Document';
            scopePill.textContent = `Scope: ${docName}`;
            scopePill.className = 'text-xs text-white font-semibold px-3 py-1 bg-amber-500/25 border border-amber-500/60 rounded-full shadow-[0_0_12px_rgba(245,158,11,0.25)]';
        }
    }

    // Query Submission Handler (With Multi-Turn Chat History)
    queryForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const queryText = queryInput.value.trim();
        if (!queryText) return;

        // If chat stream is currently showing welcome banner, clear it before appending first message
        const welcomeBanner = chatContainer.querySelector('.chat-welcome');
        if (welcomeBanner) welcomeBanner.remove();

        // Render User Message
        appendMessage('user', queryText);
        
        // Push turn to state chat history
        state.chatHistory.push({ role: 'user', content: queryText });
        if (state.chatHistory.length > 10) state.chatHistory.shift();

        queryInput.value = '';
        submitBtn.disabled = true;

        // Render Loading State
        const loadingId = appendLoadingMessage();

        try {
            const res = await fetch('/api/v1/query', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    query: queryText,
                    document_id: state.selectedDocId,
                    top_k: 4,
                    chat_history: state.chatHistory.slice(-10) // Pass last 5 turns
                })
            });

            const data = await res.json();
            removeMessage(loadingId);

            if (res.ok) {
                appendMessage('assistant', data.answer, data.citations, data.execution_time_ms);
                state.chatHistory.push({ role: 'assistant', content: data.answer });
                if (state.chatHistory.length > 10) state.chatHistory.shift();
            } else {
                appendMessage('assistant', `⚠️ Error: ${data.detail || 'Failed to generate response'}`);
            }
        } catch (err) {
            removeMessage(loadingId);
            appendMessage('assistant', '⚠️ Network error: Unable to communicate with DevsRAG backend engine.');
        } finally {
            submitBtn.disabled = false;
        }
    });

    // Chat UI Helpers & Enhanced Citation Chips
    function appendMessage(role, text, citations = [], execTime = null) {
        const msgDiv = document.createElement('div');
        msgDiv.className = `p-4 rounded-2xl text-sm leading-relaxed max-w-[85%] ${
            role === 'user'
                ? 'self-end bg-gradient-to-r from-amber-900/40 to-amber-800/40 border border-amber-500/40 text-white shadow-lg'
                : 'self-start bg-[#121215] border border-amber-500/20 backdrop-blur-md text-gray-200 shadow-md'
        }`;

        let citationsHTML = '';
        if (citations && citations.length > 0) {
            citationsHTML = `
                <div class="mt-3.5 pt-2.5 border-t border-dashed border-amber-500/20 flex flex-wrap gap-2">
                    <div class="w-full text-[10px] text-gray-500 font-semibold tracking-wider uppercase mb-0.5">GROUNDED SOURCES:</div>
                    ${citations.map((c, idx) => `
                        <button class="citation-pill bg-amber-950/40 text-amber-300 border border-amber-500/30 px-2.5 py-1 rounded-lg text-xs hover:border-amber-400 hover:shadow-[0_0_10px_rgba(245,158,11,0.3)] cursor-pointer transition-all font-medium" data-idx="${idx}">
                            📄 [${c.citation_id}] ${c.document_name} (p. ${c.page_number})
                        </button>
                    `).join('')}
                </div>
            `;
        }

        let timeHTML = execTime ? `<span class="text-[10px] text-gray-500 ml-2">(${execTime}ms)</span>` : '';

        msgDiv.innerHTML = `
            <div class="text-[11px] font-semibold text-amber-400 mb-1.5 flex items-center">${role === 'user' ? 'You' : 'DevsRAG Engine'}${timeHTML}</div>
            <div class="msg-content text-gray-200">${formatMarkdown(text)}</div>
            ${citationsHTML}
        `;

        chatContainer.appendChild(msgDiv);
        chatContainer.scrollTop = chatContainer.scrollHeight;

        // Attach Side Drawer Click Event to Citation Chips
        if (citations && citations.length > 0) {
            msgDiv.querySelectorAll('.citation-pill').forEach(pill => {
                pill.addEventListener('click', () => {
                    const citIdx = parseInt(pill.dataset.idx);
                    openPreviewDrawer(citIdx, citations);
                });
            });
        }
    }

    function appendLoadingMessage() {
        const id = 'msg-' + Date.now();
        const msgDiv = document.createElement('div');
        msgDiv.className = 'p-4 rounded-2xl text-sm leading-relaxed max-w-[85%] self-start bg-[#121215] border border-amber-500/20 text-gray-400';
        msgDiv.id = id;
        msgDiv.innerHTML = `
            <div class="text-[11px] font-semibold text-amber-400 mb-1">DevsRAG Engine</div>
            <div class="flex items-center gap-2">
                <span class="w-2 h-2 rounded-full bg-amber-400 animate-ping"></span>
                <span>Resolving context & retrieving vector chunks...</span>
            </div>
        `;
        chatContainer.appendChild(msgDiv);
        chatContainer.scrollTop = chatContainer.scrollHeight;
        return id;
    }

    function removeMessage(id) {
        const elem = document.getElementById(id);
        if (elem) elem.remove();
    }

    function formatMarkdown(str) {
        // Robust Markdown Comparison Table Renderer
        if (str.includes('|') && str.includes('---')) {
            const lines = str.split('\n');
            let resultHTML = '';
            let inTable = false;
            let tableHTML = '<table class="w-full my-3.5 border-collapse text-xs bg-[#0c0d0f] rounded-xl overflow-hidden border border-amber-500/30 shadow-lg">';

            for (let i = 0; i < lines.length; i++) {
                const line = lines[i].trim();
                if (line.startsWith('|') && line.endsWith('|')) {
                    if (line.includes('---')) continue; // Skip separator line
                    const cells = line.split('|').slice(1, -1).map(c => c.trim());
                    if (!inTable) {
                        tableHTML += '<thead><tr class="bg-[#18181b] text-amber-300 border-b border-amber-500/40">' + cells.map(c => `<th class="p-3 text-left font-semibold">${c}</th>`).join('') + '</tr></thead><tbody>';
                        inTable = true;
                    } else {
                        tableHTML += '<tr class="border-b border-amber-900/20 odd:bg-[#121214] even:bg-[#0e0f11] hover:bg-amber-500/10 transition-colors">' + cells.map(c => `<td class="p-3 text-gray-300">${c}</td>`).join('') + '</tr>';
                    }
                } else {
                    if (inTable) {
                        tableHTML += '</tbody></table>';
                        resultHTML += tableHTML;
                        inTable = false;
                        tableHTML = '<table class="w-full my-3.5 border-collapse text-xs bg-[#0c0d0f] rounded-xl overflow-hidden border border-amber-500/30 shadow-lg">';
                    }
                    if (line) {
                        let formattedLine = line.replace(/</g, '&lt;').replace(/>/g, '&gt;');
                        formattedLine = formattedLine.replace(/\*\*(.*?)\*\*/g, '<strong class="text-white font-semibold">$1</strong>');
                        resultHTML += formattedLine + '<br>';
                    }
                }
            }
            if (inTable) {
                tableHTML += '</tbody></table>';
                resultHTML += tableHTML;
            }
            return resultHTML;
        }

        // Basic formatting
        let clean = str.replace(/</g, '&lt;').replace(/>/g, '&gt;');
        clean = clean.replace(/\*\*(.*?)\*\*/g, '<strong class="text-white font-semibold">$1</strong>');
        clean = clean.replace(/\n•/g, '<br>•');
        clean = clean.replace(/\n/g, '<br>');
        return clean;
    }

    // Side Preview Drawer Controller
    function openPreviewDrawer(citIdx, citationsList) {
        state.activeCitations = citationsList;
        state.currentCitationIdx = citIdx;
        renderDrawerContent();
        previewDrawer.classList.remove('translate-x-full');
        previewDrawer.classList.add('translate-x-0');
        drawerBackdrop.classList.remove('hidden');
    }

    function renderDrawerContent() {
        const citation = state.activeCitations[state.currentCitationIdx];
        if (!citation) return;

        drawerDocName.textContent = citation.document_name;
        drawerPageNum.textContent = `Page ${citation.page_number}`;
        drawerChunkContent.textContent = citation.snippet;
        chunkCounter.textContent = `${state.currentCitationIdx + 1} of ${state.activeCitations.length}`;

        prevChunkBtn.disabled = state.currentCitationIdx === 0;
        nextChunkBtn.disabled = state.currentCitationIdx === state.activeCitations.length - 1;
    }

    closeDrawerBtn.addEventListener('click', closeDrawer);
    drawerBackdrop.addEventListener('click', closeDrawer);

    function closeDrawer() {
        previewDrawer.classList.remove('translate-x-0');
        previewDrawer.classList.add('translate-x-full');
        drawerBackdrop.classList.add('hidden');
    }

    prevChunkBtn.addEventListener('click', () => {
        if (state.currentCitationIdx > 0) {
            state.currentCitationIdx--;
            renderDrawerContent();
        }
    });

    nextChunkBtn.addEventListener('click', () => {
        if (state.currentCitationIdx < state.activeCitations.length - 1) {
            state.currentCitationIdx++;
            renderDrawerContent();
        }
    });
});
