function generateSessionID() {
    return "session-" + Math.random().toString(36).substr(2, 9);
}

function getServerUrl() {
    const urlParams = new URLSearchParams(window.location.search);
    let serverUrl = urlParams.get('server') || window.location.origin;
    if (serverUrl.includes('localhost')) {
        serverUrl = "http://localhost:9000";
    }

    return serverUrl;
}

function getServiceId() {
    const urlParams = new URLSearchParams(window.location.search);
    return urlParams.get('service_id');
}

async function getService(token, ping = true) {
    const serviceId = getServiceId();
    return await getServiceWithId(token, serviceId, ping);
}

async function getServiceWithId(token, serviceId, ping = false) {
    const serverUrl = getServerUrl();
    console.log("service ID: ", serviceId);
    // method_timeout: 500 (8.3 minutes) is arbitrary number. Must be at least a few minutes due to slow functions
    const server = await hyphaWebsocketClient.connectToServer({ "server_url": serverUrl, "token": token, "method_timeout": 500 });
    const svc = await server.getService(serviceId || "aria-agents/*:aria-agents");
    
    if (ping) {
        await svc.ping();
    }
    console.log("service connected: ", svc);
    return svc;
}

function login_callback(context) {
    window.open(context.login_url);
}

async function login() {
    const serverUrl = getServerUrl();
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
}


function jsonToMarkdown(jsonStr) {
    const json = JSON.parse(jsonStr);

    function createListMarkdown(data, indentLevel = 0) {
        let markdown = '';
        const indent = '  '.repeat(indentLevel);

        for (const [key, value] of Object.entries(data)) {
            if (value === null) {
                markdown += `${indent}- **${key}**: null\n`;
            } else if (Array.isArray(value)) {
                markdown += `${indent}- **${key}**:\n`;
                value.forEach(item => {
                    if (typeof item === 'object' && item !== null) {
                        markdown += createListMarkdown(item, indentLevel + 1);
                    } else {
                        markdown += `${indent}  - ${item === null ? 'null' : item}\n`;
                    }
                });
            } else if (typeof value === 'object') {
                markdown += `${indent}- **${key}**:\n`;
                markdown += createListMarkdown(value, indentLevel + 1);
            }
            else {
                markdown += `${indent}- **${key}**: ${value}\n`;
            }
        }
        return markdown;
    }

    let markdown = '';

    for (const [key, value] of Object.entries(json)) {
        markdown += `#### ${key}\n`;
        if (value === null) {
            markdown += `- null\n`;
        } else if (Array.isArray(value)) {
            value.forEach(item => {
                if (typeof item === 'object' && item !== null) {
                    markdown += createListMarkdown(item, 1);
                } else {
                    markdown += `- ${item === null ? 'null' : item}\n`;
                }
            });
        } else if (typeof value === 'object') {
            markdown += createListMarkdown(value, 1);
        }
        else {
            markdown += `- ${value}\n`;
        }
        markdown += '\n';
    }

    return markdown;
}


function modifyLinksToOpenInNewTab(htmlContent) {
    const div = document.createElement('div');
    div.innerHTML = htmlContent;
    const links = div.querySelectorAll('a');
    links.forEach(link => {
        link.setAttribute('target', '_blank');
    });
    return div.innerHTML;
}

window.helpers = {
    generateSessionID: generateSessionID,
    getService: getService,
    login: login,
    completeCodeBlocks: completeCodeBlocks,
    jsonToMarkdown: jsonToMarkdown,
    modifyLinksToOpenInNewTab: modifyLinksToOpenInNewTab,
    getServiceWithId: getServiceWithId,
};
