function AlertDialog({ children }) {
    return (
      <>
          <div className="fixed inset-0 bg-black bg-opacity-50 z-40">
            <div className="flex items-center justify-center h-full">
              <div className="bg-white p-6 rounded shadow-lg max-w-md w-full">
                {children}
              </div>
            </div>
          </div>
      </>
    );
  };

window.AlertDialog = AlertDialog; 

function ShareDialog({onClose, shareUrl}) {
    const [showFirstDialog, setShowFirstDialog] = useState(true);
    const [showSecondDialog, setShowSecondDialog] = useState(false);

    return (
        <>
            {showFirstDialog && (
                <AlertDialog>
                    <p className="text-lg">
                        Share chat? This will allow anyone with the link to read it.
                    </p>
                    <div className="flex justify-center mt-6">
                        <button
                            className="px-4 py-2 mr-3 text-white bg-blue-500 rounded-lg hover:bg-blue-600"
                            onClick={() => {
                                setShowFirstDialog(false);
                                setShowSecondDialog(true);
                            }}
                        >
                            Yes
                        </button>
                        <button
                            className="px-4 py-2 text-gray-700 bg-gray-300 rounded-lg hover:bg-gray-400"
                            onClick={onClose}
                        >
                            No
                        </button>
                    </div>
                </AlertDialog>
            )}
            
            {showSecondDialog && (
                <AlertDialog>
                    <p className="text-lg justify-center center-text text-center">
                        Anyone with the link can view the chat.
                    </p>
                    <div className="flex flex-row mt-6 space-y-2">
                        <input
                            className="width-fill px-4 h-12 mr-2 py-2 text-gray-700 border-2 border-gray-300 rounded-lg focus:outline-none focus:border-blue-500"
                            readOnly
                            value={shareUrl}
                        />
                        <button
                            className="width-fill px-4 py-2 h-12 text-white bg-blue-500 mt-0 rounded-lg hover:bg-blue-600"
                            onClick={() => navigator.clipboard.writeText(shareUrl)}
                        >
                            Copy Link
                        </button>
                    </div>
                    <div className="flex justify-center">
                        <button
                            className="px-4 py-2 mt-4 text-gray-700 bg-gray-300 rounded-lg hover:bg-gray-400"
                            onClick={() => {
                                setShowFirstDialog(true);
                                setShowSecondDialog(false);
                                onClose();
                            }}
                        >
                            OK
                        </button>
                    </div>
                </AlertDialog>
            )}
        </>
    );
}

window.ShareDialog = ShareDialog;

function InfoDialog({onClose, content}) {
    return (
        <>
            <AlertDialog>
                <p className="text-lg justify-center center-text text-center">
                    {content}
                </p>
                <div className="flex justify-center">
                    <button
                        className="px-4 py-2 mt-4 text-gray-700 bg-gray-300 rounded-lg hover:bg-gray-400"
                        onClick={onClose}
                    >
                        OK
                    </button>
                </div>
            </AlertDialog>
        </>
    );
}

window.InfoDialog = InfoDialog;