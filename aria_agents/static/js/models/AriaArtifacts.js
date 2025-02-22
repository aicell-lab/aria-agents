/* global Chat */
/**
 * Class representing the Aria Artifacts manager.
 */
class AriaArtifacts {
    /**
     * Create an Aria Artifacts manager.
     * @param {Object} artifactManager - The artifact manager service.
     * @param {string} workspace - The workspace ID.
     */
    constructor(artifactManager, workspace) {
        this.artifactManager = artifactManager;
        this.workspace = workspace;
    }

    /**
     * Create a chat collection in the artifact manager.
     */
    async createChatCollection() {
        const galleryManifest = {
            name: "Aria Agents Chat History",
            description: "A collection used to store previous chat sessions with the Aria Agents chatbot",
            collection: [],
        };

        try {
            await this.artifactManager.create({
                type: "collection",
                workspace: this.workspace,
                alias: "aria-agents-chats",
                manifest: galleryManifest,
                _rkwargs: true
            });
        } catch {
            console.log("User chat collection already exists.");
        }
    }

    /**
     * Save a chat session to the artifact manager.
     * @param {Chat} chat - The chat session to save.
     * @param {string} userId - The ID of the user.
     * @param {Object} [permissions=null] - The permissions for the chat session.
     */
    async saveChat(chat, userId, permissions = null) {
        const manifest = chat.toManifest(userId);
        try {
            await this.artifactManager.create({
                type: "chat",
                parent_id: `${this.workspace}/aria-agents-chats`,
                alias: `aria-agents-chats:${chat.id}`,
                manifest: manifest,
                ...(permissions && { config: { permissions: permissions } }),
                _rkwargs: true
            });
        } catch {
            const chatId = `${this.workspace}/aria-agents-chats:${chat.id}`;
            await this.artifactManager.edit({
                artifact_id: chatId,
                manifest: manifest,
                ...(permissions && { config: { permissions: permissions } }),
                _rkwargs: true
            });
            await this.artifactManager.commit(chatId);
        }
    }

    /**
     * Load all chat sessions from the artifact manager.
     * @returns {Promise<Array<Chat>>} The list of chat sessions.
     */
    async loadChats() {
        try {
            const artifacts = await this.artifactManager.list({
                parent_id: `${this.workspace}/aria-agents-chats`,
                _rkwargs: true,
            });
            return artifacts
                .map(a => Chat.fromManifest(a.manifest))
                .filter(chat => chat.title !== "");
        } catch (e) {
            console.log("Chats couldn't be loaded. Error: ", e);
            return [];
        }
    }

    /**
     * Read a chat session from the artifact manager.
     * @param {string} userId - The ID of the user.
     * @param {string} chatId - The ID of the chat session.
     * @returns {Promise<Chat>} The chat session.
     */
    async readChat(userId, chatId) {
        const chat = await this.artifactManager.read({
            artifact_id: `ws-user-${userId}/aria-agents-chats:${chatId}`,
            _rkwargs: true
        });
        return Chat.fromManifest(chat.manifest);
    }

    /**
     * Delete a chat session from the artifact manager.
     * @param {Chat} chat - The chat session to delete.
     */
    async deleteChat(chat) {
        try {
            await this.artifactManager.delete({
                artifact_id: `${this.workspace}/aria-agents-chats:${chat.id}`,
                delete_files: true,
                recursive: true,
                _rkwargs: true
            });
        } catch {
            console.log(`Chat ${chat.id} is already deleted.`);
        }
    }
}

window.AriaArtifacts = AriaArtifacts;
