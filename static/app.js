/**
 * AutoDesk Agent — Frontend Chat Application
 * Handles chat interaction, session management, and agent trace display.
 */

// ============================================
// State
// ============================================
const state = {
    sessionId: null,
    isLoading: false,
    traceVisible: false,
    sidebarOpen: false,
    sessions: [], // stored locally
};

// ============================================
// DOM Elements
// ============================================
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

const elements = {
    sidebar: $('#sidebar'),
    chatMain: $('#chat-main'),
    messagesContainer: $('#messages-container'),
    welcomeScreen: $('#welcome-screen'),
    messageInput: $('#message-input'),
    sendBtn: $('#send-btn'),
    menuToggle: $('#menu-toggle'),
    toggleTrace: $('#toggle-trace'),
    tracePanel: $('#trace-panel'),
    traceContent: $('#trace-content'),
    traceClose: $('#trace-close'),
    newChatHeader: $('#new-chat-header'),
    newChatBtn: $('#new-chat-btn'),
    navChat: $('#nav-chat'),
    navSessions: $('#nav-sessions'),
    sessionList: $('#session-list'),
    sessionsContainer: $('#sessions-container'),
    sidebarActions: $('#sidebar-actions'),
};

// ============================================
// Initialization
// ============================================
function init() {
    generateSessionId();
    loadSessions();
    bindEvents();
}

function generateSessionId() {
    state.sessionId = 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 6);
}

// ============================================
// Event Binding
// ============================================
function bindEvents() {
    // Send message
    elements.sendBtn.addEventListener('click', sendMessage);
    elements.messageInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    // Auto-grow textarea
    elements.messageInput.addEventListener('input', () => {
        const el = elements.messageInput;
        el.style.height = 'auto';
        el.style.height = Math.min(el.scrollHeight, 120) + 'px';
        elements.sendBtn.disabled = el.value.trim().length === 0;
    });

    // Toggle trace panel
    elements.toggleTrace.addEventListener('click', toggleTrace);
    elements.traceClose.addEventListener('click', toggleTrace);

    // Mobile sidebar
    elements.menuToggle.addEventListener('click', toggleSidebar);

    // New chat
    elements.newChatHeader.addEventListener('click', startNewChat);
    if (elements.newChatBtn) {
        elements.newChatBtn.addEventListener('click', startNewChat);
    }
    
    // Delete current chat
    const deleteBtn = $('#delete-chat-header');
    if (deleteBtn) {
        deleteBtn.addEventListener('click', deleteCurrentChat);
    }

    // Navigation
    elements.navChat.addEventListener('click', () => switchView('chat'));
    elements.navSessions.addEventListener('click', () => switchView('sessions'));

    // Quick action chips
    $$('.action-chip').forEach(chip => {
        chip.addEventListener('click', () => {
            const prompt = chip.dataset.prompt;
            if (prompt) {
                elements.messageInput.value = prompt;
                elements.sendBtn.disabled = false;
                sendMessage();
            }
        });
    });

    // Welcome cards
    $$('.welcome-card').forEach(card => {
        card.addEventListener('click', () => {
            const prompt = card.dataset.prompt;
            if (prompt) {
                elements.messageInput.value = prompt;
                elements.sendBtn.disabled = false;
                sendMessage();
            }
        });
    });
}

// ============================================
// Chat Logic
// ============================================
async function sendMessage() {
    const message = elements.messageInput.value.trim();
    if (!message || state.isLoading) return;

    // Hide welcome screen
    if (elements.welcomeScreen) {
        elements.welcomeScreen.style.display = 'none';
    }

    // Add user message to UI
    appendMessage('user', message);

    // Clear input
    elements.messageInput.value = '';
    elements.messageInput.style.height = 'auto';
    elements.sendBtn.disabled = true;

    // Show typing indicator
    const typingEl = showTypingIndicator();

    state.isLoading = true;

    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: message,
                session_id: state.sessionId,
            }),
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();

        // Remove typing indicator
        typingEl.remove();

        // Add agent response
        appendMessage('agent', data.response);

        // Update session ID if server changed it
        if (data.session_id) {
            state.sessionId = data.session_id;
        }

        // Update trace panel
        if (data.trace && data.trace.length > 0) {
            updateTrace(data.trace);
        }

        // Save session
        saveCurrentSession(message);
        
        // Show delete button
        const deleteBtn = $('#delete-chat-header');
        if (deleteBtn) deleteBtn.style.display = 'flex';

    } catch (error) {
        typingEl.remove();
        appendMessage('agent', `Sorry, I encountered an error: ${error.message}. Please try again.`);
        console.error('Chat error:', error);
    } finally {
        state.isLoading = false;
    }
}

// ============================================
// UI Rendering
// ============================================
function appendMessage(role, content) {
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${role}`;

    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.textContent = role === 'agent' ? 'A' : 'U';

    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';

    const bubble = document.createElement('div');
    bubble.className = 'message-bubble';
    bubble.innerHTML = role === 'agent' ? formatMarkdown(content) : escapeHtml(content);

    const timestamp = document.createElement('div');
    timestamp.className = 'message-timestamp';
    timestamp.textContent = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    contentDiv.appendChild(bubble);
    contentDiv.appendChild(timestamp);
    msgDiv.appendChild(avatar);
    msgDiv.appendChild(contentDiv);

    elements.messagesContainer.appendChild(msgDiv);
    scrollToBottom();
}

function showTypingIndicator() {
    const msgDiv = document.createElement('div');
    msgDiv.className = 'message agent';
    msgDiv.id = 'typing-indicator';

    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.textContent = 'A';

    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';

    const indicator = document.createElement('div');
    indicator.className = 'typing-indicator';
    indicator.innerHTML = '<div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div>';

    contentDiv.appendChild(indicator);
    msgDiv.appendChild(avatar);
    msgDiv.appendChild(contentDiv);

    elements.messagesContainer.appendChild(msgDiv);
    scrollToBottom();

    return msgDiv;
}

function scrollToBottom() {
    elements.messagesContainer.scrollTop = elements.messagesContainer.scrollHeight;
}

// ============================================
// Trace Panel
// ============================================
function toggleTrace() {
    state.traceVisible = !state.traceVisible;
    elements.tracePanel.style.display = state.traceVisible ? 'flex' : 'none';
    elements.toggleTrace.classList.toggle('active', state.traceVisible);
}

function updateTrace(traceSteps) {
    elements.traceContent.innerHTML = '';

    traceSteps.forEach((step, index) => {
        const stepEl = document.createElement('div');
        const stepType = step.type || 'thought';
        stepEl.className = `trace-step ${stepType}`;

        const label = document.createElement('div');
        label.className = 'trace-step-label';

        const typeLabels = {
            thought: '💭 Thought',
            action: '⚡ Action',
            observation: '👁️ Observation',
            error: '❌ Error',
        };
        label.textContent = `Step ${index + 1} — ${typeLabels[stepType] || stepType}`;

        const content = document.createElement('div');
        content.className = 'trace-step-content';
        content.textContent = step.content || step.message || JSON.stringify(step);

        stepEl.appendChild(label);
        stepEl.appendChild(content);
        elements.traceContent.appendChild(stepEl);
    });

    // Auto-show trace if there are steps
    if (!state.traceVisible && traceSteps.length > 0) {
        toggleTrace();
    }
}

// ============================================
// Session Management
// ============================================
function switchView(view) {
    if (view === 'chat') {
        elements.navChat.classList.add('active');
        elements.navSessions.classList.remove('active');
        elements.sessionList.style.display = 'none';
        elements.sidebarActions.style.display = 'flex';
    } else {
        elements.navSessions.classList.add('active');
        elements.navChat.classList.remove('active');
        elements.sessionList.style.display = 'flex';
        elements.sidebarActions.style.display = 'none';
        renderSessions();
    }
}

function startNewChat() {
    // Save current session if it has messages
    saveCurrentSession();

    // Reset state
    generateSessionId();

    // Clear UI
    elements.messagesContainer.innerHTML = '';
    if (elements.welcomeScreen) {
        // Re-create the welcome screen
        elements.messagesContainer.innerHTML = getWelcomeScreenHTML();
        bindWelcomeCards();
    }
    
    // Hide delete button on new chat
    const deleteBtn = $('#delete-chat-header');
    if (deleteBtn) deleteBtn.style.display = 'none';

    // Clear trace
    elements.traceContent.innerHTML = '<p class="trace-empty">Send a message to see the agent\'s reasoning trace here.</p>';

    // Close sidebar on mobile
    if (state.sidebarOpen) toggleSidebar();
}

async function deleteCurrentChat() {
    if (!state.sessionId) return;
    
    if (confirm("Are you sure you want to delete this conversation?")) {
        try {
            await fetch(`/api/chat/history/${state.sessionId}`, { method: 'DELETE' });
            
            // Remove from state
            state.sessions = state.sessions.filter(s => s.id !== state.sessionId);
            localStorage.setItem('autodesk_sessions', JSON.stringify(state.sessions));
            
            // Clear UI by starting a new chat
            startNewChat();
            renderSessions();
        } catch (err) {
            console.error("Failed to delete session", err);
        }
    }
}

function saveCurrentSession(lastMessage) {
    const messages = elements.messagesContainer.querySelectorAll('.message');
    if (messages.length === 0) return;

    const existingIdx = state.sessions.findIndex(s => s.id === state.sessionId);
    const session = {
        id: state.sessionId,
        title: lastMessage ? lastMessage.substring(0, 50) : 'New conversation',
        timestamp: Date.now(),
        messageCount: messages.length,
    };

    if (existingIdx >= 0) {
        state.sessions[existingIdx] = session;
    } else {
        state.sessions.unshift(session);
    }

    // Keep max 20 sessions
    state.sessions = state.sessions.slice(0, 20);
    localStorage.setItem('autodesk_sessions', JSON.stringify(state.sessions));
}

function loadSessions() {
    try {
        const saved = localStorage.getItem('autodesk_sessions');
        if (saved) {
            state.sessions = JSON.parse(saved);
        }
    } catch (e) {
        state.sessions = [];
    }
}

function renderSessions() {
    const container = elements.sessionsContainer;
    container.innerHTML = '';

    if (state.sessions.length === 0) {
        container.innerHTML = '<p style="color: var(--color-text-sidebar); font-size: var(--font-size-xs); padding: var(--space-md); text-align: center; opacity: 0.7;">No previous conversations</p>';
        return;
    }

    state.sessions.forEach(session => {
        const item = document.createElement('div');
        item.className = `session-item ${session.id === state.sessionId ? 'active' : ''}`;
        
        const titleSpan = document.createElement('span');
        titleSpan.className = 'session-title';
        titleSpan.textContent = session.title;
        titleSpan.title = new Date(session.timestamp).toLocaleString();
        
        item.appendChild(titleSpan);

        item.addEventListener('click', async () => {
            state.sessionId = session.id;
            switchView('chat');
            await loadSessionHistory(session.id);
        });
        container.appendChild(item);
    });
}

async function loadSessionHistory(sessionId) {
    elements.messagesContainer.innerHTML = '';
    if (elements.welcomeScreen) {
        elements.welcomeScreen.style.display = 'none';
    }
    
    // Show a loading indicator
    const loadingEl = showTypingIndicator();
    
    try {
        const response = await fetch(`/api/chat/history/${sessionId}`);
        if (!response.ok) throw new Error("Failed to load history");
        
        const data = await response.json();
        loadingEl.remove();
        
        if (data.messages && data.messages.length > 0) {
            data.messages.forEach(msg => {
                if (msg.role === 'user' || msg.role === 'assistant') {
                    appendMessage(msg.role === 'assistant' ? 'agent' : 'user', msg.content);
                }
            });
        } else {
            // History is empty (e.g. wiped after server restart if using in-memory store)
            appendMessage('agent', '*Note: The history for this session was cleared due to a server restart. You can continue the conversation below!*');
        }
        
        const deleteBtn = $('#delete-chat-header');
        if (deleteBtn) deleteBtn.style.display = 'flex';
        
    } catch (e) {
        loadingEl.remove();
        console.error(e);
        appendMessage('agent', 'Failed to load conversation history.');
    }
}

// ============================================
// Sidebar Toggle (Mobile)
// ============================================
function toggleSidebar() {
    state.sidebarOpen = !state.sidebarOpen;
    elements.sidebar.classList.toggle('open', state.sidebarOpen);

    // Manage overlay
    let overlay = document.querySelector('.overlay');
    if (state.sidebarOpen) {
        if (!overlay) {
            overlay = document.createElement('div');
            overlay.className = 'overlay visible';
            overlay.addEventListener('click', toggleSidebar);
            document.body.appendChild(overlay);
        } else {
            overlay.classList.add('visible');
        }
    } else if (overlay) {
        overlay.classList.remove('visible');
    }
}

// ============================================
// Utilities
// ============================================
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatMarkdown(text) {
    if (!text) return '';

    let html = escapeHtml(text);

    // Bold
    html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

    // Inline code
    html = html.replace(/`(.*?)`/g, '<code>$1</code>');

    // Unordered lists
    html = html.replace(/^[\s]*[-•]\s+(.*?)$/gm, '<li>$1</li>');
    html = html.replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>');

    // Numbered lists
    html = html.replace(/^\d+\.\s+(.*?)$/gm, '<li>$1</li>');

    // Line breaks → paragraphs
    html = html.split('\n\n').map(p => `<p>${p.trim()}</p>`).join('');
    html = html.replace(/\n/g, '<br>');

    // Clean up empty paragraphs
    html = html.replace(/<p><\/p>/g, '');
    html = html.replace(/<p><br><\/p>/g, '');

    return html;
}

function getWelcomeScreenHTML() {
    return `
    <div class="welcome-screen" id="welcome-screen">
        <div class="welcome-icon">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M12 2L2 7L12 12L22 7L12 2Z" fill="currentColor" opacity="0.6"/>
                <path d="M2 17L12 22L22 17" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
                <path d="M2 12L12 17L22 12" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
        </div>
        <h2>Hello! I'm AutoDesk Agent</h2>
        <p>Your AI-powered IT helpdesk assistant. I can answer questions about company IT policies, check ticket statuses, and create new support tickets for you.</p>
        <div class="welcome-cards">
            <button class="welcome-card" data-prompt="How do I reset my password?">
                <div class="card-icon">🔐</div>
                <div class="card-text">
                    <strong>Password Help</strong>
                    <span>Reset passwords & MFA setup</span>
                </div>
            </button>
            <button class="welcome-card" data-prompt="I can't connect to the VPN. Help me troubleshoot.">
                <div class="card-icon">🌐</div>
                <div class="card-text">
                    <strong>VPN Issues</strong>
                    <span>Access & troubleshooting</span>
                </div>
            </button>
            <button class="welcome-card" data-prompt="I need to report a security incident.">
                <div class="card-icon">🛡️</div>
                <div class="card-text">
                    <strong>Security Incident</strong>
                    <span>Report & escalation</span>
                </div>
            </button>
            <button class="welcome-card" data-prompt="Create a ticket for my laptop keyboard not working. Medium priority.">
                <div class="card-icon">🎫</div>
                <div class="card-text">
                    <strong>Create a Ticket</strong>
                    <span>Submit a new IT request</span>
                </div>
            </button>
        </div>
    </div>`;
}

function bindWelcomeCards() {
    $$('.welcome-card').forEach(card => {
        card.addEventListener('click', () => {
            const prompt = card.dataset.prompt;
            if (prompt) {
                elements.messageInput.value = prompt;
                elements.sendBtn.disabled = false;
                sendMessage();
            }
        });
    });
}

// ============================================
// Start
// ============================================
document.addEventListener('DOMContentLoaded', init);
