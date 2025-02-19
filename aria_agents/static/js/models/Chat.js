/* global marked, completeCodeBlocks */
class Chat {
    constructor(id = null, title = "", history = new Map(), artifacts = [], attachments = []) {
        this.id = id || this.generateId();
        this.title = title;
        this.history = history;
        this.artifacts = artifacts;
        this.attachments = attachments;
    }

    generateId() {
        return "session-" + Math.random().toString(36).substr(2, 9);
    }

    addMessage(message) {
        const newHistory = new Map(this.history);
        newHistory.set(message.id, message);
        this.history = newHistory;
    }

    updateMessage(id, updates) {
        const message = this.history.get(id);
        if (message) {
            this.history.set(id, { ...message, ...updates });
        }
    }

    addArtifact(artifact) {
        this.artifacts = [...this.artifacts, artifact];
    }

    toManifest(userId) {
        return {
            id: this.id,
            name: this.title,
            description: `The Aria Agents chat history of ${this.id}`,
            type: "chat",
            conversations: Object.fromEntries(this.history),
            artifacts: this.artifacts,
            attachments: this.attachments,
            timestamp: new Date().toISOString(),
            userId: userId,
        };
    }

    static fromManifest(manifest) {
        return new Chat(
            manifest.id,
            manifest.name,
            new Map(Object.entries(manifest.conversations || {})),
            manifest.artifacts || [],
            manifest.attachments || []
        );
    }

    addUserMessage(content, attachments = []) {
        this.addMessage({
            id: this.history.size.toString(),
            role: "user",
            content: marked(completeCodeBlocks(content)),
            attachments
        });
    }

    isEmpty() {
        return this.history.size === 0;
    }

    getLastMessage() {
        const messages = Array.from(this.history.values());
        return messages[messages.length - 1];
    }

    clone() {
        return new Chat(
            this.id,
            this.title,
            new Map(this.history),
            [...this.artifacts],
            [...this.attachments]
        );
    }
}

window.Chat = Chat;