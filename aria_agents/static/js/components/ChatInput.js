function ChatInput({ onLogin, question, setQuestion, handleSend, svc, placeholder, handleAttachment, attachmentNames, undoAttach }) {

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
            {attachmentNames.length > 0 && (
                <div className="mb-2 w-full">
                    <div className="flex flex-wrap gap-2">
                        {attachmentNames.map((fileName, index) => (
                            <div 
                                key={index} 
                                className="bg-gray-200 text-gray-700 px-3 py-1 rounded-md flex items-center cursor-pointer hover:scale-105 transition-transform duration-150 ease-in-out"
                                onClick={() => undoAttach(index)}
                            >
                                <span>{fileName}</span>
                                <button
                                    className="text-gray-500 ml-2"
                                    onClick={(e) => {
                                        e.stopPropagation();
                                        undoAttach(index);
                                    }}
                                >
                                    x
                                </button>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {svc ? (
                <>
                    <div
                        onDrop={handleDrop}
                        onDragOver={handleDragOver}
                        onDragEnter={handleDragEnter}
                        onDragLeave={handleDragLeave}
                        className="mb-2 p-4 border-2 border-dashed border-gray-300 rounded w-full text-center cursor-pointer hover:border-blue-500"
                        onClick={() => document.getElementById('fileUpload').click()}
                    >
                        <input
                            type="file"
                            onChange={handleAttachment}
                            className="hidden"
                            multiple
                            id="fileUpload"
                        />
                        <label htmlFor="fileUpload" className="cursor-pointer">
                            Drag & drop files here, or click to browse
                        </label>
                    </div>
                    <button
                        onClick={handleSend}
                        className="button w-full"
                    >
                        Send ✈️
                    </button>
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
    );
}

// Expose ChatInput globally
window.ChatInput = ChatInput;