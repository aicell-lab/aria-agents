const { useState, useEffect } = React;
const { marked } = window; // Ensure marked library is available for markdown rendering
const { getService, login, completeCodeBlocks, generateMessage, generateSessionID } = window.helpers;
const { Sidebar, ProfileDialog, ChatInput, SuggestedStudies, ChatHistory, ArtefactsPanel } = window;


function App() {
    const [question, setQuestion] = useState("");
    const [chatHistory, setChatHistory] = useState([]);
    const [svc, setSvc] = useState(null);
    const [sessionId, setSessionId] = useState(null);
    const [status, setStatus] = useState("Ready to chat! Type your message and press enter!");
    const [showProfileDialog, setShowProfileDialog] = useState(false);
    const [userProfile, setUserProfile] = useState({
        name: "",
        occupation: "",
        background: ""
    });
    const [isArtefactsPanelOpen, setIsArtefactsPanelOpen] = useState(false);
    const [artefacts, setArtefacts] = useState([]);
    const [currentArtefactIndex, setCurrentArtefactIndex] = useState(0);
    const [assistantName, setAssistantName] = useState("Aria");
    const [streamingContent, setStreamingContent] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const [isSending, setIsSending] = useState(false);
    const [accumulatedArgs, setAccumulatedArgs] = useState("");

    useEffect(() => {
        // Automatically generate a session ID
        setSessionId(generateSessionID());
    }, []);

    const handleLogin = async () => {
        setIsLoading(true);
        const token = await login();
        const service = await getService(token);
        setSvc(service);
        setIsLoading(false);
    };

    const statusCallback = (message) => {
        if (message.type === 'function_call' || message.type === 'text') {
            setAccumulatedArgs((prevArgs) => {
                const newArgs = prevArgs + (message.arguments || message.content);
                if (!newArgs) return "";
                const args = newArgs.replace(/\\n/g, '\n');

                let content;
                if (message.name === "CompleteUserQuery") {
                    content = `## ✅ Generating Final Response...\n\n${args}`;
                } else {
                    content = `## ⏳ Calling tool 🛠️ \`${message.name}\`...\n\n${args}`;
                }
                setStreamingContent(marked(completeCodeBlocks(content)));
                return newArgs;
            });
        }
    };

    const artefactCallback = (artefact, url) => {
        setArtefacts(prevArtefacts => [...prevArtefacts, { artefact, url }]);
    };

    const handleSend = async () => {
        if (!svc) {
            setStatus("Please log in before sending a message.");
            await handleLogin();
            return;
        }

        if (question.trim()) {
            const currentQuestion = question;
            const newChatHistory = [
                ...chatHistory,
                { role: "user", content: currentQuestion, sources: "", image: "" }
            ];
            setChatHistory(newChatHistory);
            setQuestion("");
            setStatus("🤔 Thinking...");
            setIsSending(true);

            const currentMessageId = "message-" + (newChatHistory.length + 1);

            try {
                const extensions = [{ id: "aria" }];
                const response = await svc.chat(currentQuestion, newChatHistory, userProfile, statusCallback, artefactCallback, sessionId, extensions, assistantName);
                const message = generateMessage(response.text, response.steps);
                setChatHistory([
                    ...newChatHistory,
                    { role: "assistant", content: message, sources: response.sources || "", image: response.image || "" }
                ]);
                setStatus("Ready to chat! Type your message and press enter!");
                setStreamingContent(""); // Clear streaming content after completion
                setAccumulatedArgs(""); // Reset accumulated arguments after completion
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
                <Sidebar onLogin={handleLogin} onEditProfile={() => setShowProfileDialog(true)} />
                <div className={`main-panel ${isArtefactsPanelOpen ? 'main-panel-artefacts' : 'main-panel-full'}`}>
                    <div className="bg-white shadow-md rounded-lg p-6 w-full max-w-3xl">
                        <h1 className="text-3xl font-bold mb-4 text-center">🚀 Great science starts here</h1>
                        {chatHistory.length === 0 && (
                            <ChatInput 
                                question={question}
                                setQuestion={setQuestion}
                                handleSend={handleSend}
                                isSending={isSending}
                                svc={svc}
                            />
                        )}
                        <div className="text-center text-gray-700 mb-4 markdown-body" dangerouslySetInnerHTML={{ __html: status }}></div>
                        {chatHistory.length === 0 ? (
                            <SuggestedStudies 
                                setQuestion={setQuestion}
                            />
                        ) : (
                            <ChatHistory 
                                chatHistory={chatHistory}
                                streamingContent={streamingContent}
                                assistantName={assistantName}
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
            {isSending && (
                <div className={`spinner-container ${isArtefactsPanelOpen ? 'margin-right-artefacts' : ''}`}>
                    <div className="spinner"></div>
                </div>
            )}
        </div>
    );
}