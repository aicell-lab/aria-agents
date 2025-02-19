/* global Chat */
class AriaArtifacts {
    constructor(artifactManager, workspace) {
        this.artifactManager = artifactManager;
        this.workspace = workspace;
    }

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

    async readChat(userId, chatId) {
        const chat = await this.artifactManager.read({
            artifact_id: `ws-user-${userId}/aria-agents-chats:${chatId}`,
            _rkwargs: true
        });
        return Chat.fromManifest(chat.manifest);
    }

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
