function ChatHistory({ chatHistory, streamingContent, assistantName }) {
    const { marked } = window; // Ensure marked library is available for markdown rendering
    const { completeCodeBlocks } = window.helpers; // Ensure helpers are available

    return (
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
    );
};

// Expose ChatHistory globally
window.ChatHistory = ChatHistory;
