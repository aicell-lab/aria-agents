async function getService(token) {
    const urlParams = new URLSearchParams(window.location.search);
    const service_id = urlParams.get('service_id');
    let serverUrl = urlParams.get('server') || window.location.origin;
    if (serverUrl.includes('localhost')) {
        serverUrl = "http://localhost:9000";
    }
    const server = await hyphaWebsocketClient.connectToServer({ "server_url": serverUrl, "token": token });
    const svc = await server.getService(service_id || "public/workspace-manager:aria-agents");
    await svc.ping();
    console.log("service connected: ", svc);
    return svc;
}

function login_callback(context) {
    window.open(context.login_url);
}

async function login() {
    const urlParams = new URLSearchParams(window.location.search);
    let serverUrl = urlParams.get('server') || window.location.origin;
    if (serverUrl.includes('localhost')) {
        serverUrl = "http://localhost:9000";
    }
    let token = localStorage.getItem('token');
    if (token) {
        const tokenExpiry = localStorage.getItem('tokenExpiry');
        if (tokenExpiry && new Date(tokenExpiry) > new Date()) {
            console.log("Using saved token:", token);
            return token;
        }
    }
    token = await hyphaWebsocketClient.login({
        "server_url": serverUrl,
        "login_callback": login_callback,
    });
    localStorage.setItem('token', token);
    localStorage.setItem('tokenExpiry', new Date(Date.now() + 3 * 60 * 60 * 1000).toISOString());
    return token;
}

function completeCodeBlocks(markdownText) {
    if (!markdownText) {
        return markdownText;
    }
    const codeBlockIndicator = '```';

    // Replace "```" in JSON strings with "```"
    markdownText = markdownText.replace(/```/g, '```');

    // Split text by code block indicator
    const parts = markdownText.split(codeBlockIndicator);

    // If there's an odd number of parts, it means a code block is not closed
    if (parts.length > 1 && parts.length % 2 !== 0) {
        // Append a closing code block indicator
        markdownText += `\n${codeBlockIndicator}`;
    }

    return markdownText;
};


function generateMessage(text, steps) {
    let message = text ? marked(text) : "";

    if (steps && steps.length > 0) {
        let details = "<details class='details-box'> <summary>🔍More Details</summary>\n\n";
        for (let step of steps) {
            details += `## ${step.name}\n\n`;

            if (step.details.details) {
                for (let detail of step.details.details) {
                    details += `-----\n### Tool Call: \`${detail.name}\`\n\n`;
                    details += "#### Arguments:\n\n";
                    if (detail.args && detail.args.length > 0) {
                        for (let arg of detail.args) {
                            const argValue = JSON.stringify(arg);
                            details += `\`\`\`\n${argValue}\n\`\`\`\n\n`;
                        }
                        details += "\n\n";
                    }

                    if (detail.kwargs) {
                        for (let kwarg in detail.kwargs) {
                            const kwargValue = typeof detail.kwargs[kwarg] === 'string' ? detail.kwargs[kwarg] : JSON.stringify(detail.kwargs[kwarg], null, 2);
                            if (kwargValue.includes('\n'))
                                details += `**- \`${kwarg}\`**:\n\n\`\`\`\n${kwargValue}\n\`\`\`\n\n`;
                            else
                                details += `**- \`${kwarg}\`**: \`${kwargValue}\`\n\n`;
                        }
                        details += "\n\n";
                    }

                    if (detail.result) {
                        const result = typeof detail.result === 'string' ? detail.result : JSON.stringify(detail.result, null, 2);
                        if (result.includes('\n'))
                            details += `#### Result:\n\n\`\`\`\n${result}\n\`\`\`\n\n`;
                        else
                            details += `#### Result: \`${result}\`\n\n`;
                    }
                }
            }
        }
        details += "\n\n</details>";
        details = marked(details);
        message = message + details;
    }
    return message;
};


function generateSessionID() {
    return "session-" + Math.random().toString(36).substr(2, 9);
}

window.helpers = {
    getService: getService,
    login: login,
    completeCodeBlocks: completeCodeBlocks,
    generateMessage: generateMessage,
    generateSessionID: generateSessionID,
};
