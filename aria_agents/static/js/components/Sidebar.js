function Sidebar({ onLogin, onEditProfile }) {
    return (
        <div className="sidebar">
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
            <button onClick={onLogin} className="w-full mt-4 bg-blue-600 text-white py-2 px-4 rounded transition duration-300 ease-in-out transform hover:scale-105">
                Login 🚀
            </button>
        </div>
    );
}

// Expose Sidebar globally
window.Sidebar = Sidebar;
