function ChatHistory({ chatHistory, isSending }) {
	const { marked } = window;
	const { completeCodeBlocks } = window.helpers;

	const isEmoji = (icon) => /^[\p{Emoji}]+$/u.test(icon);

	const chatArray = Array.from(chatHistory.values());
	const [expandedMessages, setExpandedMessages] = React.useState(
		chatArray.map(() => false)
	);

	const toggleContent = (index) => {
		setExpandedMessages((prevState) => {
			const newState = [...prevState];
			newState[index] = !newState[index];
			return newState;
		});
	};

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
			<div className="bg-gray-100 p-3 rounded mb-2">
				{chat.role !== "user" && (
					<>
						<div
							className="bg-gray-100 markdown-body"
							dangerouslySetInnerHTML={{ __html: chat.title }}
						></div>
						{chat.role !== "Aria" && (
							<div
								className="collapsible"
								onClick={() => toggleContent(index)}
								style={{
									cursor: "pointer",
									display: "flex",
									alignItems: "center",
								}}
							>
								<span
									className="arrow"
									style={{
										marginRight: "10px",
										transition: "transform 0.3s ease",
										transform: expandedMessages[index]
											? "rotate(90deg)"
											: "rotate(0deg)",
									}}
								>
									▶
								</span>
								<span>
									{expandedMessages[index]
										? "Hide details"
										: "Show more details"}
								</span>
							</div>
						)}
					</>
				)}
				{(expandedMessages[index] ||
					chat.role === "user" ||
					chat.role === "Aria") && (
					<div
						className="bg-gray-100 markdown-body"
						dangerouslySetInnerHTML={{ __html: chat.content }}
					></div>
				)}
				{chat.role === "user" &&
					chat.attachments &&
					chat.attachments.length > 0 && (
						<div className="mt-2 flex flex-wrap gap-2">
							{chat.attachments.map((fileName, fileIndex) => (
								<div
									key={fileIndex}
									className="bg-gray-200 text-gray-700 px-3 py-1 rounded-md"
								>
									<span>{fileName}</span>
								</div>
							))}
						</div>
					)}
			</div>
			{isSending && chat.status === "in_progress" && (
				<div className="absolute inset-0 flex items-center justify-center">
					<div className="spinner"></div>
				</div>
			)}
		</div>
	);

	return (
		<div className="mt-4">
			<div style={{ paddingLeft: "20px", marginTop: "10px" }}>
				{chatArray.map((chat, index) => renderChatMessage(chat, index))}
			</div>
		</div>
	);
}

// Expose ChatHistory globally
window.ChatHistory = ChatHistory;
