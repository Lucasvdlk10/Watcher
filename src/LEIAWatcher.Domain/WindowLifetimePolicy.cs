namespace LEIAWatcher.Domain;

public enum WindowCloseAction
{
    HideToTray,
    Exit
}

public sealed class WindowLifetimePolicy
{
    public bool IsExitRequested { get; private set; }

    public WindowCloseAction OnWindowCloseRequested() =>
        IsExitRequested ? WindowCloseAction.Exit : WindowCloseAction.HideToTray;

    public void RequestExit() => IsExitRequested = true;
}
