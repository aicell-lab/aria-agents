const { useState, useEffect } = React;
const { marked } = window; // Ensure marked library is available for markdown rendering
const { getService, login, completeCodeBlocks, generateMessage, generateSessionID } = window.helpers;
const { Sidebar, ProfileDialog, ArtefactsPanel } = window;


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
                const extensions = [{ id: "aria" }]
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
                const newArgs = prevArgs + message.arguments || message.content;
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

    const handleProfileSave = () => {
        setShowProfileDialog(false);
    };

    const handleArtefactsToggle = () => {
        setIsArtefactsPanelOpen(!isArtefactsPanelOpen);
    };

    const handlePrevArtefact = () => {
        if (currentArtefactIndex > 0) {
            setCurrentArtefactIndex(currentArtefactIndex - 1);
        }
    };

    const handleNextArtefact = () => {
        if (currentArtefactIndex < artefacts.length - 1) {
            setCurrentArtefactIndex(currentArtefactIndex + 1);
        }
    };

    // The main panel is adjusted based on the artefacts-panel state
    return (
        <div className="min-h-screen flex flex-col ">
            <div className="flex-1 flex ">
                <Sidebar onLogin={handleLogin} onEditProfile={() => setShowProfileDialog(true)} />
                <div className={`main-panel ${isArtefactsPanelOpen ? 'main-panel-artefacts' : 'main-panel-full'}`}>
                    <div className="bg-white shadow-md rounded-lg p-6 w-full max-w-3xl">
                        <h1 className="text-3xl font-bold mb-4 text-center">🚀 Great science starts here</h1>
                        {chatHistory.length === 0 && (
                            <div className="mb-4 flex flex-col items-center">
                                <input
                                    type="text"
                                    placeholder="Type what you want to study"
                                    value={question}
                                    onChange={(e) => setQuestion(e.target.value)}
                                    className="w-full p-3 border border-gray-300 rounded mb-2 text-lg"
                                    onKeyPress={(e) => e.key === 'Enter' && handleSend()}
                                />
                                {svc ? (
                                    <button
                                        onClick={handleSend}
                                        className="w-full bg-blue-600 text-white py-2 px-4 rounded text-lg transition duration-300 ease-in-out transform hover:scale-105"
                                    >
                                        Send ✈️
                                    </button>
                                ) : (
                                    <button
                                        disabled
                                        className="w-full bg-gray-400 text-white py-2 px-4 rounded text-lg"
                                        title="Please login to send"
                                    >
                                        Please Login 🚀
                                    </button>
                                )}
                            </div>
                        )}
                        <div className="text-center text-gray-700 mb-4 markdown-body" dangerouslySetInnerHTML={{ __html: status }}></div>
                        {chatHistory.length === 0 ? (
                            <div className="mt-4 text-center">
                                <div className="text-gray-700 font-semibold mb-2">Suggested Studies:</div>
                                <div className="flex flex-wrap justify-center">
                                    <button
                                        className="bg-gray-200 p-2 m-1 rounded-lg cursor-pointer text-lg transition duration-300 ease-in-out transform hover:scale-105"
                                        onClick={() => setQuestion("I want to study the effect of osmotic pressure on yeast cells.")}
                                    >
                                        Osmotic pressure on yeast cells
                                    </button>
                                    <button
                                        className="bg-gray-200 p-2 m-1 rounded-lg cursor-pointer text-lg transition duration-300 ease-in-out transform hover:scale-105"
                                        onClick={() => setQuestion("I'm interested in studying the metabolomics of U2OS cells.")}
                                    >
                                        Metabolomics of U2OS cells
                                    </button>
                                    <button
                                        className="bg-gray-200 p-2 m-1 rounded-lg cursor-pointer text-lg transition duration-300 ease-in-out transform hover:scale-105"
                                        onClick={() => setQuestion("I want to investigate the influence of circadian rhythm on the behavior of Drosophila.")}
                                    >
                                        Circadian rhythm in Drosophila
                                    </button>
                                    <button
                                        className="bg-gray-200 p-2 m-1 rounded-lg cursor-pointer text-lg transition duration-300 ease-in-out transform hover:scale-105"
                                        onClick={() => setQuestion("I'm interested in studying the factors affecting photosynthetic efficiency in C4 plants.")}
                                    >
                                        Photosynthetic efficiency in C4 plants
                                    </button>
                                    <button
                                        className="bg-gray-200 p-2 m-1 rounded-lg cursor-pointer text-lg transition duration-300 ease-in-out transform hover:scale-105"
                                        onClick={() => setQuestion("I'm interested in investigating the genetic basis of thermotolerance in extremophiles.")}
                                    >
                                        Thermotolerance in extremophiles
                                    </button>
                                    <button
                                        className="bg-gray-200 p-2 m-1 rounded-lg cursor-pointer text-lg transition duration-300 ease-in-out transform hover:scale-105"
                                        onClick={() => setQuestion("I aim to examine the neural plasticity in adult zebrafish after spinal cord injury.")}
                                    >
                                        Neural plasticity in adult zebrafish
                                    </button>
                                </div>
                            </div>
                        ) : (
                            <div className="mt-4">
                                {chatHistory.map((chat, index) => (
                                    <div key={index} className="mb-4">
                                        <div className="text-gray-800 font-semibold">{chat.role === "user" ? "👤 You:" : `🤖 ${assistantName}:`}</div>
                                        {chat.role === "user" ? (
                                            <>
                                                <div className="bg-gray-100 p-3 rounded mb-2">{chat.content}</div>
                                            </>
                                        ) : (
                                            <>
                                                <div className="bg-gray-100 p-3 rounded mb-2 markdown-body" dangerouslySetInnerHTML={{ __html: marked(completeCodeBlocks(chat.content || "")) }}></div>
                                                <div className="flex flex-wrap">
                                                    {chat.sources && chat.sources.map((source, i) => (
                                                        <div key={i} className="bg-gray-200 p-2 m-1 rounded">{source}</div>
                                                    ))}
                                                </div>
                                                {chat.image && (
                                                    <img src={chat.image} alt="Returned Image" className="mt-2 rounded" />
                                                )}
                                            </>
                                        )}
                                    </div>
                                ))}
                                {streamingContent && (
                                    <div className="mb-4 fade-in">
                                        <div className="text-gray-800 font-semibold">🤖 {assistantName}:</div>
                                        <div className="bg-gray-100 p-3 rounded mb-2 markdown-body" dangerouslySetInnerHTML={{ __html: streamingContent }}></div>
                                    </div>
                                )}
                                <div className="bg-white shadow-md rounded-lg p-4 w-full max-w-3xl mx-auto mt-4 flex items-center">
                                    <textarea
                                        placeholder="Type what you want to study"
                                        value={question}
                                        onChange={(e) => setQuestion(e.target.value)}
                                        className="w-full p-3 border border-gray-300 rounded resize-none"
                                        rows="1"
                                        onKeyPress={(e) => e.key === 'Enter' && handleSend()}
                                    ></textarea>
                                    <div className="flex items-center ml-2">
                                        <button className="text-gray-600 hover:text-gray-900 focus:outline-none transition duration-300 ease-in-out transform hover:scale-105">
                                            📎
                                        </button>
                                        <button
                                            onClick={handleSend}
                                            className="ml-2 bg-blue-600 text-white p-2 rounded-full focus:outline-none transition duration-300 ease-in-out transform hover:scale-105"
                                        >
                                            ✈️
                                        </button>
                                    </div>
                                </div>
                            </div>
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
                        handleProfileSave();
                    }}
                />
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
            {isArtefactsPanelOpen && (
                <ArtefactsPanel
                    onClose={handleArtefactsToggle}
                    artefacts={artefacts}
                    currentArtefactIndex={currentArtefactIndex}
                    onPrev={handlePrevArtefact}
                    onNext={handleNextArtefact}
                />
            )}
            {!isArtefactsPanelOpen && (
                <button
                    onClick={handleArtefactsToggle}
                    className="fixed top-0 right-0 mt-4 mr-4 bg-blue-600 text-white py-2 px-4 rounded text-lg transition duration-300 ease-in-out transform hover:scale-105"
                >
                    Artefacts
                </button>
            )}
        </div>
    );
}