function ArtifactsPanel({
    onClose,
    artifacts,
    currentArtifactIndex,
    onPrev,
    onNext,
}) {
    const artifact = artifacts[currentArtifactIndex];
    return (
        <div className="artifacts-panel">
            <div className="flex justify-between items-center mb-4">
                <h2 className="text-xl font-bold">Artifacts</h2>
                <button
                    onClick={onClose}
                    className="text-2xl text-gray-600 hover:text-gray-900"
                >
                    X
                </button>
            </div>
            <div className="flex-1 overflow-y-auto mb-4">
                {artifact && (
                    <iframe
                        srcDoc={artifact.artifact}
                        title={`Artifact ${currentArtifactIndex + 1}`}
                        className="w-full h-full border border-gray-300"
                        style={{ height: "calc(100vh - 200px)" }} // Adjust height to account for buttons
                    />
                )}
            </div>
            <div className="flex justify-between mb-4">
                <button
                    onClick={onPrev}
                    className={`text-gray-600 hover:text-gray-900 ${
                        currentArtifactIndex === 0
                            ? "opacity-50 cursor-not-allowed"
                            : ""
                    }`}
                    disabled={currentArtifactIndex === 0}
                >
                    Prev
                </button>
                <button
                    onClick={onNext}
                    className={`text-gray-600 hover:text-gray-900 ${
                        currentArtifactIndex === artifacts.length - 1 ||
                        artifacts.length === 0
                            ? "opacity-50 cursor-not-allowed"
                            : ""
                    }`}
                    disabled={
                        currentArtifactIndex === artifacts.length - 1 ||
                        artifacts.length === 0
                    }
                >
                    Next
                </button>
            </div>
            {artifact && (
                <a
                    href={artifact.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="button text-center"
                >
                    Download current artifact
                </a>
            )}
        </div>
    );
}

// Expose ArtifactsPanel globally
window.ArtifactsPanel = ArtifactsPanel;
