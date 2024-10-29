const { useState, useEffect } = React;
const { marked } = window; // Ensure marked library is available for markdown rendering
const {
	generateSessionID,
	getService,
	login,
	completeCodeBlocks,
	jsonToMarkdown,
	modifyLinksToOpenInNewTab,
	getServiceId,
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
	const [dataStore, setDataStore] = useState(null);
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
	const [prevChatObjects, setPrevChatObjects] = useState([]);

	useEffect(() => {
		// Automatically generate a session ID
		setSessionId(generateSessionID());
	}, []);

	const listArtifactFiles = async (userId, filename) => {
		const files = await artifactManager.putFile({
			prefix: `collections/aria-agents-chats/${userId}-chats`,
			path: filename,
		});
	
		return files;
	};

	const loadPrevChatObjects = async () => {
		try {
			const chatObjects = await listArtifactFiles();
			const sortedChatObjects = chatObjects
				.map((chatObject, index) => ({
					...chatObject,
					id: index.toString(),
				}))
				.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
			return sortedChatObjects;
		} catch (error) {
			console.error('Error loading past chats:', error);
			return [];
		}
	};

	const setServices = async (token) => {
		try {
			const dataStoreService = await getService(
				token, getServiceId() || "aria-agents/*:aria-agents", true);
			const ariaAgentsService = await getService(
				token, "aria-agents/*:data-store", false);
			const artifactManagerService = await getService(
				token, "public/artifact-manager", false);
			setDataStore(dataStoreService);
			setSvc(ariaAgentsService);
			setArtifactManager(artifactManagerService);
		} catch (error) {
			alert(
				`You don't have permission to use the chatbot, please sign up and wait for approval`
			);
			console.error(error);
		}
	};
	
	const createArtifactDataset = async (userId) => {
		const datasetManifest = {
			"id": `${userId}-chats`,
			"name": `${userId} Chat History`,
			"description": `The Aria Agents chat history of ${userId}`,
			"type": "dataset"
		};
	
		await artifactManager.create({
			prefix: `collections/aria-agents-chats/${userId}-chats`,
			manifest: datasetManifest,
			permissions: { [userId]: "rw+" }
		});
	}

	const putArtifactFile = async (userId, fileContent, filename) => {
		const putUrl = await artifactManager.putFile({
			prefix: `collections/aria-agents-chats/${userId}-chats`,
			filePath: filename,
		});
	
		const response = await fetch(putUrl, {
			method: 'PUT',
			body: fileContent
		});
	
		if (!response.ok) {
			throw new Error("File upload failed");
		}
	
		await artifactManager.commit(`collections/aria-agents-chats/${userId}-chats`);
	};
	
	const getArtifactFile = async (userId, filename) => {
		const getUrl = await artifactManager.putFile({
			prefix: `collections/aria-agents-chats/${userId}-chats`,
			path: filename,
		});
	
		const response = await fetch(getUrl);
	
		if (!response.ok) {
			throw new Error("File download failed");
		}
	
		await artifactManager.commit(`collections/aria-agents-chats/${userId}-chats`);
	
		return response;
	};

	const handleLogin = async () => {
		const token = await login();
		setIsLoading(true);
		await createArtifactDataset(token); // TODO: or use existing
		prevChatObjects = await loadPrevChatObjects();
		setPrevChatObjects(prevChatObjects);
		await setServices(token);
		setStatus("Ready to chat! Type your message and press enter!");
		setIsLoading(false);
		setPrevChatObjects(prevChatObjects);
	};

	const handleAttachment = async (event) => {
		const files = event.target.files || event.dataTransfer.files;

		const newAttachmentPrompts = [];
		const newAttachmentNames = [];
		let attachmentCount = attachmentStatePrompts.length;

		for (const file of files) {
			try {
				const fileId = await uploadAttachment(file);
				const fileUrl = await dataStore.get_url(fileId);
				newAttachmentPrompts.push(
					`- **${file.name}**, available at: [${fileUrl}](${fileUrl})`
				);
				newAttachmentNames.push(file.name);
				attachmentCount++;
			} catch (error) {
				console.error(`Error uploading ${file.name}:`, error);
			}
		}

		setAttachmentStatePrompts([
			...attachmentStatePrompts,
			...newAttachmentPrompts,
		]);
		setAttachmentNames([...attachmentNames, ...newAttachmentNames]);
	};

	const uploadAttachment = async (file) => {
		const fileBytes = await file.arrayBuffer();
		const byteArray = new Uint8Array(fileBytes);

		const fileId = await dataStore.put("file", byteArray, file.name);

		addItemToLocalStorageArr("attachments", {
			value: file.name,
			id: fileId,
		});

		return fileId;
	};

	const addItemToLocalStorageArr = (arrName, item) => {
		const arr = JSON.parse(localStorage.getItem(arrName)) || [];
		arr.push(item);
		localStorage.setItem(arrName, JSON.stringify(arr));
	};

	const testUploadAttachment = async () => {
		const fileContents = "Hello, World!";
		const file = new File([fileContents], "test.txt", {
			type: "text/plain",
		});
		const fileId = await uploadAttachment(file);

		const returned_object = await dataStore.get({
			query_string: "id=" + fileId,
		});
		const returnedBytes = returned_object.body;
		const returnedFileContents = new Blob([returnedBytes], {
			type: "text/plain",
		});
		const returnedText = await returnedFileContents.text();

		console.assert(
			returnedText === fileContents,
			"File contents do not match"
		);
	};

	const statusCallback = (message) => {
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

	const getAttachmentStatePrompt = (attachmentStatePrompts) => {
		if (attachmentStatePrompts.size > 0) {
			return "User attached the following files to the current query:\n" +
				attachmentStatePrompts.join("\n");
		}
		else {
			return "User did not attach any files."
		}
	}

	const saveChatHistory = async () => {
		const historyDict = dict(chatHistory);
		const history_json = json.dumps(historyDict);
		putArtifactFile("userId", history_json, `${sessionId}.json`);
	}

	const handleSend = async () => {
		if (!svc) {
			await handleLogin();
			return;
		}

		if (question.trim()) {
			const currentQuestion = question;
			const joinedStatePrompt =
				getAttachmentStatePrompt(attachmentStatePrompts);

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

			const newChatMap = makeChatHistoryMap(newChatHistory);
			
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
			} catch (e) {
				setStatus(`❌ Error: ${e.message || e}`);
			} finally {
				saveChatHistory();
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

	const makeChatHistoryMap = (chatHistory) => {
		return new Map(
			chatHistory.map((item, index) => [
				index.toString(),
				item,
			])
		)
	}

	const onSelectChat = (chatObject) => {
		const chatHistoryMap = makeChatHistoryMap(chatObject.conversations);
		setChatHistory((chatHistoryMap));
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
					prevChats={prevChatObjects}
					onSelectChat={onSelectChat}
					isLoggedIn={svc != null}
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
							<ChatHistory
								chatHistory={chatHistory}
								isSending={isSending}
							/>
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
