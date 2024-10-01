function ChatInput({ onLogin, question, setQuestion, handleSend, svc, placeholder, handleAttachment }) {

    return (
        <div className="mb-4 flex flex-col items-center">
            <input
                type="text"
                placeholder={placeholder}
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                className="w-full p-3 border border-gray-300 rounded mb-2 text-lg"
                onKeyPress={(e) => e.key === 'Enter' && handleSend()}
            />
            {svc ? (
                <>
                    <button
                        onClick={handleSend}
                        className="button w-full"
                    >
                        Send ✈️
                    </button>
                    <input
                        type="file"
                        accept=".csv, .xls, .xlsx"
                        onChange={handleAttachment}
                        className="mt-2"
                    />
                </>
            ) : (
                <button
                    onClick={onLogin}
                    className="button w-full mt-4"
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