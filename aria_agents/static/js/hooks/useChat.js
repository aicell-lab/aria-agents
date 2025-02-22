import { useState } from 'react';
import { Chat } from '../models';

export function useChat() {
    const [chat, setChat] = useState(new Chat());

    return { chat, setChat };
}
