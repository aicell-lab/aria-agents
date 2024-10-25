function ProfileDialog({ userProfile, onClose, onSave }) {
	const [profile, setProfile] = useState(userProfile);

	const handleChange = (e) => {
		const { name, value } = e.target;
		setProfile({ ...profile, [name]: value });
	};

	const handleSave = () => {
		onSave(profile);
	};

	return (
		<div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center">
			<div className="bg-white p-6 rounded shadow-lg w-96">
				<h2 className="text-2xl mb-4">Edit Profile</h2>
				<div className="mb-4">
					<label className="block text-gray-700">Name</label>
					<input
						type="text"
						name="name"
						value={profile.name}
						onChange={handleChange}
						className="w-full p-2 border border-gray-300 rounded"
					/>
				</div>
				<div className="mb-4">
					<label className="block text-gray-700">Occupation</label>
					<input
						type="text"
						name="occupation"
						value={profile.occupation}
						onChange={handleChange}
						className="w-full p-2 border border-gray-300 rounded"
					/>
				</div>
				<div className="mb-4">
					<label className="block text-gray-700">Background</label>
					<input
						type="text"
						name="background"
						value={profile.background}
						onChange={handleChange}
						className="w-full p-2 border border-gray-300 rounded"
					/>
				</div>
				<div className="flex justify-end">
					<button
						onClick={onClose}
						className="button bg-gray-500 mr-2"
					>
						Cancel
					</button>
					<button onClick={handleSave} className="button">
						Save
					</button>
				</div>
			</div>
		</div>
	);
}

// Expose ProfileDialog globally
window.ProfileDialog = ProfileDialog;
