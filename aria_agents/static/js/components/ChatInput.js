function ChatInput({ onLogin, question, setQuestion, handleSend, svc }) {
    return (
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
                    onClick={onLogin}
                    className="w-full mt-4 bg-blue-600 text-white py-2 px-4 rounded transition duration-300 ease-in-out transform hover:scale-105"
                    title="Please login to send"
                >
                    Login 🚀
                </button>
            )}
        </div>
    )
};

// Expose ChatInput globally
window.ChatInput = ChatInput;