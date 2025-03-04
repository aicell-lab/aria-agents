class AriaArtifacts {
  constructor() {
    this.artifactManager = null;
    this.artifactWorkspace = '';
    this.userId = '';
    this.currentSessionId = null;
  }

  async setServices(token) {
    const server = await getServer(token);
    const configUserId = server.config.user.id;
    this.userId = configUserId;
    this.artifactWorkspace = `ws-user-${configUserId}`;

    const artifactManagerService = await getService(server, 'public/artifact-manager');
    this.artifactManager = artifactManagerService;
  }

  _artifactAlias(name) {
    return `aria-agents-${name}`;
  }

  _artifactId(collName) {
    return `${this.artifactWorkspace}/${this._artifactAlias(collName)}`;
  }

  async createVectorCollection(collName, manifest, config, overwrite = false) {
    const artId = this._artifactId(collName);
    try {
      await this.artifactManager.create({
        alias: artId,
        type: 'vector-collection',
        manifest: manifest,
        config: config,
        overwrite: overwrite,
        _rkwargs: true
      });
    } catch (e) {
      if (!e.message.includes('already exists')) {
        throw e;
      }
    }
  }

  async addVectors(collName, vectors) {
    const artId = this._artifactId(collName);
    return await this.artifactManager.add_vectors({
      artifact_id: artId,
      vectors: vectors,
      _rkwargs: true
    });
  }

  async searchVectors(collName, vector, topK = null) {
    const artId = this._artifactId(collName);
    return await this.artifactManager.search_vectors({
      artifact_id: artId,
      query: { "content_vector": vector },
      limit: topK,
      _rkwargs: true
    });
  }

  async removeVectors(collName, vectorIds = null) {
    const artId = this._artifactId(collName);
    if (!vectorIds) {
      let allVectors = await this.artifactManager.list_vectors({
        artifact_id: artId,
        _rkwargs: true
      });
      while (allVectors.length > 0) {
        vectorIds = allVectors.map(vector => vector.id);
        await this.artifactManager.remove_vectors({
          artifact_id: artId,
          vector_ids: vectorIds,
          _rkwargs: true
        });
        allVectors = await this.artifactManager.list_vectors({
          artifact_id: artId,
          _rkwargs: true
        });
      }
    } else {
      await this.artifactManager.remove_vectors({
        artifact_id: artId,
        vector_ids: vectorIds,
        _rkwargs: true
      });
    }
  }

  // Chat history related methods
  async createChatCollection() {
    const galleryManifest = {
      name: 'Aria Agents Chat History',
      description: 'A collection used to store previous chat sessions with the Aria Agents chatbot',
      collection: [],
    };

    try {
      await this.artifactManager.create({
        type: 'collection',
        workspace: this.artifactWorkspace,
        alias: 'aria-agents-chats',
        manifest: galleryManifest,
        _rkwargs: true,
      });
    } catch {
      console.log('User chat collection already exists.');
    }
  }

  async saveChat(sessionId, chatTitle, chatHistory, artifacts, attachments, permissions = null) {
    this.currentSessionId = sessionId;
    const datasetManifest = this.getChatManifest(sessionId, chatTitle, chatHistory, artifacts, attachments);

    try {
      await this.artifactManager.create({
        type: 'chat',
        parent_id: `${this.artifactWorkspace}/aria-agents-chats`,
        alias: `aria-agents-chats:${sessionId}`,
        manifest: datasetManifest,
        ...(permissions && {
          config: {
            permissions: permissions,
          },
        }),
        _rkwargs: true,
      });
    } catch {
      const chatId = `${this.artifactWorkspace}/aria-agents-chats:${sessionId}`;
      await this.artifactManager.edit({
        artifact_id: chatId,
        manifest: datasetManifest,
        ...(permissions && {
          config: {
            permissions: permissions,
          },
        }),
        _rkwargs: true,
      });
    }
  }

  async deleteChat(chat) {
    try {
      await this.artifactManager.delete({
        artifact_id: `${this.artifactWorkspace}/aria-agents-chats:${chat.id}`,
        delete_files: true,
        recursive: true,
        _rkwargs: true,
      });
    } catch {
      console.log(`Chat ${chat.id} is already deleted.`);
    }
  }

  async loadChats() {
    try {
      let prevChatArtifacts = await this.artifactManager.list({
        parent_id: `${this.artifactWorkspace}/aria-agents-chats`,
        _rkwargs: true,
      });
      const prevChatManifests = prevChatArtifacts.map((chat) => chat.manifest);
      const unnamedChats = prevChatManifests.filter((chat) => chat.name === '');
      unnamedChats.forEach(this.deleteChat.bind(this));
      const namedChats = prevChatManifests.filter((chat) => chat.name !== '');
      return namedChats;
    } catch (e) {
      console.log("Chats couldn't be loaded. Error: ", e);
      return [];
    }
  }

  async readChat(newUserId, newSessionId) {
    this.currentSessionId = newSessionId;
    const chat = await this.artifactManager.read({
      artifact_id: `ws-user-${newUserId}/aria-agents-chats:${newSessionId}`,
      _rkwargs: true,
    });
    return chat.manifest;
  }

  getChatManifest(sessionId, chatTitle, chatHistory, artifacts, attachments) {
    return {
      id: sessionId,
      name: chatTitle,
      description: `The Aria Agents chat history of ${sessionId}`,
      type: 'chat',
      conversations: chatHistory,
      artifacts: artifacts,
      attachments: attachments,
      timestamp: new Date().toISOString(),
      userId: this.userId,
    };
  }
}

window.AriaArtifacts = AriaArtifacts;