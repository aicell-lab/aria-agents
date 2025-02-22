const handleMessageStart = (queryId, toolName, session, setChat) => {
    const { role_setting: { name: roleName, icon: roleIcon } = {} } = session;
    setChat(prevChat => {
        const newChat = prevChat.clone();
        newChat.addMessage({
            id: queryId,
            role: roleName || "Agent",
            icon: roleIcon || "🤖",
            toolName,
            title: `### ⏳ Calling tool 🛠️ \`${toolName}\`...`,
            content: "",
            status: "in_progress"
        });
        return newChat;
    });
};

const handleMessageProgress = (queryId, toolName, args, setChat) => {
    setChat(prevChat => {
        const newChat = prevChat.clone();
        newChat.updateMessage(queryId, {
            accumulatedArgs: (args || "").replace(/\n/g, ""),
            title: `### ⏳ Calling tool 🛠️ \`${toolName}\`...`,
            content: `<div>${args || ""}</div>`,
        });
        return newChat;
    });
};

const handleMessageFinished = (queryId, toolName, content, args, setChat) => {
    const { jsonToMarkdown, modifyLinksToOpenInNewTab, completeCodeBlocks, marked } = window.helpers;

    setChat(prevChat => {
        const newChat = prevChat.clone();
        if (toolName === "SummaryWebsite") {
            const artifactIndex = newChat.artifacts.length;
            newChat.updateMessage(queryId, {
                content: `
                    <button 
                        class="button" 
                        onclick="openSummaryWebsite(${artifactIndex})"
                    >
                        View Summary Website
                    </button>`,
                status: "finished"
            });
        } else {
            let finalContent = content || jsonToMarkdown(args) || "";
            finalContent = modifyLinksToOpenInNewTab(
                marked(completeCodeBlocks(finalContent))
            );
            newChat.updateMessage(queryId, {
                title: `### Tool 🛠️ \`${toolName}\``,
                content: finalContent,
                status: "finished"
            });
        }
        return newChat;
    });
};

window.chatStatusHelpers = {
    handleMessageStart,
    handleMessageProgress,
    handleMessageFinished
};
