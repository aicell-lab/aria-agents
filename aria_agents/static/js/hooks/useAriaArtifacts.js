window.useAriaArtifacts = function() {
    const { useState } = React;
    const [ariaArtifacts, setAriaArtifacts] = useState(null);
    return { ariaArtifacts, setAriaArtifacts };
};
