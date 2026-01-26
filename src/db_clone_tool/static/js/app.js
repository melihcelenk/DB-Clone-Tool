let currentConnectionId = null;
let currentSchemaName = null;
let currentJobId = null;
let logPollInterval = null;
let availableSchemas = []; // Store schemas for dropdowns

// Load connections on page load
document.addEventListener('DOMContentLoaded', function() {
    loadConnections();
    loadConfig();
});

// Load connections
async function loadConnections() {
    try {
        const response = await fetch('/api/connections');
        const connections = await response.json();
        renderConnections(connections);
    } catch (error) {
        console.error('Failed to load connections:', error);
    }
}

// Render connections list
function renderConnections(connections) {
    const list = document.getElementById('connections-list');
    if (connections.length === 0) {
        list.innerHTML = '<div class="empty-state"><div class="empty-state-icon">🔌</div><p>No connections</p></div>';
        return;
    }
    
    list.innerHTML = connections.map(conn => `
        <div class="connection-item ${conn.id === currentConnectionId ? 'active' : ''}" 
             onclick="selectConnection('${conn.id}')">
            <div class="connection-name">${escapeHtml(conn.name)}</div>
            <div class="connection-details">${escapeHtml(conn.host)}:${conn.port}</div>
            <div class="connection-details">${conn.database || 'All databases'}</div>
            <div style="display: flex; gap: 5px; margin-top: 8px;">
                <button class="btn btn-secondary" onclick="event.stopPropagation(); editConnection('${conn.id}')" 
                        style="padding: 5px 10px; font-size: 12px; flex: 1;">Edit</button>
                <button class="btn btn-danger" onclick="event.stopPropagation(); deleteConnection('${conn.id}')" 
                        style="padding: 5px 10px; font-size: 12px; flex: 1;">Delete</button>
            </div>
        </div>
    `).join('');
}

// Select connection
async function selectConnection(connectionId) {
    currentConnectionId = connectionId;
    
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
    
    list.innerHTML = schemas.map(schema => `
        <div class="schema-item" 
             oncontextmenu="event.preventDefault(); showContextMenu(event, '${escapeHtml(schema.name)}')">
            <div class="schema-name">${escapeHtml(schema.name)}</div>
            <div class="schema-info">
                <span>📊 ${schema.table_count} tables</span>
                <span>💾 ${schema.size_mb.toFixed(2)} MB</span>
            </div>
        </div>
    `).join('');
    
    // Update dropdowns if connection is selected
    updateSchemaDropdowns();
}

// Show context menu
function showContextMenu(event, schemaName) {
    currentSchemaName = schemaName;
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
    
    // Update import target schema dropdown
    const importSelect = document.getElementById('import-target-schema-select');
    if (importSelect) {
        importSelect.innerHTML = '<option value="">Select target schema...</option>' +
            availableSchemas.map(s => `<option value="${escapeHtml(s.name)}">${escapeHtml(s.name)}</option>`).join('');
    }
    
    // Update export source schema dropdown
    const exportSelect = document.getElementById('export-source-schema-select');
    if (exportSelect) {
        exportSelect.innerHTML = '<option value="">Select schema to export...</option>' +
            availableSchemas.map(s => `<option value="${escapeHtml(s.name)}">${escapeHtml(s.name)}</option>`).join('');
    }
}

// Duplicate schema
function duplicateSchema() {
    if (!currentConnectionId || !currentSchemaName) {
        alert('Please select a connection and schema');
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
            alert('Failed to load connection: ' + (conn.error || 'Unknown error'));
            return;
        }
        
        // Fill form with connection data
        document.getElementById('add-connection-form').reset();
        document.getElementById('add-connection-form').querySelector('[name="name"]').value = conn.name || '';
        document.getElementById('add-connection-form').querySelector('[name="host"]').value = conn.host || '';
        document.getElementById('add-connection-form').querySelector('[name="port"]').value = conn.port || '3306';
        document.getElementById('add-connection-form').querySelector('[name="user"]').value = conn.user || '';
        document.getElementById('add-connection-form').querySelector('[name="password"]').value = conn.password || '';
        document.getElementById('add-connection-form').querySelector('[name="database"]').value = conn.database || '';
        
        // Store connection ID for update
        document.getElementById('add-connection-form').dataset.connectionId = connectionId;
        
        // Change form title and button
        document.querySelector('#add-connection-modal .modal-title').textContent = 'Edit Connection';
        const submitBtn = document.querySelector('#add-connection-form button[type="submit"]');
        submitBtn.textContent = 'Update Connection';
        
        // Show modal
        document.getElementById('connection-result').style.display = 'none';
        document.getElementById('add-connection-modal').style.display = 'flex';
    } catch (error) {
        alert('Error: ' + error.message);
    }
}

// Delete connection
async function deleteConnection(connectionId) {
    if (!confirm('Are you sure you want to delete this connection?')) {
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
                document.getElementById('schemas-list').innerHTML = 
                    '<div class="empty-state"><div class="empty-state-icon">📋</div><p>Select a connection to view schemas</p></div>';
                document.getElementById('active-connection-info').style.display = 'none';
            }
        } else {
            alert('Failed to delete connection: ' + (result.error || 'Unknown error'));
        }
    } catch (error) {
        alert('Error: ' + error.message);
    }
}

// Show add connection modal
function showAddConnectionModal() {
    const form = document.getElementById('add-connection-form');
    form.reset();
    delete form.dataset.connectionId;
    document.querySelector('#add-connection-modal .modal-title').textContent = 'Add Connection';
    const submitBtn = form.querySelector('button[type="submit"]');
    submitBtn.textContent = 'Add Connection';
    document.getElementById('connection-result').style.display = 'none';
    document.getElementById('add-connection-modal').style.display = 'flex';
}

// Show config modal
function showConfigModal() {
    document.getElementById('mysql-bin-input').value = document.getElementById('mysql-bin-path').textContent;
    document.getElementById('config-result').style.display = 'none';
    document.getElementById('config-modal').style.display = 'flex';
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

// Load config
async function loadConfig() {
    try {
        const response = await fetch('/api/config/mysql-bin');
        const result = await response.json();
        const path = result.path || 'Not configured';
        document.getElementById('mysql-bin-path').textContent = path;
    } catch (error) {
        console.error('Failed to load config:', error);
    }
}

// Close modal
function closeModal(modalId) {
    document.getElementById(modalId).style.display = 'none';
}

// Show result
function showResult(elementId, message, type) {
    const element = document.getElementById(elementId);
    element.textContent = message;
    element.className = 'result ' + type;
    element.style.display = 'block';
}

// Import dump file
async function importDump() {
    const fileInput = document.getElementById('dump-file-input');
    const targetSelect = document.getElementById('import-target-schema-select');
    const targetInput = document.getElementById('import-target-schema-input');
    
    const targetSchema = (targetSelect && targetSelect.value) || (targetInput ? targetInput.value.trim() : '');
    
    if (!fileInput.files || fileInput.files.length === 0) {
        alert('Please select a SQL dump file');
        return;
    }
    
    if (!targetSchema) {
        alert('Please select or enter target schema name');
        return;
    }
    
    if (!currentConnectionId) {
        alert('Please select a connection first');
        return;
    }
    
    if (!confirm(`Import dump to schema '${targetSchema}'? This will overwrite existing data if the schema exists.`)) {
        return;
    }
    
    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    formData.append('connection_id', currentConnectionId);
    formData.append('target_schema', targetSchema);
    
    try {
        const response = await fetch('/api/import/dump', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (result.success) {
            alert('Dump imported successfully!');
            // Reload schemas
            if (currentConnectionId) {
                await loadSchemas(currentConnectionId);
            }
            // Clear inputs
            fileInput.value = '';
            if (targetSelect) targetSelect.value = '';
            if (targetInput) targetInput.value = '';
        } else {
            alert('Import failed: ' + (result.error || 'Unknown error'));
        }
    } catch (error) {
        alert('Error: ' + error.message);
    }
}

// Export dump file
async function exportDump() {
    const sourceSelect = document.getElementById('export-source-schema-select');
    const pathInput = document.getElementById('export-path-input');
    const resultDiv = document.getElementById('export-result');
    
    const sourceSchema = sourceSelect ? sourceSelect.value : '';
    const exportPath = pathInput ? pathInput.value.trim() : '';
    
    if (!sourceSchema) {
        alert('Please select a schema to export');
        return;
    }
    
    if (!currentConnectionId) {
        alert('Please select a connection first');
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
