/* global useState */
function ChatInput({ 
    question, 
    setQuestion, 
    onSend, 
    onLogin, 
    isLoggedIn, 
    canShare = false,
    onShare
}) {
    const [attachments, setAttachments] = useState([]);

    const handleAttachment = async (event) => {
        const files = event.target.files || event.dataTransfer.files;
        const newAttachments = await Promise.all(
            Array.from(files).map(async file => ({
                name: file.name,
                content: await file.text()
            }))
        );
        setAttachments([...attachments, ...newAttachments]);
    };

    const removeAttachment = (index) => {
        setAttachments(prev => prev.filter((_, i) => i !== index));
    };

    return (
        <div className="chat-input-container">
            <TextArea 
                value={question}
                onChange={setQuestion}
                placeholder="Type what you want to study"
            />
            {isLoggedIn && (
                <AttachmentSection
                    attachments={attachments}
                    onAttach={handleAttachment}
                    onRemove={removeAttachment}
                />
            )}
            {canShare && <ShareButton onClick={onShare} />}
            <ActionButton
                isLoggedIn={isLoggedIn}
                onLogin={onLogin}
                onSend={onSend}
            />
        </div>
    );
}

// Subcomponents
function TextArea({ value, onChange, placeholder }) {
    return (
        <textarea
            value={value}
            onChange={(e) => onChange(e.target.value)}
            onInput={(e) => {
                e.target.style.height = 'auto';
                e.target.style.height = `${e.target.scrollHeight}px`;
            }}
            className="flex-grow p-3 border border-gray-300 rounded mb-2 text-lg overflow-hidden resize-none w-full"
            placeholder={placeholder}
            rows="1"
        />
    );
}

function ShareButton({ onClick }) {
    return (
        <button 
            onClick={onClick} 
            className="p-3 border border-gray-300 mb-2 rounded text-lg"
        >
            Share
        </button>
    );
}

function AttachmentSection({ attachments, onAttach, onRemove }) {
    const handleDrop = (e) => {
        e.preventDefault();
        if (e.dataTransfer.files.length > 0) {
            onAttach(e);
        }
    };

    return (
        <div 
            onDrop={handleDrop}
            onDragOver={(e) => e.preventDefault()}
            className="mb-4"
        >
            {attachments.length > 0 ? (
                <div className="mb-2 w-full">
                    <div className="flex flex-wrap gap-2">
                        {attachments.map((file, index) => (
                            <AttachmentTag
                                key={index}
                                fileName={file.name}
                                onRemove={() => onRemove(index)}
                            />
                        ))}
                        <AddFileButton onAttach={onAttach} />
                    </div>
                </div>
            ) : (
                <DropZone onAttach={onAttach} />
            )}
        </div>
    );
}

function AttachmentTag({ fileName, onRemove }) {
    return (
        <div className="bg-gray-200 text-gray-700 px-3 py-1 rounded-md flex items-center hover:bg-gray-300">
            <span>{fileName}</span>
            <button
                className="ml-2 text-gray-500 hover:text-gray-700"
                onClick={onRemove}
            >
                ×
            </button>
        </div>
    );
}

function AddFileButton({ onAttach }) {
    return (
        <div className="flex items-center border-2 border-dashed border-gray-300 rounded px-2 hover:border-blue-500 cursor-pointer">
            <input
                type="file"
                onChange={onAttach}
                className="hidden"
                multiple
                id="addFile"
            />
            <label htmlFor="addFile" className="cursor-pointer">
                +
            </label>
        </div>
    );
}

function DropZone({ onAttach }) {
    return (
        <div
            className="p-4 border-2 border-dashed border-gray-300 rounded w-full text-center cursor-pointer hover:border-blue-500"
            onClick={() => document.getElementById("fileUpload").click()}
        >
            <input
                type="file"
                onChange={onAttach}
                className="hidden"
                multiple
                id="fileUpload"
            />
            <label htmlFor="fileUpload" className="cursor-pointer">
                Drag & drop tabular files (e.g. .csv, .xls, .txt), or click to browse
            </label>
        </div>
    );
}

function ActionButton({ isLoggedIn, onLogin, onSend }) {
    if (!isLoggedIn) {
        return (
            <button
                onClick={onLogin}
                className="button w-full"
                title="Please login to send"
            >
                Login 🚀
            </button>
        );
    }

    return (
        <button 
            onClick={onSend} 
            className="button w-full"
        >
            Send ✈️
        </button>
    );
}

window.ChatInput = ChatInput;
