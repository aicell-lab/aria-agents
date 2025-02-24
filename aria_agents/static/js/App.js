const { useState, useEffect, useContext, createContext } = React;
const { MainLayout, Sidebar, ChatPanel, ArtifactsPanel, DialogManager } = window;
const { getServer, getService, login, getUrlParam } = window.helpers;
const { useChat, useAriaArtifacts, useUiState } = window;

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
        try {
            const chatManifest = await ariaArtifacts.readChat(userId, sessionId);
            const newChat = Chat.fromManifest(chatManifest);
            setChat(newChat);
            setUiState(prev => ({ ...prev, status: 'Chat loaded successfully!' }));
        } catch (e) {
            console.error(e);
            alert(`The chat ${sessionId} doesn't exist or you lack the permissions to access it.`);
            setChat(new Chat());
            window.open("https://hypha.aicell.io/public/apps/hypha-login/", '_blank').focus();
        }
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
        handleServices,
        loadSharedChat,
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
    const { chat, uiState, services, setUiState, handleSend,
        handlePause, handleShare,
        handleArtifactNavigation, ariaArtifacts, handleLogin } = window.useAppContext();
    return (
        <div className="min-h-screen flex flex-col">
            <MainLayout
                sidebar={
                    <Sidebar
                        isOpen={uiState.isSidebarOpen}
                        onClose={() => setUiState(prev => ({ ...prev, isSidebarOpen: false }))}
                        prevChats={[]}
                        onSelectChat={ariaArtifacts.loadChat}
                        onDeleteChat={ariaArtifacts.deleteChat}
                        isLoggedIn={!!services.chatService}
                        currentChatId={chat.id}
                        ariaArtifacts={ariaArtifacts} // Pass ariaArtifacts to Sidebar
                    />
                }
                content={
                    <ChatPanel
                        chat={chat}
                        uiState={uiState}
                        onSend={(query, attachments) => chat.sendMessage(query, attachments, services.chatService, chat.statusCallback, ariaArtifacts.artifactCallback, chat.titleCallback, chat.id, services.userId, services.userToken)}
                        onPause={handlePause}
                        onShare={() => setUiState(prev => ({ ...prev, showShareDialog: true }))}
                        onLogin={handleLogin}
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

window.useAppContext = useAppContext;
window.AppProvider = AppProvider;
window.App = App;