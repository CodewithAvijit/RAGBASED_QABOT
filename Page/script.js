// DOM elements
const chatContainer = document.getElementById('chat-container');
const inputForm = document.getElementById('input-form');
const userInput = document.getElementById('user-input');
const sendButton = document.getElementById('send-button');
const fileInput = document.getElementById('file-input');
const viewKnowledgeBtn = document.getElementById('view-knowledge-btn');
const resetKnowledgeBtn = document.getElementById('reset-knowledge-btn');
const knowledgeModal = document.getElementById('knowledge-modal');
const closeModalBtn = document.getElementById('close-modal-btn');
const knowledgeList = document.getElementById('knowledge-list');

// Prompt history
const promptHistory = [];
let historyIndex = -1;

// Add message to chat
function addMessage(text, type, source=null, highlight=null, quickReplies=[], tokens=null) {
    const messageDiv = document.createElement('div');
    messageDiv.classList.add('message', type);

    const content = document.createElement('p');
    content.textContent = text;
    messageDiv.appendChild(content);

    if(source) {
        const sourceDiv = document.createElement('div');
        sourceDiv.classList.add('source-link', 'mt-2');
        sourceDiv.textContent = `Source: ${source}`;
        messageDiv.appendChild(sourceDiv);
    }

    if(highlight) {
        const highlightDiv = document.createElement('div');
        highlightDiv.classList.add('highlight-snippet');
        highlightDiv.textContent = `"${highlight}"`;
        messageDiv.appendChild(highlightDiv);
    }

    if(tokens !== null) {
        const tokenDiv = document.createElement('div');
        tokenDiv.classList.add('token-info');
        tokenDiv.textContent = `Tokens used: ${tokens}`;
        messageDiv.appendChild(tokenDiv);
    }

    chatContainer.appendChild(messageDiv);

    if(quickReplies.length) {
        const container = document.createElement('div');
        container.classList.add('quick-replies');
        quickReplies.forEach(q => {
            const btn = document.createElement('button');
            btn.classList.add('quick-reply-btn');
            btn.textContent = q;
            btn.onclick = () => {
                userInput.value = q;
                inputForm.dispatchEvent(new Event('submit'));
                container.remove();
            };
            container.appendChild(btn);
        });
        chatContainer.appendChild(container);
    }

    chatContainer.scrollTop = chatContainer.scrollHeight;
}

// Typing indicator
function showTyping() {
    const div = document.createElement('div');
    div.id = 'typing-indicator';
    div.classList.add('message', 'bot-message');
    div.innerHTML = `<p>Nova is typing<span class="dots">...</span></p>`;
    chatContainer.appendChild(div);
    chatContainer.scrollTop = chatContainer.scrollHeight;
}
function hideTyping() { 
    const d = document.getElementById('typing-indicator'); 
    if(d) d.remove(); 
}

// Loading toggle
function toggleLoading(isLoading) {
    sendButton.disabled = isLoading;
    userInput.disabled = isLoading;
    fileInput.disabled = isLoading;
    viewKnowledgeBtn.disabled = isLoading;
    resetKnowledgeBtn.disabled = isLoading;
    sendButton.innerHTML = isLoading ? `<div class="loader"></div>` : 
        `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="w-6 h-6">
            <path d="M3.478 2.405a.75.75 0 0 0-.926.94l2.432 7.917H17.5a.75.75 0 0 1 0 1.5H4.984l-2.432 7.917a.75.75 0 0 0 .926.94 60.519 60.519 0 0 0 18.445-8.986.75.75 0 0 0 0-1.218A60.517 60.517 0 0 0 3.478 2.405Z" />
        </svg>`;
}

// Fetch knowledge
async function fetchKnowledgeBase(topic='') {
    knowledgeList.innerHTML = '<p class="text-center text-gray-400">Loading knowledge base...</p>';
    try {
        let url = 'http://127.0.0.1:8000/view-knowledge';
        if(topic) url += `?topic=${topic}`;
        const res = await fetch(url);
        const data = await res.json();
        knowledgeList.innerHTML = '';
        if(data.knowledge.length) {
            data.knowledge.forEach(item => {
                const div = document.createElement('div');
                div.className = 'p-4 rounded-lg bg-gray-800 border border-gray-700 break-words';
                div.innerHTML = `<p class="font-bold text-sm text-sky-400">${item.source}</p>
                                 <p class="mt-2 text-sm">${item.content}</p>`;
                knowledgeList.appendChild(div);
            });
        } else {
            knowledgeList.innerHTML = '<p class="text-center text-gray-400">Knowledge base is empty.</p>';
        }
    } catch(e) {
        knowledgeList.innerHTML = '<p class="text-center text-red-400">Failed to load knowledge. Server might be down.</p>';
    }
}

// Submit question
inputForm.addEventListener('submit', async e => {
    e.preventDefault();
    const q = userInput.value.trim();
    if(!q) return;

    // Add to prompt history only if it's not empty
    if(q !== '') promptHistory.push(q);
    historyIndex = promptHistory.length; // Point past the last item

    addMessage(q, 'user-message'); 
    userInput.value = '';
    toggleLoading(true);
    showTyping();

    try {
        const res = await fetch('http://127.0.0.1:8000/ask', {
            method:'POST',
            headers:{'Content-Type':'application/json'},
            body: JSON.stringify({question:q})
        });

        const data = await res.json();
        hideTyping();

        addMessage(
            data.answer || "No answer found", 
            'bot-message', 
            'Knowledge Base', 
            data.highlight, 
            data.quick_replies || [],
            data.tokens
        );

    } catch(err) { 
        hideTyping(); 
        addMessage("Server error!", 'bot-message'); 
    }

    toggleLoading(false);
});

// File upload
fileInput.addEventListener('change', async e => {
    const file = e.target.files[0];
    if(!file) return;
    addMessage(`Uploading ${file.name}...`, 'bot-message');
    toggleLoading(true);
    const formData = new FormData();
    formData.append('file', file);
    try {
        const res = await fetch('http://127.0.0.1:8000/upload', { method:'POST', body:formData });
        const data = await res.json();
        addMessage(data.message, 'bot-message');
    } catch(err) { addMessage("Upload failed!", 'bot-message'); }
    toggleLoading(false);
});

// Knowledge modal & reset
viewKnowledgeBtn.addEventListener('click', () => {
    knowledgeModal.style.display='flex';
    fetchKnowledgeBase();
});
closeModalBtn.addEventListener('click', () => knowledgeModal.style.display='none');
resetKnowledgeBtn.addEventListener('click', async ()=> {
    toggleLoading(true);
    try{
        const res = await fetch('http://127.0.0.1:8000/reset-knowledge', {method:'POST'});
        const data = await res.json();
        addMessage(data.message, 'bot-message');
    }catch(err){ addMessage("Reset failed!", 'bot-message'); }
    toggleLoading(false);
});

// Prompt history navigation (fixed)
// Elements
const viewHistoryBtn = document.getElementById('view-history-btn');
const historyModal = document.getElementById('history-modal');
const closeHistoryModalBtn = document.getElementById('close-history-modal-btn');
const historyList = document.getElementById('history-list');

// Open history modal and populate prompts
viewHistoryBtn.addEventListener('click', () => {
    historyList.innerHTML = ''; // Clear previous list

    if(promptHistory.length === 0){
        historyList.innerHTML = '<p class="text-center text-gray-400">No history yet.</p>';
    } else {
        promptHistory.forEach((prompt, index) => {
            const div = document.createElement('div');
            div.className = 'p-2 rounded-lg bg-gray-800 border border-gray-700 break-words cursor-pointer';
            div.textContent = prompt;
            div.onclick = () => {
                userInput.value = prompt;  // Fill input with clicked prompt
                historyModal.style.display = 'none'; // Close modal
                userInput.focus();
            };
            historyList.appendChild(div);
        });
    }

    historyModal.style.display = 'flex'; // Show modal
});

// Close modal
closeHistoryModalBtn.addEventListener('click', () => {
    historyModal.style.display = 'none';
});

// Optional: close modal if clicking outside content
window.addEventListener('click', (e) => {
    if(e.target === historyModal){
        historyModal.style.display = 'none';
    }
});
