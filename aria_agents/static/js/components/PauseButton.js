function PauseButton({ pause }) {
    return (
        <div className="flex justify-center items-center h-full">
            <button onClick={pause} className="bg-red-500 hover:bg-red-700 text-white font-bold py-2 px-4 rounded">
                Pause
            </button>
        </div>
    );
}

window.PauseButton = PauseButton;