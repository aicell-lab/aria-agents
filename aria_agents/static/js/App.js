import { useState, useEffect, useContext, createContext } from 'react';
import { MainLayout, Sidebar, ChatPanel, ArtifactsPanel, DialogManager } from './components';
import { getServer, getService, login, getUrlParam } from './utils/helpers';
import { useChat, useAriaArtifacts, useUiState } from './hooks';
import { AriaArtifacts } from './models';

const AppContext = createContext();

function AppProvider({ children }) {
    const { chat, setChat } = useChat();
    const { ariaArtifacts, setAriaArtifacts } = useAriaArtifacts();
    const { uiState, setUiState } = useUiState();
    const [services, setServices] = useState({
        chatService: null,
        artifactManager: null,
        userId: '',
        userToken: '',
        artifactWorkspace: ''
    });

    useEffect(() => {
        initializeChat();
    }, []);

    const initializeChat = async () => {
        if (localStorage.getItem('token')) {
            await handleLogin();
        }
        const sessionIdParam = getUrlParam('sessionId');
        const userIdParam = getUrlParam('userId');
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
            status: 'Ready to chat! Type your message and press enter!'
        }));
    };

    const handleServices = async (token) => {
        const server = await getServer(token);
        const userId = server.config.user.id;
        const workspace = `ws-user-${userId}`;
        const chatService = await getService(server, 'aria-agents/aria-agents', 'public/aria-agents');
        const artifactManager = await getService(server, 'public/artifact-manager');
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

    const loadSharedChat = async (sessionId, userId) => {
        // Implement the logic to load a shared chat session
    };

    const value = {
        chat,
        setChat,
        ariaArtifacts,
        uiState,
        setUiState,
        services,
        setServices,
        initializeChat,
        handleLogin,
        handleServices
    };

    return (
        <AppContext.Provider value={value}>
            {children}
        </AppContext.Provider>
    );
}

function useAppContext() {
    return useContext(AppContext);
}

function App() {
    const { chat, uiState, services, setUiState, handleSend, handleAttachment, handlePause, handleShare, handleArtifactNavigation, loadChat, deleteChat } = useAppContext();
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

export { AppProvider, useAppContext, App };
