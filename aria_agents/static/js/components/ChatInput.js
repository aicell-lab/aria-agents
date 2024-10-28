function ChatInput({
	onLogin,
	question,
	setQuestion,
	handleSend,
	svc,
	placeholder,
	handleAttachment,
	attachmentNames,
	undoAttach,
}) {
	return (
		<div className="mb-4 flex flex-col items-center">
			<input
				type="text"
				placeholder={placeholder}
				value={question}
				onChange={(e) => setQuestion(e.target.value)}
				className="w-full p-3 border border-gray-300 rounded mb-2 text-lg"
				onKeyPress={(e) => e.key === "Enter" && handleSend()}
			/>
			{svc ? (
				<>
					{attachmentNames.length > 0 ? (
						<div className="mb-2 w-full">
							<div className="flex flex-wrap gap-2">
								{attachmentNames.map((fileName, index) => (
									<div
										key={fileName + index}
										className="bg-gray-200 text-gray-700 px-3 py-1 rounded-md flex items-center cursor-pointer hover:scale-105 transition-transform duration-300 ease-in-out"
										onClick={() => undoAttach(index)}
										style={{
											transition:
												"transform 0.3s, opacity 0.3s",
										}}
									>
										<span>{fileName}</span>
										<button
											className="text-gray-500 ml-2"
											onClick={(e) => {
												e.stopPropagation();
												undoAttach(index);
											}}
										>
											x
										</button>
									</div>
								))}
								<div
									className="items-center border-2 border-dashed border-gray-300 rounded flex cursor-pointer hover:border-blue-500 px-2"
									onClick={() =>
										document
											.getElementById("addFile")
											.click()
									}
								>
									<input
										type="file"
										onChange={handleAttachment}
										className="hidden"
										multiple
										id="addFile"
									/>
									<label
										htmlFor="addFile"
										className="cursor-pointer"
									>
										+
									</label>
								</div>
							</div>
						</div>
					) : (
						<div
							className="mb-2 p-4 border-2 border-dashed border-gray-300 rounded w-full text-center cursor-pointer hover:border-blue-500"
							onClick={() =>
								document.getElementById("fileUpload").click()
							}
						>
							<input
								type="file"
								onChange={handleAttachment}
								className="hidden"
								multiple
								id="fileUpload"
							/>
							<label
								htmlFor="fileUpload"
								className="cursor-pointer"
							>
								Drag & drop files, or click to browse
							</label>
						</div>
					)}
					<button onClick={handleSend} className="button w-full">
						Send ✈️
					</button>
				</>
			) : (
				<button
					onClick={onLogin}
					className="button w-full"
					title="Please login to send"
				>
					Login 🚀
				</button>
			)}
		</div>
	);
}

// Expose ChatInput globally
window.ChatInput = ChatInput;
