window.useUiState = function() {
    const { useState } = React;
    const [uiState, setUiState] = useState({
        question: '',
        attachmentNames: [],
        isPaused: false,
        isSending: false,
        isLoading: false,
        isSidebarOpen: false,
        isArtifactsPanelOpen: false,
        showShareDialog: false,
        alertContent: '',
        status: 'Please log in before sending a message.',
        currentArtifactIndex: 0,
    });

    return { uiState, setUiState };
};
