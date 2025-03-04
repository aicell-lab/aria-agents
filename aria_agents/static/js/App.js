// App.js
/* global React */
const { useState, useEffect, useRef } = React;
const { marked } = window; // Ensure marked library is available for markdown rendering
const {
	generateSessionID,
	getService,
	login,
	completeCodeBlocks,
	jsonToMarkdown,
	modifyLinksToOpenInNewTab,
	getServer,
	getUrlParam,
	urlMinusParam,
	urlPlusParam,
} = window.helpers;
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

function App() {
	const [question, setQuestion] = useState("");
	const [attachments, setAttachments] = useState([]);
	const [attachmentNames, setAttachmentNames] = useState([]);
	const [chatHistory, setChatHistory] = useState(new Map());
	const [svc, setSvc] = useState(null);
	const [sessionId, setSessionId] = useState(null);
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
	const [ariaArtifacts] = useState(new AriaArtifacts());

	useEffect(async () => {
		// Automatically generate a session ID
		setSessionId(generateSessionID());
		if (localStorage.getItem("token")) {
			await handleLogin();
		}
	}, []);

	useEffect(() => {
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
	
	const handleScroll = () => {
		if (chatContainerRef.current) {
			const { scrollTop, scrollHeight, clientHeight } = document.documentElement;
			const buffer = 100; // Pixels from bottom to consider "at bottom"
			setIsNearBottom(scrollHeight - scrollTop - clientHeight <= buffer);
		}
	};
	
	useEffect(async () => {
		if (ariaArtifacts.artifactManager) {
			await ariaArtifacts.createChatCollection();
			await loadChats();
			const sessionIdParam = getUrlParam("sessionId");
			const userIdParam = getUrlParam("userId");
			if (sessionIdParam && userIdParam) {
				try {
					const chat = await ariaArtifacts.readChat(userIdParam, sessionIdParam);
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
	}, [ariaArtifacts.artifactManager]);

	useEffect(async () => {
		if (chatTitle !== "" && messageIsComplete) {
			await ariaArtifacts.saveChat(sessionId, chatTitle, Array.from(chatHistory.values()), artifacts, attachments);
			setUrlParams(userId, sessionId);
			await loadChats();
		}
	}, [messageIsComplete, chatTitle]);

	const loadChats = async() => {
		try {
			const namedChats = await ariaArtifacts.loadChats();
			setPrevChats(namedChats);
		}
		catch (e) {
			console.log("Chats couldn't be loaded. Error: ", e);
		}
	}
	
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

	const setServices = async (token) => {
		await ariaArtifacts.setServices(token);
		const server = await getServer(token);
		const configUserId = server.config.user.id;
		setUserId(configUserId);
		setArtifactWorkspace(`ws-user-${configUserId}`);

		const ariaAgentsService = await getService(
			server, "aria-agents/aria-agents", "public/aria-agents");

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
	};

	const deleteChat = async (chat) => {
		await ariaArtifacts.deleteChat(chat);
		await loadChats();
	}

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
						setArtifacts((prevArtifacts) => {
							const artifactIndex = prevArtifacts.length;
							lastMessage.content = `
                                <button 
                                    class="button" 
                                    onclick="openSummaryWebsite(${artifactIndex})"
                                >
                                    View Summary Website
                                </button>`;
							return prevArtifacts;
						});
					} else {
						let finalContent = content || "";
						if (args) {
							try {
								const parsedArgs = JSON.parse(args);
								if (parsedArgs.status && parsedArgs.status.type === "error") {
									finalContent = `❌ Error: ${parsedArgs.response}`;
								} else {
									finalContent = parsedArgs.response;
									if (parsedArgs.status) {
										finalContent = `✅ ${parsedArgs.status.message}\n\n${finalContent}`;
									}
								}
							} catch {
								finalContent = args;
							}
						}
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

	async function handleCorpusEvents(eventType, args) {
		switch (eventType) {
			case 'list_corpus':
				const files = await ariaArtifacts.loadFiles();
				return {
					files: files.map(f => f.name),
					status: `Found ${files.length} files in corpus`
				};
			case 'get_corpus':
				const { file_paths } = args;
				const contents = [];
				const failed = [];
				
				for (const path of file_paths) {
					try {
						const content = await ariaArtifacts.getFile(path);
						contents.push({ name: path, content });
					} catch (e) {
						failed.push(path);
					}
				}
				
				return {
					contents,
					failed,
					status: `Retrieved ${contents.length} files successfully${failed.length ? `, failed to retrieve ${failed.length} files` : ''}`
				};
			default:
				console.warn(`Unknown corpus event: ${eventType}`);
				return null;
		}
	}

	const artifactCallback = async (toolResponse) => {
		// Parse the tool response
		const response = JSON.parse(toolResponse);
		
		// Handle corpus events if present
		if (response._corpus_event) {
			return await handleCorpusEvents(response._corpus_event, response._corpus_args);
		}
		
		// Handle files that need to be saved
		if (response.to_save && response.to_save.length > 0) {
			for (const file of response.to_save) {
				const { name, content, model } = file;
				// Save to artifact manager
				await ariaArtifacts.saveFile(name, content, model);
			}
		}

		// Handle status
		let statusPrefix = "";
		if (response.status) {
			const { code, message, type } = response.status;
			statusPrefix = `${type === "error" ? "❌" : "✅"} ${message}\n\n`;
		}
		
		// Handle response
		if (response.response) {
			if (typeof response.response === 'object') {
				// If it's a BaseModel response, convert to markdown
				return statusPrefix + jsonToMarkdown(response.response);
			}
			return statusPrefix + response.response;
		}
		
		return statusPrefix || "";
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

	const contentWithAttachments = (content, attachmentNames) => {
		const attachmentNamesString = attachmentNames.join(",\n");
		return `<MESSAGE_CONTENT>\n${content.toString()}\n</MESSAGE_CONTENT>\n\n<ATTACHMENT_NAMES>\n${attachmentNamesString}</ATTACHMENT_NAMES>`;
	}

    const handleCommand = async (message) => {
        if (message.startsWith('/load_files')) {
            const files = message.substring(11).trim().split(',').map(f => f.trim());
            let fileContents = [];
            for (const file of files) {
                try {
                    const content = await ariaArtifacts.getFile(file);
                    fileContents.push(`File: ${file}\n\n${content}`);
                } catch (e) {
                    fileContents.push(`Error loading ${file}: ${e.message}`);
                }
            }
            return fileContents.join('\n\n---\n\n');
        }
        return null;
    };

	const handleSend = async () => {
		if (!svc) {
			await handleLogin();
			return;
		}

		if (question.trim()) {
			// First check if this is a command
			const commandResponse = await handleCommand(question.trim());
			if (commandResponse) {
				const newChatHistory = [
					...chatHistory.values(),
					{
						role: "user",
						title: "",
						content: marked(completeCodeBlocks(question)),
						sources: "",
						image: "",
						attachments: [],
					},
					{
						role: "assistant",
						title: "",
						content: marked(completeCodeBlocks(commandResponse)),
						sources: "",
						image: "",
						attachments: [],
					}
				];
				const newChatMap = new Map(
					newChatHistory.map((item, index) => [
						index.toString(),
						item,
					])
				);
				setChatHistory(newChatMap);
				setQuestion("");
				return;
			}

			// Not a command, proceed with normal chat
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
					await ariaArtifacts.saveChat(sessionId, chatTitle, Array.from(chatHistory.values()), artifacts, attachments);
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

	const undoAttach = (index) => {
		const attachmentName = attachments[index].name;
		const updatedAttachments = [...attachments];
		updatedAttachments.splice(index, 1);
		setAttachments(updatedAttachments);
		setStatus(`📎 Removed ${attachmentName}`);
	};

	const setUrlParams = (newUserId, newSessionId) => {
		const newUrl = urlPlusParam({
			"sessionId": newSessionId,
			"userId": newUserId,
		});
		window.history.replaceState({}, '', newUrl);
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
					onDeleteChat={deleteChat}
					isLoggedIn={svc != null}
					sessionId={sessionId}
				/>
				<div
					className={`main-panel ${
						isArtifactsPanelOpen
							? "main-panel-artifacts"
							: "main-panel-full"
					}`}
					onDrop={handleDrop}
					onDragOver={handleDragOver}
					onDragEnter={handleDragEnter}
					onDragLeave={handleDragLeave}
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
				<ShareDialog shareUrl={window.location} onConfirm={() => ariaArtifacts.saveChat(sessionId, chatTitle, Array.from(chatHistory.values()), artifacts, attachments, {"*": "r"}) } onClose={() => setShowShareDialog(false) }></ShareDialog>
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
