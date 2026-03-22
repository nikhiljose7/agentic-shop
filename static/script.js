// Utility to generate a pseudo-random UUID for session management
function generateSessionId() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
        var r = Math.random() * 16 | 0,
            v = c == 'x' ? r : (r & 0x3 | 0x8);
        return v.toString(16);
    });
}

const state = {
    sessionId: localStorage.getItem('chatbot_session_id') || (() => {
        const id = generateSessionId();
        localStorage.setItem('chatbot_session_id', id);
        return id;
    })(),
    isWaiting: false,
    user: JSON.parse(localStorage.getItem('chatbot_user') || 'null')
};


const dom = {
    form: document.getElementById('chatForm'),
    input: document.getElementById('userInput'),
    sendBtn: document.getElementById('sendBtn'),
    chatContent: document.getElementById('chatContent'),
    chatContainer: document.getElementById('chatContainer'),
    clearBtn: document.getElementById('clearBtn'),
    scrollBottomBtn: document.getElementById('scrollBottomBtn'),
    
    // Auth Modal DOM elements
    authModal: document.getElementById('authModal'),
    authForm: document.getElementById('authForm'),
    authEmail: document.getElementById('authEmail'),
    authName: document.getElementById('authName'),
    authAddress: document.getElementById('authAddress'),
    signupFields: document.getElementById('signupFields'),
    authTitle: document.getElementById('authTitle'),
    authSubtitle: document.getElementById('authSubtitle'),
    authSubmitBtn: document.getElementById('authSubmitBtn'),
    authToggleBtn: document.getElementById('authToggleBtn'),
    authToggleText: document.getElementById('authToggleText'),
    authError: document.getElementById('authError'),
    
    // Header Auth buttons
    headerLoginBtn: document.getElementById('headerLoginBtn'),
    headerLogoutBtn: document.getElementById('headerLogoutBtn')
};

let isLoginMode = true;

// UI State Updater
function updateHeaderAuthUI() {
    if (state.user) {
        dom.headerLoginBtn.style.display = 'none';
        dom.headerLogoutBtn.style.display = 'block';
    } else {
        dom.headerLoginBtn.style.display = 'block';
        dom.headerLogoutBtn.style.display = 'none';
    }
}

// Initial setup
updateHeaderAuthUI();
// Allow guest chat by default
dom.authModal.style.display = 'none';
dom.input.focus();

// Event Listeners
dom.input.addEventListener('input', () => {
    dom.sendBtn.disabled = dom.input.value.trim() === '' || state.isWaiting;
});

dom.form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const text = dom.input.value.trim();
    if (!text || state.isWaiting) return;

    // Send user message
    appendMessage(text, 'user');
    dom.input.value = '';
    dom.sendBtn.disabled = true;
    
    // Show typing
    const typingId = showTypingIndicator();
    
    try {
        state.isWaiting = true;
        const response = await fetch('/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: state.sessionId,
                text: text,
                user_id: state.user ? state.user.user_id : null,
                user_name: state.user ? state.user.name : null
            })
        });

        if (!response.ok) {
            throw new Error(`Server returned ${response.status}`);
        }

        const data = await response.json();
        removeTypingIndicator(typingId);
        
        appendMessage(data.reply, 'model');
        
        // If the backend states this action requires authentication, trigger the login popup
        if (data.requires_auth) {
            dom.authModal.style.display = 'flex';
        }

    } catch (err) {
        console.error(err);
        removeTypingIndicator(typingId);
        appendMessage("⚠️ Connection error. Please make sure the backend is running.", 'model');
    } finally {
        state.isWaiting = false;
        // Re-evaluate button state
        dom.sendBtn.disabled = dom.input.value.trim() === '';
        dom.input.focus();
    }
});

dom.clearBtn.addEventListener('click', async () => {
    if(!confirm("Are you sure you want to clear the chat history and log out?")) return;
    try {
        await fetch(`/chat/${state.sessionId}`, { method: 'DELETE' });
        // Generate new session to truly reset state
        state.sessionId = generateSessionId();
        localStorage.setItem('chatbot_session_id', state.sessionId);
        
        // Also log out the user
        state.user = null;
        localStorage.removeItem('chatbot_user');
        updateHeaderAuthUI();
        
        dom.chatContent.innerHTML = `
            <div class="message-wrapper bot">
                <div class="avatar bot-avatar">A</div>
                <div class="message bot-message">
                    Chat history cleared and you have been safely logged out. How can I help you today?
                </div>
            </div>
        `;
    } catch (err) {
        console.error(err);
        alert("Failed to clear chat history.");
    }
});

dom.chatContainer.addEventListener('scroll', () => {
    const isAtBottom = dom.chatContainer.scrollHeight - dom.chatContainer.scrollTop <= dom.chatContainer.clientHeight + 100;
    if (!isAtBottom) {
        dom.scrollBottomBtn.classList.add('visible');
    } else {
        dom.scrollBottomBtn.classList.remove('visible');
    }
});

dom.headerLoginBtn.addEventListener('click', () => {
    isLoginMode = true;
    dom.authTitle.textContent = 'Welcome Back';
    dom.authSubtitle.textContent = 'Please sign in to continue';
    dom.signupFields.style.display = 'none';
    dom.authSubmitBtn.textContent = 'Sign In';
    dom.authToggleText.textContent = "Don't have an account?";
    dom.authToggleBtn.textContent = 'Sign up';
    dom.authName.required = false;
    dom.authAddress.required = false;
    dom.authError.textContent = '';
    dom.authModal.style.display = 'flex';
});

dom.headerLogoutBtn.addEventListener('click', async () => {
    if(!confirm("Are you sure you want to log out?")) return;
    
    try {
        await fetch(`/chat/${state.sessionId}`, { method: 'DELETE' });
    } catch (e) {
        console.error("Failed to clear backend session:", e);
    }
    
    // Generate new session to truly reset state
    state.sessionId = generateSessionId();
    localStorage.setItem('chatbot_session_id', state.sessionId);

    state.user = null;
    localStorage.removeItem('chatbot_user');
    updateHeaderAuthUI();
    
    dom.chatContent.innerHTML = `
        <div class="message-wrapper bot">
            <div class="avatar bot-avatar">A</div>
            <div class="message bot-message">
                Successfully logged out. How can I help you today?
            </div>
        </div>
    `;
});

dom.scrollBottomBtn.addEventListener('click', () => {
    scrollToBottom(true);
});

// Auth Logic
dom.authToggleBtn.addEventListener('click', () => {
    isLoginMode = !isLoginMode;
    dom.authError.textContent = '';
    
    if (isLoginMode) {
        dom.authTitle.textContent = 'Welcome Back';
        dom.authSubtitle.textContent = 'Please sign in to continue';
        dom.signupFields.style.display = 'none';
        dom.authSubmitBtn.textContent = 'Sign In';
        dom.authToggleText.textContent = "Don't have an account?";
        dom.authToggleBtn.textContent = 'Sign up';
        dom.authName.required = false;
        dom.authAddress.required = false;
    } else {
        dom.authTitle.textContent = 'Create Account';
        dom.authSubtitle.textContent = 'Sign up to get started';
        dom.signupFields.style.display = 'block';
        dom.authSubmitBtn.textContent = 'Sign Up';
        dom.authToggleText.textContent = "Already have an account?";
        dom.authToggleBtn.textContent = 'Sign in';
        dom.authName.required = true;
        dom.authAddress.required = true;
    }
});

dom.authForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    dom.authError.textContent = '';
    dom.authSubmitBtn.disabled = true;
    
    const endpoint = isLoginMode ? '/auth/login' : '/auth/signup';
    const payload = isLoginMode ? {
        email: dom.authEmail.value.trim()
    } : {
        name: dom.authName.value.trim(),
        email: dom.authEmail.value.trim(),
        address: dom.authAddress.value.trim()
    };
    
    try {
        const response = await fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.detail || 'Authentication failed');
        }
        
        // Success
        state.user = data;
        localStorage.setItem('chatbot_user', JSON.stringify(data));
        updateHeaderAuthUI();
        
        // Hide Modal
        dom.authModal.style.display = 'none';
        
        appendMessage(isLoginMode ? `Welcome back, ${data.name}!` : "Account created successfully! How can I help you today?", "model");
        
        dom.input.focus();
        
    } catch (err) {
        dom.authError.textContent = err.message;
    } finally {
        dom.authSubmitBtn.disabled = false;
    }
});

// UI Functions
function appendMessage(text, role) {
    const wrapper = document.createElement('div');
    wrapper.className = `message-wrapper ${role === 'user' ? 'user' : 'bot'}`;
    
    // For bot role use marked parsing
    const content = role === 'user' ? escapeHtml(text) : marked.parse(text);

    wrapper.innerHTML = `
        <div class="avatar ${role === 'user' ? 'user-avatar' : 'bot-avatar'}">
            ${role === 'user' ? 'U' : 'E'}
        </div>
        <div class="message ${role === 'user' ? 'user-message' : 'bot-message'}">
            ${content}
        </div>
    `;
    
    dom.chatContent.appendChild(wrapper);
    scrollToBottom();
}

function showTypingIndicator() {
    const id = 'typing-' + Date.now();
    const wrapper = document.createElement('div');
    wrapper.className = 'typing-wrapper';
    wrapper.id = id;
    wrapper.innerHTML = `
        <div class="avatar bot-avatar">E</div>
        <div class="typing-indicator">
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
        </div>
    `;
    dom.chatContent.appendChild(wrapper);
    scrollToBottom();
    return id;
}

function removeTypingIndicator(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
}

function scrollToBottom(smooth = false) {
    dom.chatContainer.scrollTo({
        top: dom.chatContainer.scrollHeight,
        behavior: smooth ? 'smooth' : 'auto'
    });
}

function escapeHtml(unsafe) {
    return unsafe
         .replace(/&/g, "&amp;")
         .replace(/</g, "&lt;")
         .replace(/>/g, "&gt;")
         .replace(/"/g, "&quot;")
         .replace(/'/g, "&#039;");
}
