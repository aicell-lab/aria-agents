// ...existing code...

const jsonToMarkdown = (obj) => {
    if (typeof obj !== 'object' || obj === null) {
        return String(obj);
    }

    const formatField = (value) => {
        if (Array.isArray(value)) {
            return value.map(v => `  - ${v}`).join('\n');
        }
        return value;
    };

    const lines = [];
    for (const [key, value] of Object.entries(obj)) {
        // Convert key from camelCase/snake_case to Title Case
        const title = key
            .replace(/_/g, ' ')
            .replace(/([A-Z])/g, ' $1')
            .replace(/^./, str => str.toUpperCase());
        
        // Skip empty arrays and null/undefined values
        if ((Array.isArray(value) && value.length === 0) || value == null) {
            continue;
        }

        lines.push(`**${title}:**\n${formatField(value)}\n`);
    }

    return lines.join('\n');
};

// ...existing code...

window.helpers = {
    // ...existing exports...
    jsonToMarkdown,
    // ...existing exports...
};