function ArtefactsPanel({
	onClose,
	artefacts,
	currentArtefactIndex,
	onPrev,
	onNext,
}) {
	const artefact = artefacts[currentArtefactIndex];

	return (
		<div className="artefacts-panel">
			<div className="flex justify-between items-center mb-4">
				<h2 className="text-xl font-bold">Artefacts</h2>
				<button
					onClick={onClose}
					className="text-2xl text-gray-600 hover:text-gray-900"
				>
					X
				</button>
			</div>
			<div className="flex-1 overflow-y-auto mb-4">
				{artefact && (
					<iframe
						srcDoc={artefact.artefact}
						title={`Artefact ${currentArtefactIndex + 1}`}
						className="w-full h-full border border-gray-300"
						style={{ height: "calc(100vh - 200px)" }} // Adjust height to account for buttons
					/>
				)}
			</div>
			<div className="flex justify-between mb-4">
				<button
					onClick={onPrev}
					className={`text-gray-600 hover:text-gray-900 ${
						currentArtefactIndex === 0
							? "opacity-50 cursor-not-allowed"
							: ""
					}`}
					disabled={currentArtefactIndex === 0}
				>
					Prev
				</button>
				<button
					onClick={onNext}
					className={`text-gray-600 hover:text-gray-900 ${
						currentArtefactIndex === artefacts.length - 1 ||
						artefacts.length === 0
							? "opacity-50 cursor-not-allowed"
							: ""
					}`}
					disabled={
						currentArtefactIndex === artefacts.length - 1 ||
						artefacts.length === 0
					}
				>
					Next
				</button>
			</div>
			{artefact && (
				<a
					href={artefact.url}
					target="_blank"
					rel="noopener noreferrer"
					className="button text-center"
				>
					Download current artefact
				</a>
			)}
		</div>
	);
}

// Expose ArtefactsPanel globally
window.ArtefactsPanel = ArtefactsPanel;
