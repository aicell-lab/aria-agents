/* global marked, completeCodeBlocks, jsonToMarkdown, modifyLinksToOpenInNewTab */

/**
 * Class representing a chat session.
 */
class Chat {
    /**
     * Create a chat session.
     * @param {string} [id=null] - The ID of the chat session.
     * @param {string} [title=""] - The title of the chat session.
     * @param {Map} [history=new Map()] - The history of messages in the chat session.
     * @param {Array} [artifacts=[]] - The artifacts associated with the chat session.
     * @param {Array} [attachments=[]] - The attachments associated with the chat session.
     */
    constructor(id = null, title = "", history = new Map(), artifacts = [], attachments = []) {
        this.id = id || this.generateId();
        this.title = title;
        this.history = history;
        this.artifacts = artifacts;
        this.attachments = attachments;
    }

    /**
     * Generate a unique ID for the chat session.
     * @returns {string} The generated ID.
     */
    generateId() {
        return "session-" + Math.random().toString(36).substr(2, 9);
    }

    /**
     * Add a message to the chat history.
     * @param {Object} message - The message to add.
     */
    addMessage(message) {
        const newHistory = new Map(this.history);
        newHistory.set(message.id, message);
        this.history = newHistory;
    }

    /**
     * Update a message in the chat history.
     * @param {string} id - The ID of the message to update.
     * @param {Object} updates - The updates to apply to the message.
     */
    updateMessage(id, updates) {
        const message = this.history.get(id);
        if (message) {
            this.history.set(id, { ...message, ...updates });
        }
    }

    /**
     * Add an artifact to the chat session.
     * @param {Object} artifact - The artifact to add.
     */
    addArtifact(artifact) {
        this.artifacts = [...this.artifacts, artifact];
    }

    /**
     * Convert the chat session to a manifest object.
     * @param {string} userId - The ID of the user.
     * @returns {Object} The manifest object.
     */
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

    /**
     * Create a chat session from a manifest object.
     * @param {Object} manifest - The manifest object.
     * @returns {Chat} The created chat session.
     */
    static fromManifest(manifest) {
        return new Chat(
            manifest.id,
            manifest.name,
            new Map(Object.entries(manifest.conversations || {})),
            manifest.artifacts || [],
            manifest.attachments || []
        );
    }

    /**
     * Add a user message to the chat history.
     * @param {string} content - The content of the message.
     * @param {Array} [attachments=[]] - The attachments associated with the message.
     */
    addUserMessage(content, attachments = []) {
        this.addMessage({
            id: this.history.size.toString(),
            role: "user",
            content: marked(completeCodeBlocks(content)),
            attachments
        });
    }

    /**
     * Check if the chat session is empty.
     * @returns {boolean} True if the chat session is empty, false otherwise.
     */
    isEmpty() {
        return this.history.size === 0;
    }

    /**
     * Get the last message in the chat history.
     * @returns {Object} The last message.
     */
    getLastMessage() {
        const messages = Array.from(this.history.values());
        return messages[messages.length - 1];
    }

    /**
     * Clone the chat session.
     * @returns {Chat} The cloned chat session.
     */
    clone() {
        return new Chat(
            this.id,
            this.title,
            new Map(this.history),
            [...this.artifacts],
            [...this.attachments]
        );
    }

    /**
     * Send a message using the chat service.
     * @param {string} query - The query to send.
     * @param {Array} attachments - The attachments to send.
     * @param {Object} chatService - The chat service.
     * @param {Function} statusCallback - The status callback function.
     * @param {Function} artifactCallback - The artifact callback function.
     * @param {Function} titleCallback - The title callback function.
     * @param {string} sessionId - The session ID.
     * @param {string} userId - The user ID.
     * @param {string} userToken - The user token.
     */
    async sendMessage(query, attachments, chatService, statusCallback, artifactCallback, titleCallback, sessionId, userId, userToken) {
        const currentChatHistory = Array.from(this.history.values()).map(
            (chat) => {
                let { role, content, attachments, ...rest } = chat;
                role = role.toString() === "user" ? "user" : "assistant";
                return {
                    ...rest,
                    role: role.toString(),
                    content: this.contentWithAttachments(content, attachments),
                };
            }
        );
        const extensions = [{ id: "aria" }];
        if (this.title === "") {
            const summaryQuestion = `Give a succinct title to this chat
             session summarizing this prompt written by
             the user: "${query}". Respond ONLY with words,
             maximum six words. DO NOT include the words
             "Chat Session Title" or similar`;
            await chatService.chat(
                summaryQuestion,
                currentChatHistory,
                titleCallback,
                () => { },
                sessionId,
                userId,
                userToken,
                extensions,
            );
        }
        await chatService.chat(
            query,
            currentChatHistory,
            statusCallback,
            artifactCallback,
            sessionId,
            userId,
            userToken,
            extensions,
        );
    }

    /**
     * Combine content with attachments.
     * @param {string} content - The content of the message.
     * @param {Array} attachmentNames - The names of the attachments.
     * @returns {string} The combined content and attachments.
     */
    contentWithAttachments(content, attachmentNames) {
        const attachmentNamesString = attachmentNames.join(",\n");
        return `<MESSAGE_CONTENT>\n${content.toString()}\n</MESSAGE_CONTENT>\n\n<ATTACHMENT_NAMES>\n${attachmentNamesString}</ATTACHMENT_NAMES>`;
    }
}

window.Chat = Chat;