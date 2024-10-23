function Sidebar({ isOpen, onClose, onEditProfile }) {
    return (
        <div className={`hidden md:block sidebar z-50 ${isOpen? 'open' : ''}`}>
            <button onClick={onClose} className="text-2xl  mt-2 ml-2 p-2 md:hidden text-gray-600 hover:text-gray-900">X</button>
            <div className="text-xl font-bold mb-4">Aria Agents</div>
            <div className="mb-4">
                <button className="w-full text-left py-2 px-4 rounded hover:bg-gray-200">🏠 Home</button>
                <button className="w-full text-left py-2 px-4 rounded hover:bg-gray-200">🔍 Discover</button>
                <button className="w-full text-left py-2 px-4 rounded hover:bg-gray-200">📚 Library</button>
            </div>
            <div className="mt-auto">
                <div className="flex items-center p-2 cursor-pointer hover:bg-gray-200 rounded" onClick={onEditProfile}>
                    <span>👤 User Profile</span>
                </div>
            </div>
        </div>
    );
}

// Expose Sidebar globally
window.Sidebar = Sidebar;
