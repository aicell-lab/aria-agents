function ChatHistory({ chatHistory, isSending }) {
    const { marked } = window;
    const { completeCodeBlocks } = window.helpers;

    // Helper function to determine if the icon is an emoji
    const isEmoji = (icon) => /^[\p{Emoji}]+$/u.test(icon);

    // State to track collapsible visibility
    const [isExpanded, setIsExpanded] = React.useState(false);

    // Function to toggle collapsible content
    const toggleContent = () => {
        setIsExpanded(!isExpanded);
    };

    // Helper function to render individual chat messages
    const renderChatMessage = (chat, index) => (
        <div key={index} className="mb-4 relative">
            <div className="text-gray-800 font-semibold flex items-center">
                {chat.role === "user" ? (
                    <>
                        <span className="icon-emoji">👤</span>
                        <span className="ml-1">You</span>
                    </>
                ) : (
                    <>
                        {isEmoji(chat.icon) ? (
                            <span className="icon-emoji">{chat.icon}</span>
                        ) : (
                            <img
                                src={chat.icon}
                                alt={chat.role}
                                className="w-7 h-7"
                            />
                        )}
                        <span className="ml-1">{chat.role}</span>
                    </>
                )}
            </div>
            <div className="bg-gray-100 p-3 rounded mb-2 markdown-body" dangerouslySetInnerHTML={{ __html: chat.content }}></div>
            {isSending && chat.status === 'in_progress' && (
                <div className="absolute inset-0 flex items-center justify-center">
                    <div className="spinner"></div>
                </div>
            )}
        </div>
    );

    // Get all chat entries as an array
    const chatArray = [...chatHistory.values()];

    return (
        <div className="mt-4">
            {chatArray.length > 0 && renderChatMessage(chatArray[0], 0)}

            {chatArray.length > 1 && (
                <>
                    <div className="collapsible" onClick={toggleContent} style={{ cursor: 'pointer', display: 'flex', alignItems: 'center' }}>
                        <span className="arrow" style={{ marginRight: '10px', transition: 'transform 0.3s ease', transform: isExpanded ? 'rotate(90deg)' : 'rotate(0deg)' }}>▶</span>
                        <span>{isExpanded ? "Hide chat history" : "Show more chat history"}</span>
                    </div>

                    {isExpanded && (
                        <div className="collapsible-content" style={{ paddingLeft: '20px', marginTop: '10px' }}>
                            {chatArray.slice(1, -1).map((chat, index) => renderChatMessage(chat, index + 1))}
                        </div>
                    )}
                </>
            )}

            {chatArray.length > 1 && renderChatMessage(chatArray[chatArray.length - 1], chatArray.length - 1)}

        </div>
    );
}

// Expose ChatHistory globally
window.ChatHistory = ChatHistory;