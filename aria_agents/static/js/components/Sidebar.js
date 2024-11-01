function Sidebar({ isOpen, onClose, prevChats, onSelectChat, onDeleteChat, isLoggedIn }) {
	return (
		<div className={`hidden md:block sidebar z-50 ${isOpen ? "open" : ""}`}>
			<button
				onClick={onClose}
				className="text-2xl mt-2 ml-2 p-2 md:hidden text-gray-600 hover:text-gray-900"
			>
				X
			</button>
			<div className="text-xl font-bold mb-4">Aria Agents</div>
			<div className="mb-4">
				{isLoggedIn &&
					<button
						className="block w-full text-left p-2 text-gray-700 hover:bg-gray-200 rounded"
						onClick={() => onSelectChat({})}
					>
						New chat 🪶
					</button>
				}
				<div className="max-h-[calc(100vh-8rem)] overflow-y-auto">
					{prevChats.map((chatObject) => (
						<div key={chatObject.id} className="flex w-full items-center hover:bg-gray-200 rounded">
							<button
								className="flex-1 text-left p-2 text-gray-700 overflow-hidden whitespace-nowrap text-ellipsis"
								onClick={() => onSelectChat(chatObject)}
							>
								{chatObject.name}
							</button>
							<button
								className="ml-2 mr-4 text-gray-500 hover:text-gray-700"
								onClick={() => onDeleteChat(chatObject)}
							>
								X
							</button>
						</div>

					))}
				</div>
			</div>
		</div>
	);
}

// Expose Sidebar globally
window.Sidebar = Sidebar;