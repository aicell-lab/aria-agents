// App.js
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
} = window.helpers;
const {
	Sidebar,
	ProfileDialog,
	ChatInput,
	SuggestedStudies,
	ChatHistory,
	ArtifactsPanel,
} = window;

function App() {
	const [question, setQuestion] = useState("");
	const [attachmentStatePrompts, setAttachmentStatePrompts] = useState([]);
	const [attachmentNames, setAttachmentNames] = useState([]);
	const [chatHistory, setChatHistory] = useState(new Map());
	const [svc, setSvc] = useState(null);
	const [sessionId, setSessionId] = useState(null);
	const [artifactManager, setArtifactManager] = useState(null);
	const [status, setStatus] = useState(
		"Please log in before sending a message."
	);
	const [showProfileDialog, setShowProfileDialog] = useState(false);
	const [userProfile, setUserProfile] = useState({
		name: "",
		occupation: "",
		background: "",
	});
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

	useEffect(() => {
		// Automatically generate a session ID
		setSessionId(generateSessionID());
	}, []);

	useEffect(() => {
		// Add scroll listener to window
		window.addEventListener('scroll', handleScroll);
		return () => window.removeEventListener('scroll', handleScroll);
	}, []);

	
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
		if (artifactManager) {
			await createChatCollection();
			await loadChats();
		}
	}, [artifactManager]);

	useEffect(async () => {
		if (chatTitle !== "" && messageIsComplete) {
			await saveChat();
			await loadChats();
		}
	}, [messageIsComplete, chatTitle]);

	const loadChats = async() => {
		try {
			const prevChatObjects = await artifactManager.list({
				prefix: "aria-agents-chats",
				summary_fields: ["*"],
				_rkwargs: true,
			});
			const invalidChats = prevChatObjects.filter((chat) => chat.name === "");
			invalidChats.forEach(deleteChat);
			const validChats =  prevChatObjects.filter((chat) => chat.name !== "");
			setPrevChats(validChats);
		}
		catch {
			console.log("No previous chats.");
		}
	}
	
	const createChatCollection = async () => {
		const galleryManifest = {
			"name": "Aria Agents Chat History",
			"description": "A collection used to store previous chat sessions with the Aria Agents chatbot",
			"type": "collection",
			"collection": [],
		};
	
		try {
			await artifactManager.create({
				prefix: "aria-agents-chats",
				manifest: galleryManifest,
				orphan: true,
				_rkwargs: true
			});
		}
		catch {
			console.log("User chat collection already exists.");
		}
	};

	const saveChat = async () => {
		const datasetManifest = {
			"id": `${sessionId}`,
			"name": `${chatTitle}`,
			"description": `The Aria Agents chat history of ${sessionId}`,
			"type": "chat",
			"conversations": chatHistory,
			"artifacts": artifacts,
			"attachmentPrompts": attachmentStatePrompts,
			"timestamp": new Date().toISOString(),
		};

		try {
			await artifactManager.create({
				prefix: `aria-agents-chats/${sessionId}`,
				manifest: datasetManifest,
				_rkwargs: true
			});
		} catch {
			await artifactManager.edit({
				prefix: `aria-agents-chats/${sessionId}`,
				manifest: datasetManifest,
				_rkwargs: true
			})
			await artifactManager.commit(`aria-agents-chats/${sessionId}`);
		}
	};

	const deleteChat = async (chat) => {
		try {
			await artifactManager.delete({
				prefix: `aria-agents-chats/${chat.id}`,
				delete_files: true,
				recursive: true,
				_rkwargs: true
			});
			await loadChats();
		}
		catch {
			console.log(`Chat ${chat.id} is already deleted.`);
		}
	}

	const setServices = async (token) => {
		const server = await getServer(token);
		const artifactServer = await getServer(token, "https://hypha.aicell.io");

		const ariaAgentsService = await getService(
			server, "aria-agents/aria-agents", "public/aria-agents");
		const artifactManagerService = await getService(
			artifactServer, "public/artifact-manager");

		try {
			await ariaAgentsService.ping();
		} catch (error) {
			alert(
				`You don't have permission to use the chatbot, please sign up and wait for approval`
			);
			console.error(error);
		}

		setSvc(ariaAgentsService);
		setArtifactManager(artifactManagerService);
	};

	const handleLogin = async () => {
		const token = await login();
		setIsLoading(true);
		await setServices(token);
		setStatus("Ready to chat! Type your message and press enter!");
		setIsLoading(false);
	};

	const handleAttachment = async (event) => {
		const files = event.target.files || event.dataTransfer.files;

		const newAttachmentPrompts = [];
		const newAttachmentNames = [];

		for (const file of files) {
			try {
				await saveFile(file);
			} catch (error) {
				alert(error);
				continue;
			}
			newAttachmentPrompts.push(
				`- **${file.name}**, available at: aria-agents-chats/${sessionId}`
			);
			newAttachmentNames.push(file.name);
		}

		setAttachmentStatePrompts([
			...attachmentStatePrompts,
			...newAttachmentPrompts,
		]);
		setAttachmentNames([...attachmentNames, ...newAttachmentNames]);
	};

	const saveFile = async (file) => {
		await saveChat()
		const putUrl = await artifactManager.putFile({
			prefix: `aria-agents-chats/${sessionId}`,
			file_path: file.name, // TODO: handle files with same name
			_rkwargs: true
		});

		const response = await fetch(putUrl, {
			method: "PUT",
			body: file
		})

		if (!response.ok) {
			throw new Error(`Upload of ${file.name} failed`);
		}
	};

	const statusCallback = async (message) => {
		const {
			type,
			session: { id, role_setting: roleSetting },
			status,
			content,
			arguments: args,
			name,
			query_id,
		} = message;
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

	const getAttachmentStatePrompt = () => {
		if (attachmentStatePrompts.length > 0) {
			return "User attached the following files to the current query:\n" +
				attachmentStatePrompts.join("\n");
		}
		else {
			return "User did not attach any files."
		}
	}

	const titleCallback = async (message) => {
		if (message.status === "finished") {
			const newTitle = JSON.parse(message.arguments).response.trim();
			setChatTitle(newTitle);
		}
	}

	const handleSend = async () => {
		if (!svc) {
			await handleLogin();
			return;
		}

		if (question.trim()) {
			const currentQuestion = question;
			const joinedStatePrompt =
				getAttachmentStatePrompt();

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

			try {
				const currentChatHistory = Array.from(chatHistory.values()).map(
					(chat) => {
						let { role, content, attachments, ...rest } = chat;
						role =
							role.toString() === "user" ? "user" : "assistant";
						return {
							...rest,
							role: role.toString(),
							content: content.toString(),
						};
					}
				);
				const extensions = [{ id: "aria" }];
				await svc.chat(
					currentQuestion,
					currentChatHistory,
					userProfile,
					statusCallback,
					artifactCallback,
					sessionId,
					extensions,
					joinedStatePrompt
				);
				if (chatTitle === "") {
					const summaryQuestion = `Give a succinct title to this chat
					 session summarizing this prompt written by
					 the user: "${currentQuestion}". Respond ONLY with words,
					 maximum six words. DO NOT include the words
					 "Chat Session Title" or similar`
					await svc.chat(
						summaryQuestion,
						currentChatHistory,
						userProfile,
						titleCallback,
						() => {},
						sessionId,
						extensions,
						joinedStatePrompt
					);
				}
			} catch (e) {
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
		const attachmentName = attachmentNames[index];
		const updatedAttachments = [...attachmentStatePrompts];
		const updatedAttachmentNames = [...attachmentNames];

		updatedAttachments.splice(index, 1);
		updatedAttachmentNames.splice(index, 1);

		setAttachmentStatePrompts(updatedAttachments);
		setAttachmentNames(updatedAttachmentNames);
		setStatus(`📎 Removed ${attachmentName}`);
	};

	const displayChat = async (chat) => {
		const chatMap = new Map(Object.entries(chat.conversations || {}));
		setChatHistory(chatMap);
		setChatTitle(chat.name || "");
		setArtifacts(chat.artifacts || []);
		setSessionId(chat.id || generateSessionID());
		setAttachmentStatePrompts(chat.attachmentPrompts || []);
		setMessageIsComplete(false);
		awaitUserResponse();
	}

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
								placeholder="Type what you want to study"
							/>
						)}
					</div>
				</div>
			</div>
			{showProfileDialog && (
				<ProfileDialog
					userProfile={userProfile}
					onClose={() => setShowProfileDialog(false)}
					onSave={(profile) => {
						setUserProfile(profile);
						setShowProfileDialog(false);
					}}
				/>
			)}
			{isArtifactsPanelOpen ? (
				<ArtifactsPanel
					onClose={() =>
						setIsArtifactsPanelOpen(!isArtifactsPanelOpen)
					}
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
				<button
					onClick={() =>
						setIsArtifactsPanelOpen(!isArtifactsPanelOpen)
					}
					className="button fixed top-0 right-0 mt-4 mr-4"
				>
					Artifacts
				</button>
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
		</div>
	);
}

// Expose App globally
window.App = App;
