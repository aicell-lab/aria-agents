import { useState } from 'react';

export function useAriaArtifacts() {
    const [ariaArtifacts, setAriaArtifacts] = useState(null);

    return { ariaArtifacts, setAriaArtifacts };
}
