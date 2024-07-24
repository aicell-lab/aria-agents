const { useState, useEffect } = React;
const { marked } = window; // Ensure marked library is available for markdown rendering
const { generateSessionID, getService, login, completeCodeBlocks, jsonToMarkdown, modifyLinksToOpenInNewTab } = window.helpers;
const { Sidebar, ProfileDialog, ChatInput, SuggestedStudies, ChatHistory, ArtefactsPanel } = window;

function App() {
    const [question, setQuestion] = useState("");
    const [chatHistory, setChatHistory] = useState(new Map());
    const [svc, setSvc] = useState(null);
    const [sessionId, setSessionId] = useState(null);
    const [status, setStatus] = useState("Please log in before sending a message.");
    const [showProfileDialog, setShowProfileDialog] = useState(false);
    const [userProfile, setUserProfile] = useState({
        name: "",
        occupation: "",
        background: ""
    });
    const [isArtefactsPanelOpen, setIsArtefactsPanelOpen] = useState(false);
    const [artefacts, setArtefacts] = useState([]);
    const [currentArtefactIndex, setCurrentArtefactIndex] = useState(0);
    const [isLoading, setIsLoading] = useState(false);
    const [isSending, setIsSending] = useState(false);

    useEffect(() => {
        // Automatically generate a session ID
        setSessionId(generateSessionID());
    }, []);

    const handleLogin = async () => {
        setIsLoading(true);
        const token = await login();
        const service = await getService(token);
        setSvc(service);
        setStatus("Ready to chat! Type your message and press enter!");
        setIsLoading(false);
    };

const statusCallback = (message) => {
    const { type, session: { id, role_setting: roleSetting }, status, content, arguments: args, name, query_id } = message;
    const { name: roleName, icon: roleIcon } = roleSetting || {};
    
    const headerStartInProgress = marked(`### ⏳ Calling tool 🛠️ \`${name}\`...\n\n`);
    const headerFinished = marked(`### Tool 🛠️ \`${name}\`\n\n`);

    if (status === 'start') {
        // Initialize new message entry in chat history
        setChatHistory(prevHistory => {
            const updatedHistory = new Map(prevHistory);
            updatedHistory.set(query_id, {
                role: roleName || 'Agent',
                icon: roleIcon || '🤖',
                toolName: name,
                accumulatedArgs: '',
                content: headerStartInProgress,
                status: 'in_progress',
            });
            return updatedHistory;
        });
    } else if (status === 'in_progress') {
        // Update existing message entry with new content
        setChatHistory(prevHistory => {
            const updatedHistory = new Map(prevHistory);
            const lastMessage = updatedHistory.get(query_id);
            if (lastMessage) {
                lastMessage.accumulatedArgs += (args || "").replace(/\n/g, ''); // Accumulate arguments
                if (name === 'SummaryWebsite') {
                    lastMessage.content = 'Generating summary website...';
                } else {
                    lastMessage.content = headerStartInProgress + `<div>${lastMessage.accumulatedArgs}</div>`;
                }
                updatedHistory.set(query_id, lastMessage);
            }
            return updatedHistory;
        });
    } else if (status === 'finished') {
        // Finalize the message entry
        setChatHistory(prevHistory => {
            const updatedHistory = new Map(prevHistory);
            const lastMessage = updatedHistory.get(query_id);
            if (lastMessage) {
                if (name === 'SummaryWebsite') {
                    // TODO: Update the URL to the actual summary website
                    lastMessage.content = `<a href="${null}" target="_blank">View Summary Website</a>`;
                } else {
                    let finalContent = (content || jsonToMarkdown(args) || "");
                    finalContent = modifyLinksToOpenInNewTab(marked(completeCodeBlocks(finalContent)));
                    lastMessage.content = headerFinished + finalContent;
                }
                lastMessage.status = 'finished';
                updatedHistory.set(query_id, lastMessage);
            }
            return updatedHistory;
        });
    }
};


    const artefactCallback = (artefact, url) => {
        setArtefacts(prevArtefacts => [...prevArtefacts, { artefact, url }]);
    };

    const handleSend = async () => {
        if (!svc) {
            await handleLogin();
            return;
        }
    
        if (question.trim()) {
            const currentQuestion = question;
            const newChatHistory = [
                ...chatHistory,
                { role: "user", content: marked(completeCodeBlocks(currentQuestion)), sources: "", image: "" }
            ];
            setChatHistory(new Map(newChatHistory.map((item, index) => [index.toString(), item])));
            setQuestion("");
            setStatus("🤔 Thinking...");
            setIsSending(true);
    
            try {
                const currentChatHistory = Array.from(chatHistory.values()).map(chat => {
                    const { role, content, ...rest } = chat;
                    return { ...rest, role: role.toString(), content: content.toString() };
                });
                const extensions = [{ id: "aria" }];
                await svc.chat(currentQuestion, currentChatHistory, userProfile, statusCallback, artefactCallback, sessionId, extensions);
                setStatus("Ready to chat! Type your message and press enter!");
            } catch (e) {
                setStatus(`❌ Error: ${e.message}`);
            } finally {
                setIsSending(false);
            }
        }
    };

    return (
        <div className="min-h-screen flex flex-col">
            <div className="flex-1 flex">
                <Sidebar onEditProfile={() => setShowProfileDialog(true)} />
                <div className={`main-panel ${isArtefactsPanelOpen ? 'main-panel-artefacts' : 'main-panel-full'}`}>
                    <div className="bg-white shadow-md rounded-lg p-6 w-full max-w-3xl">
                        <h1 className="text-3xl font-bold mb-4 text-center">🚀 Great science starts here</h1>
                        {chatHistory.size === 0 && (
                            <ChatInput
                                onLogin={handleLogin}
                                question={question}
                                setQuestion={setQuestion}
                                handleSend={handleSend}
                                svc={svc}
                            />
                        )}
                        <div className="text-center text-gray-700 mb-4 markdown-body" dangerouslySetInnerHTML={{ __html: status }}></div>
                        {chatHistory.size === 0 ? (
                            <SuggestedStudies setQuestion={setQuestion} />
                        ) : (
                            <ChatHistory
                                chatHistory={chatHistory}
                                isSending={isSending}
                            />
                        )}
                    </div>
                </div>
            </div>
            {showProfileDialog && (
                <ProfileDialog
                    userProfile={userProfile}
                    onClose={() => setShowProfileDialog(false)}
                    onSave={(profile) => {
                        setUserProfile(profile);
                        setShowProfileDialog(false);
                    }}
                />
            )}
            {isArtefactsPanelOpen ? (
                <ArtefactsPanel
                    onClose={() => setIsArtefactsPanelOpen(!isArtefactsPanelOpen)}
                    artefacts={artefacts}
                    currentArtefactIndex={currentArtefactIndex}
                    onPrev={() => {
                        if (currentArtefactIndex > 0) {
                            setCurrentArtefactIndex(currentArtefactIndex - 1);
                        }
                    }}
                    onNext={() => {
                        if (currentArtefactIndex < artefacts.length - 1) {
                            setCurrentArtefactIndex(currentArtefactIndex + 1);
                        }
                    }}
                />
            ) : (
                <button
                    onClick={() => setIsArtefactsPanelOpen(!isArtefactsPanelOpen)}
                    className="fixed top-0 right-0 mt-4 mr-4 bg-blue-600 text-white py-2 px-4 rounded text-lg transition duration-300 ease-in-out transform hover:scale-105"
                >
                    Artefacts
                </button>
            )}
            {isLoading && (
                <div className={`spinner-container ${isArtefactsPanelOpen ? 'margin-right-artefacts' : ''}`}>
                    <div className="spinner"></div>
                </div>
            )}
        </div>
    );
}

// Expose App globally
window.App = App;
