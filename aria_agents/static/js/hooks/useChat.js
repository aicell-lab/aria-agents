window.useChat = function() {
    const { useState } = React;
    const { Chat } = window;
    const [chat, setChat] = useState(new Chat());
    return { chat, setChat };
};
