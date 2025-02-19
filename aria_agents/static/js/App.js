/* global React */
const { useState, useEffect } = React;
const { 
    getServer, getService, login, getUrlParam
} = window.helpers;
const {
    handleMessageStart, handleMessageProgress, handleMessageFinished
} = window.chatStatusHelpers;
const {
    MainLayout, Sidebar, ChatPanel, ArtifactsPanel, DialogManager, Chat, AriaArtifacts
} = window;

function App() {
    const [chat, setChat] = useState(new Chat());
    const [ariaArtifacts, setAriaArtifacts] = useState(null);
    const [uiState, setUiState] = useState({
        question: "",
        attachmentNames: [],
        isPaused: false,
        isSending: false,
        isLoading: false,
        isSidebarOpen: false,
        isArtifactsPanelOpen: false,
        showShareDialog: false,
        alertContent: "",
        status: "Please log in before sending a message.",
        currentArtifactIndex: 0,
    });

    const [services, setServices] = useState({
        chatService: null,
        artifactManager: null,
        userId: "",
        userToken: "",
        artifactWorkspace: ""
    });

    useEffect(() => {
        initializeChat();
    }, []);

    const initializeChat = async () => {
        if (localStorage.getItem("token")) {
            await handleLogin();
        }
        
        const sessionIdParam = getUrlParam("sessionId");
        const userIdParam = getUrlParam("userId");
        if (sessionIdParam && userIdParam) {
            await loadSharedChat(sessionIdParam, userIdParam);
        }
    };

    const handleLogin = async () => {
        const token = await login();
        setUiState(prev => ({ ...prev, isLoading: true }));
        await handleServices(token);
        setUiState(prev => ({ 
            ...prev, 
            isLoading: false,
            status: "Ready to chat! Type your message and press enter!"
        }));
    };

    const handleServices = async (token) => {
        const server = await getServer(token);
        const userId = server.config.user.id;
        const workspace = `ws-user-${userId}`;
        
        const chatService = await getService(server, "aria-agents/aria-agents", "public/aria-agents");
        const artifactManager = await getService(server, "public/artifact-manager");
        
        try {
            await chatService.ping();
        } catch (error) {
            setUiState(prev => ({
                ...prev,
                alertContent: "This account doesn't have permission to use the chatbot"
            }));
            throw error;
        }

        const ariaArtifacts = new AriaArtifacts(artifactManager, workspace);
        await ariaArtifacts.createChatCollection();
        setAriaArtifacts(ariaArtifacts);
        
        setServices({
            chatService,
            artifactManager,
            userId,
            userToken: token,
            artifactWorkspace: workspace
        });
    };

    const validateSession = (sessionId) => {
        const currentSessionId = getUrlParam("sessionId") ?? chat.id;
        return sessionId === currentSessionId && !uiState.isPaused;
    };

    const handleSend = async () => {
        if (!services.chatService) {
            await handleLogin();
            return;
        }

        if (!uiState.question.trim()) return;

        setUiState(prev => ({ ...prev, isSending: true, isPaused: false }));
        await sendMessage(uiState.question);
        setUiState(prev => ({ 
            ...prev, 
            question: "", 
            attachmentNames: [],
            status: "🤔 Thinking..."
        }));
    };

    const sendMessage = async (content) => {
        try {
            const currentHistory = prepareMessageHistory();
            await sendChatRequest(content, currentHistory);
        } catch (error) {
            console.error(error);
            setUiState(prev => ({ 
                ...prev, 
                status: `❌ Error: ${error.message || error}` 
            }));
        } finally {
            awaitUserResponse();
        }
    };

    const loadChat = async (chatData) => {
        try {
            const loadedChat = await ariaArtifacts.readChat(services.userId, chatData.id);
            setChat(loadedChat);
            setUiState(prev => ({
                ...prev,
                isSending: false,
                isPaused: false,
                status: "Chat loaded successfully!"
            }));
        } catch (e) {
            console.error("Failed to load chat:", e);
            setUiState(prev => ({
                ...prev,
                alertContent: "Failed to load chat. Please try again."
            }));
        }
    };

    const deleteChat = async (chatToDelete) => {
        try {
            await ariaArtifacts.deleteChat(chatToDelete);
            const loadedChats = await ariaArtifacts.loadChats();
            // Update chats list
        } catch (e) {
            console.error("Failed to delete chat:", e);
            setUiState(prev => ({
                ...prev,
                alertContent: "Failed to delete chat. Please try again."
            }));
        }
    };

    const handleAttachment = async (event) => {
        const files = event.target.files || event.dataTransfer.files;
        const newAttachments = await Promise.all(
            Array.from(files).map(async file => ({
                name: file.name,
                content: await file.text()
            }))
        );
        
        setChat(prev => {
            const newChat = prev.clone();
            newChat.attachments = [...newChat.attachments, ...newAttachments];
            return newChat;
        });
        
        setUiState(prev => ({
            ...prev,
            attachmentNames: [...prev.attachmentNames, ...newAttachments.map(a => a.name)]
        }));
    };

    const handlePause = () => {
        setUiState(prev => ({ 
            ...prev, 
            isPaused: true,
            status: "Chat stopped."
        }));
    };

    const handleShare = async () => {
        await ariaArtifacts.saveChat(chat, services.userId, { "*": "r" });
        setUiState(prev => ({ ...prev, showShareDialog: false }));
    };

    const handleArtifactNavigation = (direction) => {
        setUiState(prev => ({
            ...prev,
            currentArtifactIndex: prev.currentArtifactIndex + direction
        }));
    };

    const prepareMessageHistory = () => {
        return Array.from(chat.history.values()).map(msg => ({
            role: msg.role === "user" ? "user" : "assistant",
            content: contentWithAttachments(msg.content, msg.attachments || [])
        }));
    };

    const contentWithAttachments = (content, attachments) => {
        const attachmentNames = attachments.map(a => a.name || a).join(",\n");
        return `<MESSAGE_CONTENT>\n${content}\n</MESSAGE_CONTENT>\n\n<ATTACHMENT_NAMES>\n${attachmentNames}</ATTACHMENT_NAMES>`;
    };

    const sendChatRequest = async (content, history) => {
        if (!services.chatService) throw new Error("Chat service not initialized");
        
        const extensions = [{ id: "aria" }];
        
        if (!chat.title) {
            const titleQuestion = 
                `Give a succinct title to this chat session summarizing this prompt: "${content}". 
                 Respond ONLY with words, maximum six words. DO NOT include "Chat Session Title".`;
            
            await services.chatService.chat(
                titleQuestion,
                history,
                handleTitleCallback,
                () => {},
                chat.id,
                services.userId,
                services.userToken,
                extensions
            );
        }
        
        await services.chatService.chat(
            content,
            history,
            handleStatusCallback,
            handleArtifactCallback,
            chat.id,
            services.userId,
            services.userToken,
            extensions
        );
    };

    const handleTitleCallback = async (message) => {
        if (message.status === "finished") {
            const newTitle = JSON.parse(message.arguments).response.trim();
            setChat(prev => {
                const newChat = prev.clone();
                newChat.title = newTitle;
                return newChat;
            });
            await saveChatToArtifacts();
        }
    };

    const saveChatToArtifacts = async () => {
        if (!ariaArtifacts) return;
        try {
            await ariaArtifacts.saveChat(chat, services.userId);
        } catch (e) {
            console.error("Failed to save chat:", e);
        }
    };

    const handleArtifactCallback = (artifact, url) => {
        setChat(prev => {
            const newChat = prev.clone();
            newChat.artifacts = [...newChat.artifacts, { artifact, url }];
            return newChat;
        });
    };

    const loadSharedChat = async (sessionId, userId) => {
        try {
            const loadedChat = await ariaArtifacts.readChat(userId, sessionId);
            setChat(loadedChat);
        } catch (e) {
            setUiState(prev => ({
                ...prev,
                alertContent: "Failed to load shared chat. Please try again. Error: " + e
            }));
        }
    };

    const handleStatusCallback = async (message) => {
        const { status, content, query_id, session, name, args } = message;
        
        if (!validateSession(session.id)) return;

        switch (status) {
            case "start":
                handleMessageStart(query_id, name, session);
                break;
            case "in_progress":
                handleMessageProgress(query_id, name, args);
                break;
            case "finished":
                handleMessageFinished(query_id, name, content, args);
                break;
        }
    };

    const awaitUserResponse = () => {
        setUiState(prev => ({
            ...prev,
            isSending: false,
            status: "Ready to chat! Type your message and press enter!"
        }));
    };

    window.openSummaryWebsite = (index) => {
        if (index < chat.artifacts.length) {
            setUiState(prev => ({
                ...prev,
                isArtifactsPanelOpen: true,
                currentArtifactIndex: index
            }));
        }
    };

    return (
        <div className="min-h-screen flex flex-col">
            <MainLayout
                sidebar={
                    <Sidebar 
                        isOpen={uiState.isSidebarOpen}
                        onClose={() => setUiState(prev => ({ ...prev, isSidebarOpen: false }))}
                        prevChats={[]}
                        onSelectChat={loadChat}
                        onDeleteChat={deleteChat}
                        isLoggedIn={!!services.chatService}
                        currentChatId={chat.id}
                    />
                }
                content={
                    <ChatPanel
                        chat={chat}
                        uiState={uiState}
                        onSend={handleSend}
                        onAttachment={handleAttachment}
                        onPause={handlePause}
                        onShare={() => setUiState(prev => ({ ...prev, showShareDialog: true }))}
                    />
                }
                artifacts={
                    <ArtifactsPanel
                        artifacts={chat.artifacts}
                        currentIndex={uiState.currentArtifactIndex}
                        isOpen={uiState.isArtifactsPanelOpen}
                        onClose={() => setUiState(prev => ({ ...prev, isArtifactsPanelOpen: false }))}
                        onNavigate={handleArtifactNavigation}
                    />
                }
            />
            <DialogManager 
                uiState={uiState} 
                setUiState={setUiState}
                chat={chat}
                shareUrl={window.location.href}
                onShare={handleShare}
            />
        </div>
    );
}

window.App = App;
