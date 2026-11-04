using Microsoft.UI.Xaml.Controls;
namespace LEIAWatcher.App.Views;
public sealed partial class HistoryPage:Page{public HistoryPage(){InitializeComponent();DataContext=App.State;Loaded+=async(s,e)=>await App.State.LoadHistoryAsync();}}
