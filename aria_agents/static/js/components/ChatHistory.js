/* global React */
function ChatHistory({ chat, isSending }) {
    const [expandedMessages, setExpandedMessages] = React.useState(new Set());
    const messages = Array.from(chat.history.values());

    const toggleMessage = (index) => {
        setExpandedMessages(prev => {
            const newSet = new Set(prev);
            if (newSet.has(index)) {
                newSet.delete(index);
            } else {
                newSet.add(index);
            }
            return newSet;
        });
    };

    return (
        <div className="chat-history mt-4">
            {messages.map((message, index) => (
                <Message
                    key={index}
                    message={message}
                    index={index}
                    isExpanded={expandedMessages.has(index)}
                    onToggleExpand={() => toggleMessage(index)}
                    isLastMessage={index === messages.length - 1}
                    isSending={isSending}
                />
            ))}
        </div>
    );
}

function Message({ message, index, isExpanded, onToggleExpand, isLastMessage, isSending }) {
    return (
        <div id={`message-${index}`} className="mb-4 relative">
            <MessageHeader message={message} />
            <MessageContent 
                message={message}
                isExpanded={isExpanded}
                onToggleExpand={onToggleExpand}
            />
            {isLastMessage && isSending && <SendingIndicator />}
        </div>
    );
}

function MessageHeader({ message }) {
    const isEmoji = (icon) => /^[\p{Emoji}]+$/u.test(icon);

    return (
        <div className="text-gray-800 font-semibold flex items-center">
            {message.role === "user" ? (
                <>
                    <span className="icon-emoji">👤</span>
                    <span className="ml-1">You</span>
                </>
            ) : (
                <>
                    {isEmoji(message.icon) ? (
                        <span className="icon-emoji">{message.icon}</span>
                    ) : (
                        <img
                            src={message.icon}
                            alt={message.role}
                            className="w-7 h-7"
                        />
                    )}
                    <span className="ml-1">{message.role}</span>
                </>
            )}
        </div>
    );
}

function MessageContent({ message, isExpanded, onToggleExpand }) {
    return (
        <div className="bg-gray-100 p-3 rounded mb-2">
            {message.role !== "user" && (
                <>
                    <div
                        className="bg-gray-100 markdown-body"
                        dangerouslySetInnerHTML={{ __html: message.title }}
                    />
                    {(message.role !== "Aria" && message.toolName !== "SummaryWebsite") && (
                        <ExpandToggle 
                            isExpanded={isExpanded}
                            onToggle={onToggleExpand}
                        />
                    )}
                </>
            )}

            {(isExpanded || message.role === "user" || 
              message.role === "Aria" || message.toolName === "SummaryWebsite") && (
                <div
                    className="bg-gray-100 markdown-body"
                    dangerouslySetInnerHTML={{ __html: message.content }}
                />
            )}

            {message.role === "user" && message.attachments?.length > 0 && (
                <AttachmentList attachments={message.attachments} />
            )}
        </div>
    );
}

function ExpandToggle({ isExpanded, onToggle }) {
    return (
        <div
            className="collapsible cursor-pointer flex items-center"
            onClick={onToggle}
        >
            <span
                className="arrow mr-2 transition-transform duration-300"
                style={{
                    transform: isExpanded ? "rotate(90deg)" : "rotate(0deg)",
                }}
            >
                ▶
            </span>
            <span>
                {isExpanded ? "Hide details" : "Show more details"}
            </span>
        </div>
    );
}

function AttachmentList({ attachments }) {
    return (
        <div className="mt-2 flex flex-wrap gap-2">
            {attachments.map((fileName, fileIndex) => (
                <div
                    key={fileIndex}
                    className="bg-gray-200 text-gray-700 px-3 py-1 rounded-md"
                >
                    <span>{fileName}</span>
                </div>
            ))}
        </div>
    );
}

function SendingIndicator() {
    return (
        <div className="absolute inset-0 flex items-center justify-center">
            <div className="spinner"></div>
        </div>
    );
}

window.ChatHistory = ChatHistory;
