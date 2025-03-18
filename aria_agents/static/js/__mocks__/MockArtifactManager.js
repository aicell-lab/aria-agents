export class MockArtifactManager {
    constructor() {
        this.files = {};
        this.collections = {};
        this.vectors = {};
    }

    async createCollection(name) {
        this.collections[name] = {};
        return true;
    }

    async saveToCollection(collectionName, id, data) {
        if (!this.collections[collectionName]) {
            await this.createCollection(collectionName);
        }
        this.collections[collectionName][id] = data;
        return true;
    }

    async getFromCollection(collectionName, id) {
        return this.collections[collectionName]?.[id];
    }

    async getAllFromCollection(collectionName) {
        return Object.values(this.collections[collectionName] || {});
    }

    async deleteFromCollection(collectionName, id) {
        if (this.collections[collectionName]) {
            delete this.collections[collectionName][id];
        }
        return true;
    }

    async saveFile(name, content) {
        this.files[name] = content;
        return true;
    }

    async getFile(name) {
        return this.files[name];
    }

    async addVectors(query, fileContents) {
        this.vectors[query] = fileContents;
        return true;
    }

    async searchVectors(query) {
        return this.vectors[query] || [];
    }
}