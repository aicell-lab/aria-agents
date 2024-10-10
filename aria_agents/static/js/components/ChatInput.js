function ChatInput({ onLogin, question, setQuestion, handleSend, svc, placeholder, handleAttachment }) {

    // Function to handle drag-and-drop file selection
    const handleDrop = (e) => {
        e.preventDefault();
        e.stopPropagation();
        if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
            handleAttachment(e);
            e.dataTransfer.clearData();
        }
    };

    const handleDragOver = (e) => {
        e.preventDefault();
        e.stopPropagation();
    };

    const handleDragEnter = (e) => {
        e.preventDefault();
        e.stopPropagation();
    };

    const handleDragLeave = (e) => {
        e.preventDefault();
        e.stopPropagation();
    };

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
                    <div
                        onDrop={handleDrop}
                        onDragOver={handleDragOver}
                        onDragEnter={handleDragEnter}
                        onDragLeave={handleDragLeave}
                        className="mt-2 p-4 border-2 border-dashed border-gray-300 rounded w-full text-center cursor-pointer hover:border-blue-500"
                    >
                        <input
                            type="file"
                            onChange={handleAttachment}
                            className="hidden"
                            multiple
                            id="fileUpload"
                        />
                        <label htmlFor="fileUpload" className="cursor-pointer">
                            Drag & drop files here, or <span className="text-blue-500 underline">click to browse</span>
                        </label>
                    </div>
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