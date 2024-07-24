const { openSummaryWebsite } = window;  // Global function to open the summary website

function ChatHistory({ chatHistory, isSending }) {
    const { marked } = window;
    const { completeCodeBlocks } = window.helpers;

    // Helper function to determine if the icon is an emoji
    const isEmoji = (icon) => /^[\p{Emoji}]+$/u.test(icon);

    return (
        <div className="mt-4">
            {[...chatHistory.values()].map((chat, index, array) => (
                <div key={index} className="mb-4 relative">
                    {index === 0 || array[index - 1].role !== chat.role ? (
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
                    ) : null}
                    <div className="bg-gray-100 p-3 rounded mb-2 markdown-body" dangerouslySetInnerHTML={{ __html: chat.content }}></div>
                    {isSending && chat.status === 'in_progress' && (
                        <div className="absolute inset-0 flex items-center justify-center">
                            <div className="spinner"></div>
                        </div>
                    )}
                </div>
            ))}
        </div>
    );
}

// Expose ChatHistory globally
window.ChatHistory = ChatHistory;
