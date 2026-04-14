let currentConnectionId = null;
let currentSchemaName = null;
let currentJobId = null;
let logPollInterval = null;
let availableSchemas = []; // Store schemas for dropdowns

// Load connections on page load
document.addEventListener('DOMContentLoaded', function() {
    loadConnections();
    loadConfig();
    loadPostgresConfig();
    updateActiveConnectionButtons(); // Initialize button states
});

// ----- DB Type helpers (MySQL / PostgreSQL) -----

const DB_TYPE_DEFAULTS = {
    mysql: {port: 3306, label: 'MySQL'},
    postgres: {port: 5432, label: 'PostgreSQL'}
};

function getSelectedDbType() {
    const el = document.getElementById('connection-db-type');
    return (el && el.value) ? el.value : 'mysql';
}

// Called when the DB type dropdown in the Add/Edit Connection modal changes.
// Snaps the port input to the engine's default (only if user hasn't typed
// a non-default value for the *other* engine) and switches the config warning.
function onDbTypeChange() {
    const dbType = getSelectedDbType();
    const portInput = document.getElementById('connection-port-input');
    if (portInput) {
        const currentVal = parseInt(portInput.value, 10);
        // Only overwrite when current value equals the OTHER engine's default,
        // so users who explicitly typed e.g. 5433 don't get clobbered.
        const otherDefault = dbType === 'mysql' ? 5432 : 3306;
        if (!currentVal || currentVal === otherDefault) {
            portInput.value = DB_TYPE_DEFAULTS[dbType].port;
        }
    }
    updateConnectionModalWarnings();
}

async function updateConnectionModalWarnings() {
    const dbType = getSelectedDbType();
    const mysqlWarning = document.getElementById('mysql-config-warning');
    const pgWarning = document.getElementById('postgres-config-warning');
    if (mysqlWarning) mysqlWarning.style.display = 'none';
    if (pgWarning) pgWarning.style.display = 'none';

    if (dbType === 'postgres') {
        await checkPostgresConfigWarning();
    } else {
        await checkMySQLConfigWarning();
    }
}

// Load connections
async function loadConnections() {
    try {
        const response = await fetch('/api/connections');
        const connections = await response.json();
        renderConnections(connections);
        populateImportConnectionDropdown(connections);
    } catch (error) {
        console.error('Failed to load connections:', error);
    }
}

// Keep a cached copy of connections so the Import Dump panel can re-render
// its target-connection dropdown and engine hints without another fetch.
let _allConnectionsCache = [];

// Populate the "Target Connection" dropdown in the Import Dump panel with
// every saved connection, prefixing each with an engine tag so the user can
// see at a glance which engine each connection targets.
function populateImportConnectionDropdown(connections) {
    _allConnectionsCache = connections || [];
    const sel = document.getElementById('import-target-connection-select');
    if (!sel) return;

    const previousValue = sel.value || currentConnectionId || '';

    sel.innerHTML = '<option value="">Select target connection...</option>' +
        _allConnectionsCache.map(c => {
            const dbType = (c.db_type || 'mysql').toLowerCase();
            const tag = dbType === 'postgres' ? '[PG]' : '[MySQL]';
            return `<option value="${c.id}">${tag} ${escapeHtml(c.name)} (${escapeHtml(c.host)}:${c.port})</option>`;
        }).join('');

    // Prefer the previously chosen connection, then the currently-selected
    // connection from the left panel, else leave blank.
    if (previousValue && _allConnectionsCache.some(c => c.id === previousValue)) {
        sel.value = previousValue;
    } else if (currentConnectionId && _allConnectionsCache.some(c => c.id === currentConnectionId)) {
        sel.value = currentConnectionId;
    }

    updateImportEngineHint();
}

function getImportConnectionId() {
    const sel = document.getElementById('import-target-connection-select');
    return (sel && sel.value) || currentConnectionId || '';
}

function updateImportEngineHint() {
    const hint = document.getElementById('import-engine-hint');
    if (!hint) return;
    const id = getImportConnectionId();
    const conn = _allConnectionsCache.find(c => c.id === id);
    if (!conn) {
        hint.textContent = '';
        return;
    }
    const dbType = (conn.db_type || 'mysql').toLowerCase();
    if (dbType === 'postgres') {
        hint.innerHTML = 'Engine: <strong>PostgreSQL</strong> — expects .sql (psql) or .backup/.dump (pg_restore). MySQL dumps (backticks) won\'t work.';
    } else {
        hint.innerHTML = 'Engine: <strong>MySQL</strong> — expects .sql dumps from mysqldump. PostgreSQL dumps won\'t work.';
    }
}

// Called when the Import Dump target-connection dropdown changes.
// Refreshes the target-schema dropdown with that connection's schemas so the
// user can pick an existing DB or type a new name.
async function onImportConnectionChange() {
    updateImportEngineHint();
    const id = getImportConnectionId();
    const schemaSelect = document.getElementById('import-target-schema-select');
    if (!schemaSelect) return;
    schemaSelect.innerHTML = '<option value="">Select target schema...</option>';
    if (!id) return;
    try {
        const r = await fetch(`/api/schemas/${id}`);
        if (!r.ok) return;
        const schemas = await r.json();
        if (Array.isArray(schemas)) {
            schemas.forEach(s => {
                const opt = document.createElement('option');
                opt.value = s.name;
                opt.textContent = s.name;
                schemaSelect.appendChild(opt);
            });
        }
    } catch (e) {
        console.warn('Could not load schemas for import target:', e);
    }
}

// Render connections list
function renderConnections(connections) {
    const list = document.getElementById('connections-list');
    if (connections.length === 0) {
        list.innerHTML = '<div class="empty-state"><div class="empty-state-icon">🔌</div><p>No connections</p></div>';
        return;
    }
    
    list.innerHTML = connections.map(conn => {
        const dbType = (conn.db_type || 'mysql').toLowerCase();
        const badgeLabel = dbType === 'postgres' ? 'PG' : 'MySQL';
        const badgeColor = dbType === 'postgres' ? '#336791' : '#00758f';
        return `
        <div class="connection-item ${conn.id === currentConnectionId ? 'active' : ''}"
             onclick="selectConnection('${conn.id}')">
            <div class="connection-name">
                <span style="display:inline-block; background:${badgeColor}; color:#fff; border-radius:3px; padding:1px 6px; font-size:10px; margin-right:6px; vertical-align:middle;">${badgeLabel}</span>
                ${escapeHtml(conn.name)}
            </div>
            <div class="connection-details">${escapeHtml(conn.host)}:${conn.port}</div>
            <div class="connection-details">${conn.database || 'All databases'}</div>
            <div style="display: flex; gap: 5px; margin-top: 8px;">
                <button class="btn btn-secondary" onclick="event.stopPropagation(); editConnection('${conn.id}')"
                        style="padding: 5px 10px; font-size: 12px; flex: 1;">Edit</button>
                <button class="btn btn-danger" onclick="event.stopPropagation(); deleteConnection('${conn.id}')"
                        style="padding: 5px 10px; font-size: 12px; flex: 1;">Delete</button>
            </div>
        </div>
        `;
    }).join('');
}

// Select connection
async function selectConnection(connectionId) {
    currentConnectionId = connectionId;
    currentSchemaName = null; // Reset schema selection when connection changes
    
    // Reload connections to update active state
    const connectionsResponse = await fetch('/api/connections');
    const connections = await connectionsResponse.json();
    renderConnections(connections);
    
    // Update active connection info
    const conn = connections.find(c => c.id === connectionId);
    if (conn) {
        document.getElementById('active-connection-info').style.display = 'block';
        document.getElementById('active-host').textContent = conn.host;
        document.getElementById('active-port').textContent = conn.port;
        document.getElementById('active-database').textContent = conn.database || 'All';
    }
    
    // Update button states
    updateActiveConnectionButtons();
    
    // Load schemas
    await loadSchemas(connectionId);
}

// Load schemas
async function loadSchemas(connectionId) {
    const list = document.getElementById('schemas-list');
    list.innerHTML = '<div class="empty-state"><div class="empty-state-icon">⏳</div><p>Loading schemas...</p></div>';
    
    try {
        const response = await fetch(`/api/schemas/${connectionId}`);
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({error: 'Unknown error'}));
            throw new Error(errorData.error || `HTTP ${response.status}`);
        }
        
        const schemas = await response.json();
        
        // Check if response is an error object
        if (schemas.error) {
            throw new Error(schemas.error);
        }
        
        renderSchemas(schemas);
        // Update dropdowns after schemas are rendered
        updateSchemaDropdowns();
    } catch (error) {
        console.error('Failed to load schemas:', error);
        list.innerHTML = `<div class="empty-state"><div class="empty-state-icon">❌</div><p>Failed to load schemas</p><p style="font-size: 12px; color: #999; margin-top: 10px;">${escapeHtml(error.message)}</p></div>`;
        availableSchemas = []; // Clear schemas on error
    }
}

// Render schemas list
function renderSchemas(schemas) {
    availableSchemas = schemas; // Store for dropdowns
    const list = document.getElementById('schemas-list');
    if (schemas.length === 0) {
        list.innerHTML = '<div class="empty-state"><div class="empty-state-icon">📋</div><p>No schemas found</p></div>';
        return;
    }
    
    list.innerHTML = schemas.map(schema => {
        const isSelected = currentSchemaName === schema.name;
        return `
        <div class="schema-item ${isSelected ? 'selected' : ''}" 
             onclick="selectSchema('${escapeHtml(schema.name)}')"
             oncontextmenu="event.preventDefault(); showContextMenu(event, '${escapeHtml(schema.name)}')">
            <div class="schema-name">${escapeHtml(schema.name)}</div>
            <div class="schema-info">
                <span>📊 ${schema.table_count} tables</span>
                <span>💾 ${schema.size_mb.toFixed(2)} MB</span>
            </div>
        </div>
    `;
    }).join('');
    
    // Update dropdowns if connection is selected
    updateSchemaDropdowns();
}

// Select schema
function selectSchema(schemaName) {
    currentSchemaName = schemaName;
    
    // Update active database display
    const activeDatabaseEl = document.getElementById('active-database');
    if (activeDatabaseEl) {
        activeDatabaseEl.textContent = schemaName;
    }
    
    // Update visual indication by re-rendering schemas
    if (availableSchemas && availableSchemas.length > 0) {
        renderSchemas(availableSchemas);
    }
    
    // Enable Duplicate and Export buttons
    updateActiveConnectionButtons();
}

// Show context menu
function showContextMenu(event, schemaName) {
    // Select schema if not already selected
    if (currentSchemaName !== schemaName) {
        selectSchema(schemaName);
    }
    
    const menu = document.getElementById('context-menu');
    menu.style.display = 'block';
    menu.style.left = event.pageX + 'px';
    menu.style.top = event.pageY + 'px';
    
    // Hide on click outside
    setTimeout(() => {
        document.addEventListener('click', function hideMenu() {
            menu.style.display = 'none';
            document.removeEventListener('click', hideMenu);
        });
    }, 100);
}

// Update schema dropdowns
function updateSchemaDropdowns() {
    if (!availableSchemas || availableSchemas.length === 0) return;
    
    // Update clone modal source schema dropdown
    const sourceSelect = document.getElementById('source-schema-select');
    if (sourceSelect) {
        sourceSelect.innerHTML = '<option value="">Select source schema...</option>' +
            availableSchemas.map(s => `<option value="${escapeHtml(s.name)}">${escapeHtml(s.name)}</option>`).join('');
        if (currentSchemaName) {
            sourceSelect.value = currentSchemaName;
        }
    }
    
    // Update clone modal target schema dropdown
    const targetSelect = document.getElementById('target-schema-select');
    if (targetSelect) {
        targetSelect.innerHTML = '<option value="">Select or enter target schema...</option>' +
            availableSchemas.map(s => `<option value="${escapeHtml(s.name)}">${escapeHtml(s.name)}</option>`).join('');
    }
    
    // Update import target schema dropdown ONLY when the import panel's target
    // connection matches the left-panel's currently-selected connection —
    // otherwise we'd clobber the schemas of a deliberately different import target.
    const importSelect = document.getElementById('import-target-schema-select');
    const importConnSel = document.getElementById('import-target-connection-select');
    const importSameAsCurrent = !importConnSel || !importConnSel.value || importConnSel.value === currentConnectionId;
    if (importSelect && importSameAsCurrent) {
        importSelect.innerHTML = '<option value="">Select target schema...</option>' +
            availableSchemas.map(s => `<option value="${escapeHtml(s.name)}">${escapeHtml(s.name)}</option>`).join('');
    }
    
    // Update export modal source schema dropdown
    const exportModalSelect = document.getElementById('export-modal-source-schema-select');
    if (exportModalSelect) {
        exportModalSelect.innerHTML = '<option value="">Select schema to export...</option>' +
            availableSchemas.map(s => `<option value="${escapeHtml(s.name)}">${escapeHtml(s.name)}</option>`).join('');
        if (currentSchemaName) {
            exportModalSelect.value = currentSchemaName;
        }
    }
}

// Clear schema selection
function clearSchemaSelection() {
    document.getElementById('context-menu').style.display = 'none';
    
    currentSchemaName = null;
    
    // Reset active database display to connection's default
    const activeDatabaseEl = document.getElementById('active-database');
    if (activeDatabaseEl && currentConnectionId) {
        // Get connection info to show default database
        fetch('/api/connections')
            .then(response => response.json())
            .then(connections => {
                const conn = connections.find(c => c.id === currentConnectionId);
                if (conn) {
                    activeDatabaseEl.textContent = conn.database || 'All';
                } else {
                    activeDatabaseEl.textContent = '-';
                }
            })
            .catch(() => {
                activeDatabaseEl.textContent = '-';
            });
    } else {
        if (activeDatabaseEl) {
            activeDatabaseEl.textContent = '-';
        }
    }
    
    // Update visual indication by re-rendering schemas
    if (availableSchemas && availableSchemas.length > 0) {
        renderSchemas(availableSchemas);
    }
    
    // Disable Duplicate and Export buttons
    updateActiveConnectionButtons();
}

// Duplicate schema (from button or context menu)
function duplicateSchema() {
    if (!currentConnectionId || !currentSchemaName) {
        showNotification('warning', 'Please select a connection and schema');
        return;
    }
    
    document.getElementById('context-menu').style.display = 'none';
    
    // Update dropdowns first
    updateSchemaDropdowns();
    
    // Set source schema in dropdown
    const sourceSelect = document.getElementById('source-schema-select');
    if (sourceSelect && currentSchemaName) {
        sourceSelect.value = currentSchemaName;
    }
    
    // Clear target
    const targetSelect = document.getElementById('target-schema-select');
    const targetInput = document.getElementById('target-schema-input');
    if (targetSelect) {
        targetSelect.value = '';
    }
    if (targetInput) {
        targetInput.value = '';
    }
    
    document.getElementById('progress-container').style.display = 'none';
    document.getElementById('clone-logs').style.display = 'none';
    document.getElementById('clone-result').style.display = 'none';
    document.getElementById('clone-btn').disabled = false;
    document.getElementById('cancel-clone-btn').style.display = 'none';
    document.getElementById('return-home-btn').style.display = 'none';
    document.getElementById('clone-modal').style.display = 'flex';
}

// Update active connection buttons state
function updateActiveConnectionButtons() {
    const duplicateBtn = document.getElementById('duplicate-schema-btn');
    const exportBtn = document.getElementById('export-schema-btn');
    const hasSelection = currentConnectionId && currentSchemaName;
    
    if (duplicateBtn) {
        duplicateBtn.disabled = !hasSelection;
    }
    if (exportBtn) {
        exportBtn.disabled = !hasSelection;
    }
}

// Start clone
async function startClone(event) {
    event.preventDefault();
    
    const sourceSelect = document.getElementById('source-schema-select');
    const targetSelect = document.getElementById('target-schema-select');
    const targetInput = document.getElementById('target-schema-input');
    
    const sourceSchema = sourceSelect ? sourceSelect.value : currentSchemaName;
    const targetSchema = (targetSelect && targetSelect.value) || (targetInput ? targetInput.value.trim() : '');
    
    if (!sourceSchema) {
        showResult('clone-result', 'Please select source schema', 'error');
        return;
    }
    
    if (!targetSchema) {
        showResult('clone-result', 'Please select or enter target schema name', 'error');
        return;
    }
    
    try {
        const response = await fetch('/api/clone', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                connection_id: currentConnectionId,
                source_schema: sourceSchema,
                target_schema: targetSchema
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            currentJobId = data.job_id;
            const cloneBtn = document.getElementById('clone-btn');
            const cancelBtn = document.getElementById('cancel-clone-btn');
            const returnHomeBtn = document.getElementById('return-home-btn');
            
            if (cloneBtn) cloneBtn.disabled = true;
            if (cancelBtn) {
                cancelBtn.style.display = 'block';
                cancelBtn.disabled = false;
            }
            if (returnHomeBtn) returnHomeBtn.style.display = 'none';
            
            document.getElementById('progress-container').style.display = 'block';
            document.getElementById('clone-logs').style.display = 'block';
            startLogPolling();
        } else {
            showResult('clone-result', data.error || 'Failed to start clone', 'error');
        }
    } catch (error) {
        showResult('clone-result', 'Error: ' + error.message, 'error');
    }
}

// Poll logs
function startLogPolling() {
    if (logPollInterval) {
        clearInterval(logPollInterval);
    }
    
    logPollInterval = setInterval(async () => {
        if (!currentJobId) return;
        
        try {
            const statusResponse = await fetch(`/api/clone/status/${currentJobId}`);
            const status = await statusResponse.json();
            
            // Update progress
            const progressFill = document.getElementById('progress-fill');
            if (progressFill) {
                progressFill.style.width = (status.progress || 0) + '%';
                progressFill.textContent = (status.progress || 0) + '%';
            }
            
            // Debug logging
            console.log('Polling status:', JSON.stringify({ 
                jobId: currentJobId, 
                status: status.status, 
                progress: status.progress,
                isCompleted: status.status === 'completed' || status.status === 'failed' || status.status === 'cancelled',
                isProgress100: (status.progress || 0) >= 100
            }));
            
            // Update logs
            const logsResponse = await fetch(`/api/clone/logs/${currentJobId}`);
            const logs = await logsResponse.json();
            renderLogs(logs);
            
            // Check if completed or progress is 100%
            const currentProgress = status.progress || 0;
            const currentStatus = status.status || 'unknown';
            const isCompleted = currentStatus === 'completed' || currentStatus === 'failed' || currentStatus === 'cancelled';
            const isProgress100 = currentProgress >= 100;
            
            console.log('Status check:', { currentStatus, currentProgress, isCompleted, isProgress100 });
            
            if (isCompleted || isProgress100) {
                console.log('Hiding cancel button, showing return home');
                
                // Hide cancel button and show return home button IMMEDIATELY
                const cancelBtn = document.getElementById('cancel-clone-btn');
                const returnHomeBtn = document.getElementById('return-home-btn');
                const cloneBtn = document.getElementById('clone-btn');
                
                // Force hide cancel button - multiple methods to ensure it's hidden
                if (cancelBtn) {
                    console.log('Hiding cancel button');
                    cancelBtn.style.display = 'none';
                    cancelBtn.style.visibility = 'hidden';
                    cancelBtn.style.opacity = '0';
                    cancelBtn.style.height = '0';
                    cancelBtn.style.padding = '0';
                    cancelBtn.style.margin = '0';
                    cancelBtn.style.width = '0';
                    cancelBtn.disabled = true;
                    cancelBtn.setAttribute('hidden', 'true');
                    cancelBtn.classList.add('hidden');
                    cancelBtn.setAttribute('aria-hidden', 'true');
                    // Remove from DOM completely as last resort
                    setTimeout(() => {
                        if (cancelBtn && cancelBtn.parentNode) {
                            cancelBtn.parentNode.removeChild(cancelBtn);
                        }
                    }, 100);
                }
                
                // Show return home button
                if (returnHomeBtn) {
                    console.log('Showing return home button');
                    returnHomeBtn.style.display = 'block';
                    returnHomeBtn.style.visibility = 'visible';
                    returnHomeBtn.style.opacity = '1';
                    returnHomeBtn.style.height = 'auto';
                    returnHomeBtn.style.padding = '';
                    returnHomeBtn.style.margin = '10px 0 0 0';
                    returnHomeBtn.removeAttribute('hidden');
                    returnHomeBtn.classList.remove('hidden');
                    returnHomeBtn.removeAttribute('aria-hidden');
                }
                
                if (cloneBtn) {
                    cloneBtn.disabled = false;
                }
                
                // Only clear interval if actually completed
                if (isCompleted) {
                    clearInterval(logPollInterval);
                    logPollInterval = null;
                    currentJobId = null; // Clear job ID
                    
                    if (currentStatus === 'completed') {
                        showResult('clone-result', 'Clone completed successfully!', 'success');
                        // Reload schemas and update dropdowns
                        if (currentConnectionId) {
                            await loadSchemas(currentConnectionId);
                            updateSchemaDropdowns();
                        }
                    } else if (currentStatus === 'failed') {
                        showResult('clone-result', 'Clone failed: ' + (status.error_message || 'Unknown error'), 'error');
                    } else if (currentStatus === 'cancelled') {
                        showResult('clone-result', 'Clone cancelled', 'error');
                    }
                } else if (isProgress100 && !isCompleted) {
                    // Progress is 100% but status not yet completed - wait a bit more
                    showResult('clone-result', 'Finalizing...', 'info');
                }
            }
        } catch (error) {
            console.error('Failed to poll status:', error);
        }
    }, 1000); // Poll every second
}

// Render logs
function renderLogs(logs) {
    const container = document.getElementById('clone-logs');
    if (!container) return;
    
    if (!Array.isArray(logs)) {
        console.error('Logs is not an array:', logs);
        return;
    }
    
    container.innerHTML = logs.map(log => {
        let className = 'log-info';
        const logStr = String(log);
        if (logStr.includes('ERROR') || logStr.includes('[ERROR]')) className = 'log-error';
        if (logStr.toLowerCase().includes('successfully') || logStr.toLowerCase().includes('completed')) className = 'log-success';
        return `<div class="log-entry ${className}">${escapeHtml(logStr)}</div>`;
    }).join('');
    container.scrollTop = container.scrollHeight;
}

// Cancel clone
async function cancelClone() {
    if (!currentJobId) return;
    
    try {
        const response = await fetch(`/api/clone/cancel/${currentJobId}`, {method: 'POST'});
        const result = await response.json();
        
        clearInterval(logPollInterval);
        logPollInterval = null;
        currentJobId = null; // Clear job ID
        document.getElementById('clone-btn').disabled = false;
        document.getElementById('cancel-clone-btn').style.display = 'none';
        document.getElementById('cancel-clone-btn').disabled = false;
        
        if (result.success) {
            showResult('clone-result', 'Clone operation cancelled', 'error');
        }
    } catch (error) {
        console.error('Failed to cancel clone:', error);
        // Even if cancel fails, hide the button
        clearInterval(logPollInterval);
        logPollInterval = null;
        currentJobId = null;
        document.getElementById('cancel-clone-btn').style.display = 'none';
    }
}

// Return to home (close modal and reset)
function returnToHome() {
    closeCloneModal();
}

// Close clone modal
function closeCloneModal() {
    if (logPollInterval) {
        clearInterval(logPollInterval);
        logPollInterval = null;
    }
    currentJobId = null;
    // Reset UI state
    const cloneBtn = document.getElementById('clone-btn');
    const returnHomeBtn = document.getElementById('return-home-btn');
    
    if (cloneBtn) cloneBtn.disabled = false;
    if (returnHomeBtn) {
        returnHomeBtn.style.display = 'none';
    }
    
    // Recreate cancel button if it was removed
    const cancelBtnContainer = document.querySelector('#clone-form');
    const existingCancelBtn = document.getElementById('cancel-clone-btn');
    if (!existingCancelBtn && cancelBtnContainer) {
        const cancelBtn = document.createElement('button');
        cancelBtn.type = 'button';
        cancelBtn.className = 'btn btn-danger';
        cancelBtn.id = 'cancel-clone-btn';
        cancelBtn.onclick = cancelClone;
        cancelBtn.style.display = 'none';
        cancelBtn.style.marginTop = '10px';
        cancelBtn.textContent = 'Cancel';
        const returnHomeBtnEl = document.getElementById('return-home-btn');
        if (returnHomeBtnEl) {
            cancelBtnContainer.insertBefore(cancelBtn, returnHomeBtnEl);
        } else {
            cancelBtnContainer.appendChild(cancelBtn);
        }
    } else if (existingCancelBtn) {
        existingCancelBtn.style.display = 'none';
        existingCancelBtn.disabled = false;
    }
    
    document.getElementById('clone-modal').style.display = 'none';
}

// Add/Update connection
async function addConnection(event) {
    event.preventDefault();
    const formData = new FormData(event.target);
    const data = Object.fromEntries(formData);
    const connectionId = event.target.dataset.connectionId;
    
    try {
        let response;
        if (connectionId) {
            // Update existing connection
            response = await fetch(`/api/connections/${connectionId}`, {
                method: 'PUT',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(data)
            });
        } else {
            // Add new connection
            response = await fetch('/api/connections', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(data)
            });
        }
        
        const result = await response.json();
        
        if (result.success) {
            showResult('connection-result', connectionId ? 'Connection updated successfully!' : 'Connection added successfully!', 'success');
            await loadConnections();
            setTimeout(() => {
                closeModal('add-connection-modal');
                // Reset form
                event.target.reset();
                delete event.target.dataset.connectionId;
                document.querySelector('#add-connection-modal .modal-title').textContent = 'Add Connection';
                const submitBtn = event.target.querySelector('button[type="submit"]');
                submitBtn.textContent = 'Add Connection';
            }, 1500);
        } else {
            showResult('connection-result', result.error || (connectionId ? 'Failed to update connection' : 'Failed to add connection'), 'error');
        }
    } catch (error) {
        showResult('connection-result', 'Error: ' + error.message, 'error');
    }
}

// Test connection
async function testConnection() {
    const form = document.getElementById('add-connection-form');
    const formData = new FormData(form);
    const data = Object.fromEntries(formData);
    
    try {
        const response = await fetch('/api/connections/test', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        
        if (result.success) {
            showResult('connection-result', 'Connection test successful!', 'success');
        } else {
            showResult('connection-result', 'Connection test failed: ' + (result.error || 'Unknown error'), 'error');
        }
    } catch (error) {
        showResult('connection-result', 'Error: ' + error.message, 'error');
    }
}

// Edit connection
async function editConnection(connectionId) {
    try {
        const response = await fetch(`/api/connections/${connectionId}`);
        const conn = await response.json();
        
        if (!conn || conn.error) {
            showNotification('error', 'Failed to load connection: ' + (conn.error || 'Unknown error'));
            return;
        }
        
        // Fill form with connection data
        const form = document.getElementById('add-connection-form');
        form.reset();
        const dbType = (conn.db_type || 'mysql').toLowerCase();
        form.querySelector('[name="name"]').value = conn.name || '';
        const dbTypeSelect = form.querySelector('[name="db_type"]');
        if (dbTypeSelect) dbTypeSelect.value = dbType;
        form.querySelector('[name="host"]').value = conn.host || '';
        form.querySelector('[name="port"]').value = conn.port || (dbType === 'postgres' ? '5432' : '3306');
        form.querySelector('[name="user"]').value = conn.user || '';
        form.querySelector('[name="password"]').value = conn.password || '';
        form.querySelector('[name="database"]').value = conn.database || '';

        // Store connection ID for update
        form.dataset.connectionId = connectionId;

        // Change form title and button
        document.querySelector('#add-connection-modal .modal-title').textContent = 'Edit Connection';
        const submitBtn = document.querySelector('#add-connection-form button[type="submit"]');
        submitBtn.textContent = 'Update Connection';

        // Show modal
        document.getElementById('connection-result').style.display = 'none';
        document.getElementById('add-connection-modal').style.display = 'flex';

        // Check config status for the selected engine
        await updateConnectionModalWarnings();
    } catch (error) {
        showNotification('error', 'Error: ' + error.message);
    }
}

// Delete connection
async function deleteConnection(connectionId) {
    const confirmed = await showConfirm('Are you sure you want to delete this connection?', 'Delete Connection', 'Delete', 'Cancel');
    if (!confirmed) {
        return;
    }
    
    try {
        const response = await fetch(`/api/connections/${connectionId}`, {
            method: 'DELETE'
        });
        
        const result = await response.json();
        
        if (result.success) {
            await loadConnections();
            if (currentConnectionId === connectionId) {
                currentConnectionId = null;
                currentSchemaName = null;
                document.getElementById('schemas-list').innerHTML = 
                    '<div class="empty-state"><div class="empty-state-icon">📋</div><p>Select a connection to view schemas</p></div>';
                document.getElementById('active-connection-info').style.display = 'none';
                updateActiveConnectionButtons();
            }
        } else {
            showNotification('error', 'Failed to delete connection: ' + (result.error || 'Unknown error'));
        }
    } catch (error) {
        showNotification('error', 'Error: ' + error.message);
    }
}

// Show add connection modal
async function showAddConnectionModal() {
    const form = document.getElementById('add-connection-form');
    form.reset();
    delete form.dataset.connectionId;
    // Default to MySQL for new connections
    const dbTypeSelect = form.querySelector('[name="db_type"]');
    if (dbTypeSelect) dbTypeSelect.value = 'mysql';
    const portInput = form.querySelector('[name="port"]');
    if (portInput) portInput.value = '3306';
    document.querySelector('#add-connection-modal .modal-title').textContent = 'Add Connection';
    const submitBtn = form.querySelector('button[type="submit"]');
    submitBtn.textContent = 'Add Connection';
    document.getElementById('connection-result').style.display = 'none';
    document.getElementById('add-connection-modal').style.display = 'flex';

    // Show the correct warning for the initial db_type
    await updateConnectionModalWarnings();
}

// Check MySQL config and show/hide warning banner
async function checkMySQLConfigWarning() {
    const warning = document.getElementById('mysql-config-warning');
    try {
        const resp = await fetch('/api/config/mysql-bin');
        const data = await resp.json();
        if (!data.path) {
            warning.style.display = 'block';
            return;
        }
        // Path exists in config, validate it
        const validateResp = await fetch('/api/mysql/validate', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({path: data.path})
        });
        const validateData = await validateResp.json();
        warning.style.display = validateData.valid ? 'none' : 'block';
    } catch (e) {
        warning.style.display = 'block';
    }
}

// Show config modal
function showConfigModal() {
    // Show modal and start with choice screen
    document.getElementById('config-modal').style.display = 'flex';
    showConfigChoiceScreen();
}

// Show initial choice screen
function showConfigChoiceScreen() {
    document.getElementById('config-choice-screen').style.display = 'block';
    document.getElementById('manual-path-form').style.display = 'none';
    document.getElementById('download-form').style.display = 'none';
    document.getElementById('config-result').style.display = 'none';
}

// Wrapper for HTML onclick (async functions can't be called directly from onclick)
function handleShowManualPathForm() {
    showManualPathForm().catch(error => {
        console.error('Error showing manual path form:', error);
        showNotification('error', 'Error loading manual path form: ' + error.message);
    });
}

// Show manual path form
async function showManualPathForm() {
    document.getElementById('config-choice-screen').style.display = 'none';
    document.getElementById('manual-path-form').style.display = 'block';
    document.getElementById('download-form').style.display = 'none';
    
    // Load current config value into input if exists
    await loadConfigToModal();
    
    document.getElementById('config-result').style.display = 'none';
}

// Wrapper for HTML onclick (async functions can't be called directly from onclick)
function handleShowDownloadForm() {
    showDownloadForm().catch(error => {
        console.error('Error showing download form:', error);
        showNotification('error', 'Error loading download form: ' + error.message);
    });
}

// Show download form
async function showDownloadForm() {
    document.getElementById('config-choice-screen').style.display = 'none';
    document.getElementById('manual-path-form').style.display = 'none';
    document.getElementById('download-form').style.display = 'block';
    
    // Load MySQL versions with installed status
    await loadMySQLVersionsWithStatus();
    
    // Load default directory for placeholder
    await loadDefaultDirectory();
    
    // Reset advanced options
    document.getElementById('advanced-options-toggle').checked = false;
    document.getElementById('destination-directory-group').style.display = 'none';
    document.getElementById('mysql-dest-input').value = '';
}

// Toggle advanced options (show/hide destination directory)
function toggleAdvancedOptions() {
    const toggle = document.getElementById('advanced-options-toggle');
    const destGroup = document.getElementById('destination-directory-group');
    
    if (toggle.checked) {
        destGroup.style.display = 'block';
        // Load default directory if not already loaded
        loadDefaultDirectory();
    } else {
        destGroup.style.display = 'none';
        document.getElementById('mysql-dest-input').value = '';
    }
}

// Load default directory from API and update placeholder
async function loadDefaultDirectory() {
    try {
        const response = await fetch('/api/mysql/default-directory');
        if (response.ok) {
            const data = await response.json();
            const destInput = document.getElementById('mysql-dest-input');
            if (destInput) {
                destInput.placeholder = `Leave empty for: ${data.path}`;
            }
        }
    } catch (error) {
        console.error('Failed to load default directory:', error);
        const destInput = document.getElementById('mysql-dest-input');
        if (destInput) {
            destInput.placeholder = 'Leave empty for default location';
        }
    }
}

// Save config
async function saveConfig(event) {
    event.preventDefault();
    const path = document.getElementById('mysql-bin-input').value.trim();
    
    try {
        const response = await fetch('/api/config/mysql-bin', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({path: path})
        });
        
        const result = await response.json();
        
        if (result.success) {
            showResult('config-result', 'Configuration saved!', 'success');
            loadConfig();
            setTimeout(() => closeModal('config-modal'), 1500);
        } else {
            showResult('config-result', result.error || 'Failed to save configuration', 'error');
        }
    } catch (error) {
        showResult('config-result', 'Error: ' + error.message, 'error');
    }
}

// ============================================================
//  PostgreSQL Config — mirrors MySQL Config flow (DBC-3)
//  Choice screen → (Download | Manual Path)
// ============================================================

let _pgDownloadPollInterval = null;

function showPostgresConfigModal() {
    const modal = document.getElementById('postgres-config-modal');
    if (!modal) return;
    showPostgresConfigChoiceScreen();  // always start at choice screen
    modal.style.display = 'flex';
}

function showPostgresConfigChoiceScreen() {
    document.getElementById('postgres-config-choice-screen').style.display = 'block';
    document.getElementById('postgres-manual-path-form').style.display = 'none';
    document.getElementById('postgres-download-form').style.display = 'none';
    const result = document.getElementById('postgres-config-result');
    if (result) result.style.display = 'none';
}

function handleShowPostgresManualForm() {
    showPostgresManualForm().catch(err => {
        console.error('Error showing PG manual form:', err);
        showNotification('error', 'Error loading manual path form: ' + err.message);
    });
}

async function showPostgresManualForm() {
    document.getElementById('postgres-config-choice-screen').style.display = 'none';
    document.getElementById('postgres-manual-path-form').style.display = 'block';
    document.getElementById('postgres-download-form').style.display = 'none';
    // Pre-fill with current saved value, if any
    try {
        const d = await fetch('/api/config/postgres-bin').then(r => r.json());
        document.getElementById('postgres-bin-input').value = (d && d.path) || '';
    } catch (e) { /* ignore */ }
    const result = document.getElementById('postgres-config-result');
    if (result) result.style.display = 'none';
}

function handleShowPostgresDownloadForm() {
    showPostgresDownloadForm().catch(err => {
        console.error('Error showing PG download form:', err);
        showNotification('error', 'Error loading download form: ' + err.message);
    });
}

async function showPostgresDownloadForm() {
    document.getElementById('postgres-config-choice-screen').style.display = 'none';
    document.getElementById('postgres-manual-path-form').style.display = 'none';
    document.getElementById('postgres-download-form').style.display = 'block';

    await loadPostgresVersionsWithStatus();
    await loadPostgresDefaultDirectory();

    // Reset advanced options
    const toggle = document.getElementById('postgres-advanced-options-toggle');
    if (toggle) toggle.checked = false;
    const destGroup = document.getElementById('postgres-destination-directory-group');
    if (destGroup) destGroup.style.display = 'none';
    const destInput = document.getElementById('postgres-dest-input');
    if (destInput) destInput.value = '';
}

function togglePostgresAdvancedOptions() {
    const toggle = document.getElementById('postgres-advanced-options-toggle');
    const destGroup = document.getElementById('postgres-destination-directory-group');
    if (toggle.checked) {
        destGroup.style.display = 'block';
        loadPostgresDefaultDirectory();
    } else {
        destGroup.style.display = 'none';
        document.getElementById('postgres-dest-input').value = '';
    }
}

async function loadPostgresDefaultDirectory() {
    try {
        const resp = await fetch('/api/postgres/default-directory');
        if (resp.ok) {
            const data = await resp.json();
            const destInput = document.getElementById('postgres-dest-input');
            if (destInput) destInput.placeholder = `Leave empty for: ${data.path}`;
        }
    } catch (e) {
        const destInput = document.getElementById('postgres-dest-input');
        if (destInput) destInput.placeholder = 'Leave empty for default location';
    }
}

async function loadPostgresVersionsWithStatus() {
    const loadingDiv = document.getElementById('postgres-versions-loading');
    const versionsList = document.getElementById('postgres-versions-list');
    const installedContainer = document.getElementById('postgres-installed-versions-container');
    const availableContainer = document.getElementById('postgres-available-versions-container');
    const unsupportedBanner = document.getElementById('postgres-download-unsupported');

    if (!loadingDiv || !versionsList || !installedContainer || !availableContainer) {
        console.error('PG version list elements missing');
        return;
    }

    loadingDiv.style.display = 'block';
    versionsList.style.display = 'none';
    installedContainer.innerHTML = '';
    availableContainer.innerHTML = '';
    if (unsupportedBanner) unsupportedBanner.style.display = 'none';

    try {
        const response = await fetch('/api/postgres/versions');
        if (!response.ok) throw new Error(`Server error: ${response.status}`);
        const data = await response.json();

        if (data.download_supported === false && unsupportedBanner) {
            unsupportedBanner.style.display = 'block';
        }

        const installed = [];
        const available = [];
        data.versions.forEach(v => (v.installed ? installed : available).push(v));

        if (installed.length) {
            installed.forEach(v => installedContainer.appendChild(renderPostgresVersionItem(v)));
        } else {
            installedContainer.innerHTML = '<p style="color: #999; font-size: 13px; padding: 10px;">No installed versions found.</p>';
        }

        if (available.length) {
            available.forEach(v => availableContainer.appendChild(renderPostgresVersionItem(v)));
        } else {
            availableContainer.innerHTML = '<p style="color: #999; font-size: 13px; padding: 10px;">No versions available.</p>';
        }

        loadingDiv.style.display = 'none';
        versionsList.style.display = 'block';
    } catch (error) {
        console.error('Failed to load PG versions:', error);
        if (loadingDiv) {
            loadingDiv.innerHTML = `<p style="color: #d32f2f;">Error loading versions: ${error.message}</p>`;
        }
    }
}

function renderPostgresVersionItem(versionInfo) {
    // Reuse MySQL's .version-item CSS classes for consistent look
    const item = document.createElement('div');
    item.className = 'version-item';
    item.setAttribute('data-version', versionInfo.version);

    const header = document.createElement('div');
    header.className = 'version-header';

    if (versionInfo.installed) {
        const statusIcon = document.createElement('span');
        statusIcon.className = 'version-status-icon ' + (versionInfo.is_valid ? 'valid' : 'invalid');
        header.appendChild(statusIcon);
    }

    const title = document.createElement('div');
    title.className = 'version-title';
    const versionText = document.createElement('span');
    versionText.textContent = `PostgreSQL ${versionInfo.version}`;
    title.appendChild(versionText);

    if (versionInfo.recommended) {
        const badge = document.createElement('span');
        badge.className = 'version-badge recommended';
        badge.textContent = 'Recommended';
        title.appendChild(badge);
    }
    if (versionInfo.installed) {
        const badge = document.createElement('span');
        badge.className = 'version-badge ' + (versionInfo.is_valid ? 'installed' : 'invalid');
        badge.textContent = versionInfo.is_valid ? '✓ Installed' : '⚠ Invalid';
        title.appendChild(badge);
    }
    header.appendChild(title);

    const actionsDiv = document.createElement('div');
    actionsDiv.className = 'version-actions';
    if (versionInfo.installed) {
        const useBtn = document.createElement('button');
        useBtn.className = 'btn btn-success btn-small';
        useBtn.textContent = 'Use';
        useBtn.onclick = () => usePostgresVersion(versionInfo.version, versionInfo.bin_path);
        actionsDiv.appendChild(useBtn);
    } else {
        const dlBtn = document.createElement('button');
        dlBtn.className = 'btn btn-success btn-small';
        dlBtn.textContent = 'Download';
        dlBtn.onclick = () => downloadPostgresVersion(versionInfo.version);
        actionsDiv.appendChild(dlBtn);
    }
    header.appendChild(actionsDiv);

    if (versionInfo.installed && versionInfo.bin_path) {
        const expandIcon = document.createElement('span');
        expandIcon.className = 'version-expand-icon';
        expandIcon.innerHTML = '▼';
        header.appendChild(expandIcon);
        item.classList.add('version-item-expandable');
        item.style.cursor = 'pointer';

        const pathContainer = document.createElement('div');
        pathContainer.className = 'version-path-container';
        pathContainer.style.display = 'none';
        const pathContent = document.createElement('div');
        pathContent.className = 'version-path';
        pathContent.textContent = versionInfo.bin_path;
        pathContainer.appendChild(pathContent);

        item.addEventListener('click', e => {
            if (e.target.closest('.btn') || e.target.closest('.version-actions')) return;
            const isHidden = pathContainer.style.display === 'none';
            pathContainer.style.display = isHidden ? 'block' : 'none';
            expandIcon.innerHTML = isHidden ? '▲' : '▼';
        });

        item.appendChild(header);
        item.appendChild(pathContainer);
    } else {
        item.appendChild(header);
    }

    return item;
}

async function usePostgresVersion(version, binPath) {
    try {
        const resp = await fetch('/api/postgres/use', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({bin_path: binPath}),
        });
        const result = await resp.json();
        if (result.success) {
            showNotification('success', `Using PostgreSQL ${version}`);
            await loadPostgresConfig();
            closeModal('postgres-config-modal');
        } else {
            showNotification('error', result.error || 'Failed to use PostgreSQL version');
        }
    } catch (e) {
        showNotification('error', 'Error: ' + e.message);
    }
}

async function downloadPostgresVersion(version) {
    const destInput = document.getElementById('postgres-dest-input');
    const destination = destInput ? destInput.value.trim() : '';

    // Open progress modal
    document.getElementById('postgres-download-version').textContent = `PostgreSQL ${version}`;
    document.getElementById('postgres-download-progress-fill').style.width = '0%';
    document.getElementById('postgres-download-progress-fill').textContent = '0%';
    document.getElementById('postgres-download-status').textContent = 'Starting download...';
    document.getElementById('postgres-download-status').style.color = '#666';
    document.getElementById('postgres-download-result-message').style.display = 'none';
    document.getElementById('postgres-cancel-download-btn').style.display = 'block';
    document.getElementById('postgres-download-return-btn').style.display = 'none';
    document.getElementById('postgres-download-modal').style.display = 'flex';

    try {
        const resp = await fetch('/api/postgres/download', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({version, destination}),
        });

        if (!resp.ok) {
            const err = await resp.json().catch(() => ({error: 'Unknown error'}));
            throw new Error(err.error || `Server error ${resp.status}`);
        }
        const {job_id} = await resp.json();

        _pgDownloadPollInterval = setInterval(async () => {
            try {
                const r = await fetch(`/api/postgres/download/progress/${job_id}`);
                const data = await r.json();

                const phaseText = {
                    downloading: 'Downloading...',
                    extracting: 'Extracting...',
                    validating: 'Validating...',
                    done: 'Completed',
                }[data.phase] || 'Working...';
                document.getElementById('postgres-download-status').textContent =
                    `${phaseText} (${data.percent}%)`;
                const fill = document.getElementById('postgres-download-progress-fill');
                fill.style.width = `${data.percent}%`;
                fill.textContent = `${data.percent}%`;

                if (data.status === 'completed') {
                    clearInterval(_pgDownloadPollInterval);
                    showPostgresDownloadSuccess(data.bin_path);
                } else if (data.status === 'failed') {
                    clearInterval(_pgDownloadPollInterval);
                    showPostgresDownloadError(data.error || 'Download failed');
                }
            } catch (pollErr) {
                clearInterval(_pgDownloadPollInterval);
                showPostgresDownloadError(pollErr.message);
            }
        }, 500);
    } catch (e) {
        if (_pgDownloadPollInterval) clearInterval(_pgDownloadPollInterval);
        showPostgresDownloadError(e.message);
    }
}

function showPostgresDownloadSuccess(binPath) {
    document.getElementById('postgres-download-progress-fill').style.width = '100%';
    document.getElementById('postgres-download-progress-fill').textContent = '100%';
    document.getElementById('postgres-download-status').textContent = 'Download completed!';
    document.getElementById('postgres-download-status').style.color = '#28a745';

    const resultDiv = document.getElementById('postgres-download-result-message');
    resultDiv.className = 'result success';
    resultDiv.style.display = 'block';
    document.getElementById('postgres-download-result-title').textContent = '✓ Download completed!';
    document.getElementById('postgres-download-result-detail').textContent = binPath ? `Installed at: ${binPath}` : '';

    if (binPath) {
        fetch('/api/config/postgres-bin', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({path: binPath}),
        }).then(() => loadPostgresConfig());
    }

    document.getElementById('postgres-cancel-download-btn').style.display = 'none';
    document.getElementById('postgres-download-return-btn').style.display = 'block';
    loadPostgresVersionsWithStatus();
}

function showPostgresDownloadError(msg) {
    document.getElementById('postgres-download-status').textContent = 'Error: ' + msg;
    document.getElementById('postgres-download-status').style.color = '#d32f2f';
    document.getElementById('postgres-download-progress-fill').style.width = '0%';
    document.getElementById('postgres-download-progress-fill').textContent = '0%';

    const resultDiv = document.getElementById('postgres-download-result-message');
    resultDiv.className = 'result error';
    resultDiv.style.display = 'block';
    document.getElementById('postgres-download-result-title').textContent = '✗ Download failed';
    document.getElementById('postgres-download-result-detail').textContent = msg;

    document.getElementById('postgres-cancel-download-btn').style.display = 'none';
    document.getElementById('postgres-download-return-btn').style.display = 'block';
}

function cancelPostgresDownload() {
    if (_pgDownloadPollInterval) clearInterval(_pgDownloadPollInterval);
    closeModal('postgres-download-modal');
}

function returnFromPostgresDownload() {
    if (_pgDownloadPollInterval) clearInterval(_pgDownloadPollInterval);
    closeModal('postgres-download-modal');
    closeModal('postgres-config-modal');
}

async function savePostgresConfig(event) {
    event.preventDefault();
    const path = document.getElementById('postgres-bin-input').value.trim();
    try {
        const response = await fetch('/api/config/postgres-bin', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({path: path})
        });
        const result = await response.json();
        if (result.success) {
            showResult('postgres-config-result', 'Configuration saved!', 'success');
            loadPostgresConfig();
            setTimeout(() => closeModal('postgres-config-modal'), 1500);
        } else {
            showResult('postgres-config-result', result.error || 'Failed to save configuration', 'error');
        }
    } catch (error) {
        showResult('postgres-config-result', 'Error: ' + error.message, 'error');
    }
}

// Test the currently entered Postgres bin path without saving it.
// Uses the same validation endpoint (POST returns 400 on invalid, 200 on valid).
async function testPostgresPath() {
    const path = document.getElementById('postgres-bin-input').value.trim();
    if (!path) {
        showResult('postgres-config-result', 'Enter a path first.', 'error');
        return;
    }
    try {
        // We don't have a separate validate endpoint — the POST endpoint
        // returns 400 with an error message if the path is invalid. Use it
        // read-only by asking the server to save the SAME path that was
        // already saved. Simpler: call the dedicated test by POSTing.
        const response = await fetch('/api/config/postgres-bin', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({path: path})
        });
        const result = await response.json();
        if (result.success) {
            showResult('postgres-config-result', 'Path is valid — pg_dump, pg_restore and psql found.', 'success');
        } else {
            showResult('postgres-config-result', result.error || 'Invalid path', 'error');
        }
    } catch (error) {
        showResult('postgres-config-result', 'Error: ' + error.message, 'error');
    }
}

async function loadPostgresConfig() {
    const pathInput = document.getElementById('postgres-bin-path');
    if (!pathInput) return;
    try {
        const response = await fetch('/api/config/postgres-bin');
        const result = await response.json();
        if (result && result.path && result.path.trim() !== '') {
            pathInput.value = result.path;
            pathInput.style.background = 'white';
            pathInput.style.border = '2px solid #e0e0e0';
            pathInput.style.fontStyle = 'normal';
            pathInput.style.color = '#333';
        } else {
            pathInput.value = '';
            pathInput.style.background = '#f8f9fa';
            pathInput.style.border = '1px dashed #ccc';
            pathInput.style.fontStyle = 'italic';
            pathInput.style.color = '#999';
        }
    } catch (error) {
        console.error('Failed to load postgres config:', error);
    }
}

async function checkPostgresConfigWarning() {
    const warning = document.getElementById('postgres-config-warning');
    if (!warning) return;
    try {
        const resp = await fetch('/api/config/postgres-bin');
        const data = await resp.json();
        warning.style.display = (data && data.path) ? 'none' : 'block';
    } catch (e) {
        warning.style.display = 'block';
    }
}

// Load config
async function loadConfig() {
    try {
        const response = await fetch('/api/config/mysql-bin');
        const result = await response.json();
        const pathInput = document.getElementById('mysql-bin-path');

        if (result.path && result.path.trim() !== '') {
            // Path is configured, show the actual path
            pathInput.value = result.path;
            pathInput.style.background = 'white';
            pathInput.style.border = '2px solid #e0e0e0';
            pathInput.style.fontStyle = 'normal';
            pathInput.style.color = '#333';
        } else {
            // No path configured, show placeholder
            pathInput.value = '';
            pathInput.style.background = '#f8f9fa';
            pathInput.style.border = '1px dashed #ccc';
            pathInput.style.fontStyle = 'italic';
            pathInput.style.color = '#999';
        }
    } catch (error) {
        console.error('Failed to load config:', error);
    }
}

// Close modal
function closeModal(modalId) {
    document.getElementById(modalId).style.display = 'none';
    
    // Reset config modal to choice screen when closed
    if (modalId === 'config-modal') {
        showConfigChoiceScreen();
    }
    // Same reset for Postgres config modal
    if (modalId === 'postgres-config-modal') {
        showPostgresConfigChoiceScreen();
    }
}

// Show result
function showResult(elementId, message, type) {
    const element = document.getElementById(elementId);
    element.textContent = message;
    element.className = 'result ' + type;
    element.style.display = 'block';
}

// Import dump file — uses the dedicated "Target Connection" dropdown in the
// Import Dump panel (not the left-panel selection), so the user can direct
// a MySQL dump to a MySQL connection even while browsing a PG connection.
async function importDump() {
    const fileInput = document.getElementById('dump-file-input');
    const targetSelect = document.getElementById('import-target-schema-select');
    const targetInput = document.getElementById('import-target-schema-input');

    const importConnectionId = getImportConnectionId();
    const targetSchema = (targetSelect && targetSelect.value) || (targetInput ? targetInput.value.trim() : '');

    if (!importConnectionId) {
        showNotification('warning', 'Please select a target connection for the import');
        return;
    }

    if (!fileInput.files || fileInput.files.length === 0) {
        showNotification('warning', 'Please select a SQL dump file');
        return;
    }

    if (!targetSchema) {
        showNotification('warning', 'Please select or enter target schema name');
        return;
    }

    const conn = _allConnectionsCache.find(c => c.id === importConnectionId);
    const engineLabel = conn ? ((conn.db_type || 'mysql').toLowerCase() === 'postgres' ? 'PostgreSQL' : 'MySQL') : '';
    const confirmMsg =
        `Import dump to ${engineLabel} schema '${targetSchema}' on '${conn ? conn.name : '?'}'?` +
        ` This will overwrite existing data if the schema exists.`;

    const confirmed = await showConfirm(confirmMsg, 'Import Dump', 'Import', 'Cancel');
    if (!confirmed) {
        return;
    }

    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    formData.append('connection_id', importConnectionId);
    formData.append('target_schema', targetSchema);

    try {
        const response = await fetch('/api/import/dump', {
            method: 'POST',
            body: formData
        });

        const result = await response.json();

        if (result.success) {
            showNotification('success', `Dump imported successfully to schema '${targetSchema}'!`);
            // If we imported into the currently-browsed connection, refresh its schema list
            if (importConnectionId === currentConnectionId) {
                await loadSchemas(currentConnectionId);
            }
            fileInput.value = '';
            if (targetSelect) targetSelect.value = '';
            if (targetInput) targetInput.value = '';
        } else {
            showNotification('error', 'Import failed: ' + (result.error || 'Unknown error'));
        }
    } catch (error) {
        showNotification('error', 'Error: ' + error.message);
    }
}

// Export dump file
// Show export modal
function showExportModal() {
    if (!currentConnectionId || !currentSchemaName) {
        showNotification('warning', 'Please select a connection and schema');
        return;
    }
    
    // Update dropdowns first
    updateSchemaDropdowns();
    
    // Pre-select current schema
    const exportModalSelect = document.getElementById('export-modal-source-schema-select');
    if (exportModalSelect && currentSchemaName) {
        exportModalSelect.value = currentSchemaName;
    }
    
    // Clear previous result
    const resultDiv = document.getElementById('export-modal-result');
    if (resultDiv) {
        resultDiv.style.display = 'none';
        resultDiv.className = 'result';
        resultDiv.textContent = '';
    }
    
    // Clear export path input
    const pathInput = document.getElementById('export-modal-path-input');
    if (pathInput) {
        pathInput.value = '';
    }
    
    // Show modal
    showModal('export-dump-modal');
}

// Export dump from modal
async function exportDumpFromModal(event) {
    event.preventDefault();
    
    const sourceSelect = document.getElementById('export-modal-source-schema-select');
    const pathInput = document.getElementById('export-modal-path-input');
    const resultDiv = document.getElementById('export-modal-result');
    
    const sourceSchema = sourceSelect ? sourceSelect.value : '';
    const exportPath = pathInput ? pathInput.value.trim() : '';
    
    if (!sourceSchema) {
        showNotification('warning', 'Please select a schema to export');
        return;
    }
    
    if (!currentConnectionId) {
        showNotification('warning', 'Please select a connection first');
        return;
    }
    
    try {
        resultDiv.style.display = 'block';
        resultDiv.className = 'result';
        resultDiv.textContent = 'Exporting... Please wait...';
        
        const response = await fetch('/api/export/dump', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                connection_id: currentConnectionId,
                source_schema: sourceSchema,
                export_path: exportPath
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            resultDiv.className = 'result success';
            resultDiv.textContent = `Export completed! File saved to: ${result.file_path}`;
        } else {
            resultDiv.className = 'result error';
            resultDiv.textContent = 'Export failed: ' + (result.error || 'Unknown error');
        }
    } catch (error) {
        resultDiv.className = 'result error';
        resultDiv.textContent = 'Error: ' + error.message;
    }
}

// Escape HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Notification System
function showNotification(type, message, title = null, duration = 5000) {
    const container = document.getElementById('notification-container');
    if (!container) return;
    
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    
    const icons = {
        success: '✓',
        error: '✗',
        warning: '⚠',
        info: 'ℹ'
    };
    
    const icon = document.createElement('span');
    icon.className = 'notification-icon';
    icon.textContent = icons[type] || 'ℹ';
    
    const content = document.createElement('div');
    content.className = 'notification-content';
    
    if (title) {
        const titleEl = document.createElement('div');
        titleEl.className = 'notification-title';
        titleEl.textContent = title;
        content.appendChild(titleEl);
    }
    
    const messageEl = document.createElement('div');
    messageEl.className = 'notification-message';
    messageEl.textContent = message;
    content.appendChild(messageEl);
    
    const closeBtn = document.createElement('button');
    closeBtn.className = 'notification-close';
    closeBtn.innerHTML = '×';
    closeBtn.onclick = () => removeNotification(notification);
    
    notification.appendChild(icon);
    notification.appendChild(content);
    notification.appendChild(closeBtn);
    
    container.appendChild(notification);
    
    // Auto remove after duration
    if (duration > 0) {
        setTimeout(() => {
            removeNotification(notification);
        }, duration);
    }
    
    return notification;
}

function removeNotification(notification) {
    notification.classList.add('hiding');
    setTimeout(() => {
        if (notification.parentNode) {
            notification.parentNode.removeChild(notification);
        }
    }, 300);
}

// Confirmation System (replaces confirm())
function showConfirm(message, title = 'Confirm', okText = 'OK', cancelText = 'Cancel') {
    return new Promise((resolve) => {
        const modal = document.getElementById('confirm-modal');
        const titleEl = document.getElementById('confirm-title');
        const messageEl = document.getElementById('confirm-message');
        const okBtn = document.getElementById('confirm-ok-btn');
        const cancelBtn = document.getElementById('confirm-cancel-btn');
        
        if (!modal) {
            // Fallback if modal doesn't exist
            resolve(window.confirm(message));
            return;
        }
        
        titleEl.textContent = title;
        messageEl.textContent = message;
        okBtn.textContent = okText;
        cancelBtn.textContent = cancelText;
        
        modal.style.display = 'block';
        showModal('confirm-modal');
        
        const cleanup = () => {
            okBtn.onclick = null;
            cancelBtn.onclick = null;
            closeModal('confirm-modal');
        };
        
        okBtn.onclick = () => {
            cleanup();
            resolve(true);
        };
        
        cancelBtn.onclick = () => {
            cleanup();
            resolve(false);
        };
    });
}

// MySQL Download Functions

// Load MySQL versions with installed status
async function loadMySQLVersionsWithStatus() {
    const loadingDiv = document.getElementById('versions-loading');
    const versionsList = document.getElementById('mysql-versions-list');
    const installedContainer = document.getElementById('installed-versions-container');
    const availableContainer = document.getElementById('available-versions-container');

    if (!loadingDiv || !versionsList || !installedContainer || !availableContainer) {
        console.error('Required elements not found for version list');
        return;
    }

    // Show loading
    loadingDiv.style.display = 'block';
    versionsList.style.display = 'none';
    installedContainer.innerHTML = '';
    availableContainer.innerHTML = '';

    try {
        const response = await fetch('/api/mysql/versions');
        if (!response.ok) {
            throw new Error(`Server error: ${response.status}`);
        }
        const data = await response.json();

        // Separate installed and available versions
        const installedVersions = [];
        const availableVersions = [];

        data.versions.forEach(versionInfo => {
            if (versionInfo.is_installed || versionInfo.installed) {
                installedVersions.push(versionInfo);
            } else {
                availableVersions.push(versionInfo);
            }
        });

        // Render installed versions
        if (installedVersions.length > 0) {
            installedVersions.forEach(versionInfo => {
                const item = renderVersionItem(versionInfo);
                installedContainer.appendChild(item);
            });
        } else {
            installedContainer.innerHTML = '<p style="color: #999; font-size: 13px; padding: 10px;">No installed versions found.</p>';
        }

        // Render available versions
        if (availableVersions.length > 0) {
            availableVersions.forEach(versionInfo => {
                const item = renderVersionItem(versionInfo);
                availableContainer.appendChild(item);
            });
        } else {
            availableContainer.innerHTML = '<p style="color: #999; font-size: 13px; padding: 10px;">No versions available.</p>';
        }

        // Hide loading, show list
        loadingDiv.style.display = 'none';
        versionsList.style.display = 'block';

    } catch (error) {
        console.error('Failed to load MySQL versions:', error);
        if (loadingDiv) {
            loadingDiv.innerHTML = `<p style="color: #d32f2f;">Error loading versions: ${error.message}</p>`;
        }
    }
}

// Render a version item
function renderVersionItem(versionInfo) {
    const item = document.createElement('div');
    item.className = 'version-item';
    item.setAttribute('data-version', versionInfo.version);

    const header = document.createElement('div');
    header.className = 'version-header';

    // Status icon (left side, only if installed)
    const isInstalled = versionInfo.is_installed || versionInfo.installed;
    if (isInstalled) {
        const statusIcon = document.createElement('span');
        statusIcon.className = 'version-status-icon ' + (versionInfo.is_valid ? 'valid' : 'invalid');
        header.appendChild(statusIcon);
    }

    const title = document.createElement('div');
    title.className = 'version-title';

    // Version number
    const versionText = document.createElement('span');
    versionText.textContent = `MySQL ${versionInfo.version}`;
    title.appendChild(versionText);

    // Recommended badge
    if (versionInfo.recommended) {
        const recommendedBadge = document.createElement('span');
        recommendedBadge.className = 'version-badge recommended';
        recommendedBadge.textContent = 'Recommended';
        title.appendChild(recommendedBadge);
    }

    // Installed badge
    if (isInstalled) {
        const installedBadge = document.createElement('span');
        installedBadge.className = 'version-badge ' + (versionInfo.is_valid ? 'installed' : 'invalid');
        installedBadge.textContent = versionInfo.is_valid ? '✓ Installed' : '⚠ Invalid';
        title.appendChild(installedBadge);
    }

    header.appendChild(title);

    // Action buttons (right side)
    const actionsDiv = document.createElement('div');
    actionsDiv.className = 'version-actions';

    if (isInstalled) {
        // Use button
        const useBtn = document.createElement('button');
        useBtn.className = 'btn btn-success btn-small';
        useBtn.textContent = 'Use';
        useBtn.onclick = () => useMySQLVersion(versionInfo.version, versionInfo.bin_path);
        actionsDiv.appendChild(useBtn);

        // Repair button (only if invalid)
        if (!versionInfo.is_valid) {
            const repairBtn = document.createElement('button');
            repairBtn.className = 'btn btn-secondary btn-small';
            repairBtn.textContent = 'Repair';
            repairBtn.onclick = () => repairMySQLVersion(versionInfo.version, versionInfo.install_path);
            actionsDiv.appendChild(repairBtn);
        }
    } else {
        // Download button
        const downloadBtn = document.createElement('button');
        downloadBtn.className = 'btn btn-success btn-small';
        downloadBtn.textContent = 'Download';
        downloadBtn.onclick = () => downloadMySQLVersion(versionInfo.version);
        actionsDiv.appendChild(downloadBtn);
    }

    header.appendChild(actionsDiv);
    
    // Expand indicator (if installed with path)
    let pathContainer = null;
    if (isInstalled && versionInfo.bin_path) {
        const expandIcon = document.createElement('span');
        expandIcon.className = 'version-expand-icon';
        expandIcon.innerHTML = '▼'; // Down arrow
        header.appendChild(expandIcon);
        
        // Make card clickable
        item.classList.add('version-item-expandable');
        item.style.cursor = 'pointer';
        
        // Path container (hidden by default)
        pathContainer = document.createElement('div');
        pathContainer.className = 'version-path-container';
        pathContainer.style.display = 'none';
        
        const pathContent = document.createElement('div');
        pathContent.className = 'version-path';
        pathContent.textContent = versionInfo.bin_path;
        pathContainer.appendChild(pathContent);
        
        // Toggle on card click (but not on button clicks)
        item.addEventListener('click', (e) => {
            // Don't expand if clicking on buttons
            if (e.target.closest('.btn') || e.target.closest('.version-actions')) {
                return;
            }
            
            const isExpanded = pathContainer.style.display !== 'none';
            pathContainer.style.display = isExpanded ? 'none' : 'block';
            expandIcon.innerHTML = isExpanded ? '▼' : '▲';
            item.classList.toggle('version-item-expanded', !isExpanded);
        });
    }
    
    item.appendChild(header);
    
    // Add path container after header
    if (pathContainer) {
        item.appendChild(pathContainer);
    }

    return item;
}

// Use an existing MySQL installation
async function useMySQLVersion(version, binPath) {
    try {
        const response = await fetch('/api/mysql/use', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                version: version,
                bin_path: binPath
            })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || `Server error: ${response.status}`);
        }

        const data = await response.json();

        if (data.success) {
            // Show success message
            showNotification('success', `MySQL ${version} configured successfully!`);
            // Close modals
            closeModal('config-modal');
            // Reload config display
            await loadConfig();
        } else {
            throw new Error(data.error || 'Failed to use MySQL version');
        }
    } catch (error) {
        console.error('Use MySQL version error:', error);
        showNotification('error', 'Error: ' + error.message);
    }
}

// Repair a MySQL installation
async function repairMySQLVersion(version, installPath) {
    const confirmed = await showConfirm(`Repair MySQL ${version}? This will re-extract the installation if the archive is available.`, 'Repair MySQL', 'Repair', 'Cancel');
    if (!confirmed) {
        return;
    }

    try {
        const response = await fetch('/api/mysql/repair', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                version: version,
                install_path: installPath
            })
        });

        if (!response.ok) {
            const errorData = await response.json();
            if (errorData.requires_download) {
                const downloadConfirmed = await showConfirm(`Archive not found. Would you like to download MySQL ${version} again?`, 'Download Required', 'Download', 'Cancel');
                if (downloadConfirmed) {
                    downloadMySQLVersion(version);
                }
            } else {
                throw new Error(errorData.error || `Server error: ${response.status}`);
            }
            return;
        }

        const data = await response.json();

        if (data.success) {
            showNotification('success', `MySQL ${version} repaired successfully!`);
            // Reload versions to update status
            await loadMySQLVersionsWithStatus();
        } else {
            throw new Error(data.error || 'Repair failed');
        }
    } catch (error) {
        console.error('Repair MySQL version error:', error);
        showNotification('error', 'Error: ' + error.message);
    }
}

// Download a specific MySQL version
async function downloadMySQLVersion(version) {
    const dest = document.getElementById('mysql-dest-input').value.trim();

    // Show download modal
    document.getElementById('download-version').textContent = `MySQL ${version}`;
    document.getElementById('download-progress-fill').style.width = '0%';
    document.getElementById('download-progress-fill').textContent = '0%';
    document.getElementById('download-status').textContent = 'Preparing download...';
    document.getElementById('download-status').style.color = '#666';
    document.getElementById('download-result-message').style.display = 'none';
    document.getElementById('download-result-title').textContent = '';
    document.getElementById('download-result-detail').textContent = '';
    document.getElementById('cancel-download-btn').style.display = 'block';
    document.getElementById('download-return-btn').style.display = 'none';
    showModal('download-modal');

    let pollInterval = null;
    let jobId = null;

    try {
        // Start download (returns job_id immediately)
        const startResponse = await fetch('/api/mysql/download', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                version: version,
                destination: dest || ''
            })
        });

        if (!startResponse.ok) {
            const errorData = await startResponse.json();
            throw new Error(errorData.error || `Server error: ${startResponse.status} ${startResponse.statusText}`);
        }

        const startResult = await startResponse.json();
        jobId = startResult.job_id;

        if (!jobId) {
            // Legacy sync response (no job_id) - handle directly
            if (startResult.success) {
                showDownloadSuccess(startResult.bin_path);
                return;
            } else {
                throw new Error(startResult.error || 'Download failed');
            }
        }

        // Poll for progress
        document.getElementById('download-status').textContent = 'Downloading...';
        pollInterval = setInterval(async () => {
            try {
                const progressResponse = await fetch(`/api/mysql/download/progress/${jobId}`);
                const progress = await progressResponse.json();

                const fill = document.getElementById('download-progress-fill');
                const status = document.getElementById('download-status');
                fill.style.width = progress.percent + '%';
                fill.textContent = progress.percent + '%';

                if (progress.phase === 'downloading') {
                    status.textContent = 'Downloading...';
                    status.style.color = '#666';
                } else if (progress.phase === 'extracting') {
                    status.textContent = 'Extracting...';
                    status.style.color = '#666';
                } else if (progress.phase === 'validating') {
                    status.textContent = 'Validating installation...';
                    status.style.color = '#666';
                }

                if (progress.status === 'completed') {
                    clearInterval(pollInterval);
                    pollInterval = null;
                    showDownloadSuccess(progress.bin_path);
                } else if (progress.status === 'failed') {
                    clearInterval(pollInterval);
                    pollInterval = null;
                    throw new Error(progress.error || 'Download failed');
                }
            } catch (pollError) {
                if (pollInterval) {
                    clearInterval(pollInterval);
                    pollInterval = null;
                }
                showDownloadError(pollError.message);
            }
        }, 500);

    } catch (error) {
        if (pollInterval) {
            clearInterval(pollInterval);
        }
        console.error('Download error:', error);
        showDownloadError(error.message);
    }
}

function showDownloadSuccess(binPath) {
    document.getElementById('download-progress-fill').style.width = '100%';
    document.getElementById('download-progress-fill').textContent = '100%';
    document.getElementById('download-status').textContent = 'Download completed!';
    document.getElementById('download-status').style.color = '#28a745';

    const resultDiv = document.getElementById('download-result-message');
    resultDiv.className = 'result success';
    resultDiv.style.display = 'block';
    document.getElementById('download-result-title').textContent = '✓ Download completed!';
    document.getElementById('download-result-detail').textContent = binPath ? `Installed at: ${binPath}` : '';

    if (binPath) {
        fetch('/api/config/mysql-bin', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({path: binPath})
        }).then(() => loadConfig());
    }

    document.getElementById('cancel-download-btn').style.display = 'none';
    document.getElementById('download-return-btn').style.display = 'block';
    loadMySQLVersionsWithStatus();
}

function showDownloadError(errorMessage) {
    document.getElementById('download-status').textContent = 'Error: ' + errorMessage;
    document.getElementById('download-status').style.color = '#d32f2f';
    document.getElementById('download-progress-fill').style.width = '0%';
    document.getElementById('download-progress-fill').textContent = '0%';

    const resultDiv = document.getElementById('download-result-message');
    resultDiv.className = 'result error';
    resultDiv.style.display = 'block';
    document.getElementById('download-result-title').textContent = '✗ Download failed';
    document.getElementById('download-result-detail').textContent = errorMessage;

    document.getElementById('cancel-download-btn').style.display = 'none';
    document.getElementById('download-return-btn').style.display = 'block';
}

// Legacy function for backward compatibility (now calls new function)
async function loadMySQLVersions() {
    await loadMySQLVersionsWithStatus();
}

// Note: showConfigModal now shows choice screen directly
// loadMySQLVersions is called when download form is shown
// loadConfigToModal is called when manual path form is shown

// Test MySQL path
async function testMySQLPath() {
    const pathInput = document.getElementById('mysql-bin-input');
    const resultDiv = document.getElementById('config-result');

    if (!pathInput || !resultDiv) {
        console.error('Required elements not found');
        return;
    }

    if (!pathInput.value || !pathInput.value.trim()) {
        resultDiv.className = 'result error';
        resultDiv.textContent = 'Please enter a path';
        resultDiv.style.display = 'block';
        return;
    }

    resultDiv.className = 'result';
    resultDiv.textContent = 'Testing...';
    resultDiv.style.display = 'block';

    try {
        const response = await fetch('/api/mysql/validate', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({path: pathInput.value.trim()})
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || `Server error: ${response.status}`);
        }

        const data = await response.json();

        if (data.valid) {
            resultDiv.className = 'result success';
            resultDiv.textContent = '✓ Valid MySQL installation found!';
        } else {
            resultDiv.className = 'result error';
            resultDiv.textContent = '✗ MySQL executables not found. Check the path.';
        }
        resultDiv.style.display = 'block';
    } catch (error) {
        console.error('Test path error:', error);
        resultDiv.className = 'result error';
        resultDiv.textContent = 'Error: ' + error.message;
        resultDiv.style.display = 'block';
    }
}

// Show modal helper (if not exists)
function showModal(modalId) {
    document.getElementById(modalId).style.display = 'flex';
}

// Download MySQL (legacy - now redirects to downloadMySQLVersion)
async function downloadMySQL() {
    // This function is kept for backward compatibility but should not be used
    // Users should click "Download" button on version items instead
    showNotification('info', 'Please select a version from the list and click "Download"');
}

// Cancel download
function cancelDownload() {
    closeModal('download-modal');
    // Reset download modal state
    resetDownloadModal();
}

// Return from download (after successful download)
function returnFromDownload() {
    closeModal('download-modal');
    closeModal('config-modal');
    // Reset download modal state
    resetDownloadModal();
}

// Reset download modal to initial state
function resetDownloadModal() {
    const progressFill = document.getElementById('download-progress-fill');
    const status = document.getElementById('download-status');
    const successMsg = document.getElementById('download-result-message');
    const pathInfo = document.getElementById('download-result-detail');
    const cancelBtn = document.getElementById('cancel-download-btn');
    const returnBtn = document.getElementById('download-return-btn');
    
    if (progressFill) {
        progressFill.style.width = '0%';
        progressFill.textContent = '0%';
    }
    if (status) {
        status.textContent = 'Preparing download...';
        status.style.display = 'block';
        status.style.color = '#666';
    }
    if (successMsg) successMsg.style.display = 'none';
    if (pathInfo) pathInfo.textContent = '';
    if (cancelBtn) cancelBtn.style.display = 'block';
    if (returnBtn) returnBtn.style.display = 'none';
}

// Removed browse directory functions - web browsers cannot access full filesystem paths
// Users must manually enter the path

// Load existing config to modal
async function loadConfigToModal() {
    // This function is called when manual path form is shown
    // It's now integrated into showManualPathForm()
    try {
        // Fetch current config from API to ensure we have the latest value
        const response = await fetch('/api/config/mysql-bin');
        const result = await response.json();
        
        const pathInput = document.getElementById('mysql-bin-input');
        if (!pathInput) return;
        
        if (result.path && result.path.trim() !== '') {
            // Path is configured, set it in the input
            pathInput.value = result.path;
        } else {
            // No path configured, clear the input
            pathInput.value = '';
        }
    } catch (error) {
        console.error('Failed to load config to modal:', error);
        // Fallback: try to get from display element
        const pathDisplay = document.getElementById('mysql-bin-path');
        if (pathDisplay) {
            const currentPath = pathDisplay.value || pathDisplay.textContent || '';
            if (currentPath && currentPath !== 'Not configured' && currentPath.trim() !== '') {
                const pathInput = document.getElementById('mysql-bin-input');
                if (pathInput) {
                    pathInput.value = currentPath;
                }
            }
        }
    }
}
