using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using Windows.Storage.Pickers;
namespace LEIAWatcher.App.Views;
public sealed partial class FoldersPage:Page {
 public FoldersPage(){InitializeComponent();DataContext=App.State;}
 async void PickFolder(object s,RoutedEventArgs e){try{
  var picker=new FolderPicker();picker.FileTypeFilter.Add("*");
  var hwnd=WinRT.Interop.WindowNative.GetWindowHandle(App.Main!);
  WinRT.Interop.InitializeWithWindow.Initialize(picker,hwnd);
  var result=await picker.PickSingleFolderAsync();if(result!=null)App.State.NewFolderPath=result.Path;
 }catch(Exception ex){App.State.Message=ex.Message;}}
 async void PauseClicked(object s,RoutedEventArgs e){if(s is Button b && b.Tag is string id)await App.State.PauseRootAsync(id);}
 async void ResumeClicked(object s,RoutedEventArgs e){if(s is Button b && b.Tag is string id)await App.State.ResumeRootAsync(id);}
 void ModeChanged(object s,SelectionChangedEventArgs e){if(ModePicker?.SelectedItem is ComboBoxItem c)App.State.AddMode=c.Tag?.ToString()??"TRACK_ONLY";}
 void ProfileChanged(object s,SelectionChangedEventArgs e){if(ProfilePicker?.SelectedItem is ComboBoxItem c)App.State.AddProfile=c.Tag?.ToString()??"TYPE";}
}
