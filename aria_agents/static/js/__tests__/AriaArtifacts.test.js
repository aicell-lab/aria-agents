import { AriaArtifacts } from '../AriaArtifacts';
import { MockArtifactManager } from '../__mocks__/MockArtifactManager';

describe('AriaArtifacts', () => {
    let ariaArtifacts;
    let mockArtifactManager;

    beforeEach(() => {
        mockArtifactManager = new MockArtifactManager();
        ariaArtifacts = new AriaArtifacts();
        ariaArtifacts.artifactManager = mockArtifactManager;
    });

    describe('saveFile', () => {
        it('should save a file and return the file info', async () => {
            const name = 'test.txt';
            const content = 'test content';
            
            const result = await ariaArtifacts.saveFile(name, content);
            expect(result).toBeTruthy();
            expect(mockArtifactManager.files[name]).toBe(content);
        });
    });

    describe('createChatCollection', () => {
        it('should create a chat collection', async () => {
            await ariaArtifacts.createChatCollection();
            expect(mockArtifactManager.collections['chats']).toBeTruthy();
        });
    });

    describe('saveChat', () => {
        it('should save a chat with all its data', async () => {
            const chatId = 'test-chat';
            const title = 'Test Chat';
            const conversations = [
                { role: 'user', content: 'Hello' },
                { role: 'assistant', content: 'Hi there' }
            ];
            const artifacts = [
                { name: 'test.txt', content: 'test content' }
            ];
            const attachments = [
                { name: 'attachment.txt', content: 'attachment content' }
            ];

            await ariaArtifacts.saveChat(chatId, title, conversations, artifacts, attachments);

            const savedChat = mockArtifactManager.collections['chats'][chatId];
            expect(savedChat).toBeTruthy();
            expect(savedChat.name).toBe(title);
            expect(savedChat.conversations).toEqual(conversations);
            expect(savedChat.artifacts).toEqual(artifacts);
            expect(savedChat.attachments).toEqual(attachments);
        });
    });

    describe('loadChats', () => {
        it('should load all saved chats', async () => {
            const chat = {
                id: 'test-chat',
                name: 'Test Chat',
                conversations: [],
                artifacts: [],
                attachments: []
            };
            mockArtifactManager.collections['chats'] = { 'test-chat': chat };

            const chats = await ariaArtifacts.loadChats();
            expect(chats).toHaveLength(1);
            expect(chats[0]).toEqual(chat);
        });
    });

    describe('readChat', () => {
        it('should read a specific chat by ID', async () => {
            const chat = {
                id: 'test-chat',
                name: 'Test Chat',
                conversations: [],
                artifacts: [],
                attachments: []
            };
            mockArtifactManager.collections['chats'] = { 'test-chat': chat };

            const result = await ariaArtifacts.readChat('user-id', 'test-chat');
            expect(result).toEqual(chat);
        });
    });

    describe('deleteChat', () => {
        it('should delete a chat by ID', async () => {
            const chat = {
                id: 'test-chat',
                name: 'Test Chat'
            };
            mockArtifactManager.collections['chats'] = { 'test-chat': chat };

            await ariaArtifacts.deleteChat(chat);
            expect(mockArtifactManager.collections['chats']['test-chat']).toBeUndefined();
        });
    });
});