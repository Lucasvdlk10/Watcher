using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
namespace LEIAWatcher.App.Views;
public sealed partial class FilesPage:Page{public FilesPage(){InitializeComponent();DataContext=App.State;Loaded+=async(s,e)=>await App.State.LoadFilesAsync();}async void FilterChanged(object sender,object e){if(StatusFilter==null||ExtensionFilter==null||OriginFilter==null)return; App.State.FilterExtension=ExtensionFilter.Text;App.State.FilterStatus=(StatusFilter.SelectedItem as ComboBoxItem)?.Content?.ToString()=="Todos"?"":(StatusFilter.SelectedItem as ComboBoxItem)?.Content?.ToString()??"";App.State.FilterOrigin=(OriginFilter.SelectedItem as ComboBoxItem)?.Content?.ToString()??"Todos";App.State.FilePage=0;await App.State.LoadFilesAsync();}}
