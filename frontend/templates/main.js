// ============================================================================
// Financial Analyst Agent - Frontend JavaScript
// ============================================================================

let currentAgent = null;
let conversationHistory = [];
let ws = null;
let isConnecting = false;

// ============================================================================
// Initialization
// ============================================================================

document.addEventListener('DOMContentLoaded', () => {
    console.log('🚀 Financial Analyst Agent Loaded');
    
    // Load clients on startup
    loadClients();
    
    // Set up keyboard shortcuts
    document.getElementById('queryInput').addEventListener('keydown', (e) => {
        if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
            e.preventDefault();
            submitQuery();
        }
    });
    
    // Connect to WebSocket if available
    connectWebSocket();
});

// ============================================================================
// WebSocket Connection
// ============================================================================

function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;
    
    try {
        ws = new WebSocket(wsUrl);
        
        ws.onopen = () => {
            console.log('✅ WebSocket connected');
            updateStatus('Connected to agent', 'success');
        };
        
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            handleWebSocketMessage(data);
        };
        
        ws.onerror = (error) => {
            console.error('❌ WebSocket error:', error);
            updateStatus('WebSocket connection error', 'error');
        };
        
        ws.onclose = () => {
            console.log('⚠️  WebSocket disconnected');
            updateStatus('Disconnected - using REST API', 'warning');
            // Reconnect after 3 seconds
            setTimeout(connectWebSocket, 3000);
        };
    } catch (e) {
        console.error('Failed to connect WebSocket:', e);
    }
}

function handleWebSocketMessage(data) {
    switch (data.type) {
        case 'query_received':
            addMessage(data.query, 'user');
            updateStatus('Agent processing...', 'loading');
            break;
            
        case 'tool_call':
            addToolExecution(`Called ${data.tool}`, data.args);
            break;
            
        case 'tool_result':
            addToolResult(data.tool, data.result_preview);
            break;
            
        case 'final_response':
            addMessage(data.response, 'assistant');
            updateStatus('Ready', 'success');
            break;
            
        case 'error':
            addMessage(`Error: ${data.error}`, 'assistant');
            updateStatus('Error occurred', 'error');
            break;
    }
}

// ============================================================================
// Message Display
// ============================================================================

function addMessage(content, role = 'assistant') {
    const chatHistory = document.getElementById('chatHistory');
    
    // Remove welcome message on first query
    const welcomeMsg = chatHistory.querySelector('.welcome-message');
    if (welcomeMsg) {
        welcomeMsg.remove();
    }
    
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;
    
    const bubble = document.createElement('div');
    bubble.className = 'message-bubble';
    
    // Format content (basic markdown)
    bubble.innerHTML = formatContent(content);
    
    messageDiv.appendChild(bubble);
    chatHistory.appendChild(messageDiv);
    
    // Auto-scroll if enabled
    if (document.getElementById('autoScroll').checked) {
        chatHistory.scrollTop = chatHistory.scrollHeight;
    }
    
    // Store in history
    conversationHistory.push({ role, content, timestamp: new Date().toISOString() });
}

function formatContent(content) {
    // Escape HTML
    let formatted = content
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
    
    // Convert bold (**text**)
    formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    
    // Convert italic (*text*)
    formatted = formatted.replace(/\*(.*?)\*/g, '<em>$1</em>');
    
    // Convert line breaks
    formatted = formatted.replace(/\n/g, '<br>');
    
    // Convert links
    formatted = formatted.replace(
        /\[([^\]]+)\]\(([^)]+)\)/g,
        '<a href="$2" target="_blank">$1</a>'
    );
    
    // Format code blocks
    formatted = formatted.replace(
        /```([\s\S]*?)```/g,
        '<pre><code>$1</code></pre>'
    );
    
    return formatted;
}

function addToolExecution(toolName, args) {
    const chatHistory = document.getElementById('chatHistory');
    
    const toolDiv = document.createElement('div');
    toolDiv.className = 'tool-execution';
    
    let argsStr = '';
    if (typeof args === 'object') {
        argsStr = Object.entries(args)
            .map(([k, v]) => `${k}="${v}"`)
            .join(', ');
    }
    
    toolDiv.innerHTML = `<span class="tool-name">🔧 ${toolName}</span>(${argsStr})`;
    chatHistory.appendChild(toolDiv);
}

function addToolResult(toolName, result) {
    const chatHistory = document.getElementById('chatHistory');
    
    const resultDiv = document.createElement('div');
    resultDiv.className = 'tool-execution';
    resultDiv.style.borderLeftColor = '#10b981';
    resultDiv.style.marginLeft = '1rem';
    
    resultDiv.innerHTML = `<span style="color: #10b981;"><strong>✓ ${toolName} result:</strong></span><br><small>${result}</small>`;
    chatHistory.appendChild(resultDiv);
}

function updateStatus(message, type = 'info') {
    const status = document.getElementById('status');
    status.textContent = message;
    status.className = `status-bar ${type}`;
}

// ============================================================================
// Query Submission
// ============================================================================

async function submitQuery() {
    const queryInput = document.getElementById('queryInput');
    const query = queryInput.value.trim();
    
    if (!query) {
        alert('Please enter a query');
        return;
    }
    
    // Disable input during processing
    document.getElementById('sendBtn').disabled = true;
    queryInput.disabled = true;
    
    addMessage(query, 'user');
    updateStatus('Submitting query...', 'loading');
    
    try {
        // Use WebSocket if available, otherwise fall back to REST API
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ query }));
        } else {
            // Fall back to REST API
            await submitQueryREST(query);
        }
        
        queryInput.value = '';
    } catch (error) {
        console.error('Error:', error);
        addMessage(`Error: ${error.message}`, 'assistant');
        updateStatus('Error occurred', 'error');
    } finally {
        document.getElementById('sendBtn').disabled = false;
        queryInput.disabled = false;
        queryInput.focus();
    }
}

async function submitQueryREST(query) {
    updateStatus('Processing with REST API...', 'loading');
    
    const response = await fetch('/api/query', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ query })
    });
    
    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Request failed');
    }
    
    const data = await response.json();
    
    // Display tools used
    if (data.tools_used && data.tools_used.length > 0) {
        const toolsList = data.tools_used.join(', ');
        addToolExecution('Tools used', { tools: toolsList });
    }
    
    // Display reasoning steps if enabled
    if (document.getElementById('showReasoning').checked && data.reasoning_steps) {
        data.reasoning_steps.forEach(step => {
            addToolExecution('Reasoning', {});
            const chatHistory = document.getElementById('chatHistory');
            const lastTool = chatHistory.lastChild;
            lastTool.innerHTML += `<br><small>${step}</small>`;
        });
    }
    
    // Display response
    addMessage(data.response, 'assistant');
    updateStatus('Ready', 'success');
}

function quickQuery(query) {
    document.getElementById('queryInput').value = query;
    document.getElementById('queryInput').focus();
    submitQuery();
}

function clearChat() {
    if (confirm('Clear all messages?')) {
        const chatHistory = document.getElementById('chatHistory');
        chatHistory.innerHTML = `
            <div class="welcome-message">
                <h2>👋 Welcome back to Financial Analyst Agent</h2>
                <p>Chat has been cleared. Ready for new analysis.</p>
            </div>
        `;
        conversationHistory = [];
        updateStatus('Chat cleared', 'info');
    }
}

// ============================================================================
// Client Management
// ============================================================================

async function loadClients() {
    try {
        const response = await fetch('/api/clients');
        if (!response.ok) throw new Error('Failed to load clients');
        
        const data = await response.json();
        displayClients(data.clients);
    } catch (error) {
        console.error('Error loading clients:', error);
        const clientsList = document.getElementById('clientsList');
        clientsList.innerHTML = '<p class="error">Failed to load clients</p>';
    }
}

function displayClients(clients) {
    const clientsList = document.getElementById('clientsList');
    clientsList.innerHTML = '';
    
    if (!clients || clients.length === 0) {
        clientsList.innerHTML = '<p class="text-muted">No clients found</p>';
        return;
    }
    
    clients.forEach(client => {
        const item = document.createElement('div');
        item.className = 'client-item';
        item.textContent = `${client.client_id}: ${client.name}`;
        item.onclick = () => {
            quickQuery(`Show portfolio for ${client.client_id}`);
        };
        clientsList.appendChild(item);
    });
}

// ============================================================================
// Modal Management
// ============================================================================

function closeModal() {
    document.getElementById('responseModal').classList.remove('show');
}

function showDetailedResponse(response) {
    const modal = document.getElementById('responseModal');
    const body = document.getElementById('modalBody');
    body.innerHTML = formatContent(response);
    modal.classList.add('show');
}

// Close modal when clicking outside
window.onclick = (event) => {
    const modal = document.getElementById('responseModal');
    if (event.target === modal) {
        closeModal();
    }
};

// ============================================================================
// Utility Functions
// ============================================================================

function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        alert('Copied to clipboard!');
    }).catch(err => {
        console.error('Failed to copy:', err);
    });
}

function exportChat() {
    const text = conversationHistory
        .map(msg => `${msg.role.toUpperCase()}: ${msg.content}`)
        .join('\n\n---\n\n');
    
    const element = document.createElement('a');
    element.setAttribute('href', 'data:text/plain;charset=utf-8,' + encodeURIComponent(text));
    element.setAttribute('download', `chat-${new Date().toISOString().split('T')[0]}.txt`);
    element.style.display = 'none';
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
}

// ============================================================================
// Console Logging
// ============================================================================

console.log(`
╔═══════════════════════════════════════════════════════════╗
║   Financial Analyst Agentic RAG Agent                    ║
║   ReAct + Vector RAG + SQL DB + Web Search               ║
║                                                           ║
║   Available API Endpoints:                               ║
║   - POST /api/query - Submit query to agent              ║
║   - GET /api/clients - List clients                      ║
║   - GET /api/client/{id} - Get client portfolio          ║
║   - GET /api/market/{ticker} - Get market data           ║
║   - WS /ws - WebSocket for streaming                     ║
╚═══════════════════════════════════════════════════════════╝
`);
