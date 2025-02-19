const { ShareDialog, InfoDialog } = window;

function DialogManager({ 
    showShareDialog,
    alertContent,
    shareUrl,
    onShare,
    onCloseShare,
    onCloseAlert 
}) {
    return (
        <>
            {showShareDialog && (
                <ShareDialog 
                    shareUrl={shareUrl}
                    onConfirm={onShare}
                    onClose={onCloseShare}
                />
            )}
            {alertContent && (
                <InfoDialog 
                    content={alertContent}
                    onClose={onCloseAlert}
                />
            )}
        </>
    );
}

window.DialogManager = DialogManager;
