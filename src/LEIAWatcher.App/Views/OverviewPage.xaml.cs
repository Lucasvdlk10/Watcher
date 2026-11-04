using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
namespace LEIAWatcher.App.Views;
public sealed partial class OverviewPage:Page {
 public OverviewPage(){InitializeComponent();DataContext=App.State;}
 void ActivitySizeChanged(object sender,SizeChangedEventArgs e){ActivityLayout.MinItemWidth=Math.Max(44,(e.NewSize.Width-8)/7);}
 void OpenFolders(object s,RoutedEventArgs e)=>App.Main?.Show("folders");
 void OpenFiles(object s,RoutedEventArgs e)=>App.Main?.Show("files");
}
