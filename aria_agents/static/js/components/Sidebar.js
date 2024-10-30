function Sidebar({ isOpen, onClose, prevChats, onSelectChat, isLoggedIn }) {
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
						onClick={() => onSelectChat({"conversations": []})}
					>
						+
					</button>
				}
				{prevChats.map((chatObject) => (
					<button
						key={chatObject.id}
						className="block w-full text-left p-2 text-gray-700 hover:bg-gray-200 rounded"
						onClick={() => onSelectChat(chatObject)}
					>
						{chatObject.name}
					</button>
				))}
			</div>
		</div>
	);
}

// Expose Sidebar globally
window.Sidebar = Sidebar;