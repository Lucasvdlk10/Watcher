using LEIAWatcher.Domain;
using Xunit;

namespace LEIAWatcher.UnitTests;

public sealed class WindowLifetimePolicyTests
{
    [Fact]
    public void User_close_hides_window_and_keeps_process_alive()
    {
        var policy = new WindowLifetimePolicy();
        Assert.Equal(WindowCloseAction.HideToTray, policy.OnWindowCloseRequested());
        Assert.False(policy.IsExitRequested);
    }

    [Fact]
    public void Tray_exit_allows_real_process_shutdown()
    {
        var policy = new WindowLifetimePolicy();
        policy.RequestExit();
        Assert.True(policy.IsExitRequested);
        Assert.Equal(WindowCloseAction.Exit, policy.OnWindowCloseRequested());
    }
}
