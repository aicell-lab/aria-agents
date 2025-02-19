function MainLayout({ sidebar, content, artifacts }) {
    return (
        <div className="flex-1 flex">
            {sidebar}
            <div className={`main-panel ${artifacts ? 'main-panel-artifacts' : 'main-panel-full'}`}>
                {content}
            </div>
            {artifacts}
        </div>
    );
}

window.MainLayout = MainLayout;
