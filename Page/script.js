// Firebase initialization variables for Canvas environment
const __app_id = "your-app-id";
const __firebase_config = "{}";
const __initial_auth_token = "your-auth-token";

// DOM elements
const chatContainer = document.getElementById('chat-container');
const inputForm = document.getElementById('input-form');
const userInput = document.getElementById('user-input');
const sendButton = document.getElementById('send-button');
const fileInput = document.getElementById('file-input');
const viewKnowledgeBtn = document.getElementById('view-knowledge-btn');
const knowledgeModal = document.getElementById('knowledge-modal');
const closeModalBtn = document.getElementById('close-modal-btn');
const knowledgeList = document.getElementById('knowledge-list');

// Function to add a message to the chat interface
function addMessage(text, type, source = null) {
    const messageDiv = document.createElement('div');
    messageDiv.classList.add('message');
    messageDiv.classList.add(type);

    const content = document.createElement('p');
    content.textContent = text;
    messageDiv.appendChild(content);

    if (source) {
        const sourceDiv = document.createElement('div');
        sourceDiv.classList.add('source-link', 'mt-2');
        sourceDiv.textContent = `Source: ${source}`;
        messageDiv.appendChild(sourceDiv);
    }

    chatContainer.appendChild(messageDiv);
    chatContainer.scrollTop = chatContainer.scrollHeight; // Auto-scroll to the bottom
}

// Handle the user's question submission
inputForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const question = userInput.value.trim();
    if (!question) {
        return;
    }

    addMessage(question, 'user-message');
    userInput.value = '';
    toggleLoading(true);

    try {
        const response = await fetch('http://127.0.0.1:8000/ask', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question: question })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        const answer = data.answer;
        
        if (answer) {
            addMessage(answer, 'bot-message', 'Knowledge Base');
        } else {
            addMessage("Sorry, I could not find a relevant answer.", 'bot-message');
        }
    } catch (error) {
        console.error("Error asking question:", error);
        addMessage(`I'm sorry, an error occurred while connecting to the bot. Please check the server.`, 'bot-message');
    } finally {
        toggleLoading(false);
    }
});

// Handle file input changes
fileInput.addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (!file) {
        return;
    }

    addMessage(`Uploading document: ${file.name}...`, 'bot-message');
    toggleLoading(true);

    try {
        const formData = new FormData();
        formData.append('file', file);
        
        const response = await fetch('http://127.0.0.1:8000/add-knowledge', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        addMessage(data.message, 'bot-message', file.name);

    } catch (error) {
        console.error("Error uploading file:", error);
        addMessage(`Failed to upload file. Please check the server and try again.`, 'bot-message');
    } finally {
        toggleLoading(false);
    }
});

// Handle viewing knowledge
viewKnowledgeBtn.addEventListener('click', async () => {
    knowledgeList.innerHTML = '<p class="text-center text-gray-400">Loading knowledge base...</p>';
    knowledgeModal.style.display = 'flex';

    try {
        const response = await fetch(`http://127.0.0.1:8000/view-knowledge`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();

        if (data.knowledge && data.knowledge.length > 0) {
            knowledgeList.innerHTML = ''; // Clear loading message
            data.knowledge.forEach(item => {
                const div = document.createElement('div');
                div.className = 'p-4 rounded-lg bg-gray-800 border border-gray-700 break-words';
                div.innerHTML = `<p class="font-bold text-sm text-sky-400">${item.source}</p><p class="mt-2 text-sm">${item.content}</p>`;
                knowledgeList.appendChild(div);
            });
        } else {
            knowledgeList.innerHTML = '<p class="text-center text-gray-400">Knowledge base is empty.</p>';
        }
    } catch (error) {
        console.error("Error fetching knowledge:", error);
        knowledgeList.innerHTML = `<p class="text-center text-red-400">Failed to load knowledge. Server might be down.</p>`;
    }
});

// Close modal
closeModalBtn.addEventListener('click', () => {
    knowledgeModal.style.display = 'none';
});

// Close modal by clicking outside
window.addEventListener('click', (e) => {
    if (e.target === knowledgeModal) {
        knowledgeModal.style.display = 'none';
    }
});

// Function to toggle loading state
function toggleLoading(isLoading) {
    if (isLoading) {
        sendButton.disabled = true;
        sendButton.innerHTML = `<div class="loader"></div>`;
        userInput.disabled = true;
        fileInput.disabled = true;
        viewKnowledgeBtn.disabled = true;
    } else {
        sendButton.disabled = false;
        sendButton.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="w-6 h-6">
            <path d="M3.478 2.405a.75.75 0 0 0-.926.94l2.432 7.917H17.5a.75.75 0 0 1 0 1.5H4.984l-2.432 7.917a.75.75 0 0 0 .926.94 60.519 60.519 0 0 0 18.445-8.986.75.75 0 0 0 0-1.218A60.517 60.517 0 0 0 3.478 2.405Z" />
        </svg>`;
        userInput.disabled = false;
        fileInput.disabled = false;
        viewKnowledgeBtn.disabled = false;
    }
}
