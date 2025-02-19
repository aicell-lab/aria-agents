// App.js
/* global React */
const { useState, useEffect, useRef } = React;
const { marked } = window; // Ensure marked library is available for markdown rendering
const {
	Sidebar,
	ChatInput,
	SuggestedStudies,
	ChatHistory,
	ArtifactsPanel,
	ShareDialog,
	InfoDialog,
	PauseButton,
} = window;
const {
	getServer,
	getService,
	login,
	urlPlusParam,
	urlMinusParam,
	getUrlParam,
	generateSessionID,
	completeCodeBlocks,
	jsonToMarkdown,
	modifyLinksToOpenInNewTab,
} = window.helpers;
const {
	saveChat,
	deleteChat,
	createChatCollection,
	loadChats,
	readChat,
	getChatManifest,
} = window.chatHelpers;

function App() {
	const [question, setQuestion] = useState("");
	const [attachments, setAttachments] = useState([]);
	const [attachmentNames, setAttachmentNames] = useState([]);
	const [chatHistory, setChatHistory] = useState(new Map());
	const [svc, setSvc] = useState(null);
	const [sessionId, setSessionId] = useState(null);
	const [artifactManager, setArtifactManager] = useState(null);
	const [status, setStatus] = useState(
		"Please log in before sending a message."
	);
	const [isArtifactsPanelOpen, setIsArtifactsPanelOpen] = useState(false);
	const [isSidebarOpen, setIsSidebarOpen] = useState(false);
	const [artifacts, setArtifacts] = useState([]);
	const [currentArtifactIndex, setCurrentArtifactIndex] = useState(0);
	const [isLoading, setIsLoading] = useState(false);
	const [isSending, setIsSending] = useState(false);
	const [isChatComplete, setIsChatComplete] = useState(false);
	const [prevChats, setPrevChats] = useState([]);
	const [chatTitle, setChatTitle] = useState("");
	const [messageIsComplete, setMessageIsComplete] = useState(false);
	const chatContainerRef = useRef(null);
	const [isNearBottom, setIsNearBottom] = useState(true);
	const [showShareDialog, setShowShareDialog] = useState(false);
	const [alertContent, setAlertContent] = useState("");
	const [isPaused, setIsPaused] = useState(false);
	const [artifactWorkspace, setArtifactWorkspace] = useState("");
	const [userId, setUserId] = useState("");
	const [userToken, setUserToken] = useState("");
	const [viewedArtifacts, setViewedArtifacts] = useState(new Set());

	useEffect(async () => {
		// Automatically generate a session ID
		setSessionId(generateSessionID());
		if (localStorage.getItem("token")) {
			await handleLogin();
		}
		// Add scroll listener to window
		window.addEventListener('scroll', handleScroll);
		return () => window.removeEventListener('scroll', handleScroll);
	}, []);

	useEffect(() => {
		const newUrl = isPaused ? 
			urlPlusParam({ "isPaused": true }) :
			urlMinusParam("isPaused");
		window.history.replaceState({}, '', newUrl);
	}, [isPaused]);

	useEffect(() => {
		if (chatContainerRef.current && isNearBottom) {
			requestAnimationFrame(() => {
				window.scrollTo({
					top: document.documentElement.scrollHeight,
					behavior: 'smooth'
				});
			});
		}
	}, [chatHistory, isNearBottom]);

	useEffect(async () => {
		if (chatTitle !== "" && messageIsComplete) {
			await saveThisChat();
			setUrlParams(userId, sessionId);
			await updateChats();
		}
	}, [messageIsComplete, chatTitle]);

	useEffect(async () => {
		if (artifactManager) {
			await createChatCollection(artifactManager, artifactWorkspace);
			await updateChats();
			const sessionIdParam = getUrlParam("sessionId");
			const userIdParam = getUrlParam("userId");
			if (sessionIdParam && userIdParam) {
				try {
					const chat = await readChat(artifactManager, userIdParam, sessionIdParam);
					await displayChat(chat);
				}
				catch (e) {
					console.error(e);
					setAlertContent(
						`The chat ${sessionIdParam} doesn't exist or you lack\n`
						+ `the permissions to access it.`
					);
					await displayChat({});
					window.open("https://hypha.aicell.io/public/apps/hypha-login/", '_blank').focus();
				}
			}
		}
	}, [artifactManager]);

	const saveThisChat = async (permissions = null) => {
		const manifest = getChatManifest(sessionId, chatTitle, chatHistory, artifacts, attachments, userId);
		await saveChat(artifactManager, artifactWorkspace, sessionId, manifest, permissions);
	}

	const updateChats = async () => {
		const loadedChats = await loadChats(artifactManager, artifactWorkspace);
		setPrevChats(loadedChats);
	}

	const displayChat = async (chat) => {
		if (chat.id) {
			setUrlParams(chat.userId, chat.id);
			setSessionId(chat.id);
		}
		else {
			window.history.replaceState({}, '', urlMinusParam("sessionId"));
			setSessionId(generateSessionID());
		}
		const chatMap = new Map(Object.entries(chat.conversations || {})); // TODO: does this cause chat loading issue?
		setChatHistory(chatMap);
		setChatTitle(chat.name || "");
		setArtifacts(chat.artifacts || []);
		setAttachments(chat.attachments || []);
		setAttachmentNames([]);
		setMessageIsComplete(false);
		awaitUserResponse();
	}
	
	const handleScroll = () => {
		if (chatContainerRef.current) {
			const { scrollTop, scrollHeight, clientHeight } = document.documentElement;
			const buffer = 100; // Pixels from bottom to consider "at bottom"
			setIsNearBottom(scrollHeight - scrollTop - clientHeight <= buffer);
		}
	};

	const setServices = async (token) => {
		const server = await getServer(token);
		const configUserId = server.config.user.id;
		setUserId(configUserId);
		setArtifactWorkspace(`ws-user-${configUserId}`);

		const ariaAgentsService = await getService(
			server, "aria-agents/aria-agents", "public/aria-agents");
		const artifactManagerService = await getService(
			server, "public/artifact-manager");

		try {
			await ariaAgentsService.ping();
		} catch (error) {
			// Red dialog. Show logout button
			alert(
				`This account doesn't have permission to use the chatbot, please sign up and wait for approval`
			);
			console.error(error);
		}

		setSvc(ariaAgentsService);
		setArtifactManager(artifactManagerService);
	};

	const handleLogin = async () => {
		const token = await login();
		setUserToken(token);
		setIsLoading(true);
		await setServices(token);
		setStatus("Ready to chat! Type your message and press enter!");
		setIsLoading(false);
	};

	const handleAttachment = async (event) => {
		const files = event.target.files || event.dataTransfer.files;
		const newAttachments = [];
		const newAttachmentNames = [];

		for (const file of files) {
			const content = await file.text();
			newAttachments.push({ name: file.name, content });
			newAttachmentNames.push(file.name);
		}
		setAttachments([...attachments, ...newAttachments]);
		setAttachmentNames([...attachmentNames, ...newAttachmentNames]);
	};

	const statusCallback = async (message) => {
		const {
			session: { id, role_setting: roleSetting },
			status,
			content,
			arguments: args,
			name,
			query_id,
		} = message;

		const currentSessionId = getUrlParam("sessionId") ?? sessionId;
		const currentIsPaused = getUrlParam("isPaused") === "true";
		if (id !== currentSessionId || currentIsPaused) {
			throw new Error(`User has terminated this session.
				URL param session ID: ${getUrlParam('sessionId')} and
				saved sessionId: ${sessionId}.
				One of these should match message session ID: ${id}.
				isPaused: ${currentIsPaused}`);
		}

		const { name: roleName, icon: roleIcon } = roleSetting || {};

		const headerStartInProgress = marked(
			`### ⏳ Calling tool 🛠️ \`${name}\`...`
		);
		const headerFinished = marked(`### Tool 🛠️ \`${name}\``);

		if (status === "start") {
			setMessageIsComplete(false);
			// Initialize new message entry in chat history
			setChatHistory((prevHistory) => {
				const updatedHistory = new Map(prevHistory);
				updatedHistory.set(query_id, {
					role: roleName || "Agent",
					icon: roleIcon || "🤖",
					toolName: name,
					accumulatedArgs: "",
					title: headerStartInProgress,
					content: "",
					attachments: [],
					status: "in_progress",
				});
				return updatedHistory;
			});
		} else if (status === "in_progress") {
			// Update existing message entry with new content
			setChatHistory((prevHistory) => {
				const updatedHistory = new Map(prevHistory);
				const lastMessage = updatedHistory.get(query_id);
				if (lastMessage) {
					lastMessage.accumulatedArgs += (args || "").replace(
						/\n/g,
						""
					); // Accumulate arguments
					if (name === "SummaryWebsite") {
						lastMessage.title = "Generating summary website...";
					} else {
						lastMessage.title = headerStartInProgress;
						lastMessage.content = `<div>${lastMessage.accumulatedArgs}</div>`;
					}
					updatedHistory.set(query_id, lastMessage);
				}
				return updatedHistory;
			});
		} else if (status === "finished") {
			// Finalize the message entry
			setChatHistory((prevHistory) => {
				const updatedHistory = new Map(prevHistory);
				const lastMessage = updatedHistory.get(query_id);
				if (lastMessage) {
					if (name === "SummaryWebsite") {
						// Get the latest artifacts length using a functional update
						setArtifacts((prevArtifacts) => {
							const artifactIndex = prevArtifacts.length;

							lastMessage.content = `
                                <button 
                                    class="button" 
                                    onclick="openSummaryWebsite(${artifactIndex})"
                                >
                                    View Summary Website
                                </button>`;

							return prevArtifacts; // Return unchanged artifacts
						});
					} else {
						let finalContent =
							content || jsonToMarkdown(args) || "";
						finalContent = modifyLinksToOpenInNewTab(
							marked(completeCodeBlocks(finalContent))
						);
						lastMessage.title = headerFinished;
						lastMessage.content = finalContent;
					}
					lastMessage.status = "finished";
					updatedHistory.set(query_id, lastMessage);
				}
				return updatedHistory;
			});
			setMessageIsComplete(true);
		}
	};

	// Define the global function to open the summary website
	window.openSummaryWebsite = (index) => {
		if (index <= artifacts.length) {
			setIsArtifactsPanelOpen(true);
			setCurrentArtifactIndex(index);
		}
	};

	const artifactCallback = (artifact, url) => {
		setArtifacts((prevArtifacts) => [...prevArtifacts, { artifact, url }]);
	};

	const awaitUserResponse = () => {
		setIsChatComplete(true);
		setStatus("Ready to chat! Type your message and press enter!");
		setIsSending(false);
	}

	const titleCallback = async (message) => {
		if (message.status === "finished") {
			const newTitle = JSON.parse(message.arguments).response.trim();
			setChatTitle(newTitle);
		}
	}

	const undoAttach = (index) => {
		const attachmentName = attachments[index].name;
		const updatedAttachments = [...attachments];
		updatedAttachments.splice(index, 1);
		setAttachments(updatedAttachments);
		setStatus(`📎 Removed ${attachmentName}`);
	};

	const contentWithAttachments = (content, attachmentNames) => {
		const attachmentNamesString = attachmentNames.join(",\n");
		return `<MESSAGE_CONTENT>\n${content.toString()}\n</MESSAGE_CONTENT>\n\n<ATTACHMENT_NAMES>\n${attachmentNamesString}</ATTACHMENT_NAMES>`;
	}

	const handleSend = async () => {
		if (!svc) {
			await handleLogin();
			return;
		}

		if (question.trim()) {
			const currentQuestion = question;

			const newChatHistory = [
				...chatHistory.values(),
				{
					role: "user",
					title: "",
					content: marked(completeCodeBlocks(currentQuestion)),
					sources: "",
					image: "",
					attachments: attachmentNames,
				},
			];

			const newChatMap = new Map(
				newChatHistory.map((item, index) => [
					index.toString(),
					item,
				])
			);
			setIsChatComplete(false);
			setAttachmentNames([]);
			setChatHistory(newChatMap);
			setQuestion("");
			setStatus("🤔 Thinking...");
			setIsSending(true);
			setIsPaused(false);

			try {
				const currentChatHistory = Array.from(newChatMap.values()).map(
					(chat) => {
						let { role, content, attachments, ...rest } = chat;
						role =
							role.toString() === "user" ? "user" : "assistant";
						return {
							...rest,
							role: role.toString(),
							content: contentWithAttachments(content, attachments),
						};
					}
				);
				const extensions = [{ id: "aria" }];
				if (chatTitle === "") {
					const summaryQuestion = `Give a succinct title to this chat
					 session summarizing this prompt written by
					 the user: "${currentQuestion}". Respond ONLY with words,
					 maximum six words. DO NOT include the words
					 "Chat Session Title" or similar`
					await svc.chat(
						summaryQuestion,
						currentChatHistory,
						titleCallback,
						() => { },
						sessionId,
						userId,
						userToken,
						extensions,
					);
					await saveThisChat();
				}
				await svc.chat(
					currentQuestion,
					currentChatHistory,
					statusCallback,
					artifactCallback,
					sessionId,
					userId,
					userToken,
					extensions,
				);
			} catch (e) {
				console.log(e);
				setStatus(`❌ Error: ${e.message || e}`);
			} finally {
				awaitUserResponse();
			}
		}
	};

	const setUrlParams = (newUserId, newSessionId) => {
		const newUrl = urlPlusParam({
			"sessionId": newSessionId,
			"userId": newUserId,
		});
		window.history.replaceState({}, '', newUrl);
	}

	const hasUnseenArtifacts = () => {
		return artifacts.length > viewedArtifacts.size;
	};

	const handleArtifactsPanelOpen = () => {
		setIsArtifactsPanelOpen(true);
		setViewedArtifacts(new Set(artifacts.map((_, index) => index)));
	};

	return (
		<div className="min-h-screen flex flex-col">
			<button
				className={`${
					isSidebarOpen ? "open" : ""
				} md:hidden text-4xl p-2 fixed top-0 left-0 mt-4 ml-4`}
				onClick={() => setIsSidebarOpen(true)}
			>
				☰
			</button>
			<div className="flex-1 flex">
				<Sidebar
					isOpen={isSidebarOpen}
					onClose={() => setIsSidebarOpen(false)}
					prevChats={prevChats}
					onSelectChat={displayChat}
					onDeleteChat={async (chat) => {
						await deleteChat(artifactManager, artifactWorkspace, chat);
						await updateChats();
					}}
					isLoggedIn={svc != null}
					sessionId={sessionId}
				/>
				<div
					className={`main-panel ${
						isArtifactsPanelOpen
							? "main-panel-artifacts"
							: "main-panel-full"
					}`}
				>
					<div className="bg-white shadow-md rounded-lg p-6 w-full max-w-3xl">
						<h1 className="text-3xl font-bold mb-4 text-center">
							🚀 Great science starts here
						</h1>
						{chatHistory.size === 0 && (
							<ChatInput
								onLogin={handleLogin}
								question={question}
								setQuestion={setQuestion}
								handleSend={handleSend}
								svc={svc}
								handleAttachment={handleAttachment}
								attachmentNames={attachmentNames}
								undoAttach={undoAttach}
								placeholder="Type what you want to study"
							/>
						)}
						<div
							className="text-center text-gray-700 mb-4 markdown-body"
							dangerouslySetInnerHTML={{ __html: status }}
						></div>
						{chatHistory.size === 0 ? (
							<SuggestedStudies setQuestion={setQuestion} />
						) : (
							<div ref={chatContainerRef}>
								<ChatHistory chatHistory={chatHistory} isSending={isSending} />
								{!isChatComplete && chatHistory.size > 0 && (
									<PauseButton pause={() => {
											setIsPaused(true);
											setStatus("Chat stopped.");
											awaitUserResponse();
										}}
									/>	
								)}
							</div>
						)}
						{isChatComplete && chatHistory.size > 0 && (
							<ChatInput
								onLogin={handleLogin}
								question={question}
								setQuestion={setQuestion}
								handleSend={handleSend}
								svc={svc}
								handleAttachment={handleAttachment}
								attachmentNames={attachmentNames}
								undoAttach={undoAttach}
								shareChat={() => { setShowShareDialog(true) } }
								placeholder="Type what you want to study"
							/>
						)}
					</div>
				</div>
			</div>
			{isArtifactsPanelOpen ? (
				<ArtifactsPanel
					onClose={() => setIsArtifactsPanelOpen(false)}
					artifacts={artifacts}
					currentArtifactIndex={currentArtifactIndex}
					onPrev={() => {
						if (currentArtifactIndex > 0) {
							setCurrentArtifactIndex(currentArtifactIndex - 1);
						}
					}}
					onNext={() => {
						if (currentArtifactIndex < artifacts.length - 1) {
							setCurrentArtifactIndex(currentArtifactIndex + 1);
						}
					}}
				/>
			) : (
				<div className="relative">
					<button
						onClick={handleArtifactsPanelOpen}
						className="button fixed top-0 right-0 mt-4 mr-4"
					>
						Artifacts
						{hasUnseenArtifacts() && (
							<span className="absolute -top-1 -right-1 h-3 w-3 bg-red-500 rounded-full"></span>
						)}
					</button>
				</div>
			)}
			{isLoading && (
				<div
					className={`spinner-container ${
						isArtifactsPanelOpen ? "margin-right-artifacts" : ""
					}`}
				>
					<div className="spinner"></div>
				</div>
			)}
			{showShareDialog && (
				<ShareDialog shareUrl={window.location} onConfirm={() => saveThisChat({"*": "r"}) } onClose={() => setShowShareDialog(false) }></ShareDialog>
			)}
			{alertContent && (
				<InfoDialog onClose={() => setAlertContent("")} content={alertContent}>
				</InfoDialog>
			)}
		</div>
	);
}

// Expose App globally
window.App = App;
