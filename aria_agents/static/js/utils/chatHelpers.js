function getChatManifest(sessionId, chatTitle, chatHistory, artifacts, attachments, userId) {
    return {
        "id": sessionId,
        "name": chatTitle,
        "description": `The Aria Agents chat history of ${sessionId}`,
        "type": "chat",
        "conversations": chatHistory,
        "artifacts": artifacts,
        "attachments": attachments,
        "timestamp": new Date().toISOString(),
        "userId": userId,
    };
}

async function readChat(artifactManager, newUserId, newSessionId) {
    const chat = await artifactManager.read({
        artifact_id: `ws-user-${newUserId}/aria-agents-chats:${newSessionId}`,
        _rkwargs: true
    });
    return chat.manifest;
}

async function loadChats(artifactManager, artifactWorkspace) {
    try {
        const prevChatArtifacts = await artifactManager.list({
            parent_id: `${artifactWorkspace}/aria-agents-chats`,
            _rkwargs: true,
        });
        const prevChatManifests = prevChatArtifacts.map((chat) => chat.manifest);
        const unnamedChats = prevChatManifests.filter((chat) => chat.name === "");
        unnamedChats.forEach(deleteChat);
        const namedChats =  prevChatManifests.filter((chat) => chat.name !== "");
        return namedChats;
    }
    catch (e) {
        console.log("Chats couldn't be loaded. Error: ", e);
        return [];
    }
}

async function createChatCollection(artifactManager, artifactWorkspace) {
    const galleryManifest = {
        "name": "Aria Agents Chat History",
        "description": "A collection used to store previous chat sessions with the Aria Agents chatbot",
        "collection": [],
    };

    try {
        await artifactManager.create({
            type: "collection",
            workspace: artifactWorkspace,
            alias: "aria-agents-chats",
            manifest: galleryManifest,
            _rkwargs: true
        });
    }
    catch {
        console.log("User chat collection already exists.");
    }
}

async function saveChat(artifactManager, artifactWorkspace, sessionId, datasetManifest, permissions = null) {
    try {
        await artifactManager.create({
            type: "chat",
            parent_id: `${artifactWorkspace}/aria-agents-chats`,
            alias: `aria-agents-chats:${sessionId}`,
            manifest: datasetManifest,
            ...(permissions && {
                config: {
                    permissions: permissions
                }
            }),
            _rkwargs: true
        });
    } catch {
        const chatId = `${artifactWorkspace}/aria-agents-chats:${sessionId}`;
        await artifactManager.edit({
            artifact_id: chatId,
            manifest: datasetManifest,
            ...(permissions && {
                config: {
                    permissions: permissions
                }
            }),
            _rkwargs: true
        });
        await artifactManager.commit(chatId);
    }
}

async function deleteChat(artifactManager, artifactWorkspace, chat) {
    try {
        await artifactManager.delete({
            artifact_id: `${artifactWorkspace}/aria-agents-chats:${chat.id}`,
            delete_files: true,
            recursive: true,
            _rkwargs: true
        });
    }
    catch {
        console.log(`Chat ${chat.id} is already deleted.`);
    }
}

window.chatHelpers = {
    getChatManifest: getChatManifest,
    readChat: readChat,
    loadChats: loadChats,
    createChatCollection: createChatCollection,
    saveChat: saveChat,
    deleteChat: deleteChat,
};