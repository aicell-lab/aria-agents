/* global useState, useRef */
const {
    ChatHistory,
    ChatInput,
    PauseButton,
    SuggestedStudies
} = window;

function ChatPanel({ 
    chat, 
    isSending,
    isPaused,
    isComplete,
    onSend,
    onPause,
    onShare 
}) {
    const [question, setQuestion] = useState("");

    return (
        <div className="chat-panel">
            <Header />
            
            <ChatContent 
                chat={chat}
                question={question}
                setQuestion={setQuestion}
                isSending={isSending}
                isPaused={isPaused}
                isComplete={isComplete}
                onSend={onSend}
                onPause={onPause}
                onShare={onShare}
            />
        </div>
    );
}

function Header() {
    return (
        <h1 className="text-3xl font-bold mb-4 text-center">
            🚀 Great science starts here
        </h1>
    );
}

function ChatContent({ chat, ...props }) {
    if (chat.isEmpty()) {
        return <EmptyChatView {...props} />;
    }
    return <ActiveChatView chat={chat} {...props} />;
}

function EmptyChatView({ 
    question, 
    setQuestion, 
    isLoggedIn, 
    onLogin, 
    onSend 
}) {
    return (
        <div className="empty-chat-container">
            <ChatInput
                question={question}
                setQuestion={setQuestion}
                isLoggedIn={isLoggedIn}
                onLogin={onLogin}
                onSend={onSend}
            />
            <div className="mt-8">
                <SuggestedStudies setQuestion={setQuestion} />
            </div>
        </div>
    );
}

function ActiveChatView({ 
    chat,
    question,
    setQuestion,
    isSending,
    isPaused,
    isComplete,
    onSend,
    onPause,
    onShare,
    isLoggedIn,
    onLogin
}) {
    const chatContainerRef = useRef(null);  // Add ref

    return (
        <div className="active-chat-container">
            <div ref={chatContainerRef}>
                <ChatHistory chat={chat} isSending={isSending} />
                {!isComplete && !isPaused && (
                    <PauseButton pause={onPause} />
                )}
            </div>
            
            {isComplete && (
                <ChatInput
                    question={question}
                    setQuestion={setQuestion}
                    isLoggedIn={isLoggedIn}
                    onLogin={onLogin}
                    onSend={onSend}
                    canShare={true}
                    onShare={onShare}  // Pass onShare to ChatInput
                />
            )}
        </div>
    );
}

window.ChatPanel = ChatPanel;
