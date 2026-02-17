/**
 * CrackATS Application JavaScript
 * Main frontend controller for the AI Resume Generator & Job Tracker
 */

// ===== State Management =====
let currentFolder = '';
let currentResume = '';
let draggedAppId = null;
let draggedCard = null;
let editingAppId = null;
let currentDocApp = null;
let currentDocType = 'resume';
let currentDocContent = '';
let isEditMode = false;
let originalContent = '';
let templatePreviewVisible = false;
let homeTemplateLoaded = false;
let originalTemplateContent = '';

// Constants
const STATUS_COLUMNS = [
    { id: 'saved', label: 'Saved', color: '#9ca3af' },
    { id: 'applied', label: 'Applied', color: '#64748b' },
    { id: 'shortlisted', label: 'Shortlisted', color: '#475569' },
    { id: 'interview', label: 'Interview', color: '#334155' },
    { id: 'technical', label: 'Technical', color: '#1e293b' },
    { id: 'offer', label: 'Offer', color: '#059669' },
    { id: 'rejected', label: 'Rejected', color: '#991b1b' },
    { id: 'withdrawn', label: 'Withdrawn', color: '#71717a' }
];

// ===== Tab Navigation =====
function switchTab(tabName) {
    document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
    
    event.target.classList.add('active');
    document.getElementById(tabName + 'Tab').classList.add('active');
    
    if (tabName === 'tracker') {
        loadApplications();
    } else if (tabName === 'template') {
        loadTemplate();
    }
}

// ===== Generator Functions =====
function fillUrl(url) {
    document.getElementById('jobUrl').value = url;
}

function showSuccess(message) {
    document.getElementById('successMessage').textContent = message;
    document.getElementById('successAlert').classList.add('active');
    document.getElementById('errorAlert').classList.remove('active');
    setTimeout(() => {
        document.getElementById('successAlert').classList.remove('active');
    }, 5000);
}

function showError(message) {
    document.getElementById('errorMessage').textContent = message;
    document.getElementById('errorAlert').classList.add('active');
    document.getElementById('successAlert').classList.remove('active');
}

async function generateResume() {
    const url = document.getElementById('jobUrl').value.trim();
    const btn = document.getElementById('generateBtn');
    const loading = document.getElementById('loading');
    const results = document.getElementById('resultsSection');

    if (!url) {
        showError('Please enter a job URL');
        return;
    }

    btn.disabled = true;
    loading.classList.add('active');
    results.classList.remove('active');

    try {
        const formData = new FormData();
        formData.append('url', url);

        const response = await fetch('/scrape-and-generate', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || 'Failed to generate resume');
        }

        currentFolder = data.folder;
        currentResume = data.resume_tex;

        document.getElementById('jobTitle').textContent = data.title || 'Unknown Title';
        document.getElementById('jobCompany').textContent = data.company || 'Unknown Company';
        document.getElementById('resumeContent').textContent = data.resume_tex;
        document.getElementById('coverLetterContent').textContent = data.cover_letter;

        results.classList.add('active');
        showSuccess('Resume generated and added to your tracker!');

    } catch (err) {
        showError(err.message);
    } finally {
        btn.disabled = false;
        loading.classList.remove('active');
    }
}

function copyResume() {
    navigator.clipboard.writeText(currentResume).then(() => {
        showSuccess('Copied to clipboard!');
    });
}

function openInOverleaf() {
    if (!currentFolder || !currentResume) {
        showError('No resume generated yet');
        return;
    }
    
    // Get job info from DOM
    const jobTitle = document.getElementById('jobTitle').textContent || 'Resume';
    const jobCompany = document.getElementById('jobCompany').textContent || 'Company';
    
    // Create project name: RoleWithCompany
    const projectName = sanitizeProjectName(`${jobTitle}_${jobCompany}`);
    
    // Check if already opened in this session
    const storageKey = `overleaf_opened_${currentFolder}`;
    if (sessionStorage.getItem(storageKey)) {
        // Already opened - go to projects dashboard instead of creating duplicate
        window.open('https://www.overleaf.com/project', '_blank');
        return;
    }
    
    // Use base64 data URI to avoid localhost access issues
    const base64Content = btoa(unescape(encodeURIComponent(currentResume)));
    const dataUri = `data:application/x-tex;base64,${base64Content}`;
    const overleafUrl = `https://www.overleaf.com/docs?snip_uri=${encodeURIComponent(dataUri)}&snip_name=${encodeURIComponent(projectName)}.tex`;
    
    // Mark as opened
    sessionStorage.setItem(storageKey, 'true');
    
    window.open(overleafUrl, '_blank');
}

function sanitizeProjectName(name) {
    // Remove special characters and spaces, keep alphanumeric and underscores
    return name
        .replace(/[^a-zA-Z0-9_\s]/g, '')  // Remove special chars except spaces and underscores
        .replace(/\s+/g, '_')              // Replace spaces with underscores
        .replace(/_+/g, '_')               // Collapse multiple underscores
        .substring(0, 50);                 // Limit length
}

function downloadResume() {
    const blob = new Blob([currentResume], { type: 'text/x-tex' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${currentFolder || 'Resume'}.tex`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

// ===== Tracker Functions =====
async function loadApplications() {
    try {
        const response = await fetch('/api/applications');
        const applications = await response.json();
        
        const byStatus = {};
        STATUS_COLUMNS.forEach(col => byStatus[col.id] = []);
        applications.forEach(app => {
            if (byStatus[app.status]) byStatus[app.status].push(app);
        });

        const board = document.getElementById('kanbanBoard');
        board.innerHTML = STATUS_COLUMNS.map(col => `
            <div class="kanban-column" data-status="${col.id}"
                ondragover="handleColumnDragOver(event)"
                ondrop="handleColumnDrop(event, '${col.id}')">
                <div class="kanban-column-header">
                    <span class="kanban-column-title">${col.label}</span>
                    <span class="kanban-count" id="count-${col.id}">${byStatus[col.id].length}</span>
                </div>
                <div class="kanban-cards" data-status="${col.id}"
                    ondragover="handleDragOver(event)"
                    ondrop="handleDrop(event, '${col.id}')"
                    ondragenter="handleDragEnter(event)"
                    ondragleave="handleDragLeave(event)">
                    ${byStatus[col.id].map(app => `
                        <div class="kanban-card status-${app.status}" 
                             draggable="true"
                             data-app-id="${app.id}"
                             data-current-status="${app.status}"
                             onclick="editApplication(${app.id})"
                             ondragstart="handleDragStart(event, ${app.id})"
                             ondragend="handleDragEnd(event)">
                            <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                                <div class="kanban-card-company">${app.company}</div>
                                ${app.resume_path ? `<button class="view-docs-btn" onclick="event.stopPropagation(); viewDocuments(${app.id}, '${app.company}', '${app.title}')">View Docs</button>` : ''}
                            </div>
                            <div class="kanban-card-title">${app.title}</div>
                            <div class="kanban-card-meta">
                                <span>${app.date_applied || 'No date'}</span>
                                ${app.tags && app.tags.includes('ai-generated') ? '<span class="tag tag-ai">AI</span>' : ''}
                            </div>
                        </div>
                    `).join('')}
                    <button class="add-card-btn" onclick="event.stopPropagation(); openApplicationModal('${col.id}')">+ Add</button>
                </div>
            </div>
        `).join('');

        loadStats();
    } catch (err) {
        console.error('Failed to load applications:', err);
    }
}

// Drag and Drop Handlers
function handleDragStart(event, appId) {
    draggedAppId = appId;
    draggedCard = event.target;
    event.target.classList.add('dragging');
    event.dataTransfer.effectAllowed = 'move';
    event.dataTransfer.setData('text/plain', appId);
    
    const rect = event.target.getBoundingClientRect();
    event.dataTransfer.setDragImage(event.target, rect.width / 2, 20);
}

function handleDragEnd(event) {
    event.target.classList.remove('dragging');
    document.querySelectorAll('.kanban-column').forEach(col => {
        col.classList.remove('drag-over');
    });
    document.querySelectorAll('.kanban-cards').forEach(cards => {
        cards.classList.remove('drag-over');
    });
    draggedAppId = null;
    draggedCard = null;
}

function handleDragOver(event) {
    event.preventDefault();
    event.stopPropagation();
    event.dataTransfer.dropEffect = 'move';
}

// Column-level drag handlers as fallback
function handleColumnDragOver(event) {
    event.preventDefault();
    event.stopPropagation();
    event.dataTransfer.dropEffect = 'move';
    console.log('Column drag over:', event.currentTarget.dataset.status);
}

function handleColumnDrop(event, newStatus) {
    event.preventDefault();
    event.stopPropagation();
    console.log('Column drop triggered for status:', newStatus);
    
    // Delegate to main drop handler
    const appId = event.dataTransfer.getData('text/plain');
    if (!appId) {
        console.error('No appId in column drop data');
        return;
    }
    
    // Find the kanban-cards container for this status
    const cardsContainer = document.querySelector(`.kanban-cards[data-status="${newStatus}"]`);
    if (cardsContainer) {
        // Create a synthetic event for the main handler
        handleDrop({ 
            preventDefault: () => {},
            currentTarget: cardsContainer,
            dataTransfer: event.dataTransfer 
        }, newStatus);
    }
}

function handleDragEnter(event) {
    event.preventDefault();
    const cardsContainer = event.currentTarget;
    const status = cardsContainer.dataset.status;
    console.log(`Drag enter on column: ${status}`);
    cardsContainer.classList.add('drag-over');
}

function handleDragLeave(event) {
    const cardsContainer = event.currentTarget;
    if (!cardsContainer.contains(event.relatedTarget)) {
        cardsContainer.classList.remove('drag-over');
    }
}

async function handleDrop(event, newStatus) {
    event.preventDefault();
    console.log(`Drop event triggered for status: ${newStatus}`);
    
    const cardsContainer = event.currentTarget;
    cardsContainer.classList.remove('drag-over');
    
    const appId = event.dataTransfer.getData('text/plain');
    console.log(`App ID from drag data: ${appId}`);
    
    if (!appId) {
        console.error('No appId found in drag data');
        return;
    }
    
    const card = document.querySelector(`[data-app-id="${appId}"]`);
    console.log(`Found card:`, card);
    
    if (!card) {
        console.error(`No card found with appId: ${appId}`);
        return;
    }
    
    const currentStatus = card.dataset.currentStatus;
    
    if (currentStatus === newStatus) return;
    
    updateCardInUI(card, newStatus);
    updateColumnCounts();
    
    try {
        const formData = new FormData();
        formData.append('status', newStatus);
        
        console.log('DEBUG FRONTEND: Sending status update:', { appId, newStatus });
        
        const response = await fetch(`/api/applications/${appId}/status`, {
            method: 'POST',
            body: formData
        });
        
        console.log('DEBUG FRONTEND: Response status:', response.status);
        
        if (!response.ok) {
            const errorData = await response.json();
            console.error('Server error:', errorData);
            throw new Error(`Failed to update status: ${errorData.detail || response.statusText}`);
        }
        console.log('Status updated successfully');
        
        showDragSuccess(card);
        loadStats();
        
    } catch (err) {
        console.error('Failed to update status:', err);
        updateCardInUI(card, currentStatus);
        updateColumnCounts();
        showError('Failed to move application. Please try again.');
    }
}

function updateCardInUI(card, newStatus) {
    const oldStatus = card.dataset.currentStatus;
    card.classList.remove(`status-${oldStatus}`);
    card.classList.add(`status-${newStatus}`);
    card.dataset.currentStatus = newStatus;
    
    const targetColumn = document.querySelector(`.kanban-cards[data-status="${newStatus}"]`);
    if (targetColumn) {
        const addButton = targetColumn.querySelector('.add-card-btn');
        targetColumn.insertBefore(card, addButton);
    }
}

function updateColumnCounts() {
    STATUS_COLUMNS.forEach(col => {
        const column = document.querySelector(`.kanban-cards[data-status="${col.id}"]`);
        if (column) {
            const cards = column.querySelectorAll('.kanban-card');
            const countEl = document.getElementById(`count-${col.id}`);
            if (countEl) {
                countEl.textContent = cards.length;
            }
        }
    });
}

function showDragSuccess(card) {
    card.style.transition = 'all 0.3s ease';
    card.style.borderColor = 'var(--success)';
    card.style.boxShadow = '0 0 0 3px rgba(22, 163, 74, 0.2)';
    
    setTimeout(() => {
        card.style.borderColor = '';
        card.style.boxShadow = '';
    }, 800);
}

async function loadStats() {
    try {
        const response = await fetch('/api/applications/stats/overview');
        const stats = await response.json();
        
        document.getElementById('statTotal').textContent = stats.total;
        document.getElementById('statApplied').textContent = stats.by_status.applied || 0;
        document.getElementById('statInterview').textContent = 
            (stats.by_status.interview || 0) + (stats.by_status.technical || 0);
        document.getElementById('statOffer').textContent = stats.by_status.offer || 0;
        document.getElementById('statResponse').textContent = stats.response_rate + '%';
    } catch (err) {
        console.error('Failed to load stats:', err);
    }
}

function openApplicationModal(initialStatus = 'saved') {
    editingAppId = null;
    document.getElementById('appModalTitle').textContent = 'New Application';
    document.getElementById('applicationForm').reset();
    document.getElementById('appStatus').value = initialStatus;
    document.getElementById('deleteAppBtn').style.display = 'none';
    document.getElementById('appId').value = '';
    document.getElementById('applicationModal').classList.add('active');
}

function closeApplicationModal() {
    document.getElementById('applicationModal').classList.remove('active');
    editingAppId = null;
}

function closeModalOnBackdrop(event, modalId) {
    if (event.target === event.currentTarget) {
        if (modalId === 'applicationModal') closeApplicationModal();
        if (modalId === 'docModal') closeDocModal();
    }
}

async function editApplication(appId) {
    try {
        const response = await fetch(`/api/applications/${appId}`);
        const app = await response.json();
        
        editingAppId = appId;
        document.getElementById('appModalTitle').textContent = 'Edit Application';
        document.getElementById('appId').value = app.id;
        document.getElementById('appCompany').value = app.company;
        document.getElementById('appTitle').value = app.title;
        document.getElementById('appUrl').value = app.url || '';
        document.getElementById('appStatus').value = app.status;
        document.getElementById('appDate').value = app.date_applied || '';
        document.getElementById('appLocation').value = app.location || '';
        document.getElementById('appSalary').value = app.salary || '';
        document.getElementById('appNotes').value = app.notes || '';
        document.getElementById('deleteAppBtn').style.display = 'block';
        document.getElementById('applicationModal').classList.add('active');
    } catch (err) {
        showError('Failed to load application');
    }
}

async function saveApplication() {
    const company = document.getElementById('appCompany').value.trim();
    const title = document.getElementById('appTitle').value.trim();
    
    if (!company || !title) {
        alert('Company and Title are required');
        return;
    }

    const formData = new FormData();
    formData.append('company', company);
    formData.append('title', title);
    formData.append('url', document.getElementById('appUrl').value);
    formData.append('status', document.getElementById('appStatus').value);
    formData.append('date_applied', document.getElementById('appDate').value);
    formData.append('location', document.getElementById('appLocation').value);
    formData.append('salary', document.getElementById('appSalary').value);
    formData.append('notes', document.getElementById('appNotes').value);

    try {
        if (editingAppId) {
            await fetch(`/api/applications/${editingAppId}`, { method: 'PUT', body: formData });
        } else {
            await fetch('/api/applications', { method: 'POST', body: formData });
        }
        closeApplicationModal();
        loadApplications();
    } catch (err) {
        alert('Failed to save application');
    }
}

async function deleteApplication() {
    if (!editingAppId || !confirm('Delete this application?')) return;
    
    try {
        await fetch(`/api/applications/${editingAppId}`, { method: 'DELETE' });
        closeApplicationModal();
        loadApplications();
    } catch (err) {
        alert('Failed to delete');
    }
}

// ===== Document Viewer Functions =====
async function viewDocuments(appId, company, title) {
    try {
        const response = await fetch(`/api/applications/${appId}`);
        const app = await response.json();
        
        currentDocApp = app;
        currentDocType = 'resume';
        
        document.getElementById('docModalTitle').textContent = `${company} - ${title}`;
        
        await loadDocument('resume');
        
        document.getElementById('docModal').classList.add('active');
    } catch (err) {
        alert('Failed to load documents');
    }
}

async function loadDocument(type) {
    if (!currentDocApp) return;
    
    const path = type === 'resume' ? currentDocApp.resume_path : currentDocApp.cover_letter_path;
    
    if (!path) {
        document.getElementById('docContent').innerHTML = `<div style="color: var(--text-secondary); text-align: center; padding: 2rem;">${type === 'resume' ? 'Resume' : 'Cover letter'} not available</div>`;
        currentDocContent = '';
        return;
    }
    
    try {
        // Normalize path separators for cross-platform compatibility
        const normalizedPath = path.replace(/\\/g, '/');
        const pathParts = normalizedPath.split('/');
        const folder = pathParts[pathParts.length - 2];
        
        console.log('Loading document:', { type, path, normalizedPath, folder });
        
        const endpoint = type === 'resume' 
            ? `/resume/${encodeURIComponent(folder)}`
            : `/cover-letter/${encodeURIComponent(folder)}`;
        
        console.log('Fetching endpoint:', endpoint);
        
        const response = await fetch(endpoint);
        
        if (!response.ok) {
            const errorData = await response.json();
            console.error('Server error:', errorData);
            throw new Error(errorData.detail || `HTTP ${response.status}`);
        }
        
        const data = await response.json();
        
        currentDocContent = data.content;
        
        if (type === 'resume') {
            document.getElementById('docContent').innerHTML = `<pre style="font-family: 'Monaco', 'Menlo', 'Consolas', monospace; font-size: 0.8125rem; line-height: 1.6; margin: 0;">${escapeHtml(data.content)}</pre>`;
        } else {
            document.getElementById('docContent').innerHTML = `<div style="white-space: pre-wrap; line-height: 1.8;">${escapeHtml(data.content)}</div>`;
        }
    } catch (err) {
        console.error('Failed to load document:', err);
        document.getElementById('docContent').innerHTML = `
            <div style="color: var(--error); padding: 2rem;">
                <strong>Failed to load ${type}</strong><br>
                <small style="color: var(--text-secondary);">${err.message}</small>
            </div>
        `;
        currentDocContent = '';
    }
}

function switchDocTab(type) {
    currentDocType = type;
    document.querySelectorAll('.doc-tab').forEach(t => t.classList.remove('active'));
    document.getElementById(type + 'Tab').classList.add('active');
    loadDocument(type);
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function toggleEditMode() {
    if (!currentDocApp || !currentDocContent) return;
    
    isEditMode = !isEditMode;
    const btn = document.getElementById('editDocBtn');
    const contentDiv = document.getElementById('docContent');
    
    if (isEditMode) {
        originalContent = currentDocContent;
        btn.textContent = 'Save';
        btn.classList.remove('btn-secondary');
        btn.classList.add('btn-primary');
        
        contentDiv.innerHTML = `<textarea id="docEditor" style="width: 100%; min-height: 400px; border: 1px solid var(--border); border-radius: var(--radius); padding: 1rem; font-family: 'Monaco', 'Menlo', 'Consolas', monospace; font-size: 0.8125rem; line-height: 1.6; resize: vertical; background: var(--bg); color: var(--text);">${escapeHtml(currentDocContent)}</textarea>`;
    } else {
        saveDocument();
    }
}

async function saveDocument() {
    const editor = document.getElementById('docEditor');
    if (!editor) return;
    
    const newContent = editor.value;
    
    try {
        const path = currentDocType === 'resume' 
            ? currentDocApp.resume_path 
            : currentDocApp.cover_letter_path;
        
        if (!path) {
            alert('Cannot save: document path not found');
            return;
        }
        
        const formData = new FormData();
        formData.append('content', newContent);
        formData.append('path', path);
        
        const response = await fetch('/api/save-document', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            throw new Error('Failed to save');
        }
        
        currentDocContent = newContent;
        isEditMode = false;
        
        const btn = document.getElementById('editDocBtn');
        btn.textContent = 'Edit';
        btn.classList.add('btn-secondary');
        btn.classList.remove('btn-primary');
        
        if (currentDocType === 'resume') {
            document.getElementById('docContent').innerHTML = `<pre style="font-family: 'Monaco', 'Menlo', 'Consolas', monospace; font-size: 0.8125rem; line-height: 1.6; margin: 0;">${escapeHtml(currentDocContent)}</pre>`;
        } else {
            document.getElementById('docContent').innerHTML = `<div style="white-space: pre-wrap; line-height: 1.8;">${escapeHtml(currentDocContent)}</div>`;
        }
        
        alert('Document saved successfully!');
    } catch (err) {
        alert('Failed to save document: ' + err.message);
        currentDocContent = originalContent;
        isEditMode = false;
        loadDocument(currentDocType);
    }
}

function closeDocModal() {
    if (isEditMode) {
        if (!confirm('You have unsaved changes. Discard them?')) {
            return;
        }
        isEditMode = false;
        const btn = document.getElementById('editDocBtn');
        btn.textContent = 'Edit';
        btn.classList.add('btn-secondary');
        btn.classList.remove('btn-primary');
    }
    document.getElementById('docModal').classList.remove('active');
    currentDocApp = null;
    currentDocContent = '';
    originalContent = '';
}

function openCurrentDocInOverleaf() {
    if (!currentDocApp) {
        alert('No document loaded');
        return;
    }
    
    if (!currentDocContent) {
        alert('No document content available');
        return;
    }
    
    // Create project name from title and company
    const title = currentDocApp.title || 'Job';
    const company = currentDocApp.company || 'Company';
    const docType = currentDocType === 'resume' ? 'Resume' : 'CoverLetter';
    const projectName = sanitizeProjectName(`${title}_${company}_${docType}`);
    
    // Check if already opened in this session
    const docId = currentDocApp.id || 'unknown';
    const storageKey = `overleaf_opened_doc_${docId}_${currentDocType}`;
    if (sessionStorage.getItem(storageKey)) {
        // Already opened - go to projects dashboard instead of creating duplicate
        window.open('https://www.overleaf.com/project', '_blank');
        return;
    }
    
    // Use base64 data URI to avoid localhost access issues
    const mimeType = currentDocType === 'resume' ? 'application/x-tex' : 'text/plain';
    const base64Content = btoa(unescape(encodeURIComponent(currentDocContent)));
    const dataUri = `data:${mimeType};base64,${base64Content}`;
    const overleafUrl = `https://www.overleaf.com/docs?snip_uri=${encodeURIComponent(dataUri)}&snip_name=${encodeURIComponent(projectName)}.${currentDocType === 'resume' ? 'tex' : 'txt'}`;
    
    // Mark as opened
    sessionStorage.setItem(storageKey, 'true');
    
    window.open(overleafUrl, '_blank');
}

// ===== Template Preview Functions =====
function toggleTemplatePreview() {
    const content = document.getElementById('templatePreviewContent');
    const btn = document.getElementById('templateToggleBtn');
    
    templatePreviewVisible = !templatePreviewVisible;
    
    if (templatePreviewVisible) {
        content.style.display = 'block';
        btn.textContent = 'Hide Template';
        
        if (!homeTemplateLoaded) {
            loadHomeTemplate();
        }
    } else {
        content.style.display = 'none';
        btn.textContent = 'Show Template';
        document.getElementById('templateViewMode').style.display = 'block';
        document.getElementById('templateEditMode').style.display = 'none';
    }
}

async function loadHomeTemplate() {
    try {
        const response = await fetch('/template');
        const data = await response.json();
        document.getElementById('homeTemplateDisplay').textContent = data.content;
        document.getElementById('homeTemplateEditor').value = data.content;
        originalTemplateContent = data.content;
        homeTemplateLoaded = true;
    } catch (err) {
        document.getElementById('homeTemplateDisplay').textContent = 'Failed to load template';
    }
}

function enableTemplateEdit() {
    document.getElementById('templateViewMode').style.display = 'none';
    document.getElementById('templateEditMode').style.display = 'block';
    document.getElementById('homeTemplateEditor').value = originalTemplateContent;
}

function cancelTemplateEdit() {
    document.getElementById('templateViewMode').style.display = 'block';
    document.getElementById('templateEditMode').style.display = 'none';
    document.getElementById('homeTemplateEditor').value = originalTemplateContent;
}

async function saveHomeTemplate() {
    const newContent = document.getElementById('homeTemplateEditor').value;
    
    try {
        const formData = new FormData();
        formData.append('content', newContent);
        
        const response = await fetch('/template', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            throw new Error('Failed to save');
        }
        
        originalTemplateContent = newContent;
        document.getElementById('homeTemplateDisplay').textContent = newContent;
        
        document.getElementById('templateViewMode').style.display = 'block';
        document.getElementById('templateEditMode').style.display = 'none';
        
        showSuccess('Template saved successfully!');
    } catch (err) {
        showError('Failed to save template: ' + err.message);
    }
}

// ===== Database Management =====
async function refreshApplications() {
    // Refresh the applications view from database
    console.log('Refreshing applications...');
    
    const btn = event.target;
    const originalText = btn.textContent;
    btn.textContent = 'Refreshing...';
    btn.disabled = true;
    
    try {
        await loadApplications();
        await loadStats();
        showSuccess('Applications refreshed!');
    } catch (err) {
        console.error('Failed to refresh:', err);
        showError('Failed to refresh applications');
    } finally {
        btn.textContent = originalText;
        btn.disabled = false;
    }
}

// Reset Database Modal Functions
function openResetModal() {
    document.getElementById('resetModal').classList.add('active');
    document.getElementById('resetConfirmInput').value = '';
    document.getElementById('resetError').style.display = 'none';
    document.getElementById('resetConfirmInput').focus();
}

function closeResetModal() {
    document.getElementById('resetModal').classList.remove('active');
    document.getElementById('resetConfirmInput').value = '';
    document.getElementById('resetError').style.display = 'none';
}

async function executeReset() {
    const confirmation = document.getElementById('resetConfirmInput').value.trim();
    
    if (confirmation !== 'DELETE') {
        document.getElementById('resetError').style.display = 'block';
        return;
    }
    
    closeResetModal();
    console.log('Resetting database...');
    
    try {
        const formData = new FormData();
        formData.append('confirm', 'true');
        
        const response = await fetch('/api/applications/reset', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Reset failed');
        }
        
        const result = await response.json();
        
        // Clear the board
        document.getElementById('kanbanBoard').innerHTML = '';
        
        // Reload to show empty state
        await loadApplications();
        await loadStats();
        
        showSuccess(`Database reset complete! Deleted ${result.deleted_count} applications.`);
    } catch (err) {
        console.error('Failed to reset database:', err);
        showError('Failed to reset database: ' + err.message);
    }
}

// ===== API Key Management =====
let currentSavedApiKey = '';
let savedKeyVisible = false;

function showApiKeyModal() {
    document.getElementById('apiKeyModal').classList.add('active');
    document.getElementById('apiKeyInput').value = '';
    document.getElementById('apiKeyError').style.display = 'none';
    document.getElementById('apiKeyInput').type = 'password';
    document.getElementById('eyeIcon').textContent = '👁️';
    savedKeyVisible = false;
    document.getElementById('savedKeyEyeIcon').textContent = '👁️';
    document.getElementById('apiKeyInput').focus();
    
    // Load current key if exists
    loadCurrentApiKey();
}

function closeApiKeyModal() {
    document.getElementById('apiKeyModal').classList.remove('active');
    document.getElementById('apiKeyInput').value = '';
    document.getElementById('apiKeyError').style.display = 'none';
    document.getElementById('apiKeyInput').type = 'password';
    document.getElementById('eyeIcon').textContent = '👁️';
    savedKeyVisible = false;
    document.getElementById('savedKeyEyeIcon').textContent = '👁️';
}

async function loadCurrentApiKey() {
    try {
        const response = await fetch('/api/config');
        const data = await response.json();
        
        if (data.groq_api_key) {
            currentSavedApiKey = data.groq_api_key;
            // Show status indicator with masked key
            document.getElementById('apiKeyStatus').style.display = 'flex';
            document.getElementById('savedKeyDisplay').textContent = maskApiKey(data.groq_api_key);
            document.getElementById('apiKeyInput').placeholder = 'Enter new key to update or leave empty';
        } else {
            currentSavedApiKey = '';
            document.getElementById('apiKeyStatus').style.display = 'none';
            document.getElementById('apiKeyInput').placeholder = 'gsk_...';
        }
    } catch (err) {
        console.error('Failed to load current API key:', err);
        currentSavedApiKey = '';
        document.getElementById('apiKeyStatus').style.display = 'none';
    }
}

function maskApiKey(key) {
    if (!key || key.length < 10) return '••••••••';
    return key.substring(0, 7) + '••••••••••••••••••••' + key.substring(key.length - 4);
}

function toggleSavedKeyVisibility() {
    const display = document.getElementById('savedKeyDisplay');
    const eyeIcon = document.getElementById('savedKeyEyeIcon');
    
    if (savedKeyVisible) {
        // Hide key
        display.textContent = maskApiKey(currentSavedApiKey);
        eyeIcon.textContent = '👁️';
        savedKeyVisible = false;
    } else {
        // Show key
        display.textContent = currentSavedApiKey;
        eyeIcon.textContent = '🔒';
        savedKeyVisible = true;
    }
}

function toggleApiKeyVisibilityInput() {
    const input = document.getElementById('apiKeyInput');
    const eyeIcon = document.getElementById('eyeIcon');
    
    if (input.type === 'password') {
        input.type = 'text';
        eyeIcon.textContent = '🔒';
    } else {
        input.type = 'password';
        eyeIcon.textContent = '👁️';
    }
}

async function saveApiKey() {
    const apiKey = document.getElementById('apiKeyInput').value.trim();
    const errorDiv = document.getElementById('apiKeyError');
    
    // Validation
    if (!apiKey) {
        errorDiv.textContent = 'Please enter an API key';
        errorDiv.style.display = 'block';
        return;
    }
    
    if (!apiKey.startsWith('gsk_')) {
        errorDiv.textContent = 'Invalid API key format. Groq keys start with "gsk_"';
        errorDiv.style.display = 'block';
        return;
    }
    
    try {
        const formData = new FormData();
        formData.append('api_key', apiKey);
        
        const response = await fetch('/api/config', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Failed to save API key');
        }
        
        const result = await response.json();
        closeApiKeyModal();
        showSuccess('API key saved successfully!');
        
        // Test the key
        if (result.tested) {
            console.log('API key tested:', result.test_result);
        }
    } catch (err) {
        console.error('Failed to save API key:', err);
        errorDiv.textContent = err.message;
        errorDiv.style.display = 'block';
    }
}

async function exportApiKey() {
    try {
        const response = await fetch('/api/config');
        const data = await response.json();
        
        if (data.groq_api_key) {
            // Copy to clipboard
            await navigator.clipboard.writeText(data.groq_api_key);
            showSuccess('API key copied to clipboard!');
        } else {
            showError('No API key configured');
        }
    } catch (err) {
        console.error('Failed to export API key:', err);
        showError('Failed to export API key');
    }
}

function confirmResetDatabase() {
    openResetModal();
}

// ===== Donation Functions =====
function copyEthAddress() {
    const ethAddress = '0xdeFE5597a76EFECDc29Fa01798c5470224dB394F';
    
    navigator.clipboard.writeText(ethAddress).then(() => {
        // Show toast notification
        const toast = document.getElementById('donateToast');
        toast.classList.add('show');
        
        setTimeout(() => {
            toast.classList.remove('show');
        }, 2000);
    }).catch(err => {
        console.error('Failed to copy:', err);
        alert('ETH Address: ' + ethAddress);
    });
}

// ===== Initialization =====
document.getElementById('jobUrl').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') generateResume();
});

// Pre-load template for quick display
loadHomeTemplate();
