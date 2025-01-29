function generateSessionID() {
	return "session-" + Math.random().toString(36).substr(2, 9);
}

function getUrlParam(param_name) {
	const urlParams = new URLSearchParams(window.location.search);
	return urlParams.get(param_name);
}

function urlMinusParam(param_name) {
	const url = new URL(window.location);
	url.searchParams.delete(param_name);
	return url.toString();
}

function urlPlusParam(param_dict) {
	const url = new URL(window.location);
	for (const [param_name, param_value] of Object.entries(param_dict)) {
		url.searchParams.set(param_name, param_value);
	}
	return url.toString();
}

function getServerUrl() {
	return getUrlParam("server") || window.location.origin;
}

async function getServer(token) {
	return await hyphaWebsocketClient.connectToServer({
		server_url: getServerUrl(),
		token: token,
		method_timeout: 500,
	});
}

function isLocal() {
	const serverUrl = getServerUrl();
	return serverUrl.includes("127.0.0.1") || serverUrl.includes("localhost");
}

async function getService(server, remoteId, localId = null) {
	const serviceId = localId && isLocal()? localId : remoteId;
	console.log("service ID: ", serviceId);
	const svc = await server.getService(serviceId, {"case_conversion": "camel"});
	console.log("service connected: ", svc);
	return svc;
}

function login_callback(context) {
	window.open(context.login_url);
}

function isTokenExpired(token) {
	return Date.now() >= (JSON.parse(atob(token.split('.')[1]))).exp * 1000
}

async function login() {
	const serverUrl = getServerUrl();
	let token = localStorage.getItem("token");
	if (token) {
		if (!isTokenExpired(token)) {
			console.log("Using saved token:", token);
			return token;
		}
	}
	token = await hyphaWebsocketClient.login({
		server_url: serverUrl,
		login_callback: login_callback,
	});
	localStorage.setItem("token", token);
	return token;
}

function completeCodeBlocks(markdownText) {
	if (!markdownText) {
		return markdownText;
	}
	const codeBlockIndicator = "```";

	// Replace "```" in JSON strings with "```"
	markdownText = markdownText.replace(/```/g, "```");

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
		let markdown = "";
		const indent = "  ".repeat(indentLevel);

		for (const [key, value] of Object.entries(data)) {
			if (value === null) {
				markdown += `${indent}- **${key}**: null\n`;
			} else if (Array.isArray(value)) {
				markdown += `${indent}- **${key}**:\n`;
				value.forEach((item) => {
					if (typeof item === "object" && item !== null) {
						markdown += createListMarkdown(item, indentLevel + 1);
					} else {
						markdown += `${indent}  - ${
							item === null ? "null" : item
						}\n`;
					}
				});
			} else if (typeof value === "object") {
				markdown += `${indent}- **${key}**:\n`;
				markdown += createListMarkdown(value, indentLevel + 1);
			} else {
				markdown += `${indent}- **${key}**: ${value}\n`;
			}
		}
		return markdown;
	}

	let markdown = "";

	for (const [key, value] of Object.entries(json)) {
		markdown += `#### ${key}\n`;
		if (value === null) {
			markdown += `- null\n`;
		} else if (Array.isArray(value)) {
			value.forEach((item) => {
				if (typeof item === "object" && item !== null) {
					markdown += createListMarkdown(item, 1);
				} else {
					markdown += `- ${item === null ? "null" : item}\n`;
				}
			});
		} else if (typeof value === "object") {
			markdown += createListMarkdown(value, 1);
		} else {
			markdown += `- ${value}\n`;
		}
		markdown += "\n";
	}

	return markdown;
}

function modifyLinksToOpenInNewTab(htmlContent) {
	const div = document.createElement("div");
	div.innerHTML = htmlContent;
	const links = div.querySelectorAll("a");
	links.forEach((link) => {
		link.setAttribute("target", "_blank");
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
	getServer: getServer,
	getUrlParam: getUrlParam,
	urlMinusParam: urlMinusParam,
	urlPlusParam: urlPlusParam,
};
