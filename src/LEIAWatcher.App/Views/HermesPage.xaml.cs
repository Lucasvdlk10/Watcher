using Microsoft.UI.Xaml.Controls;
namespace LEIAWatcher.App.Views;
public sealed partial class HermesPage:Page { public HermesPage(){ InitializeComponent(); DataContext=App.State; } }
